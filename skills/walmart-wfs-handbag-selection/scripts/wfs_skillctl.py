#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import importlib
import json
import sqlite3
import subprocess
import sys
from collections import Counter
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

from audit_state import audit
from runtime_common import SkillRuntimeError, build_context
from validate_config import validate


BEIJING = ZoneInfo("Asia/Shanghai")
PAUSE_START = time(9, 45)
PAUSE_END = time(13, 0)


def operations_paused(context: Dict[str, Any]) -> bool:
    wrapper = context.get("wrapper") or {}
    incremental = json.loads(context["incremental_config"].read_text(encoding="utf-8"))
    if "operations_paused" in wrapper:
        return wrapper.get("operations_paused") is True
    return incremental.get("operations_paused") is True


def blocked_for_pause(command: str) -> int:
    print(json.dumps({
        "status": "BLOCKED",
        "reason": "OPERATIONS_PAUSED",
        "command": command,
        "resume_phrase": "恢复运营监督",
    }, ensure_ascii=False, indent=2))
    return 2


def readonly_validation(context: Dict[str, Any], run_date: str, now: Optional[datetime] = None) -> int:
    now = now or datetime.now(BEIJING)
    today = now.date().isoformat()
    requested = run_date or today
    if requested != today or now.weekday() >= 5 or not (PAUSE_START <= now.time() <= PAUSE_END):
        print(json.dumps({
            "status": "BLOCKED",
            "reason": "OUTSIDE_READONLY_VALIDATION_WINDOW",
            "allowed": "工作日 09:45-13:00 Asia/Shanghai",
            "now": now.isoformat(),
        }, ensure_ascii=False, indent=2))
        return 2
    marker = context["output_root"] / ".pause-readonly-validation" / f"{today}.json"
    if marker.exists():
        payload = json.loads(marker.read_text(encoding="utf-8"))
        payload["status"] = "ALREADY_VALIDATED"
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    code = run_controller(context, "smoke", today, True)
    if code != 0:
        return code
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps({
        "status": "SUCCESS",
        "mode": "PAUSED_READONLY_VALIDATION",
        "run_date": today,
        "validated_at": now.isoformat(),
        "feishu_sent": False,
        "operations_created": False,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(json.loads(marker.read_text(encoding="utf-8")), ensure_ascii=False, indent=2))
    return 0


def latest_smoke(context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    database = context["ledger_database"]
    if not database.exists():
        return None
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        row = connection.execute(
            "SELECT run_id,run_date,status,run_dir,report_hash,error FROM runs "
            "WHERE mode='TECHNICAL_SMOKE_TEST' ORDER BY updated_at DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def keyword_gate(context: Dict[str, Any]) -> Dict[str, Any]:
    with context["keyword_master"].open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    validated = [row for row in rows if str(row.get("validation_status") or "").upper() == "VALIDATED"]
    pools = Counter(row.get("pool", "") for row in validated)
    pilots = [row for row in validated if str(row.get("pilot_selected") or "").upper() == "YES"]
    return {
        "validated_total": len(validated),
        "validated_pools": dict(pools),
        "validated_pilots": len(pilots),
        "passed": len(validated) >= 60 and pools.get("MAINSTREAM", 0) >= 30 and pools.get("STYLE", 0) >= 30 and len(pilots) == 10,
    }


def run_controller(context: Dict[str, Any], command: str, run_date: str, dry_run: bool) -> int:
    controller = context["runner_root"] / "scripts" / "run_wfs_handbag_incremental.py"
    runner_python = context["runner_root"] / ".venv" / "bin" / "python"
    python_bin = runner_python if runner_python.exists() else Path(sys.executable)
    argv = [str(python_bin), str(controller), command, "--config", str(context["incremental_config"])]
    if run_date:
        argv.extend(["--date", run_date])
    if dry_run:
        argv.append("--dry-run")
    process = subprocess.run(argv, cwd=context["runner_root"])
    return process.returncode


def feishu_test(context: Dict[str, Any], run_date: str, confirm_send: bool) -> int:
    smoke = latest_smoke(context)
    if not smoke or smoke.get("status") != "SUCCESS":
        print(json.dumps({"status": "BLOCKED", "reason": "SMOKE_TEST_NOT_PASSED"}, ensure_ascii=False, indent=2))
        return 2
    if run_date and smoke.get("run_date") != run_date:
        print(json.dumps({"status": "BLOCKED", "reason": "REQUESTED_DATE_HAS_NO_SUCCESSFUL_SMOKE"}, ensure_ascii=False, indent=2))
        return 2
    report_path = Path(smoke["run_dir"]) / "daily_report.json"
    if not report_path.exists():
        print(json.dumps({"status": "BLOCKED", "reason": "SMOKE_REPORT_MISSING"}, ensure_ascii=False, indent=2))
        return 2
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("mode") != "TECHNICAL_SMOKE_TEST" or report.get("status") != "SUCCESS":
        print(json.dumps({"status": "BLOCKED", "reason": "INVALID_SMOKE_REPORT"}, ensure_ascii=False, indent=2))
        return 2

    scripts = context["runner_root"] / "scripts"
    sys.path.insert(0, str(scripts))
    module = importlib.import_module("wfs_handbag_incremental")
    runtime = module.load_runtime(context["incremental_config"])
    result = module.deliver_feishu(runtime, report, dry_run=not confirm_send)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result.get("status") not in {"FAILED"} else 2


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="WFS 女包选品 Skill 控制入口")
    result.add_argument("command", choices=["doctor", "status", "smoke", "daily", "feishu-test", "validate-readonly"])
    result.add_argument("--config", type=Path, required=True)
    result.add_argument("--date", default="")
    result.add_argument("--dry-run", action="store_true")
    result.add_argument("--confirm-send", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    if args.date:
        date.fromisoformat(args.date)
    context = build_context(config_path=args.config)
    validation = validate(context)

    if args.command == "doctor":
        print(json.dumps(validation, ensure_ascii=False, indent=2))
        return 0 if validation["status"] == "PASS" else 2
    if validation["status"] != "PASS":
        print(json.dumps(validation, ensure_ascii=False, indent=2))
        return 2
    if args.command == "status":
        status = audit(context)
        status["operations_paused"] = operations_paused(context)
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return 0
    paused = operations_paused(context)
    if args.command == "validate-readonly":
        if not paused:
            print(json.dumps({"status": "BLOCKED", "reason": "OPERATIONS_NOT_PAUSED"}, ensure_ascii=False, indent=2))
            return 2
        return readonly_validation(context, args.date)
    if paused:
        return blocked_for_pause(args.command)
    if args.command == "smoke":
        return run_controller(context, "smoke", args.date, args.dry_run)
    if args.command == "daily":
        if not args.dry_run:
            smoke = latest_smoke(context)
            gate = keyword_gate(context)
            reasons = []
            if not smoke or smoke.get("status") != "SUCCESS":
                reasons.append("SMOKE_TEST_NOT_PASSED")
            if not gate["passed"]:
                reasons.append("KEYWORD_GATE_NOT_PASSED")
            if reasons:
                print(json.dumps({"status": "BLOCKED", "reasons": reasons, "keyword_gate": gate}, ensure_ascii=False, indent=2))
                return 2
        return run_controller(context, "daily", args.date, args.dry_run)
    return feishu_test(context, args.date, args.confirm_send)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (SkillRuntimeError, OSError, ValueError, sqlite3.Error) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)
