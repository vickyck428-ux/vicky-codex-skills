#!/usr/bin/env python3
import argparse
import csv
import datetime as dt
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

GROUPS = {
    "product_database": {
        "keywords": ["商品库", "product", "asin"],
        "required": [["asin"], ["标题", "title"], ["售价", "price"], ["评论", "review"], ["履约", "fulfillment", "fba", "fbm"]],
        "method": "amazon-software-product-selection",
    },
    "keyword_database": {
        "keywords": ["关键词", "keyword"],
        "required": [["关键词", "keyword"], ["搜索量", "search volume"], ["cpc"], ["转化率", "conversion"]],
        "method": "amazon-keyword-selection",
    },
    "aba_history": {
        "keywords": ["aba", "brand analytics", "搜索词表现"],
        "required": [["关键词", "search term", "query"], ["周期", "week", "date"], ["搜索频率", "search frequency rank", "rank"], ["点击份额", "click share"], ["购买份额", "conversion share", "purchase share"]],
        "method": "amazon-aba-selection",
    },
    "market_30d": {
        "keywords": ["近30", "30d", "竞品"],
        "required": [["asin"], ["销量", "sales"], ["售价", "price"], ["评论", "review"]],
        "method": "lc_amazon_market_research",
    },
    "market_12m": {
        "keywords": ["近12", "12m", "月表", "trend"],
        "required": [["月份", "month", "date"], ["销量", "sales"]],
        "method": "lc_amazon_market_research",
    },
    "asin_keywords": {
        "keywords": ["反查", "asin keyword"],
        "required": [["asin"], ["关键词", "keyword"]],
        "method": "lc_amazon_market_research",
    },
    "keyword_conversion": {
        "keywords": ["转化率", "conversion"],
        "required": [["关键词", "keyword"], ["转化率", "conversion"], ["cpc"]],
        "method": "lc_amazon_market_research",
    },
    "competitor_store": {
        "keywords": ["同行", "storefront", "seller"],
        "required": [["店铺", "store", "seller", "url"]],
        "method": "amazon-competitor-store-selection",
    },
    "supplier_cost": {
        "keywords": ["采购", "成本", "供应链", "supplier", "cost"],
        "required": [["产品", "candidate", "sku", "offer"], ["采购价", "cost"], ["moq"], ["重量", "weight"], ["交期", "lead time", "生产"]],
        "method": "amazon-handbag-selection-orchestrator",
    },
}


def norm(value):
    return re.sub(r"[\s_\-()/]+", "", str(value or "").strip().lower())


def csv_headers(path):
    with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as fh:
        delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
        return next(csv.reader(fh, delimiter=delimiter), [])


def xlsx_headers(path):
    ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main", "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
    with zipfile.ZipFile(path) as zf:
        shared = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in root.findall("a:si", ns):
                shared.append("".join(t.text or "" for t in si.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")))
        sheets = sorted(n for n in zf.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n))
        best = []
        for sheet_name in sheets:
            root = ET.fromstring(zf.read(sheet_name))
            rows = root.findall(".//a:sheetData/a:row", ns)[:20]
            for row in rows:
                values = []
                for cell in row.findall("a:c", ns):
                    cell_type = cell.attrib.get("t")
                    value = cell.find("a:v", ns)
                    inline = cell.find("a:is", ns)
                    if cell_type == "s" and value is not None and value.text:
                        idx = int(value.text)
                        values.append(shared[idx] if idx < len(shared) else "")
                    elif inline is not None:
                        values.append("".join(t.text or "" for t in inline.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")))
                    else:
                        values.append(value.text if value is not None else "")
                if sum(bool(str(v).strip()) for v in values) > sum(bool(str(v).strip()) for v in best):
                    best = values
        return best


def headers(path):
    if path.suffix.lower() in {".csv", ".tsv"}:
        return csv_headers(path)
    if path.suffix.lower() == ".xlsx":
        return xlsx_headers(path)
    if path.suffix.lower() == ".txt":
        return ["url"]
    return []


def classify(path, cols):
    name = norm(path.stem)
    columns = norm(" ".join(cols))
    scored = []
    for group, spec in GROUPS.items():
        score = sum(5 for keyword in spec["keywords"] if norm(keyword) in name)
        score += sum(1 for keyword in spec["keywords"] if norm(keyword) in columns)
        if score:
            scored.append((score, group))
    return max(scored)[1] if scored else "unknown"


def missing_columns(cols, required):
    normalized = [norm(x) for x in cols]
    missing = []
    for aliases in required:
        if not any(norm(alias) in column or column in norm(alias) for alias in aliases for column in normalized if column):
            missing.append("/".join(aliases))
    return missing


def inspect_file(path):
    try:
        cols = headers(path)
        group = classify(path, cols)
        missing = missing_columns(cols, GROUPS[group]["required"]) if group in GROUPS else []
        age = (dt.datetime.now().timestamp() - path.stat().st_mtime) / 86400
        return {
            "path": str(path), "group": group, "method": GROUPS.get(group, {}).get("method"),
            "headers": cols, "missing": missing, "age_days": round(age, 1),
            "status": "UNKNOWN" if group == "unknown" else ("NEEDS DATA" if missing else "READY"),
        }
    except Exception as exc:
        return {"path": str(path), "group": "error", "status": "ERROR", "error": str(exc)}


def main():
    parser = argparse.ArgumentParser(description="Validate refined-handbag selection input files")
    parser.add_argument("directory")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.directory).expanduser().resolve()
    if not root.is_dir():
        parser.error(f"directory not found: {root}")
    allowed = {".xlsx", ".csv", ".tsv", ".txt"}
    files = [inspect_file(p) for p in sorted(root.rglob("*")) if p.is_file() and p.suffix.lower() in allowed and not p.name.startswith("~$")]
    ready_methods = sorted({f["method"] for f in files if f.get("status") == "READY" and f.get("method")})
    present_groups = {f["group"] for f in files}
    missing_groups = [g for g in GROUPS if g not in present_groups]
    needs_data_groups = sorted({f["group"] for f in files if f.get("status") == "NEEDS DATA"})
    result = {
        "directory": str(root), "files": files, "ready_methods": ready_methods,
        "needs_data_groups": needs_data_groups, "missing_groups": missing_groups,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"目录: {root}")
    for f in files:
        print(f"[{f['status']}] {f['group']}: {f['path']}")
        if f.get("missing"):
            print("  缺字段: " + ", ".join(f["missing"]))
        if f.get("error"):
            print("  错误: " + f["error"])
    print("可运行方法: " + (", ".join(ready_methods) or "无"))
    print("字段不完整: " + (", ".join(needs_data_groups) or "无"))
    print("缺少文件组: " + (", ".join(missing_groups) or "无"))


if __name__ == "__main__":
    main()
