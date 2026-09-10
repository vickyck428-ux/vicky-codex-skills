#!/usr/bin/env python3
"""Collect Sorftime evidence for cross-border product selection."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from typing import Any

from sorftime_client import call_tool


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


DEFAULT_REGION = {
    "amazon": "US",
    "tiktok": "US",
    "shopee": "MY",
    "walmart": "US",
    "temu": "US",
    "1688": "",
}


SEARCH_URLS = {
    "amazon": "https://www.amazon.com/s?k={query}",
    "tiktok": "https://www.tiktok.com/shop/s/{query}",
    "shopee": "https://shopee.com/search?keyword={query}",
    "walmart": "https://www.walmart.com/search?q={query}",
    "temu": "https://www.temu.com/search_result.html?search_key={query}",
    "1688": "https://s.1688.com/selloffer/offer_search.htm?keywords={query}",
}


TITLE_KEYS = (
    "title",
    "name",
    "product_name",
    "productName",
    "goods_name",
    "item_name",
    "keyword",
    "category_name",
    "categoryName",
)


URL_KEYS = (
    "url",
    "product_url",
    "productUrl",
    "goods_url",
    "item_url",
    "link",
    "detail_url",
    "offer_url",
)


ASIN_KEYS = ("asin", "ASIN", "parent_asin", "parentAsin")


ID_KEYS = (
    "product_id",
    "productId",
    "goods_id",
    "goodsId",
    "item_id",
    "itemId",
    "offer_id",
    "offerId",
)


REGION_ALIASES = {
    "美国": "US",
    "美区": "US",
    "英国": "GB",
    "日本": "JP",
    "德国": "DE",
    "法国": "FR",
    "加拿大": "CA",
    "墨西哥": "MX",
    "澳大利亚": "AU",
    "马来": "MY",
    "马来西亚": "MY",
    "菲律宾": "PH",
    "越南": "VN",
    "印尼": "ID",
    "泰国": "TH",
}


PLATFORM_ALIASES = {
    "amazon": "amazon",
    "亚马逊": "amazon",
    "tiktok": "tiktok",
    "tiktok shop": "tiktok",
    "tk": "tiktok",
    "抖音海外": "tiktok",
    "shopee": "shopee",
    "虾皮": "shopee",
    "walmart": "walmart",
    "沃尔玛": "walmart",
    "temu": "temu",
    "1688": "1688",
    "阿里巴巴": "1688",
}


def norm_platform(platform: str) -> str:
    value = platform.strip().lower()
    if value in PLATFORM_ALIASES:
        return PLATFORM_ALIASES[value]
    raise ValueError(f"Unsupported platform: {platform}")


def norm_region(region: str | None, platform: str) -> str:
    if not region:
        return DEFAULT_REGION[platform]
    value = region.strip()
    return REGION_ALIASES.get(value, value.upper())


def safe_call(name: str, args: dict[str, Any]) -> dict[str, Any]:
    try:
        data = call_tool(name, args)
        if isinstance(data, dict) and data.get("error"):
            return {"ok": False, "tool": name, "arguments": args, "error": data.get("error")}
        if isinstance(data, str) and (
            "error occurred invoking" in data.lower()
            or "使用次数已达到上限" in data
            or "authentication required" in data.lower()
            or "notauthorization" in data.lower()
            or "not acceptable" in data.lower()
        ):
            return {"ok": False, "tool": name, "arguments": args, "error": data}
        return {"ok": True, "tool": name, "arguments": args, "data": data}
    except Exception as exc:
        return {"ok": False, "tool": name, "arguments": args, "error": str(exc)}


def flatten_records(value: Any, limit: int = 300) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    def visit(node: Any) -> None:
        if len(records) >= limit:
            return
        if isinstance(node, dict):
            if any(key in node for key in TITLE_KEYS + URL_KEYS + ASIN_KEYS + ID_KEYS):
                records.append(node)
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(value)
    return records


def first_value(record: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def search_link(platform: str, query: str) -> str:
    encoded = urllib.parse.quote(query)
    return SEARCH_URLS[platform].format(query=encoded)


def competitor_link(platform: str, record: dict[str, Any], query: str) -> dict[str, str]:
    direct = first_value(record, URL_KEYS)
    if direct.startswith("http"):
        return {"url": direct, "source": "真实商品链接"}

    if platform == "amazon":
        asin = first_value(record, ASIN_KEYS)
        if asin:
            return {"url": f"https://www.amazon.com/dp/{asin}", "source": "ASIN商品链接"}

    if platform == "1688":
        product_id = first_value(record, ID_KEYS)
        if product_id:
            return {"url": f"https://detail.1688.com/offer/{product_id}.html", "source": "商品ID链接"}

    return {"url": search_link(platform, query), "source": "搜索链接兜底"}


def evidence_summary(record: dict[str, Any]) -> str:
    useful_keys = (
        "price",
        "min_price",
        "max_price",
        "sales",
        "monthly_sales",
        "recent_30_day_sale",
        "rating",
        "review_count",
        "reviews",
        "rank",
        "brand",
        "shop_name",
        "supplier_name",
    )
    parts = []
    for key in useful_keys:
        value = record.get(key)
        if value not in (None, "", [], {}):
            parts.append(f"{key}: {value}")
    return "；".join(parts[:6]) if parts else "Sorftime 返回了相关商品/类目证据，但可量化字段有限。"


def build_candidates(platform: str, query: str, evidence: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    seen: set[str] = set()
    candidates: list[dict[str, Any]] = []

    for item in evidence:
        if not item.get("ok"):
            continue
        records = flatten_records(item.get("data"))
        for record in records:
            title = first_value(record, TITLE_KEYS)
            if not title:
                continue
            dedupe_key = title.strip().lower()
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            link = competitor_link(platform, record, title or query)
            candidates.append(
                {
                    "product_direction": title,
                    "recommendation": "待结合报告综合判断",
                    "evidence_summary": evidence_summary(record),
                    "competitor_links": [link],
                    "differentiation_hint": "围绕规格、套装、材质、安装方式、场景表达或供应链价格带做差异化。",
                    "risk_hint": "需复核真实销量、评价门槛、价格带和平台合规要求。",
                    "source_tool": item.get("tool", ""),
                }
            )
            if len(candidates) >= limit:
                return candidates

    if not candidates:
        candidates.append(
            {
                "product_direction": query,
                "recommendation": "数据不足，需谨慎判断",
                "evidence_summary": "未从 Sorftime 返回结果中提取到可结构化商品方向。",
                "competitor_links": [{"url": search_link(platform, query), "source": "搜索链接兜底"}],
                "differentiation_hint": "先用更具体的产品词重新查询，再判断差异化方向。",
                "risk_hint": "当前有效机会不足10个，不能仅凭兜底搜索链接做选品决策。",
                "source_tool": "fallback",
            }
        )

    return candidates


def collect_amazon(query: str, region: str, mode: str) -> list[dict[str, Any]]:
    calls = []
    if mode in {"auto", "category"}:
        calls.append(("category_search_from_product_name", {"product_name": query, "amz_site": region, "page": 1}))
    if mode in {"auto", "keyword"}:
        calls.append(("keyword_detail", {"keyword": query, "keyword_support_site": region}))
        calls.append(("product_search_from_name", {"name": query, "amz_site": region, "page": 1}))
    return [safe_call(name, args) for name, args in calls]


def collect_tiktok(query: str, region: str, mode: str) -> list[dict[str, Any]]:
    calls = []
    if mode in {"auto", "category"}:
        calls.append(("tiktok_category_search_from_name", {"name": query, "site": region}))
    if mode in {"auto", "keyword"}:
        calls.append(("tiktok_similar_product", {"product_name": query, "site": region, "page": 1}))
    return [safe_call(name, args) for name, args in calls]


def collect_shopee(query: str, region: str, mode: str) -> list[dict[str, Any]]:
    calls = []
    if mode in {"auto", "category"}:
        calls.append(("shopee_category_search_from_name", {"name": query, "site": region, "page": 1}))
    if mode in {"auto", "keyword"}:
        calls.append(("shopee_product_search_from_name", {"name": query, "site": region, "page": 1}))
        calls.append(("shopee_keyword_search", {"keyword": query, "site": region, "page": 1}))
    return [safe_call(name, args) for name, args in calls]


def collect_walmart(query: str, region: str, mode: str) -> list[dict[str, Any]]:
    calls = []
    if mode in {"auto", "category"}:
        calls.append(("walmart_category_search_from_name", {"name": query, "page": 1}))
    if mode in {"auto", "keyword"}:
        calls.append(("walmart_product_search_from_name", {"name": query, "page": 1}))
        calls.append(("walmart_keyword_detail", {"keyword": query}))
    return [safe_call(name, args) for name, args in calls]


def collect_temu(query: str, region: str, mode: str) -> list[dict[str, Any]]:
    calls = []
    if mode in {"auto", "category"}:
        calls.append(("temu_category_search_from_name", {"name": query, "site": region, "page": 1}))
    if mode in {"auto", "keyword"}:
        calls.append(("temu_product_search_from_name", {"name": query, "site": region, "page": 1}))
    return [safe_call(name, args) for name, args in calls]


def collect_1688(query: str, region: str, mode: str) -> list[dict[str, Any]]:
    return [
        {
            "ok": True,
            "tool": "input_note",
            "arguments": {"query": query},
            "data": "1688 MCP currently supports category/product-id/filter based search. Use the query as semantic context when judging returned product/supplier evidence.",
        },
        safe_call("ali1688_category_tree", {}),
        safe_call("ali1688_product_search", {"product_id": "", "node_id": "", "supplier_name": "", "page": 1, "recent_30_day_sale_min": 0, "cumulative_sale_count_min": 0, "dropshipping_price_range_min": 0, "dropshipping_price_range_max": 0, "sku_count_min": 0, "sku_count_max": 0, "online_date_range_min": "", "online_date_range_max": "", "rights": "", "supplier_type": 0, "supplier_member_type": 0, "service_score_min": 0, "service_score_max": 0, "repurchase_rate_min": 0, "repurchase_rate_max": 0, "stock_count_min": 0, "stock_count_max": 0}),
    ]


COLLECTORS = {
    "amazon": collect_amazon,
    "tiktok": collect_tiktok,
    "shopee": collect_shopee,
    "walmart": collect_walmart,
    "temu": collect_temu,
    "1688": collect_1688,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect cross-border product-selection evidence from Sorftime.")
    parser.add_argument("--platform", required=True, help="amazon, tiktok, shopee, walmart, temu, or 1688")
    parser.add_argument("--region", required=True, help="Marketplace/site code, such as US, MY, PH, GB.")
    parser.add_argument("--query", required=True, help="Category or product keyword.")
    parser.add_argument("--mode", choices=["auto", "category", "keyword"], default="auto")
    parser.add_argument("--limit", type=int, default=10, help="Number of recommended product directions to return.")
    args = parser.parse_args()

    platform = norm_platform(args.platform)
    region = norm_region(args.region, platform)
    evidence = COLLECTORS[platform](args.query, region, args.mode)
    candidates = build_candidates(platform, args.query, evidence, args.limit)
    payload = {
        "platform": platform,
        "region": region,
        "query": args.query,
        "mode": args.mode,
        "limit": args.limit,
        "input_interpretation": "类目词优先走类目数据；产品关键词直接走同类商品/关键词/竞品数据。最终报告必须输出10个细分产品方向。",
        "candidate_count": len(candidates),
        "candidate_note": "" if len(candidates) >= args.limit else "有效机会不足10个；请在报告中明确说明数据不足。",
        "candidates": candidates,
        "evidence": evidence,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
