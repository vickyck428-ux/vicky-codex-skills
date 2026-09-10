# Amazon Finance Rules

Use these rules when calculating流水毛利 from Amazon settlement detail rows.

## Core Principle

Treat Amazon `total` as the row's post-platform-fee settlement result. Then adjust inventory-related costs based on transaction type.

## Transaction Rules

- `Order`
  - Treat as an outbound sale.
  - Subtract product cost.
  - Subtract first-leg cost.
- `Refund`
  - Treat as an inbound return.
  - Add product cost back because saleable inventory returns.
  - Add first-leg cost back for the same reason.
- `FBA Customer Return Fee`
  - Treat as an extra loss caused by the return logistics.
  - Do not reverse product cost or first-leg cost here.
- `Liquidations`
  - Treat as low-price inventory disposal.
  - Match product cost and first-leg cost.
  - Profit is usually negative after costs.
- `Adjustment`, `Ajuste`, `Fee Adjustment`
  - Keep Amazon `total` as-is unless a later business rule says otherwise.
- `Service Fee`, `FBA Inventory Fee`
  - Keep Amazon `total` as-is.
- `Transfer`
  - Ignore for profitability because it is a payout movement, not operating profit.
- Blank type or miscellaneous non-inventory rows
  - Keep Amazon `total` only.

## Profit Formula

For each included row:

`gross_profit = total + signed_product_cost + signed_first_leg_cost`

Sign rules:

- outbound sale: negative cost impact
- returned inventory: positive cost impact
- non-inventory fee row: zero cost impact

## Analysis Goals

- Reconcile a period-level 流水毛利
- Identify profitable vs low-margin SKUs
- Flag SKUs with high return rate
- Show where cost pressure comes from
- Flag SKUs missing cost mappings before trusting results
