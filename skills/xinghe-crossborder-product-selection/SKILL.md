---
name: xinghe-crossborder-product-selection
description: "Use Sorftime data to produce up to 10 cross-border product directions and competitor links from an explicit platform, region, and category or keyword. Use for Sorftime、跨平台十个方向或十个建议产品；do not use for ordinary Amazon selection, one-off refined-handbag orchestration, or 1688 operational closure."
---

# 星河跨境电商选品自动化

## Purpose

Use Sorftime MCP data to turn a user-provided platform, region, and category/product keyword into a Chinese list of exactly 10 recommended product opportunities with competitor links.

The skill exposes one customer-facing workflow. Do not ask the user to choose between category analysis and product analysis. Always decide the path from the input and always aim to output 10 recommended sub-product directions.

## First-run Sorftime setup

Before data collection, check whether Sorftime is configured globally.

Resolve all script paths relative to this `SKILL.md` file. If using a shell, first change into the directory that contains this `SKILL.md`, or call the scripts with their absolute paths. Use the available Python interpreter in the Codex environment; if `python` is not on PATH, use the bundled Python executable provided by Codex.

1. Run `python scripts/test_sorftime.py --scope global`.
2. If it reports missing configuration or invalid key, ask the user for their Sorftime MCP key.
3. Run `python scripts/setup_sorftime.py --scope global --key "<USER_KEY>"`.
4. Run `python scripts/test_sorftime.py --scope global` again.
5. Continue only after the test succeeds.

Never place a real Sorftime key in plugin files or final reports.

## Inputs

Extract these from the user request:

- `platform`: one of `amazon`, `tiktok`, `shopee`, `walmart`, `temu`, `1688`.
- `region`: marketplace or site code.
- `query`: category or product keyword.
- `mode`: `auto` by default.

Platform and region are required. If either is missing, ask the user to provide it before running any Sorftime data collection. Do not choose a default platform or region for the user.

## Workflow

Run:

```bash
python scripts/selection_workflow.py --platform PLATFORM --region REGION --query "QUERY" --mode auto --limit 10
```

Use the returned JSON as evidence. Prefer the `candidates` field when present, and use raw `evidence` to fill in missing reasoning. If a platform tool fails or returns sparse data, state that limitation and use the remaining evidence instead of inventing metrics.

### Mode selection

- Broad category input: analyze category evidence first, identify opportunity sub-directions, then output 10 recommended sub-product directions.
- Product keyword input: directly analyze same-type products, keywords, similar products, and competitors, then output 10 recommended sub-product directions.
- Ambiguous input: run category and product evidence where the platform supports both, then decide whether the input behaves more like a category or a product keyword.

## Platform routing

- Amazon: use category, category report, keyword, product, review evidence. Amazon-specific terms such as ASIN, FBA, CPC, review count, Amazon-owned share are allowed.
- TikTok Shop: use category, product, trend, video/author evidence. Focus on content-driven demand, creator/video momentum, and recent trend signals.
- Shopee: use category, product, keyword, and shop evidence. Focus on price band, local/cross-border seller mix, monthly sales, and review thresholds.
- Walmart: use category, keyword, product, trend, and traffic evidence. Focus on search demand, product count, price band, and direct competitors.
- Temu: use category, product, shop, and trend evidence. Focus on low-price competition, product velocity, and differentiable offer structure.
- 1688: treat as an independent product-selection platform. Use product search, product detail, similar product, variations, supplier/service indicators, recent sales, repurchase, price band, and SKU richness.

## Chinese report format

Always answer in Chinese with this structure:

1. **平台/地区/关键词确认**
2. **输入判断**: 类目词 / 产品关键词，并说明判断依据
3. **10个建议做的产品清单**
4. **每个产品的数据依据**: use only platform-appropriate fields
5. **对标竞品链接**: include at least one link per product when data allows
6. **差异化切入建议**
7. **主要风险**
8. **下一步行动**

For each of the 10 product directions, include:

- 产品方向
- 推荐指数/进入判断
- 数据依据
- 对标竞品链接或对标搜索链接
- 可以怎么做出差异化
- 主要风险

If fewer than 10 credible opportunities can be supported by data, output all credible opportunities and explicitly state "有效机会不足10个". Do not fabricate product directions or metrics to reach 10.

Do not force Amazon-only concepts onto other platforms. For non-Amazon platforms, use that platform's native fields and explain missing data clearly.

## Competitor link rules

- Prefer real product URLs returned by Sorftime.
- Amazon: if only ASIN is available, generate `https://www.amazon.com/dp/{ASIN}`. If no ASIN or product URL is available, generate an Amazon search link and label it `搜索链接兜底`.
- TikTok Shop, Shopee, Walmart, and Temu: prefer product URL. If no product URL is available, generate a platform search link and label it `搜索链接兜底`.
- 1688: prefer offer/product URL or product ID. If unavailable, generate a 1688 search link and label it `搜索链接兜底`.
- Never present a fallback search link as a confirmed exact competitor product.

## Scoring guidance

Score each candidate from 1 to 10 using available evidence:

- Demand strength: sales, search volume, trend, or platform-native demand signal.
- Competition pressure: competitor count, concentration, review/ratings threshold, seller/brand concentration, price crowding.
- Profit/price room: average price, price band, cost/supplier data where available.
- Entry feasibility: low-review/new-seller opportunity, supply availability, SKU complexity, operational risk.
- Differentiation: visible pain points, weak listings, content gaps, packaging/specification gaps.

Decision mapping:

- `7.5-10`: 建议进入
- `6.0-7.4`: 谨慎进入
- `4.0-5.9`: 暂缓观望
- `<4.0`: 不建议进入

## Failure handling

- Missing key: ask for Sorftime key and run setup.
- Invalid key: ask the user to verify or provide a new key.
- Unsupported region: state supported regions for that platform and ask for one.
- No data: try one broader query and one narrower query; if still sparse, output "数据不足，暂不建议决策".
- Partial data: produce a cautious report and label which fields are missing.
