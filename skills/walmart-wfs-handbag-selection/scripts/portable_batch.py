#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
import zipfile
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo


TIMEZONE = ZoneInfo("Asia/Shanghai")
POOLS = ("MAINSTREAM", "STYLE")
TRUE_VALUES = {"1", "TRUE", "YES", "Y", "是", "通过", "PASS"}
GAP_VALUES = {"INITIAL_GAP", "STRONG_GAP", "WEAK_SUPPLY", "NEEDS_REVIEW", "SUPPLY_DENSE"}
FIELDNAMES = [
    "product_group_key", "pool", "source_keywords", "candidate_id", "supplier_detail_id",
    "supplier_url", "title", "image_ref", "variant", "asin", "parent_asin", "amazon_url",
    "price", "parent_sales_30d", "child_sales_30d", "amazon_signal_status",
    "walmart_us_status", "us_demand_evidence", "walmart_ca_status", "ca_demand_evidence",
    "fbm_gate_status", "fbm_gate_reason", "manual_wfs_choice", "listing_quality_score",
    "unit_profit_rmb", "profit_complete", "infringement_pass", "patent_pass", "supply_pass",
    "packaging_pass", "barcode_pass", "country_origin_pass", "wfs_sale_price_rmb",
    "actual_weight_lb", "length_in", "width_in", "height_in", "product_cost_rmb",
    "inbound_freight_rmb", "duty_rmb", "referral_fee_rmb", "wfs_fee_rmb",
    "storage_fee_rmb", "barcode_packaging_rmb", "clearance_reserve_rmb", "walmart_sku",
    "gtin", "observed_at", "notes",
]
BASE_REQUIRED = (
    "product_group_key", "candidate_id", "title", "image_ref", "fbm_gate_status",
    "infringement_pass", "supply_pass", "packaging_pass", "unit_profit_rmb", "profit_complete",
)
WFS_BOOLEAN_GATES = (
    "profit_complete", "infringement_pass", "patent_pass", "supply_pass", "packaging_pass",
    "barcode_pass", "country_origin_pass",
)


class PortableBatchError(RuntimeError):
    pass


def now_shanghai() -> datetime:
    return datetime.now(TIMEZONE)


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise PortableBatchError(f"缺少文件：{path.name}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PortableBatchError(f"{path.name} 顶层必须是对象")
    return value


def read_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        raise PortableBatchError(f"缺少文件：{path.name}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != FIELDNAMES:
            raise PortableBatchError("daily_results.csv 字段被修改；请重新运行 portable-init")
        return [{key: str(value or "").strip() for key, value in row.items()} for row in reader]


def is_true(value: Any) -> bool:
    return str(value or "").strip().upper() in TRUE_VALUES


def number(value: Any) -> Optional[float]:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def assigned_store(pool: str, index_in_pool: int) -> str:
    if pool == "STYLE":
        return "美国站2" if index_in_pool % 2 == 0 else "美国站1"
    return "美国站1" if index_in_pool % 2 == 0 else "美国站2"


def parse_observed_at(value: str) -> Optional[datetime]:
    text = value.strip().replace("Z", "+00:00")
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=TIMEZONE)
    return parsed.astimezone(TIMEZONE)


def wfs_gate(row: Dict[str, str], reference_time: datetime) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    price = number(row["price"])
    parent_sales = number(row["parent_sales_30d"])
    child_sales = number(row["child_sales_30d"])
    listing_score = number(row["listing_quality_score"])
    profit = number(row["unit_profit_rmb"])
    if price is None or price < 25:
        errors.append("Amazon售价低于25美元或缺失")
    if parent_sales is None or not 150 <= parent_sales <= 600:
        errors.append("父体30天销量不在150–600")
    if child_sales is None or child_sales <= 0:
        errors.append("具体子体销量未确认")
    if row["amazon_signal_status"].upper() != "PASS":
        errors.append("促销/广告/断货恢复/季节性信号未排除")
    gap = row["walmart_us_status"].upper()
    if gap != "STRONG_GAP" and not (gap == "WEAK_SUPPLY" and is_true(row["us_demand_evidence"])):
        errors.append("沃美缺少STRONG_GAP或有需求证据的WEAK_SUPPLY")
    if listing_score is None or listing_score < 80:
        errors.append("Listing质量分低于80")
    if profit is None or profit < 70:
        errors.append("预计贡献利润低于70元")
    for field in WFS_BOOLEAN_GATES:
        if not is_true(row[field]):
            errors.append(f"{field}未通过")
    observed_at = parse_observed_at(row["observed_at"])
    if observed_at is None or observed_at > reference_time or reference_time - observed_at > timedelta(days=7):
        errors.append("证据时间缺失、在未来或超过7天")
    if not row["walmart_sku"]:
        warnings.append("缺Walmart SKU，不能进入正式WFS交接")
    if not row["gtin"]:
        warnings.append("缺UPC/GTIN，不能进入正式WFS交接")
    return errors, warnings


def inspect_batch(batch_dir: Path, require_success: bool) -> Dict[str, Any]:
    metadata = read_json(batch_dir / "submission.json")
    source_rows = read_rows(batch_dir / "daily_results.csv")
    rows = [row for row in source_rows if any(row.values()) and row["product_group_key"]]
    errors: List[str] = []
    warnings: List[str] = []
    if metadata.get("mode") != "DAILY":
        errors.append("submission.json 的 mode 必须是 DAILY")
    if require_success and metadata.get("status") != "SUCCESS":
        errors.append("正式交回前 status 必须是 SUCCESS")
    run_date = str(metadata.get("run_date") or "")
    try:
        reference_time = datetime.fromisoformat(run_date).replace(tzinfo=TIMEZONE) + timedelta(hours=23, minutes=59)
    except ValueError:
        reference_time = now_shanghai()
        errors.append("run_date 必须是 YYYY-MM-DD")
    if len(rows) != 30:
        errors.append(f"必须填写30个独立产品组，当前{len(rows)}个")
    keys = [row["product_group_key"] for row in rows]
    duplicate_keys = sorted(key for key, count in Counter(keys).items() if count > 1)
    if duplicate_keys:
        errors.append("产品组ID重复：" + "、".join(duplicate_keys))
    pool_counts = Counter(row["pool"].upper() for row in rows)
    if pool_counts != Counter({"MAINSTREAM": 15, "STYLE": 15}):
        errors.append(f"候选池必须MAINSTREAM/STYLE各15，当前{dict(pool_counts)}")

    pool_indexes = Counter()
    wfs_rows = []
    fbm_pass = 0
    fbm_pending = 0
    fbm_blocked = 0
    for line_number, row in enumerate(rows, start=2):
        pool = row["pool"].upper()
        store = assigned_store(pool, pool_indexes[pool]) if pool in POOLS else ""
        pool_indexes[pool] += 1
        row["__assigned_us_store"] = store
        missing = [field for field in BASE_REQUIRED if not row[field]]
        if not row["supplier_detail_id"] and not row["supplier_url"]:
            missing.append("supplier_detail_id/supplier_url")
        if missing:
            errors.append(f"第{line_number}行缺基础字段：{','.join(missing)}")
        fbm_status = row["fbm_gate_status"].upper()
        if fbm_status == "PASS":
            fbm_pass += 1
        elif fbm_status == "BLOCKED":
            fbm_blocked += 1
        else:
            fbm_pending += 1
        if require_success and fbm_status != "PASS":
            errors.append(f"第{line_number}行FBM基础门禁不是PASS")
        for market_field in ("walmart_us_status", "walmart_ca_status"):
            value = row[market_field].upper()
            if value and value not in GAP_VALUES:
                errors.append(f"第{line_number}行{market_field}值无效：{value}")
        choice = row["manual_wfs_choice"].upper() or "SYSTEM"
        if choice not in {"SYSTEM", "WFS", "FBM"}:
            errors.append(f"第{line_number}行manual_wfs_choice值无效：{choice}")
        if choice == "WFS":
            gate_errors, gate_warnings = wfs_gate(row, reference_time)
            if gate_errors:
                errors.append(f"第{line_number}行标记WFS但门禁未通过：{'；'.join(gate_errors)}")
            warnings.extend(f"第{line_number}行：{item}" for item in gate_warnings)
            wfs_rows.append(row)

    store_counts = Counter(row["__assigned_us_store"] for row in wfs_rows)
    if len(wfs_rows) > 4:
        errors.append(f"WFS最多4款，当前{len(wfs_rows)}款")
    for store in ("美国站1", "美国站2"):
        if store_counts[store] > 2:
            errors.append(f"{store}最多2款，当前{store_counts[store]}款")
    handoff_ready = sum(bool(row["walmart_sku"] and row["gtin"]) for row in wfs_rows)
    return {
        "status": "PASS" if not errors else "BLOCKED",
        "batch_dir": str(batch_dir),
        "mode": metadata.get("mode"),
        "submission_status": metadata.get("status"),
        "run_date": run_date,
        "run_id": metadata.get("run_id"),
        "rows": len(rows),
        "pool_counts": dict(pool_counts),
        "fbm": {"pass": fbm_pass, "pending": fbm_pending, "blocked": fbm_blocked},
        "wfs": {"selected": len(wfs_rows), "by_store": dict(store_counts), "handoff_ready": handoff_ready},
        "errors": errors,
        "warnings": warnings,
        "marketplace_mutations_performed": False,
    }


def initialize(batch_dir: Path, run_date: str) -> Dict[str, Any]:
    if batch_dir.exists() and any(batch_dir.iterdir()):
        raise PortableBatchError(f"输出目录非空，拒绝覆盖：{batch_dir}")
    batch_dir.mkdir(parents=True, exist_ok=True)
    (batch_dir / "images").mkdir()
    created = now_shanghai()
    metadata = {
        "schema_version": 1,
        "mode": "DAILY",
        "status": "PENDING",
        "run_date": run_date,
        "run_id": f"macmini-wfs-{run_date.replace('-', '')}-01",
        "created_at": created.isoformat(timespec="seconds"),
        "prepared_by": "Mac mini Codex",
        "notes": "只有完成30款正式核验后才把status改为SUCCESS",
        "marketplace_mutations_performed": False,
    }
    (batch_dir / "submission.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (batch_dir / "daily_results.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        for index in range(30):
            writer.writerow({"pool": "MAINSTREAM" if index < 15 else "STYLE", "manual_wfs_choice": "SYSTEM"})
    (batch_dir / "images" / "图片放这里.txt").write_text(
        "图片放在此目录，并在daily_results.csv的image_ref填写相对路径，例如 images/GROUP-001.jpg。\n",
        encoding="utf-8",
    )
    return {"status": "CREATED", "batch_dir": str(batch_dir), "rows": 30, "pool_counts": {"MAINSTREAM": 15, "STYLE": 15}}


def write_validation(batch_dir: Path, result: Dict[str, Any]) -> None:
    (batch_dir / "validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def pack(batch_dir: Path, output: Optional[Path]) -> Dict[str, Any]:
    result = inspect_batch(batch_dir, require_success=True)
    write_validation(batch_dir, result)
    if result["status"] != "PASS":
        raise PortableBatchError("结果包未通过检查，已生成 validation.json")
    target = output or batch_dir.with_suffix(".zip")
    if target.exists():
        raise PortableBatchError(f"压缩包已存在，拒绝覆盖：{target}")
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(batch_dir.rglob("*")):
            if path.is_file():
                archive.write(path, Path(batch_dir.name) / path.relative_to(batch_dir))
    return {**result, "archive": str(target)}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="WFS每日30款便携结果包：无需Node/npm/飞书权限")
    subparsers = result.add_subparsers(dest="command", required=True)
    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("--output", type=Path, required=True)
    init_parser.add_argument("--date", default=now_shanghai().date().isoformat())
    for name in ("inspect", "check"):
        child = subparsers.add_parser(name)
        child.add_argument("--batch-dir", type=Path, required=True)
    pack_parser = subparsers.add_parser("pack")
    pack_parser.add_argument("--batch-dir", type=Path, required=True)
    pack_parser.add_argument("--output", type=Path)
    return result


def main() -> int:
    args = parser().parse_args()
    if args.command == "init":
        datetime.fromisoformat(args.date)
        output = initialize(args.output.expanduser().resolve(), args.date)
    elif args.command == "inspect":
        output = inspect_batch(args.batch_dir.expanduser().resolve(), require_success=False)
        write_validation(args.batch_dir.expanduser().resolve(), output)
    elif args.command == "check":
        output = inspect_batch(args.batch_dir.expanduser().resolve(), require_success=True)
        write_validation(args.batch_dir.expanduser().resolve(), output)
    else:
        output = pack(args.batch_dir.expanduser().resolve(), args.output.expanduser().resolve() if args.output else None)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output.get("status") in {"CREATED", "PASS"} else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PortableBatchError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)
