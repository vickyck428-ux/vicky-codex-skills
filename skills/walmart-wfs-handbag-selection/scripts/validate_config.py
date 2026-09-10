#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List

from runtime_common import SKILL_ROOT, SkillRuntimeError, build_context, is_within, read_json, runner_path


BANNED_TERMS = (
    "backpack", "rucksack", "bookbag", "laptop", "computer", "briefcase", "lunch bag",
    "lunch box", "lunch tote", "cooler bag", "cooler tote", "duffel", "luggage", "suitcase", "diaper bag", "makeup bag",
    "cosmetic bag", "toiletry bag", "storage bag", "organizer bag", "gym bag",
)
DIRECT_HANDBAG_TERMS = ("purse", "handbag")
HANDBAG_FORM_TERMS = (
    "shoulder bag", "crossbody bag", "hobo bag", "tote bag", "work bag", "satchel",
    "clutch", "baguette bag", "bucket bag", "wristlet", "top handle bag", "crescent bag",
    "underarm bag", "evening bag", "mini bag", "concert bag", "ita bag", "display bag",
    "bow bag", "shaped bag",
)
SECRET_FRAGMENTS = ("app_secret", "cookie", "password", "private_key", "secret", "token", "owneropenid", "user_id")


def walk_keys(value: Any, prefix: str = "") -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            yield path
            yield from walk_keys(child, path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_keys(child, f"{prefix}[{index}]")


def keyword_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def is_strict_womens_handbag_keyword(value: Any) -> bool:
    keyword = str(value or "").strip().lower()
    if not keyword or any(term in keyword for term in BANNED_TERMS):
        return False
    return any(term in keyword for term in DIRECT_HANDBAG_TERMS + HANDBAG_FORM_TERMS)


def validate(context: Dict[str, Any], allow_missing_runtime: bool = False) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []
    checks: Dict[str, Any] = {}

    wrapper = context["wrapper"]
    if wrapper:
        if wrapper.get("schema_version") != 1:
            errors.append("schema_version 必须为 1。")
        if wrapper.get("no_marketplace_mutations") is not True:
            errors.append("no_marketplace_mutations 必须为 true。")
        if wrapper.get("schedule_enabled") is not False:
            errors.append("封装/迁移阶段 schedule_enabled 必须为 false。")
        if not isinstance(wrapper.get("operations_paused"), bool):
            errors.append("operations_paused 必须显式为 true 或 false。")
        markets = wrapper.get("markets") or {}
        if str((markets.get("US") or {}).get("postal_code")) != "10001":
            errors.append("美国配送邮编必须为 10001。")
        if str((markets.get("CA") or {}).get("postal_code")) != "M5V 2T6":
            errors.append("加拿大核验邮编必须为 M5V 2T6。")
        secret_keys = [key for key in walk_keys(wrapper) if any(fragment in key.lower() for fragment in SECRET_FRAGMENTS)]
        if secret_keys:
            errors.append("Skill 外部路径配置不得内嵌账号或密钥字段：" + ",".join(secret_keys))

    required_files = {
        "runner": context["runner_root"],
        "incremental_config": context["incremental_config"],
        "selection_config": context["selection_config"],
        "keyword_master": context["keyword_master"],
        "controller": context["runner_root"] / "scripts" / "run_wfs_handbag_incremental.py",
        "crawler_entry": context["runner_root"] / "lc-amazon-data-crawl.sh",
        "crawl_skill": context["lc_amazon_data_crawl_skill"] / "SKILL.md",
    }
    missing = [name for name, path in required_files.items() if not path.exists()]
    if missing and not allow_missing_runtime:
        errors.append("缺少运行依赖：" + ",".join(missing))
    elif missing:
        warnings.append("模板尚未配置运行依赖：" + ",".join(missing))
    checks["required_files"] = {name: path.exists() for name, path in required_files.items()}

    machine_checks = {
        "python": Path(sys.executable).exists(),
        "runner_python": (context["runner_root"] / ".venv" / "bin" / "python").exists(),
        "lark_cli": shutil.which("lark-cli") is not None,
        "chrome": any(path.exists() for path in (
            Path("/Applications/Google Chrome.app"),
            Path("/Applications/Google Chrome for Testing.app"),
        )),
        "cdp_browser_script": (context["lc_amazon_data_crawl_skill"] / "scripts" / "start_cdp_browser.py").exists(),
        "sellersprite_check_script": (context["lc_amazon_data_crawl_skill"] / "scripts" / "run_sellersprite_check.py").exists(),
        "feishu_config": context["feishu_integrations_file"].exists(),
    }
    checks["machine"] = machine_checks
    for name, present in machine_checks.items():
        if not present:
            warnings.append(f"Mac Mini 启用前仍需配置：{name}")

    runner_shell = context["runner_root"] / "lc-amazon-data-crawl.sh"
    if runner_shell.exists():
        runner_text = runner_shell.read_text(encoding="utf-8", errors="ignore")
        if "cdp-browser-start" not in runner_text or "sellersprite-check" not in runner_text:
            warnings.append("当前 runner 仍是旧浏览器接口；迁移时应由现有 lc-amazon-data-crawl setup_runner.sh 更新。")

    if context["incremental_config"].exists() and context["selection_config"].exists():
        incremental = read_json(context["incremental_config"])
        selection = read_json(context["selection_config"])
        if not isinstance(incremental.get("operations_paused"), bool):
            errors.append("WFS 运行配置必须显式包含 operations_paused。")
        if incremental.get("no_marketplace_mutations") is not True or selection.get("no_marketplace_mutations") is not True:
            errors.append("现有 WFS 配置必须保持 no_marketplace_mutations=true。")
        if incremental.get("smoke_keywords") != ["leather shoulder bag for women", "y2k shoulder bag"]:
            errors.append("技术试跑词必须固定为两个指定关键词。")
        if int(incremental.get("smoke_pages_per_keyword") or 0) != 3:
            errors.append("技术试跑必须每词3页。")
        if int(incremental.get("daily_keywords_per_pool") or 0) != 2:
            errors.append("正式日跑必须每池2词。")
        if int(incremental.get("keyword_cooldown_days") or 0) != 28:
            errors.append("关键词冷却必须为28天。")
        if float(incremental.get("required_field_coverage") or 0) != 0.8:
            errors.append("字段覆盖率门禁必须为80%。")
        if str(incremental.get("amazon_delivery_postal_code")) != "10001":
            errors.append("Amazon 美国配送邮编必须为10001。")
        node_path = runner_path(incremental.get("artifact_node_bin"), context["runner_root"]) if incremental.get("artifact_node_bin") else None
        checks["machine"]["node"] = bool(node_path and node_path.exists())
        if not checks["machine"]["node"]:
            warnings.append("Mac Mini 启用前仍需配置：node/artifact runtime")
        thresholds = selection.get("core_thresholds") or {}
        expected = {"amazon_price_min": 25, "amazon_sales_30d_min": 150, "amazon_sales_30d_max": 600}
        if any(float(thresholds.get(key) or -1) != value for key, value in expected.items()):
            errors.append("核心价格/月销门槛被修改。")
        if int(selection.get("formal_keyword_min") or 0) < 60 or int(selection.get("formal_keyword_min_per_pool") or 0) < 30:
            errors.append("正式关键词门禁不得低于总数60、每池30。")
        if int(selection.get("pilot_keyword_count") or 0) != 10:
            errors.append("深度试跑词必须为10个。")
        if float(selection.get("benchmark_candidate_share_max") or 0) != 0.2:
            errors.append("BENCHMARK 候选上限必须为20%。")
        if set(selection.get("walmart_markets") or []) != {"US", "CA"}:
            errors.append("Walmart 必须分别配置 US 和 CA。")

        if wrapper:
            configured_selection = runner_path(incremental.get("selection_config_file"), context["runner_root"])
            configured_database = runner_path(incremental.get("database_file"), context["runner_root"])
            configured_output = runner_path(incremental.get("output_root"), context["runner_root"])
            configured_keywords = runner_path(selection.get("keyword_master_file"), context["runner_root"])
            path_pairs = (
                ("selection_config", configured_selection, context["selection_config"]),
                ("ledger_database", configured_database, context["ledger_database"]),
                ("output_root", configured_output, context["output_root"]),
                ("keyword_master", configured_keywords, context["keyword_master"]),
            )
            for name, actual, declared in path_pairs:
                if actual != declared:
                    errors.append(f"{name} 与现有控制器配置不一致：{actual} != {declared}")

    rows = keyword_rows(context["keyword_master"])
    if rows:
        pools = Counter(row.get("pool", "") for row in rows)
        unique = {row.get("keyword", "").strip().lower() for row in rows}
        pilots = [row for row in rows if row.get("pilot_selected", "").upper() == "YES"]
        banned = [row.get("keyword", "") for row in rows if any(term in row.get("keyword", "").lower() for term in BANNED_TERMS)]
        off_topic = [row.get("keyword", "") for row in rows if not is_strict_womens_handbag_keyword(row.get("keyword"))]
        if len(rows) != 80 or len(unique) != 80:
            errors.append(f"关键词模板必须为80个唯一词，当前 {len(rows)}/{len(unique)}。")
        if pools != Counter({"MAINSTREAM": 40, "STYLE": 40}):
            errors.append(f"关键词双池必须为40+40，当前 {dict(pools)}。")
        if len(pilots) != 10 or Counter(row.get("pool", "") for row in pilots) != Counter({"MAINSTREAM": 5, "STYLE": 5}):
            errors.append("深度试跑词必须主流5个、风格5个。")
        if banned:
            errors.append("关键词库含排除词：" + ",".join(banned))
        if off_topic:
            errors.append("关键词库含非明确女包词：" + ",".join(off_topic))
        checks["keywords"] = {"total": len(rows), "unique": len(unique), "pools": dict(pools), "pilots": len(pilots)}

    for name in ("ledger_database", "output_root", "keyword_master"):
        if is_within(context[name], SKILL_ROOT):
            errors.append(f"运行数据不得位于 Skill 目录内：{name}")

    hardcoded = []
    users_prefix = "/" + "Users" + "/"
    for path in SKILL_ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".md", ".json", ".yaml", ".yml", ".py", ".csv"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if re.search(re.escape(users_prefix) + r"[^/$\s]+", text):
                hardcoded.append(str(path.relative_to(SKILL_ROOT)))
    if hardcoded:
        errors.append("Skill 含当前 Mac 用户绝对路径：" + ",".join(hardcoded))

    return {"status": "PASS" if not errors else "FAIL", "errors": errors, "warnings": warnings, "checks": checks}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="检查 WFS Skill 外部配置与固定门禁")
    group = result.add_mutually_exclusive_group(required=True)
    group.add_argument("--config", type=Path)
    group.add_argument("--runner-root", type=Path)
    result.add_argument("--allow-missing-runtime", action="store_true")
    result.add_argument("--json", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    context = build_context(config_path=args.config, runner_root=args.runner_root)
    result = validate(context, allow_missing_runtime=args.allow_missing_runtime)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["status"])
        for item in result["errors"]:
            print(f"ERROR: {item}")
        for item in result["warnings"]:
            print(f"WARNING: {item}")
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (SkillRuntimeError, OSError, ValueError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)
