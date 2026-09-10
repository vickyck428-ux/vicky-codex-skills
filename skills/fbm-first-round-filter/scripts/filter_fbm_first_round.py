#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import pandas as pd


REQUIRED_COLUMNS = [
    "评论数量",
    "卖家名称",
    "卖家所处国家",
    "配送方式",
    "是否有卖家精灵类目排名",
    "上架时间天数",
]


def parse_comment_count(value) -> float:
    if pd.isna(value):
        return float("nan")
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text:
        return float("nan")
    try:
        return float(text)
    except ValueError:
        return float("nan")


def choose_sheet(path: Path, sheet_name: str | None) -> str:
    excel = pd.ExcelFile(path)
    if sheet_name:
        if sheet_name not in excel.sheet_names:
            raise ValueError(f"工作表不存在: {sheet_name}")
        return sheet_name
    for candidate in excel.sheet_names:
        if "失败" not in candidate:
            return candidate
    return excel.sheet_names[0]


def ensure_columns(df: pd.DataFrame, required_columns: Iterable[str]) -> None:
    missing = [column for column in required_columns if column not in df.columns]
    if missing:
        raise ValueError(f"缺少必要列: {', '.join(missing)}")


def build_mask(df: pd.DataFrame) -> tuple[pd.Series, dict[str, int]]:
    comments = df["评论数量"].apply(parse_comment_count)
    seller = df["卖家名称"].fillna("").astype(str).str.strip()
    country = df["卖家所处国家"].fillna("").astype(str).str.strip()
    ship_method = df["配送方式"].fillna("").astype(str).str.strip()
    has_rank = df["是否有卖家精灵类目排名"].fillna("").astype(str).str.strip()
    listing_days = pd.to_numeric(df["上架时间天数"], errors="coerce")

    condition_counts = {
        "评论数 < 50": int(comments.lt(50).fillna(False).sum()),
        "排除卖家名称 = Amazon": int(seller.ne("Amazon").fillna(False).sum()),
        "卖家所处地 = 中国": int(country.eq("中国").fillna(False).sum()),
        "配送方式 = FBM": int(ship_method.eq("FBM").fillna(False).sum()),
        "有类目排名": int(has_rank.eq("是").fillna(False).sum()),
        "上架天数 <= 200": int(listing_days.le(200).fillna(False).sum()),
    }

    mask = (
        comments.lt(50)
        & seller.ne("Amazon")
        & country.eq("中国")
        & ship_method.eq("FBM")
        & has_rank.eq("是")
        & listing_days.le(200)
    )
    return mask, condition_counts


def export_result(
    *,
    source_file: Path,
    sheet_name: str,
    original_df: pd.DataFrame,
    filtered_df: pd.DataFrame,
    condition_counts: dict[str, int],
    output_path: Path,
) -> None:
    summary_rows = [
        ["源文件", str(source_file)],
        ["源工作表", sheet_name],
        ["总行数", int(len(original_df))],
        ["命中数量", int(len(filtered_df))],
        ["条件 1", "评论数 < 50"],
        ["条件 2", "排除卖家名称 = Amazon"],
        ["条件 3", "卖家所处地 = 中国"],
        ["条件 4", "配送方式 = FBM"],
        ["条件 5", "有类目排名"],
        ["条件 6", "上架天数 <= 200"],
    ]
    summary_rows.extend([[name, count] for name, count in condition_counts.items()])
    summary_df = pd.DataFrame(summary_rows, columns=["项目", "值"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        filtered_df.to_excel(writer, sheet_name="筛选结果", index=False)
        if filtered_df.empty:
            sheet = writer.book["筛选结果"]
            sheet["A2"] = "本次筛选结果为 0 条。"
        summary_df.to_excel(writer, sheet_name="筛选说明", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="按固定 FBM 第一轮条件筛选 Amazon 商品表。")
    parser.add_argument("--input", required=True, help="输入 Excel/CSV 文件路径")
    parser.add_argument("--output", help="输出 Excel 文件路径")
    parser.add_argument("--sheet", help="指定工作表名称，仅对 Excel 生效")
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {input_path}")

    if input_path.suffix.lower() == ".csv":
        sheet_name = "Sheet1"
        df = pd.read_csv(input_path)
    else:
        sheet_name = choose_sheet(input_path, args.sheet)
        df = pd.read_excel(input_path, sheet_name=sheet_name)

    ensure_columns(df, REQUIRED_COLUMNS)
    mask, condition_counts = build_mask(df)
    filtered_df = df.loc[mask].copy()

    output_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else input_path.with_name(f"{input_path.stem}_fbm_first_round.xlsx")
    )
    export_result(
        source_file=input_path,
        sheet_name=sheet_name,
        original_df=df,
        filtered_df=filtered_df,
        condition_counts=condition_counts,
        output_path=output_path,
    )
    print(f"输出文件: {output_path}")
    print(f"命中数量: {len(filtered_df)}")


if __name__ == "__main__":
    main()
