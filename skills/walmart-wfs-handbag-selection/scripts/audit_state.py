#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from runtime_common import SkillRuntimeError, build_context, read_json


BANNED_TERMS = (
    "backpack", "rucksack", "bookbag", "laptop", "computer", "briefcase", "lunch bag",
    "lunch box", "lunch tote", "cooler bag", "cooler tote", "duffel", "luggage", "suitcase", "diaper bag", "makeup bag",
    "cosmetic bag", "toiletry bag", "storage bag", "organizer bag", "gym bag",
)


def read_keywords(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def database_audit(path: Path) -> Dict[str, Any]:
    result: Dict[str, Any] = {"exists": path.exists(), "path": str(path)}
    if not path.exists():
        return result
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        counts = {}
        for table in ("runs", "run_keywords", "products", "observations", "deliveries"):
            counts[table] = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] if table in tables else None
        latest = None
        latest_smoke = None
        if "runs" in tables:
            row = connection.execute(
                "SELECT run_id,run_date,mode,status,requested_pages,completed_pages,raw_records,unique_asins,report_hash,error,run_dir "
                "FROM runs ORDER BY updated_at DESC LIMIT 1"
            ).fetchone()
            latest = dict(row) if row else None
            row = connection.execute(
                "SELECT run_id,run_date,mode,status,requested_pages,completed_pages,raw_records,unique_asins,report_hash,error,run_dir "
                "FROM runs WHERE mode='TECHNICAL_SMOKE_TEST' ORDER BY updated_at DESC LIMIT 1"
            ).fetchone()
            latest_smoke = dict(row) if row else None
        result.update({"table_counts": counts, "latest_run": latest, "latest_smoke": latest_smoke})
    finally:
        connection.close()
    return result


def audit(context: Dict[str, Any]) -> Dict[str, Any]:
    incremental = read_json(context["incremental_config"])
    selection = read_json(context["selection_config"])
    rows = read_keywords(context["keyword_master"])
    pool_counts = Counter(str(row.get("pool") or "") for row in rows)
    validation_counts = Counter(str(row.get("validation_status") or "") for row in rows)
    validated_rows = [row for row in rows if str(row.get("validation_status") or "").upper() == "VALIDATED"]
    validated_pools = Counter(str(row.get("pool") or "") for row in validated_rows)
    validated_pilots = [row for row in validated_rows if str(row.get("pilot_selected") or "").upper() == "YES"]
    banned = [row.get("keyword", "") for row in rows if any(term in row.get("keyword", "").lower() for term in BANNED_TERMS)]
    pilots = [row.get("keyword", "") for row in rows if str(row.get("pilot_selected") or "").upper() == "YES"]
    ledger = database_audit(context["ledger_database"])

    smoke = ledger.get("latest_smoke") or {}
    smoke_report_path = Path(smoke.get("run_dir") or "") / "daily_report.json" if smoke.get("run_dir") else None
    smoke_report = read_json(smoke_report_path) if smoke_report_path and smoke_report_path.exists() else {}
    latest_status = smoke_report.get("status") or smoke.get("status")
    requested_pages = int(smoke.get("requested_pages") or 0)
    completed_pages = int(smoke_report.get("completed_pages") or smoke.get("completed_pages") or 0)
    raw_records = int(smoke_report.get("raw_record_count") or smoke.get("raw_records") or 0)
    unique_asins = int(smoke_report.get("unique_asin_count") or smoke.get("unique_asins") or 0)
    blockers = smoke_report.get("blocked_reasons") or ([smoke.get("error")] if smoke.get("error") else [])

    return {
        "runner_root": str(context["runner_root"]),
        "assets": {
            "incremental_config": str(context["incremental_config"]),
            "selection_config": str(context["selection_config"]),
            "keyword_master": str(context["keyword_master"]),
            "ledger_database": str(context["ledger_database"]),
            "output_root": str(context["output_root"]),
        },
        "keywords": {
            "total": len(rows),
            "unique": len({str(row.get("keyword") or "").strip().lower() for row in rows}),
            "pool_counts": dict(pool_counts),
            "validation_counts": dict(validation_counts),
            "validated_pool_counts": dict(validated_pools),
            "validated_pilot_count": len(validated_pilots),
            "pilot_count": len(pilots),
            "pilot_keywords": pilots,
            "banned_keywords": banned,
            "metric_files": selection.get("keyword_metric_files", []),
        },
        "technical_smoke": {
            "configured_keywords": incremental.get("smoke_keywords", []),
            "pages_per_keyword": incremental.get("smoke_pages_per_keyword"),
            "status": latest_status or "NOT_RUN",
            "requested_pages": requested_pages,
            "completed_pages": completed_pages,
            "raw_records": raw_records,
            "unique_asins": unique_asins,
            "field_coverage": smoke_report.get("field_coverage") or {},
            "report_hash": smoke_report.get("report_hash") or smoke.get("report_hash"),
            "blocked_reasons": [item for item in blockers if item],
        },
        "ledger": ledger,
        "formal_daily_ready": (
            latest_status == "SUCCESS"
            and len(validated_rows) >= int(selection.get("formal_keyword_min", 60))
            and validated_pools.get("MAINSTREAM", 0) >= int(selection.get("formal_keyword_min_per_pool", 30))
            and validated_pools.get("STYLE", 0) >= int(selection.get("formal_keyword_min_per_pool", 30))
            and len(validated_pilots) == int(selection.get("pilot_keyword_count", 10))
        ),
        "marketplace_mutations_performed": False,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="只读盘点 WFS 女包选品现状")
    group = result.add_mutually_exclusive_group(required=True)
    group.add_argument("--config", type=Path)
    group.add_argument("--runner-root", type=Path)
    return result


def main() -> int:
    args = parser().parse_args()
    context = build_context(config_path=args.config, runner_root=args.runner_root)
    print(json.dumps(audit(context), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (SkillRuntimeError, sqlite3.Error, OSError, ValueError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)
