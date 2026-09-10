#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openpyxl import load_workbook


ORDER_TYPES = {"order", "pedido", "liquidations"}
REFUND_TYPES = {"refund", "refund_retrocharge"}
IGNORE_TYPES = {"transfer"}
DIRECT_TOTAL_TYPES = {
    "",
    "adjustment",
    "ajuste",
    "fee adjustment",
    "service fee",
    "fba inventory fee",
    "fba customer return fee",
    "order_retrocharge",
    "chargeback refund",
    "空白",
}


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_sku(value: Any) -> str:
    return normalize_text(value).upper()


def is_legacy_pencil_case(value: Any) -> bool:
    compact = re.sub(r"[^a-z0-9]+", " ", normalize_text(value).lower()).strip()
    return any(term in compact for term in ("pencil case", "pencil pouch", "pen case", "pen pouch", "pen bag"))


def normalize_type(value: Any) -> str:
    return normalize_text(value).lower()


def to_number(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def slug(label: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in label)
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_")


def find_header_row(ws, required_headers: set[str], scan_rows: int = 20) -> tuple[int, dict[str, int]]:
    for row_idx in range(1, min(scan_rows, ws.max_row) + 1):
        row_map: dict[str, int] = {}
        for col_idx in range(1, ws.max_column + 1):
            header = normalize_type(ws.cell(row_idx, col_idx).value)
            if header:
                row_map[header] = col_idx
        if required_headers.issubset(row_map.keys()):
            return row_idx, row_map
    raise ValueError(f"Could not find header row with required headers: {sorted(required_headers)}")


def read_cost_map(cost_xlsx: Path, cost_sheet: str) -> dict[str, dict[str, float]]:
    wb = load_workbook(cost_xlsx, data_only=True, read_only=True)
    ws = wb[cost_sheet]
    cost_map: dict[str, dict[str, float]] = {}
    for row in ws.iter_rows(min_row=3, values_only=True):
        sku = normalize_sku(row[0] if len(row) > 0 else None)
        if not sku:
            continue
        unit_product_cost = to_number(row[3] if len(row) > 3 else 0)
        unit_first_leg_cost = to_number(row[4] if len(row) > 4 else 0)
        cost_map[sku] = {
            "unit_product_cost": unit_product_cost,
            "unit_first_leg_cost": unit_first_leg_cost,
        }
    return cost_map


def infer_action(txn_type: str) -> str:
    if txn_type in ORDER_TYPES:
        return "consume_inventory"
    if txn_type in REFUND_TYPES:
        return "return_inventory"
    if txn_type in IGNORE_TYPES:
        return "ignore"
    return "direct_total"


@dataclass
class DetailRow:
    date_time: str
    tx_type: str
    order_id: str
    sku: str
    quantity: float
    product_sales: float
    total: float
    action: str
    unit_product_cost: float
    unit_first_leg_cost: float
    product_cost_impact: float
    first_leg_cost_impact: float
    gross_profit: float
    margin: float | None
    cost_found: bool


def read_detail_rows(report_xlsx: Path, report_sheet: str, cost_map: dict[str, dict[str, float]]) -> list[DetailRow]:
    wb = load_workbook(report_xlsx, data_only=True, read_only=True)
    ws = wb[report_sheet]
    required_headers = {"type", "order id", "sku", "quantity", "product sales", "total"}
    header_row, headers = find_header_row(ws, required_headers)
    rows: list[DetailRow] = []

    for raw in ws.iter_rows(min_row=header_row + 1, values_only=True):
        tx_type = normalize_type(raw[headers["type"] - 1])
        order_id = normalize_text(raw[headers["order id"] - 1])
        sku = normalize_sku(raw[headers["sku"] - 1])
        quantity = to_number(raw[headers["quantity"] - 1])
        product_sales = to_number(raw[headers["product sales"] - 1])
        total = to_number(raw[headers["total"] - 1])
        date_time = normalize_text(raw[headers.get("date/time", 1) - 1]) if "date/time" in headers else ""

        if not any([tx_type, order_id, sku, quantity, product_sales, total]):
            continue

        action = "ignore" if is_legacy_pencil_case(sku) else infer_action(tx_type)
        cost_info = cost_map.get(sku, {"unit_product_cost": 0.0, "unit_first_leg_cost": 0.0})
        cost_found = bool(sku) and sku in cost_map
        unit_product_cost = cost_info["unit_product_cost"]
        unit_first_leg_cost = cost_info["unit_first_leg_cost"]

        sign = 0.0
        if action == "consume_inventory":
            sign = -1.0
        elif action == "return_inventory":
            sign = 1.0

        product_cost_impact = sign * quantity * unit_product_cost
        first_leg_cost_impact = sign * quantity * unit_first_leg_cost
        gross_profit = 0.0 if action == "ignore" else total + product_cost_impact + first_leg_cost_impact
        margin = None
        if product_sales > 0.01 and action != "ignore":
            margin = gross_profit / product_sales

        rows.append(
            DetailRow(
                date_time=date_time,
                tx_type=tx_type or "blank",
                order_id=order_id,
                sku=sku,
                quantity=quantity,
                product_sales=product_sales,
                total=total,
                action=action,
                unit_product_cost=unit_product_cost,
                unit_first_leg_cost=unit_first_leg_cost,
                product_cost_impact=product_cost_impact,
                first_leg_cost_impact=first_leg_cost_impact,
                gross_profit=gross_profit,
                margin=margin,
                cost_found=cost_found,
            )
        )
    return rows


def build_analysis(rows: list[DetailRow]) -> dict[str, Any]:
    included = [r for r in rows if r.action != "ignore"]
    type_counter = Counter(r.tx_type for r in rows)
    missing_cost_rows = [r for r in included if r.sku and not r.cost_found and r.action in {"consume_inventory", "return_inventory"}]

    sku_groups: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "sku": "",
            "orders": 0,
            "refunds": 0,
            "order_units": 0.0,
            "refund_units": 0.0,
            "product_sales": 0.0,
            "amazon_total": 0.0,
            "product_cost_impact": 0.0,
            "first_leg_cost_impact": 0.0,
            "gross_profit": 0.0,
            "missing_cost_rows": 0,
        }
    )

    for row in included:
        if not row.sku:
            continue
        group = sku_groups[row.sku]
        group["sku"] = row.sku
        group["product_sales"] += row.product_sales
        group["amazon_total"] += row.total
        group["product_cost_impact"] += row.product_cost_impact
        group["first_leg_cost_impact"] += row.first_leg_cost_impact
        group["gross_profit"] += row.gross_profit
        if not row.cost_found and row.action in {"consume_inventory", "return_inventory"}:
            group["missing_cost_rows"] += 1
        if row.action == "consume_inventory":
            group["orders"] += 1
            group["order_units"] += row.quantity
        elif row.action == "return_inventory":
            group["refunds"] += 1
            group["refund_units"] += row.quantity

    sku_summary: list[dict[str, Any]] = []
    for sku, group in sku_groups.items():
        order_units = group["order_units"]
        refund_units = group["refund_units"]
        net_units = order_units - refund_units
        gross_margin = group["gross_profit"] / group["product_sales"] if group["product_sales"] > 0.01 else None
        return_rate = refund_units / order_units if order_units > 0 else None
        profit_per_unit = group["gross_profit"] / order_units if order_units > 0 else None
        risk_tags = []
        if group["missing_cost_rows"] > 0:
            risk_tags.append("缺成本")
        if group["orders"] > 0 and group["gross_profit"] < 0:
            risk_tags.append("亏损")
        if group["orders"] >= 10 and gross_margin is not None and gross_margin < 0.15:
            risk_tags.append("低毛利")
        if order_units >= 5 and return_rate is not None and return_rate >= 0.2:
            risk_tags.append("高退货")
        risk_level = "高风险" if {"缺成本", "亏损"} & set(risk_tags) else ("关注" if risk_tags else "正常")
        group.update(
            {
                "net_units": net_units,
                "gross_margin": gross_margin,
                "return_rate": return_rate,
                "profit_per_unit": profit_per_unit,
                "risk_tags": risk_tags,
                "risk_level": risk_level,
            }
        )
        sku_summary.append(group)

    sku_summary.sort(key=lambda item: item["gross_profit"], reverse=True)

    low_margin = [
        item
        for item in sku_summary
        if item["orders"] >= 10 and item["gross_margin"] is not None and item["gross_margin"] < 0.15
    ]
    high_return = [
        item
        for item in sku_summary
        if item["order_units"] >= 5 and item["return_rate"] is not None and item["return_rate"] >= 0.2
    ]
    loss_making = [
        item
        for item in sku_summary
        if item["orders"] > 0 and item["gross_profit"] < 0
    ]
    missing_cost_skus = [
        item
        for item in sku_summary
        if item["missing_cost_rows"] > 0
    ]

    summary = {
        "included_rows": len(included),
        "ignored_rows": len(rows) - len(included),
        "amazon_total": sum(r.total for r in included),
        "product_sales": sum(r.product_sales for r in included),
        "product_cost_impact": sum(r.product_cost_impact for r in included),
        "first_leg_cost_impact": sum(r.first_leg_cost_impact for r in included),
        "gross_profit": sum(r.gross_profit for r in included),
        "order_rows": sum(1 for r in included if r.action == "consume_inventory"),
        "refund_rows": sum(1 for r in included if r.action == "return_inventory"),
        "return_fee_loss": sum(r.gross_profit for r in included if r.tx_type == "fba customer return fee"),
        "service_fee_loss": sum(r.gross_profit for r in included if r.tx_type == "service fee"),
        "inventory_fee_loss": sum(r.gross_profit for r in included if r.tx_type == "fba inventory fee"),
        "missing_cost_rows": len(missing_cost_rows),
        "missing_cost_skus": len(missing_cost_skus),
        "loss_skus": len(loss_making),
        "low_margin_skus": len(low_margin),
        "high_return_skus": len(high_return),
        "excluded_pencil_case_rows": sum(1 for row in rows if is_legacy_pencil_case(row.sku)),
    }
    summary["gross_margin"] = (
        summary["gross_profit"] / summary["product_sales"] if summary["product_sales"] > 0 else None
    )

    type_summary: list[dict[str, Any]] = []
    type_groups: dict[str, dict[str, Any]] = defaultdict(lambda: {"type": "", "rows": 0, "amazon_total": 0.0, "gross_profit": 0.0})
    for row in included:
        group = type_groups[row.tx_type]
        group["type"] = row.tx_type
        group["rows"] += 1
        group["amazon_total"] += row.total
        group["gross_profit"] += row.gross_profit
    type_summary.extend(type_groups.values())
    type_summary.sort(key=lambda item: abs(item["gross_profit"]), reverse=True)

    insights = []
    if sku_summary:
        top = sku_summary[0]
        insights.append(
            f"利润贡献最高的SKU是 {top['sku']}，累计流水毛利 {top['gross_profit']:.2f} 美元。"
        )
    if low_margin:
        sku = low_margin[0]
        margin_pct = sku["gross_margin"] * 100 if sku["gross_margin"] is not None else 0
        insights.append(
            f"低毛利预警：{sku['sku']} 订单数 {sku['orders']}，毛利率仅 {margin_pct:.1f}%。"
        )
    if high_return:
        sku = sorted(high_return, key=lambda item: item["return_rate"] or 0, reverse=True)[0]
        rate = (sku["return_rate"] or 0) * 100
        insights.append(
            f"退货率偏高：{sku['sku']} 退货率 {rate:.1f}%，建议结合客服与产品问题复核。"
        )
    if missing_cost_rows:
        sample = ", ".join(sorted({row.sku for row in missing_cost_rows})[:5])
        insights.append(f"发现 {len(missing_cost_rows)} 行未匹配成本，示例 SKU：{sample}。")

    detail_rows = [
        {
            "date_time": row.date_time,
            "type": row.tx_type,
            "order_id": row.order_id,
            "sku": row.sku,
            "quantity": row.quantity,
            "product_sales": row.product_sales,
            "amazon_total": row.total,
            "action": row.action,
            "unit_product_cost": row.unit_product_cost,
            "unit_first_leg_cost": row.unit_first_leg_cost,
            "product_cost_impact": row.product_cost_impact,
            "first_leg_cost_impact": row.first_leg_cost_impact,
            "gross_profit": row.gross_profit,
            "margin": row.margin,
            "cost_found": row.cost_found,
        }
        for row in included
    ]

    missing_cost_summary = [
        {
            "sku": row.sku,
            "type": row.tx_type,
            "order_id": row.order_id,
            "quantity": row.quantity,
        }
        for row in missing_cost_rows[:200]
    ]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "type_counts": dict(type_counter),
        "type_summary": type_summary,
        "sku_summary": sku_summary,
        "detail_rows": detail_rows,
        "missing_cost_rows": missing_cost_summary,
        "risk_summary": {
            "loss_making": sorted(loss_making, key=lambda item: item["gross_profit"])[:30],
            "low_margin": sorted(low_margin, key=lambda item: item["gross_margin"] or 0)[:30],
            "high_return": sorted(high_return, key=lambda item: item["return_rate"] or 0, reverse=True)[:30],
            "missing_cost": sorted(missing_cost_skus, key=lambda item: item["missing_cost_rows"], reverse=True)[:30],
        },
        "insights": insights,
    }


def fmt_money(value: float) -> str:
    return f"${value:,.2f}"


def fmt_pct(value: float | None) -> str:
    if value is None or math.isnan(value):
        return "-"
    return f"{value * 100:.1f}%"


def build_html(analysis: dict[str, Any]) -> str:
    summary = analysis["summary"]
    top_skus = analysis["sku_summary"][:12]
    low_margin = sorted(
        [row for row in analysis["sku_summary"] if row["orders"] >= 10 and row["gross_margin"] is not None],
        key=lambda row: row["gross_margin"],
    )[:12]
    type_rows = analysis["type_summary"][:10]
    search_rows = analysis["sku_summary"]
    risk_summary = analysis["risk_summary"]
    max_top_profit = max((row["gross_profit"] for row in top_skus), default=1) or 1
    max_type_impact = max((abs(row["gross_profit"]) for row in type_rows), default=1) or 1

    def render_rows(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> str:
        body = []
        for row in rows:
            tds = []
            for key, kind in columns:
                value = row.get(key)
                if kind == "money":
                    text = fmt_money(float(value or 0))
                elif kind == "pct":
                    text = fmt_pct(value)
                elif kind == "int":
                    text = f"{int(value or 0):,}"
                else:
                    text = str(value or "-")
                tds.append(f"<td>{text}</td>")
            body.append("<tr>" + "".join(tds) + "</tr>")
        return "\n".join(body)

    def render_sku_bars(rows: list[dict[str, Any]]) -> str:
        cards = []
        for row in rows[:8]:
            width = max(8, min(100, (row["gross_profit"] / max_top_profit) * 100))
            cards.append(
                f"""
                <div class="sku-bar-card">
                  <div class="sku-bar-head">
                    <strong>{row['sku']}</strong>
                    <span>{fmt_money(row['gross_profit'])}</span>
                  </div>
                  <div class="bar-track"><div class="bar-fill" style="width:{width:.1f}%"></div></div>
                  <div class="sku-bar-meta">
                    <span>毛利率 {fmt_pct(row.get('gross_margin'))}</span>
                    <span>退货率 {fmt_pct(row.get('return_rate'))}</span>
                  </div>
                </div>
                """
            )
        return "".join(cards)

    def render_type_tiles(rows: list[dict[str, Any]]) -> str:
        blocks = []
        for row in rows[:6]:
            width = max(10, min(100, abs(row["gross_profit"]) / max_type_impact * 100))
            tone = "good" if row["gross_profit"] >= 0 else "bad"
            blocks.append(
                f"""
                <div class="impact-row">
                  <div class="impact-label">
                    <span>{row['type']}</span>
                    <strong>{fmt_money(row['gross_profit'])}</strong>
                  </div>
                  <div class="impact-track {tone}"><div class="impact-fill" style="width:{width:.1f}%"></div></div>
                </div>
                """
            )
        return "".join(blocks)

    def render_risk_items(rows: list[dict[str, Any]], metric: str) -> str:
        items = []
        for row in rows[:5]:
            if metric == "profit":
                value = fmt_money(row["gross_profit"])
            elif metric == "margin":
                value = fmt_pct(row.get("gross_margin"))
            elif metric == "return":
                value = fmt_pct(row.get("return_rate"))
            else:
                value = f"{row['missing_cost_rows']} 行"
            items.append(
                f"""
                <button class="risk-item sku-jump" data-sku="{row['sku']}">
                  <span>{row['sku']}</span>
                  <strong>{value}</strong>
                </button>
                """
            )
        return "".join(items) or '<div class="risk-empty">暂无符合条件的 SKU</div>'

    insight_list = "".join(f"<li>{item}</li>" for item in analysis["insights"]) or "<li>暂无自动洞察。</li>"
    search_payload = json.dumps(search_rows, ensure_ascii=False)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>亚马逊财务分析看板</title>
  <style>
    :root {{
      --bg: #f6f2ea;
      --ink: #16202a;
      --muted: #687483;
      --line: rgba(22, 32, 42, 0.10);
      --panel: rgba(255, 255, 255, 0.82);
      --panel-strong: rgba(255, 255, 255, 0.96);
      --hero-a: #113c5b;
      --hero-b: #c35e4f;
      --hero-c: #efb366;
      --good: #157a6e;
      --bad: #c2483b;
      --gold: #edb75a;
      --shadow: 0 18px 60px rgba(27, 39, 52, 0.10);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Avenir Next", "PingFang SC", "Microsoft YaHei", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at 15% 10%, rgba(195, 94, 79, 0.20), transparent 22%),
        radial-gradient(circle at 85% 0%, rgba(17, 60, 91, 0.18), transparent 24%),
        linear-gradient(180deg, #fbf8f3 0%, var(--bg) 100%);
    }}
    .wrap {{
      max-width: 1340px;
      margin: 0 auto;
      padding: 32px 20px 72px;
    }}
    .hero {{
      display: grid;
      grid-template-columns: 1.3fr 0.9fr;
      gap: 20px;
      margin-bottom: 24px;
    }}
    .hero-card, .panel {{
      background: var(--panel);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(255,255,255,0.5);
      border-radius: 24px;
      box-shadow: var(--shadow);
    }}
    .hero-card {{
      padding: 14px 30px 30px;
      background:
        radial-gradient(circle at top right, rgba(237, 183, 90, 0.20), transparent 26%),
        linear-gradient(135deg, rgba(17, 60, 91, 0.95), rgba(195, 94, 79, 0.92));
      color: #fff7ef;
      overflow: hidden;
      position: relative;
    }}
    .hero-card::after {{
      content: "";
      position: absolute;
      right: -60px;
      top: -20px;
      width: 220px;
      height: 220px;
      background: radial-gradient(circle, rgba(255,255,255,0.16), transparent 62%);
      pointer-events: none;
    }}
    .eyebrow {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(255,255,255,0.12);
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    h1 {{
      margin: 4px 0 10px;
      font-size: clamp(28px, 4vw, 48px);
      line-height: 1.05;
      letter-spacing: -0.03em;
      max-width: 10ch;
    }}
    .subtitle {{
      color: rgba(255,247,239,0.84);
      line-height: 1.7;
      font-size: 15px;
      max-width: 54ch;
    }}
    .insights {{
      margin-top: 14px;
      padding-left: 18px;
      color: #fff7ef;
      line-height: 1.7;
    }}
    .hero-ribbon {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin-top: 18px;
    }}
    .hero-metric {{
      padding: 14px 16px;
      border-radius: 18px;
      background: rgba(255,255,255,0.12);
      border: 1px solid rgba(255,255,255,0.12);
    }}
    .hero-metric span {{
      display: block;
      font-size: 12px;
      color: rgba(255,247,239,0.72);
    }}
    .hero-metric strong {{
      display: block;
      margin-top: 8px;
      font-size: 24px;
      color: #fff;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }}
    .stat {{
      padding: 18px 18px 16px;
      border-radius: 22px;
      background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(251,247,241,0.88));
      border: 1px solid var(--line);
      position: relative;
      overflow: hidden;
    }}
    .stat::before {{
      content: "";
      position: absolute;
      inset: 0 auto auto 0;
      width: 100%;
      height: 4px;
      background: linear-gradient(90deg, var(--hero-a), var(--hero-b), var(--hero-c));
    }}
    .stat .label {{
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
    }}
    .stat .value {{
      margin-top: 10px;
      font-size: 28px;
      font-weight: 700;
    }}
    .stat .hint {{
      margin-top: 8px;
      color: var(--muted);
      font-size: 12px;
    }}
    .toolbar {{
      display: flex;
      justify-content: flex-end;
      gap: 10px;
      margin: -4px 0 20px;
    }}
    .action-button {{
      appearance: none;
      border: 1px solid rgba(17,60,91,0.16);
      border-radius: 999px;
      padding: 10px 15px;
      background: rgba(255,255,255,0.84);
      color: var(--hero-a);
      font: inherit;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      box-shadow: 0 8px 24px rgba(27,39,52,0.06);
    }}
    .action-button.primary {{
      border-color: transparent;
      background: var(--hero-a);
      color: #fff;
    }}
    .risk-overview {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
      margin-top: 20px;
    }}
    .risk-card {{
      padding: 18px;
      border-radius: 22px;
      background: rgba(255,255,255,0.9);
      border: 1px solid var(--line);
      box-shadow: var(--shadow);
      overflow: hidden;
      position: relative;
    }}
    .risk-card::before {{
      content: "";
      position: absolute;
      inset: 0 auto 0 0;
      width: 5px;
      background: var(--risk-color, var(--gold));
    }}
    .risk-card.loss {{ --risk-color: #b63f36; }}
    .risk-card.margin {{ --risk-color: #d98732; }}
    .risk-card.return {{ --risk-color: #247f88; }}
    .risk-card.cost {{ --risk-color: #4b607d; }}
    .risk-card-head {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 12px;
      margin-bottom: 13px;
    }}
    .risk-card-head span {{
      color: var(--muted);
      font-size: 12px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }}
    .risk-card-head strong {{
      font-size: 28px;
      line-height: 1;
    }}
    .risk-list {{
      display: grid;
      gap: 7px;
    }}
    .risk-item {{
      width: 100%;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      padding: 9px 10px;
      border: 0;
      border-radius: 12px;
      background: rgba(22,32,42,0.04);
      color: var(--ink);
      cursor: pointer;
      text-align: left;
      font: inherit;
    }}
    .risk-item:hover {{
      background: rgba(17,60,91,0.09);
      transform: translateX(2px);
    }}
    .risk-item span {{
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-size: 12px;
    }}
    .risk-item strong {{
      flex: 0 0 auto;
      font-size: 12px;
      color: var(--risk-color, var(--hero-a));
    }}
    .risk-empty {{
      color: var(--muted);
      font-size: 12px;
      padding: 10px;
    }}
    .viz-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
      margin-top: 20px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: 1.1fr 0.9fr;
      gap: 20px;
      margin-top: 20px;
    }}
    .panel {{
      padding: 20px;
    }}
    .panel.soft {{
      background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(255,250,244,0.82));
    }}
    h2 {{
      margin: 0 0 14px;
      font-size: 20px;
    }}
    .panel-head {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 14px;
    }}
    .panel-note {{
      font-size: 12px;
      color: var(--muted);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}
    th, td {{
      padding: 10px 8px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      white-space: nowrap;
    }}
    th {{
      color: var(--muted);
      font-weight: 600;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .sku-bar-card {{
      padding: 14px 14px 12px;
      border-radius: 18px;
      background: linear-gradient(180deg, rgba(244, 247, 250, 0.9), rgba(255, 255, 255, 0.9));
      border: 1px solid var(--line);
    }}
    .sku-bar-head, .sku-bar-meta, .impact-label, .search-top {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }}
    .sku-bar-head strong {{
      font-size: 14px;
    }}
    .sku-bar-head span, .sku-bar-meta {{
      color: var(--muted);
      font-size: 12px;
    }}
    .bar-track, .impact-track {{
      height: 10px;
      border-radius: 999px;
      background: rgba(17, 60, 91, 0.08);
      overflow: hidden;
      margin: 10px 0 8px;
    }}
    .bar-fill {{
      height: 100%;
      border-radius: 999px;
      background: linear-gradient(90deg, var(--hero-a), var(--hero-b), var(--hero-c));
    }}
    .impact-stack {{
      display: grid;
      gap: 14px;
    }}
    .impact-row {{
      padding: 14px;
      border-radius: 18px;
      background: linear-gradient(180deg, rgba(247,249,251,0.92), rgba(255,255,255,0.92));
      border: 1px solid var(--line);
    }}
    .impact-label span {{
      text-transform: capitalize;
      color: var(--muted);
    }}
    .impact-label strong {{
      font-size: 14px;
    }}
    .impact-track.good .impact-fill {{
      background: linear-gradient(90deg, #1d7c73, #47b09a);
    }}
    .impact-track.bad .impact-fill {{
      background: linear-gradient(90deg, #c2483b, #ef8f6a);
    }}
    .impact-fill {{
      height: 100%;
      border-radius: 999px;
    }}
    .search-shell {{
      display: grid;
      grid-template-columns: 320px 1fr;
      gap: 20px;
      margin-top: 22px;
    }}
    .search-box {{
      background: linear-gradient(180deg, rgba(17,60,91,0.96), rgba(28,83,110,0.96));
      color: #fff;
      padding: 22px;
      border-radius: 24px;
      box-shadow: var(--shadow);
    }}
    .search-box p {{
      color: rgba(255,255,255,0.76);
      line-height: 1.65;
      margin-bottom: 14px;
    }}
    .search-input {{
      width: 100%;
      border: 0;
      outline: none;
      padding: 14px 16px;
      border-radius: 16px;
      font-size: 15px;
      color: var(--ink);
      background: #fffdf9;
    }}
    .search-field {{
      position: relative;
    }}
    .match-list {{
      display: none;
      position: absolute;
      z-index: 5;
      top: calc(100% + 8px);
      left: 0;
      right: 0;
      max-height: 260px;
      overflow: auto;
      padding: 8px;
      border-radius: 16px;
      background: #fffdf9;
      color: var(--ink);
      box-shadow: 0 18px 40px rgba(13,32,48,0.24);
    }}
    .match-item {{
      width: 100%;
      display: flex;
      justify-content: space-between;
      gap: 12px;
      padding: 10px;
      border: 0;
      border-radius: 10px;
      background: transparent;
      color: var(--ink);
      cursor: pointer;
      font: inherit;
      text-align: left;
    }}
    .match-item:hover {{
      background: rgba(17,60,91,0.08);
    }}
    .match-item span {{
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .match-item small {{
      flex: 0 0 auto;
      color: var(--muted);
    }}
    .search-suggestions {{
      margin-top: 14px;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .pill {{
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(255,255,255,0.12);
      border: 1px solid rgba(255,255,255,0.12);
      color: #fff;
      font-size: 12px;
      cursor: pointer;
    }}
    .search-panel {{
      padding: 22px;
      border-radius: 24px;
      background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(253,249,243,0.88));
      border: 1px solid var(--line);
      box-shadow: var(--shadow);
    }}
    .sku-badge {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(17,60,91,0.08);
      color: var(--hero-a);
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }}
    .sku-badge.attention {{
      background: rgba(217,135,50,0.12);
      color: #a65f1d;
    }}
    .sku-badge.danger {{
      background: rgba(194,72,59,0.12);
      color: var(--bad);
    }}
    .search-metrics {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin-top: 18px;
    }}
    .search-card {{
      padding: 14px;
      border-radius: 18px;
      background: rgba(255,255,255,0.86);
      border: 1px solid var(--line);
    }}
    .search-card .k {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .search-card .v {{
      margin-top: 8px;
      font-size: 20px;
      font-weight: 700;
    }}
    .search-meta {{
      margin-top: 18px;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }}
    .meta-box {{
      padding: 16px;
      border-radius: 18px;
      background: rgba(247, 249, 252, 0.88);
      border: 1px solid var(--line);
    }}
    .meta-box ul {{
      margin: 10px 0 0;
      padding-left: 18px;
      color: var(--muted);
      line-height: 1.7;
    }}
    .empty-state {{
      margin-top: 18px;
      padding: 18px;
      border-radius: 18px;
      background: rgba(194,72,59,0.08);
      color: var(--bad);
      display: none;
    }}
    .footer {{
      margin-top: 18px;
      color: var(--muted);
      font-size: 12px;
    }}
    @media (max-width: 920px) {{
      .hero, .grid, .viz-grid, .search-shell, .search-meta {{ grid-template-columns: 1fr; }}
      .risk-overview {{ grid-template-columns: 1fr 1fr; }}
      .stats {{ grid-template-columns: 1fr 1fr; }}
      .search-metrics {{ grid-template-columns: 1fr 1fr; }}
      .hero-ribbon {{ grid-template-columns: 1fr; }}
    }}
    @media (max-width: 560px) {{
      .risk-overview, .stats, .search-metrics {{ grid-template-columns: 1fr; }}
      .toolbar {{ justify-content: stretch; }}
      .action-button {{ flex: 1; }}
    }}
    @media print {{
      body {{ background: #fff; }}
      .wrap {{ max-width: none; padding: 0; }}
      .toolbar, .search-box {{ display: none; }}
      .hero, .viz-grid, .grid, .risk-overview {{ break-inside: avoid; }}
      .hero-card, .panel, .risk-card, .search-panel {{ box-shadow: none; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <div class="hero-card">
        <div class="eyebrow">Amazon Finance Skill Output</div>
        <h1>亚马逊流水毛利与 SKU 经营分析</h1>
        <div class="subtitle">
          这份页面把 Amazon 结算明细、SKU 成本和退货规则整合成更适合员工演示的经营驾驶舱，重点展示期间利润、退货损失、低毛利风险和单品查询。
        </div>
        <ul class="insights">{insight_list}</ul>
        <div class="hero-ribbon">
          <div class="hero-metric"><span>纳入分析行数</span><strong>{summary['included_rows']:,}</strong></div>
          <div class="hero-metric"><span>订单行数</span><strong>{summary['order_rows']:,}</strong></div>
          <div class="hero-metric"><span>退款行数</span><strong>{summary['refund_rows']:,}</strong></div>
        </div>
      </div>
      <div class="stats">
        <div class="stat"><div class="label">Amazon结算净额</div><div class="value">{fmt_money(summary['amazon_total'])}</div><div class="hint">平台流水汇总后的净额</div></div>
        <div class="stat"><div class="label">流水毛利</div><div class="value">{fmt_money(summary['gross_profit'])}</div><div class="hint">已纳入产品成本与头程成本</div></div>
        <div class="stat"><div class="label">产品成本影响</div><div class="value">{fmt_money(summary['product_cost_impact'])}</div><div class="hint">销售出库与退货回补后的净影响</div></div>
        <div class="stat"><div class="label">头程成本影响</div><div class="value">{fmt_money(summary['first_leg_cost_impact'])}</div><div class="hint">头程分摊后的净影响</div></div>
        <div class="stat"><div class="label">毛利率</div><div class="value">{fmt_pct(summary['gross_margin'])}</div><div class="hint">流水毛利 / 销售额</div></div>
        <div class="stat"><div class="label">未匹配成本行数</div><div class="value">{summary['missing_cost_rows']}</div><div class="hint">需要补成本映射后再复核</div></div>
      </div>
    </section>

    <div class="toolbar">
      <button class="action-button" id="print-dashboard">打印 / 保存 PDF</button>
      <button class="action-button primary" id="export-sku-csv">导出全部 SKU 明细</button>
    </div>

    <section class="panel soft">
      <div class="panel-head">
        <div>
          <h2>经营预警中心</h2>
          <div class="panel-note">点击任意 SKU，可直接跳到单品查询并查看原因</div>
        </div>
        <div class="panel-note">判断阈值：毛利率 &lt; 15%，退货率 ≥ 20%</div>
      </div>
      <div class="risk-overview">
        <article class="risk-card loss">
          <div class="risk-card-head"><span>亏损 SKU</span><strong>{summary['loss_skus']}</strong></div>
          <div class="risk-list">{render_risk_items(risk_summary['loss_making'], 'profit')}</div>
        </article>
        <article class="risk-card margin">
          <div class="risk-card-head"><span>低毛利 SKU</span><strong>{summary['low_margin_skus']}</strong></div>
          <div class="risk-list">{render_risk_items(risk_summary['low_margin'], 'margin')}</div>
        </article>
        <article class="risk-card return">
          <div class="risk-card-head"><span>高退货 SKU</span><strong>{summary['high_return_skus']}</strong></div>
          <div class="risk-list">{render_risk_items(risk_summary['high_return'], 'return')}</div>
        </article>
        <article class="risk-card cost">
          <div class="risk-card-head"><span>缺成本 SKU</span><strong>{summary['missing_cost_skus']}</strong></div>
          <div class="risk-list">{render_risk_items(risk_summary['missing_cost'], 'cost')}</div>
        </article>
      </div>
    </section>

    <section class="viz-grid">
      <div class="panel soft">
        <div class="panel-head">
          <h2>Top SKU 利润热区</h2>
          <div class="panel-note">按流水毛利从高到低展示</div>
        </div>
        {render_sku_bars(top_skus)}
      </div>
      <div class="panel soft">
        <div class="panel-head">
          <h2>类型影响雷达</h2>
          <div class="panel-note">正负影响一眼看清</div>
        </div>
        <div class="impact-stack">{render_type_tiles(type_rows)}</div>
      </div>
    </section>

    <section class="search-shell" id="sku-search">
      <div class="search-box">
        <div class="eyebrow">SKU Search</div>
        <h2 style="margin-top:16px;color:#fff;">直接搜索 SKU</h2>
        <p>输入完整 SKU 或部分关键字，就能直接看到该产品的订单量、净件数、流水毛利、毛利率和退货率。</p>
        <div class="search-field">
          <input id="sku-search-input" class="search-input" placeholder="例如：FI-XXZS-BLUE-01" autocomplete="off" />
          <div class="match-list" id="sku-match-list"></div>
        </div>
        <div class="search-suggestions">
          {"".join(f'<button class="pill sku-jump" data-sku="{row["sku"]}">{row["sku"]}</button>' for row in top_skus[:5])}
        </div>
      </div>
      <div class="search-panel">
        <div class="search-top">
          <div>
            <div class="sku-badge" id="sku-badge">SKU OVERVIEW</div>
            <h2 id="sku-title" style="margin-top:12px;">默认展示利润最高的 SKU</h2>
          </div>
          <div class="panel-note">支持模糊搜索，自动取最接近结果</div>
        </div>
        <div class="search-metrics">
          <div class="search-card"><div class="k">订单数</div><div class="v" id="metric-orders">-</div></div>
          <div class="search-card"><div class="k">净件数</div><div class="v" id="metric-net-units">-</div></div>
          <div class="search-card"><div class="k">销售额</div><div class="v" id="metric-sales">-</div></div>
          <div class="search-card"><div class="k">流水毛利</div><div class="v" id="metric-profit">-</div></div>
          <div class="search-card"><div class="k">毛利率</div><div class="v" id="metric-margin">-</div></div>
          <div class="search-card"><div class="k">退货率</div><div class="v" id="metric-return-rate">-</div></div>
        </div>
        <div class="search-meta">
          <div class="meta-box">
            <strong>经营摘要</strong>
            <ul id="sku-summary-points"></ul>
          </div>
          <div class="meta-box">
            <strong>成本与退货观察</strong>
            <ul id="sku-risk-points"></ul>
          </div>
        </div>
        <div class="empty-state" id="sku-empty">没有找到匹配的 SKU，请换一个关键词再试。</div>
      </div>
    </section>

    <section class="grid">
      <div class="panel">
        <div class="panel-head">
          <h2>Top SKU 利润贡献</h2>
          <div class="panel-note">适合做重点经营复盘</div>
        </div>
        <table>
          <thead>
            <tr><th>SKU</th><th>订单数</th><th>净件数</th><th>流水毛利</th><th>毛利率</th><th>退货率</th></tr>
          </thead>
          <tbody>
            {render_rows(top_skus, [('sku', 'text'), ('orders', 'int'), ('net_units', 'int'), ('gross_profit', 'money'), ('gross_margin', 'pct'), ('return_rate', 'pct')])}
          </tbody>
        </table>
      </div>
      <div class="panel">
        <div class="panel-head">
          <h2>类型影响</h2>
          <div class="panel-note">区分利润来源与损耗来源</div>
        </div>
        <table>
          <thead>
            <tr><th>类型</th><th>行数</th><th>Amazon净额</th><th>流水毛利</th></tr>
          </thead>
          <tbody>
            {render_rows(type_rows, [('type', 'text'), ('rows', 'int'), ('amazon_total', 'money'), ('gross_profit', 'money')])}
          </tbody>
        </table>
      </div>
    </section>

    <section class="grid">
      <div class="panel">
        <div class="panel-head">
          <h2>低毛利复核区</h2>
          <div class="panel-note">优先排查毛利偏低的 SKU</div>
        </div>
        <table>
          <thead>
            <tr><th>SKU</th><th>订单数</th><th>销售额</th><th>流水毛利</th><th>毛利率</th></tr>
          </thead>
          <tbody>
            {render_rows(low_margin, [('sku', 'text'), ('orders', 'int'), ('product_sales', 'money'), ('gross_profit', 'money'), ('gross_margin', 'pct')])}
          </tbody>
        </table>
      </div>
      <div class="panel">
        <div class="panel-head">
          <h2>期间结构</h2>
          <div class="panel-note">培训时可直接解释口径</div>
        </div>
        <table>
          <thead>
            <tr><th>指标</th><th>结果</th></tr>
          </thead>
          <tbody>
            <tr><td>纳入分析行数</td><td>{summary['included_rows']:,}</td></tr>
            <tr><td>忽略的转账行数</td><td>{summary['ignored_rows']:,}</td></tr>
            <tr><td>订单行数</td><td>{summary['order_rows']:,}</td></tr>
            <tr><td>退款行数</td><td>{summary['refund_rows']:,}</td></tr>
            <tr><td>退货费损失</td><td>{fmt_money(summary['return_fee_loss'])}</td></tr>
            <tr><td>服务费损失</td><td>{fmt_money(summary['service_fee_loss'])}</td></tr>
            <tr><td>库存费损失</td><td>{fmt_money(summary['inventory_fee_loss'])}</td></tr>
          </tbody>
        </table>
        <div class="footer">生成时间：{analysis['generated_at']}</div>
      </div>
    </section>
  </div>
  <script>
    const skuDataset = {search_payload};
    const money = (value) => new Intl.NumberFormat("en-US", {{ style: "currency", currency: "USD" }}).format(value || 0);
    const pct = (value) => value == null ? "-" : (value * 100).toFixed(1) + "%";
    const intFmt = (value) => new Intl.NumberFormat("en-US").format(value || 0);

    const els = {{
      input: document.getElementById("sku-search-input"),
      title: document.getElementById("sku-title"),
      badge: document.getElementById("sku-badge"),
      orders: document.getElementById("metric-orders"),
      netUnits: document.getElementById("metric-net-units"),
      sales: document.getElementById("metric-sales"),
      profit: document.getElementById("metric-profit"),
      margin: document.getElementById("metric-margin"),
      returnRate: document.getElementById("metric-return-rate"),
      summary: document.getElementById("sku-summary-points"),
      risks: document.getElementById("sku-risk-points"),
      empty: document.getElementById("sku-empty"),
      matches: document.getElementById("sku-match-list"),
    }};

    function skuNarrative(row) {{
      return [
        "销售额 " + money(row.product_sales) + "，Amazon净额 " + money(row.amazon_total) + "。",
        "订单数 " + intFmt(row.orders) + "，净件数 " + intFmt(row.net_units) + "。",
        "单件利润 " + money(row.profit_per_unit || 0) + "。",
      ];
    }}

    function skuRisks(row) {{
      const items = [
        "退货率 " + pct(row.return_rate) + "。",
        "毛利率 " + pct(row.gross_margin) + "。",
      ];
      if ((row.return_rate || 0) >= 0.2) items.push("退货率偏高，建议检查评价、尺码和售后原因。");
      if ((row.gross_margin || 0) < 0.15) items.push("毛利率偏低，建议复核定价、佣金和头程成本。");
      if ((row.gross_profit || 0) < 0) items.push("该 SKU 当前为亏损，建议暂停扩量并核对广告、售价与平台费用。");
      if ((row.missing_cost_rows || 0) > 0) items.push("存在 " + intFmt(row.missing_cost_rows) + " 行缺成本，当前毛利不可作为最终结论。");
      if ((row.gross_margin || 0) >= 0.3) items.push("毛利结构相对健康，可作为重点经营 SKU 观察。");
      return items;
    }}

    function renderSku(row) {{
      els.empty.style.display = "none";
      els.badge.textContent = row.risk_level + " · " + row.sku;
      els.badge.className = "sku-badge" + (row.risk_level === "高风险" ? " danger" : row.risk_level === "关注" ? " attention" : "");
      els.title.textContent = row.sku + " 单品经营概览";
      els.orders.textContent = intFmt(row.orders);
      els.netUnits.textContent = intFmt(row.net_units);
      els.sales.textContent = money(row.product_sales);
      els.profit.textContent = money(row.gross_profit);
      els.margin.textContent = pct(row.gross_margin);
      els.returnRate.textContent = pct(row.return_rate);
      els.summary.innerHTML = skuNarrative(row).map((item) => "<li>" + item + "</li>").join("");
      els.risks.innerHTML = skuRisks(row).map((item) => "<li>" + item + "</li>").join("");
    }}

    function showEmpty(term) {{
      els.title.textContent = "没有找到与 “" + term + "” 匹配的 SKU";
      els.badge.textContent = "NO MATCH";
      els.orders.textContent = "-";
      els.netUnits.textContent = "-";
      els.sales.textContent = "-";
      els.profit.textContent = "-";
      els.margin.textContent = "-";
      els.returnRate.textContent = "-";
      els.summary.innerHTML = "<li>请尝试输入更完整的 SKU，或只输入一段核心关键字。</li>";
      els.risks.innerHTML = "<li>当前没有可展示的数据。</li>";
      els.empty.style.display = "block";
    }}

    function findSku(term) {{
      const q = term.trim().toUpperCase();
      if (!q) return skuDataset[0];
      return skuDataset.find((row) => row.sku === q)
        || skuDataset.find((row) => row.sku.includes(q))
        || skuDataset.find((row) => q.includes(row.sku));
    }}

    function matchingSkus(term) {{
      const q = term.trim().toUpperCase();
      if (!q) return [];
      return skuDataset
        .filter((row) => row.sku.includes(q))
        .sort((a, b) => a.sku.indexOf(q) - b.sku.indexOf(q) || b.gross_profit - a.gross_profit)
        .slice(0, 8);
    }}

    function renderMatches(term) {{
      const matches = matchingSkus(term);
      if (!matches.length) {{
        els.matches.style.display = "none";
        els.matches.innerHTML = "";
        return;
      }}
      els.matches.innerHTML = matches.map((row) =>
        '<button class="match-item" data-sku="' + row.sku + '"><span>' + row.sku +
        '</span><small>' + money(row.gross_profit) + '</small></button>'
      ).join("");
      els.matches.style.display = "block";
      els.matches.querySelectorAll(".match-item").forEach((button) => {{
        button.addEventListener("click", () => selectSku(button.dataset.sku || "", false));
      }});
    }}

    function selectSku(sku, shouldScroll = true) {{
      els.input.value = sku;
      const row = findSku(sku);
      if (row) renderSku(row);
      els.matches.style.display = "none";
      if (shouldScroll) document.getElementById("sku-search").scrollIntoView({{ behavior: "smooth", block: "start" }});
    }}

    els.input.addEventListener("input", (event) => {{
      const term = event.target.value;
      const match = findSku(term);
      if (match) renderSku(match);
      else showEmpty(term);
      renderMatches(term);
    }});

    document.querySelectorAll(".sku-jump").forEach((button) => {{
      button.addEventListener("click", () => {{
        selectSku(button.dataset.sku || "");
      }});
    }});

    document.addEventListener("click", (event) => {{
      if (!event.target.closest(".search-field")) els.matches.style.display = "none";
    }});

    document.getElementById("print-dashboard").addEventListener("click", () => window.print());

    document.getElementById("export-sku-csv").addEventListener("click", () => {{
      const headers = ["SKU", "风险等级", "风险标签", "订单数", "退款数", "出库件数", "退回件数", "净件数", "销售额", "Amazon净额", "流水毛利", "毛利率", "退货率", "单件利润", "缺成本行数"];
      const rows = skuDataset.map((row) => [
        row.sku,
        row.risk_level,
        (row.risk_tags || []).join("|"),
        row.orders,
        row.refunds,
        row.order_units,
        row.refund_units,
        row.net_units,
        row.product_sales,
        row.amazon_total,
        row.gross_profit,
        row.gross_margin == null ? "" : row.gross_margin,
        row.return_rate == null ? "" : row.return_rate,
        row.profit_per_unit == null ? "" : row.profit_per_unit,
        row.missing_cost_rows || 0,
      ]);
      const escapeCsv = (value) => '"' + String(value ?? "").replaceAll('"', '""') + '"';
      const csv = "\\ufeff" + [headers, ...rows].map((row) => row.map(escapeCsv).join(",")).join("\\n");
      const url = URL.createObjectURL(new Blob([csv], {{ type: "text/csv;charset=utf-8" }}));
      const link = document.createElement("a");
      link.href = url;
      link.download = "amazon_sku_profit_analysis.csv";
      link.click();
      URL.revokeObjectURL(url);
    }});

    renderSku(skuDataset[0]);
  </script>
</body>
</html>
"""


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run_workbook_builder(skill_dir: Path, analysis_path: Path, workbook_path: Path) -> None:
    runtime_root = Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies"
    node_candidates = [
        os.environ.get("CODEX_NODE_BIN"),
        str(runtime_root / "node" / "bin" / "node"),
        shutil.which("node"),
    ]
    node_bin = next((Path(item) for item in node_candidates if item and Path(item).is_file()), None)
    module_candidates = [
        os.environ.get("CODEX_NODE_MODULES"),
        str(runtime_root / "node" / "node_modules"),
    ]
    node_modules = next((Path(item) for item in module_candidates if item and Path(item).is_dir()), None)
    if node_bin is None or node_modules is None:
        raise RuntimeError(
            "Codex spreadsheet runtime not found. Load workspace dependencies and set "
            "CODEX_NODE_BIN and CODEX_NODE_MODULES before running this skill."
        )

    run_dir = workbook_path.parent / ".artifact-tool-runtime"
    run_dir.mkdir(parents=True, exist_ok=True)
    link_path = run_dir / "node_modules"
    if link_path.is_symlink() and link_path.resolve() != node_modules.resolve():
        link_path.unlink()
    if not link_path.exists():
        link_path.symlink_to(node_modules)
    script_path = run_dir / "build_workbook.mjs"
    shutil.copy2(skill_dir / "scripts" / "build_workbook.mjs", script_path)
    subprocess.run(
        [str(node_bin), str(script_path), str(analysis_path), str(workbook_path)],
        cwd=run_dir,
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Amazon finance analysis outputs.")
    parser.add_argument("--report-xlsx", required=True)
    parser.add_argument("--report-sheet", required=True)
    parser.add_argument("--cost-xlsx", required=True)
    parser.add_argument("--cost-sheet", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    skill_dir = Path(__file__).resolve().parents[1]
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    cost_map = read_cost_map(Path(args.cost_xlsx), args.cost_sheet)
    rows = read_detail_rows(Path(args.report_xlsx), args.report_sheet, cost_map)
    analysis = build_analysis(rows)

    analysis_path = output_dir / "analysis.json"
    html_path = output_dir / "amazon_finance_dashboard.html"
    workbook_path = output_dir / "amazon_finance_profit_analysis.xlsx"

    write_json(analysis_path, analysis)
    html_path.write_text(build_html(analysis), encoding="utf-8")
    run_workbook_builder(skill_dir, analysis_path, workbook_path)

    print(json.dumps(
        {
            "analysis_json": str(analysis_path),
            "html": str(html_path),
            "xlsx": str(workbook_path),
        },
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
