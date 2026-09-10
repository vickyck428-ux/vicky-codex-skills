---
name: financial-analysis
description: Analyze Amazon settlement reports together with SKU cost sheets and accounting rules to calculate running gross profit, refund impact, return-fee losses, and SKU-level profitability. Use when Codex needs to turn Amazon financial exports (`.xlsx`, `.csv`) plus product-cost mappings into employee-facing Excel or HTML analysis, especially for order/refund/customer-return-fee workflows and low-margin SKU diagnosis.
---

# 财务分析 Skill

Use the bundled scripts to convert an Amazon settlement detail sheet and a SKU cost sheet into:

- A row-level profit analysis table
- A SKU summary with gross profit, margin, return rate, missing-cost checks, and risk tags
- An employee-facing Excel workbook
- A browser-ready HTML dashboard with SKU search, risk drill-down, print, and CSV export

Keep the workflow deterministic. Reuse the provided scripts instead of rewriting parsing or workbook-generation logic.

Before any sales, profit, return-rate, success-rate, or SKU summary, exclude `pencil case`, `pencil pouch`, `pen case`, `pen pouch`, and `pen bag`. If physical legacy inventory exists, report it only as `历史遗留清退`; never include it in normal operating totals.

## 快速用法

```text
$financial-analysis
请分析这两份亚马逊财务表，生成 Excel 利润核算表和 HTML 可视化看板，并重点标出亏损 SKU、低毛利 SKU、高退货 SKU、缺失成本 SKU。
```

## Workflow

1. Read [references/finance-rules.md](references/finance-rules.md) before interpreting transaction types.
2. Inspect the input workbook and locate:
   - The transaction detail sheet with headers such as `type`, `order id`, `sku`, `quantity`, and `total`
   - The cost sheet with `SKU`, unit product cost, and first-leg cost
3. Run `scripts/run_finance_analysis.py` to produce normalized JSON, HTML, and Excel outputs.
4. Review the generated summary:
   - Confirm `Transfer` rows are excluded
   - Confirm `Order` rows consume product and first-leg cost
   - Confirm `Refund` rows add costs back
   - Confirm `FBA Customer Return Fee` remains a standalone loss
5. If margin outliers or missing costs appear, use the SKU summary and missing-cost section to explain the issue.
6. Use the risk center to prioritize loss-making, low-margin, high-return, and missing-cost SKUs.

## Input Expectations

- Transaction sheet:
  - One header row
  - Columns for `type`, `order id`, `sku`, `quantity`, `product sales`, and `total`
- Cost sheet:
  - One SKU per row
  - Unit product cost in USD
  - Unit first-leg cost in USD
- Optional rule transcript or notes file for audit context

If headers are not in English, map them explicitly before running the scripts or adapt the parser in `scripts/run_finance_analysis.py`.

## Calculation Rules

- Use Amazon `total` as the post-platform-fee settlement amount for the row.
- Apply cost impact by transaction type:
  - `Order`, `Pedido`, `Liquidations`: subtract product cost and first-leg cost
  - `Refund`, `Refund_Retrocharge`: add product cost and first-leg cost back
  - `FBA Customer Return Fee`: keep as a direct loss with no cost reversal
  - `Transfer`: exclude from profitability
  - `Adjustment`, `Service Fee`, `FBA Inventory Fee`, blank or unknown administrative rows: keep `total` only unless business rules say otherwise
- Define row gross profit as:
  - `gross_profit = total + signed_product_cost + signed_first_leg_cost`

Read [references/finance-rules.md](references/finance-rules.md) when you need the business explanation behind these signs.

## Commands

Use the bundled Python runtime when available. The main entrypoint is:

```bash
python3 scripts/run_finance_analysis.py \
  --report-xlsx /path/to/report.xlsx \
  --report-sheet 财务报表 \
  --cost-xlsx /path/to/cost.xlsx \
  --cost-sheet 成本表 \
  --output-dir /path/to/output
```

The script writes:

- `analysis.json`
- `amazon_finance_dashboard.html`
- `amazon_finance_profit_analysis.xlsx`

## Output Interpretation

- `Summary` / dashboard output:
  - Headline settlement amount
  - Product-cost impact
  - First-leg-cost impact
  - Running gross profit
- `SKU Analysis`:
  - Focus on SKUs with enough order volume to be meaningful
  - Prioritize low-margin SKUs and high return-rate SKUs
- `Missing Costs`:
  - Any SKU without a cost match weakens the gross-profit result
  - Fix the cost sheet first, then rerun the analysis

## Resources

- `references/finance-rules.md`: business logic extracted from the meeting transcript
- `scripts/run_finance_analysis.py`: parser, aggregator, insight builder, and HTML generator
- `scripts/build_workbook.mjs`: employee-facing Excel generator using `@oai/artifact-tool`

Only patch the parsing logic when the source workbook structure genuinely differs. Do not create ad hoc formulas manually if the bundled scripts already cover the calculation path.
