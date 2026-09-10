#!/usr/bin/env python3
"""Build and validate idempotent 1688 purchase/shipping manifests."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 1
PAYMENT_STATUSES = {"已下单", "待付款"}
PURCHASE_STATUSES = {
    "待付款",
    "待发货",
    "已发货",
    "运输中",
    "待取件",
    "待收货",
    "已签收",
    "已取消",
}
REQUIRED_TEXT_FIELDS = (
    "source_index",
    "payment_status",
    "purchase_status",
    "product_name",
    "spec",
    "supplier",
)
DEFAULT_BASE_URL = "https://my.feishu.cn/base/RQVSbSMusaNYlbsy5oxcgFHon3m"
DEFAULT_TABLE_NAME = "采购发货明细"


class ManifestError(Exception):
    """Raised for malformed input that prevents a deterministic result."""


def normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).strip().lower()
    return " ".join(text.split())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_path(raw_path: str, manifest_dir: Path) -> Path:
    path = Path(raw_path).expanduser()
    return path if path.is_absolute() else manifest_dir / path


def batch_fingerprint(paths: Iterable[Path]) -> str:
    resolved = [path.expanduser().resolve() for path in paths]
    if not resolved:
        raise ManifestError("截图批次不能为空")
    missing = [str(path) for path in resolved if not path.is_file()]
    if missing:
        raise ManifestError("找不到源截图: " + ", ".join(missing))
    file_hashes = sorted(sha256_file(path) for path in resolved)
    payload = "\n".join(file_hashes).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def product_signature(item: dict[str, Any]) -> str:
    parts = (
        normalize_text(item.get("supplier")),
        normalize_text(item.get("product_name")),
        normalize_text(item.get("spec")),
    )
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:24]


def detail_id_for(
    item: dict[str, Any], source_batch_fingerprint: str, occurrence_index: int
) -> str:
    order_no = normalize_text(item.get("order_no"))
    anchor = f"order:{order_no}" if order_no else f"batch:{source_batch_fingerprint}"
    raw = f"{anchor}|product:{product_signature(item)}|occ:{occurrence_index}"
    return "1688-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ManifestError(f"找不到清单: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ManifestError(f"清单不是有效 JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ManifestError("清单顶层必须是 JSON 对象")
    return data


def write_json(data: Any, output: str | None) -> None:
    rendered = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if output in (None, "-"):
        sys.stdout.write(rendered)
        return
    Path(output).expanduser().write_text(rendered, encoding="utf-8")


def blocking_issue(message: str) -> dict[str, Any]:
    return {"code": "possible_duplicate", "message": message, "blocking": True}


def prepare_manifest(data: dict[str, Any], manifest_dir: Path) -> dict[str, Any]:
    prepared = copy.deepcopy(data)
    prepared["schema_version"] = SCHEMA_VERSION
    batch = prepared.setdefault("batch", {})
    items = prepared.setdefault("items", [])
    prepared.setdefault("excluded", [])
    if not isinstance(batch, dict) or not isinstance(items, list):
        raise ManifestError("batch 必须是对象，items 必须是数组")

    source_files = batch.get("source_files") or []
    if not isinstance(source_files, list):
        raise ManifestError("batch.source_files 必须是数组")
    source_paths = [
        resolve_path(str(entry["path"] if isinstance(entry, dict) else entry), manifest_dir)
        for entry in source_files
    ]
    fingerprint = batch_fingerprint(source_paths)
    batch["source_batch_fingerprint"] = fingerprint
    batch.setdefault("generated_at", datetime.now(timezone.utc).astimezone().isoformat())

    occurrence_counters: defaultdict[tuple[str, str], int] = defaultdict(int)
    for item in items:
        if not isinstance(item, dict) or item.get("include", True) is False:
            continue
        order_anchor = normalize_text(item.get("order_no")) or fingerprint
        signature = product_signature(item)
        counter_key = (order_anchor, signature)
        explicit_occurrence = item.get("occurrence_index")
        if explicit_occurrence is None:
            occurrence_counters[counter_key] += 1
            occurrence = occurrence_counters[counter_key]
        else:
            if isinstance(explicit_occurrence, bool) or not isinstance(
                explicit_occurrence, int
            ):
                raise ManifestError("occurrence_index 必须是正整数")
            occurrence = explicit_occurrence
            occurrence_counters[counter_key] = max(
                occurrence_counters[counter_key], occurrence
            )
        item["occurrence_index"] = occurrence
        item.setdefault("include", True)
        item.setdefault("issues", [])
        item.setdefault("notes", "")
        item.setdefault("order_no", None)
        item.setdefault("order_date", None)
        if occurrence > 1 and not item.get("duplicate_reviewed"):
            issues = item["issues"]
            if isinstance(issues, list) and not any(
                isinstance(issue, dict) and issue.get("code") == "possible_duplicate"
                for issue in issues
            ):
                issues.append(
                    blocking_issue(
                        "同一订单/批次出现相同供应商、名称和规格；请先排除滚动重叠，"
                        "若确为多笔明细则设置 duplicate_reviewed=true"
                    )
                )
        if not normalize_text(item.get("detail_id")):
            item["detail_id"] = detail_id_for(item, fingerprint, occurrence)
    return prepared


def has_control_characters(value: str) -> bool:
    return any(character in value for character in ("\t", "\r", "\n"))


def validate_manifest(
    data: dict[str, Any], manifest_dir: Path, require_images: bool
) -> list[str]:
    errors: list[str] = []
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version 必须为 {SCHEMA_VERSION}")
    batch = data.get("batch")
    items = data.get("items")
    excluded = data.get("excluded", [])
    if not isinstance(batch, dict):
        errors.append("batch 必须是对象")
        batch = {}
    if not isinstance(items, list):
        errors.append("items 必须是数组")
        items = []
    if not isinstance(excluded, list):
        errors.append("excluded 必须是数组")

    fingerprint = batch.get("source_batch_fingerprint")
    if not isinstance(fingerprint, str) or len(fingerprint) != 64:
        errors.append("缺少有效的 batch.source_batch_fingerprint；请先运行 prepare")

    seen_indexes: Counter[str] = Counter()
    seen_ids: Counter[str] = Counter()
    for position, item in enumerate(items, start=1):
        prefix = f"items[{position}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} 必须是对象")
            continue
        if item.get("include", True) is False:
            continue
        for field in REQUIRED_TEXT_FIELDS:
            value = item.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{prefix}.{field} 必须是非空文本")
            elif has_control_characters(value):
                errors.append(f"{prefix}.{field} 不得包含制表符或换行")
        qty = item.get("ordered_qty")
        if isinstance(qty, bool) or not isinstance(qty, int) or qty <= 0:
            errors.append(f"{prefix}.ordered_qty 必须是大于 0 的整数")
        payment_status = item.get("payment_status")
        purchase_status = item.get("purchase_status")
        if payment_status not in PAYMENT_STATUSES:
            errors.append(f"{prefix}.payment_status 不是允许值")
        if purchase_status not in PURCHASE_STATUSES:
            errors.append(f"{prefix}.purchase_status 不是允许值")
        if (payment_status == "待付款") != (purchase_status == "待付款"):
            errors.append(f"{prefix} 的付款状态与采购状态不一致")

        occurrence = item.get("occurrence_index")
        if isinstance(occurrence, bool) or not isinstance(occurrence, int) or occurrence <= 0:
            errors.append(f"{prefix}.occurrence_index 必须是正整数")
        detail_id = item.get("detail_id")
        if not isinstance(detail_id, str) or not detail_id.strip():
            errors.append(f"{prefix}.detail_id 不能为空")
        else:
            seen_ids[detail_id] += 1
        source_index = item.get("source_index")
        if isinstance(source_index, str):
            seen_indexes[source_index] += 1

        issues = item.get("issues", [])
        if not isinstance(issues, list):
            errors.append(f"{prefix}.issues 必须是数组")
        else:
            for issue in issues:
                if isinstance(issue, str):
                    errors.append(f"{prefix} 存在阻塞疑点: {issue}")
                elif not isinstance(issue, dict):
                    errors.append(f"{prefix}.issues 中存在无效项")
                elif issue.get("blocking", True):
                    errors.append(
                        f"{prefix} 存在阻塞疑点 "
                        f"{issue.get('code', 'unknown')}: {issue.get('message', '')}"
                    )

        for field in ("source_screenshot", "product_image"):
            raw_path = item.get(field)
            if not isinstance(raw_path, str) or not raw_path.strip():
                errors.append(f"{prefix}.{field} 不能为空")
                continue
            if require_images and not resolve_path(raw_path, manifest_dir).is_file():
                errors.append(f"{prefix}.{field} 文件不存在: {raw_path}")

    errors.extend(
        f"source_index 重复: {value}" for value, count in seen_indexes.items() if count > 1
    )
    errors.extend(
        f"明细ID 重复: {value}" for value, count in seen_ids.items() if count > 1
    )
    return errors


def summarize(data: dict[str, Any]) -> dict[str, Any]:
    included = [
        item
        for item in data.get("items", [])
        if isinstance(item, dict) and item.get("include", True) is not False
    ]
    by_status: Counter[str] = Counter()
    blocking_count = 0
    for item in included:
        by_status[str(item.get("purchase_status", ""))] += int(
            item.get("ordered_qty", 0) or 0
        )
        for issue in item.get("issues", []):
            if isinstance(issue, str) or (
                isinstance(issue, dict) and issue.get("blocking", True)
            ):
                blocking_count += 1
    pending = [item for item in included if item.get("purchase_status") == "待付款"]
    return {
        "row_count": len(included),
        "total_quantity": sum(int(item.get("ordered_qty", 0) or 0) for item in included),
        "pending_row_count": len(pending),
        "pending_quantity": sum(
            int(item.get("ordered_qty", 0) or 0) for item in pending
        ),
        "by_purchase_status_quantity": dict(sorted(by_status.items())),
        "excluded_count": len(data.get("excluded", [])),
        "blocking_issue_count": blocking_count,
    }


def build_payload(data: dict[str, Any], manifest_dir: Path) -> dict[str, Any]:
    batch = data.get("batch", {})
    batch_id = str(batch.get("batch_id") or batch.get("source_batch_fingerprint", "")[:12])
    records = []
    for item in data.get("items", []):
        if not isinstance(item, dict) or item.get("include", True) is False:
            continue
        fields: dict[str, Any] = {
            "商品名称": item["product_name"],
            "规格/SKU": item["spec"],
            "明细ID": item["detail_id"],
            "采购批次": batch_id,
            "供应商": item["supplier"],
            "订购数": item["ordered_qty"],
            "已核对收货": bool(item.get("received_checked", False)),
            "去向": item.get("destination", "待定"),
            "采购状态": item["purchase_status"],
            "备注": item.get("notes", ""),
        }
        optional_mapping = {
            "order_no": "1688订单号",
            "order_date": "下单日期",
            "received_qty": "实收数",
            "arrival_date": "到货日期",
            "amazon_split_qty": "Amazon拆分数",
            "walmart_split_qty": "Walmart拆分数",
            "amazon_shipped_qty": "Amazon已发数",
            "walmart_shipped_qty": "Walmart已发数",
            "last_shipping_date": "最后发货日期",
            "amazon_sku": "Amazon SKU",
            "walmart_sku": "Walmart SKU",
        }
        for source, target in optional_mapping.items():
            value = item.get(source)
            if value not in (None, ""):
                fields[target] = value
        records.append(
            {
                "match_value": item["detail_id"],
                "fields": fields,
                "attachments": {
                    "商品主图": str(
                        resolve_path(item["product_image"], manifest_dir).resolve()
                    ),
                    "源订单截图": str(
                        resolve_path(item["source_screenshot"], manifest_dir).resolve()
                    ),
                },
            }
        )
    return {
        "mode": "dry-run",
        "base_url": batch.get("base_url", DEFAULT_BASE_URL),
        "table_name": batch.get("table_name", DEFAULT_TABLE_NAME),
        "match_field": "明细ID",
        "record_count": len(records),
        "records": records,
    }


def manifest_from_tsv(args: argparse.Namespace) -> dict[str, Any]:
    source_root = Path(args.source_root).expanduser().resolve()
    image_root = Path(args.image_root).expanduser().resolve()
    input_path = Path(args.input).expanduser().resolve()
    items: list[dict[str, Any]] = []
    source_files: list[str] = []
    with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {
            "编号",
            "付款状态",
            "订单状态",
            "商品名称",
            "规格/SKU",
            "订购数",
            "供应商",
            "源订单截图",
            "商品图文件",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ManifestError("TSV 缺少列: " + ", ".join(sorted(missing)))
        for row in reader:
            index = row["编号"].strip().zfill(3)
            source_path = (source_root / row["源订单截图"].strip()).resolve()
            image_path = (image_root / row["商品图文件"].strip()).resolve()
            if str(source_path) not in source_files:
                source_files.append(str(source_path))
            items.append(
                {
                    "source_index": index,
                    "detail_id": f"{args.batch_id}-{index}",
                    "include": True,
                    "payment_status": row["付款状态"].strip(),
                    "purchase_status": row["订单状态"].strip(),
                    "product_name": row["商品名称"].strip(),
                    "spec": row["规格/SKU"].strip(),
                    "ordered_qty": int(row["订购数"].strip()),
                    "supplier": row["供应商"].strip(),
                    "order_no": None,
                    "order_date": None,
                    "source_screenshot": str(source_path),
                    "product_image": str(image_path),
                    "occurrence_index": 1,
                    "issues": [],
                    "notes": "",
                }
            )
    for raw_path in args.extra_source:
        extra_path = Path(raw_path).expanduser().resolve()
        if str(extra_path) not in source_files:
            source_files.append(str(extra_path))
    excluded = [
        {
            "product_name": product_name,
            "reason": reason,
            "source_screenshot": str(Path(source).expanduser().resolve()),
            "notes": "由已确认的旧版清单迁移",
        }
        for product_name, reason, source in args.excluded
    ]
    data = {
        "schema_version": SCHEMA_VERSION,
        "batch": {
            "batch_id": args.batch_id,
            "source_files": source_files,
        },
        "items": items,
        "excluded": excluded,
    }
    return prepare_manifest(data, input_path.parent)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        description="1688 截图采购发货清单：指纹、稳定 ID、校验、汇总与 dry-run 载荷"
    )
    subparsers = root.add_subparsers(dest="command", required=True)

    fingerprint_parser = subparsers.add_parser("fingerprint", help="计算截图批次指纹")
    fingerprint_parser.add_argument("sources", nargs="+")

    prepare_parser = subparsers.add_parser("prepare", help="补齐批次指纹和稳定明细ID")
    prepare_parser.add_argument("manifest")
    prepare_parser.add_argument("--output", "-o", default="-")

    validate_parser = subparsers.add_parser("validate", help="校验清单")
    validate_parser.add_argument("manifest")
    validate_parser.add_argument("--require-images", action="store_true")

    summary_parser = subparsers.add_parser("summary", help="汇总行数和数量")
    summary_parser.add_argument("manifest")

    payload_parser = subparsers.add_parser("payload", help="生成飞书 dry-run 写入载荷")
    payload_parser.add_argument("manifest")
    payload_parser.add_argument("--output", "-o", default="-")
    payload_parser.add_argument("--require-images", action="store_true")

    tsv_parser = subparsers.add_parser("from-tsv", help="把已确认的旧版 TSV 转为 JSON")
    tsv_parser.add_argument("input")
    tsv_parser.add_argument("--batch-id", required=True)
    tsv_parser.add_argument("--source-root", required=True)
    tsv_parser.add_argument("--image-root", required=True)
    tsv_parser.add_argument("--extra-source", action="append", default=[])
    tsv_parser.add_argument(
        "--excluded",
        nargs=3,
        action="append",
        default=[],
        metavar=("PRODUCT_NAME", "REASON", "SOURCE"),
    )
    tsv_parser.add_argument("--output", "-o", required=True)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "fingerprint":
            print(batch_fingerprint(Path(path) for path in args.sources))
            return 0
        if args.command == "from-tsv":
            write_json(manifest_from_tsv(args), args.output)
            return 0

        manifest_path = Path(args.manifest).expanduser().resolve()
        manifest_dir = manifest_path.parent
        data = read_json(manifest_path)
        if args.command == "prepare":
            write_json(prepare_manifest(data, manifest_dir), args.output)
            return 0
        if args.command == "validate":
            errors = validate_manifest(data, manifest_dir, args.require_images)
            if errors:
                for error in errors:
                    print(f"ERROR: {error}", file=sys.stderr)
                return 1
            write_json({"valid": True, **summarize(data)}, "-")
            return 0
        if args.command == "summary":
            write_json(summarize(data), "-")
            return 0
        if args.command == "payload":
            errors = validate_manifest(data, manifest_dir, args.require_images)
            if errors:
                for error in errors:
                    print(f"ERROR: {error}", file=sys.stderr)
                return 1
            write_json(build_payload(data, manifest_dir), args.output)
            return 0
    except (ManifestError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
