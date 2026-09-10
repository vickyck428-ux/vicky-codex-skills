---
name: amazon-inventory-orchestrator
description: Orchestrate the read-only Amazon inventory workflow across clearance, replenishment, repricing, and FBM reminders through inventory-ai-runner. Use when the user asks for a weekly inventory run, a single-SKU recalculation, a representative-SKU pilot, or a combined clearance/replenishment/repricing decision. Process exactly one sellerId and marketplace per run.
---

# Amazon Inventory Orchestrator

Use this Skill as a thin entrypoint. Keep `inventory-ai-runner` as the only
calculation, snapshot, and state center. Do not reproduce or modify the
clearance, replenishment, or repricing formulas in this Skill.

## Resolve the run

1. Resolve exactly one `sellerId + marketplace` from the user request or config.
   If neither supplies an unambiguous scope, ask the user to select one store
   and site. Never traverse all stores implicitly.
2. Choose one run type:
   - `WEEKLY_FULL`: complete store/site weekly shadow run.
   - `SKU`: incremental recalculation; require one Seller SKU.
   - `PILOT`: representative-SKU validation; require one Seller SKU.
3. Collect the inventory/age report, SKU mapping, sales windows, and config.
   Add costs, exact fees, current effective prices, competitor events, and
   image cache when available.
   Competitor events must be assessed once through
   `$amazon-competitor-monitor`; do not copy its seller-level FBA-transition
   scoring into clearance, replenishment, or repricing.
4. Reject a formal conclusion when the inventory-age snapshot is more than
   seven days old or SKU/ASIN/snapshot identities conflict. A confirmed A-grade
   competitor observation older than four days may remain in the review queue
   but cannot produce a formal price suggestion.

Before invoking any calculator, remove pencil-case records from the normal SKU set. They may appear only in a separate `历史遗留清退` output and must not affect sales, profit, success rate, inventory, selection, or replenishment totals.

## Run the canonical workflow

From `${INVENTORY_AI_RUNNER}`, call:

```text
node run_inventory_decision.mjs \
  --mode <WEEKLY_FULL|SKU|PILOT> \
  --report <inventory-age-report.csv> \
  --mapping <sku-mapping.json> \
  --windows <sales-windows.json> \
  --config <inventory-ai.config.json> \
  --as-of-date <YYYY-MM-DD> \
  --output-dir <shadow-output-directory>
```

Pass `--pricing`, `--competitors`, and `--image-cache` when supplied. For
`SKU` and `PILOT`, also pass `--sku`. Pass `--pilot-baseline` only in `PILOT`
and only when its snapshot date matches the current report.

The runner must call the canonical exported calculators:
`calculateClearance`, `calculateReplenishmentScenarios`, and repricing
`calculate`. Never use a copied formula or a silent fallback.

## Interpret decisions

- Treat `clearance_decision.main_status` as the only inventory master status.
- For `紧急清退`, `主动清货`, or `停补观察`, require replenishment quantities and
  FBM reminders to be zero.
- For `待补货`, explain both the 7-day fast and 14-day formal scenarios.
- Carry `competitor_fba_transition_risk`, reasons, stress-test requirement,
  and manual-quantity-review flag into the replenishment decision. A high-risk
  result may recommend a smaller trial, but must preserve the calculator's
  original quantities until the user confirms a conservative quantity.
- Route repricing only for urgent/active clearance, low-stock replenishment
  risk with recent sales, or a confirmed A-grade competitor price/delivery
  anomaly.
- A confirmed A-grade `FBM→FBA` event routes repricing review and
  replenishment recalculation. FBA-transition risk alone never changes the
  clearance master status and never opens the clearance route.
- Treat `TEMP_A` results as provisional. Treat B/C competitors as manual-review
  evidence only. Allow a healthy SKU to return `HOLD`.
- If cost, exact fees, current effective price, fresh confirmed-A evidence, or
  identity checks are missing, keep formal price fields empty and report the
  blocking codes.

## Preserve safety and state

- Generate read-only previews only. Never purchase, create an FBA shipment,
  change a price, or activate/modify an FBM offer.
- Keep project-level `price_write` as `FORBIDDEN` even if a calculation is
  otherwise ready.
- Never recommend, create, or execute an own-store Coupon.
- Use `inventory-actions.json` schema `1.1.0`; do not create a parallel state
  file.
- Preserve user decisions and historical snapshots idempotently. Do not
  overwrite them during a model refresh.
- Reuse the existing `ai` heartbeat. Do not create another automation.
- Keep full-store output in a shadow directory until representative-SKU review
  and safety checks pass.
- The Feishu operations dashboard and HTML dashboard are retired. Never build,
  validate, sync, publish, link, or refresh them. `dashboard-payload.json` may
  remain an internal compatibility payload, but it is not a user entrypoint.
- Generate reports with `build_inventory_skill_workbooks.mjs` in
  `SEPARATE_WORKBOOKS` mode. Never create or send a combined workbook.

## Report the result

State the run type, seller/site, as-of date, source snapshot, status counts,
replenishment count, repricing queue/ready counts, blockers, and confirmation
that all write policies remained forbidden. Link `inventory-actions.json`, then
show three independent attachment sections in this order: repricing,
replenishment, clearance. Each section must contain only its own summary and
XLSX. On Thursday, send a changed-domain workbook only when that domain changed;
otherwise send the domain-specific text `本周期无关键变化`. Feishu delivery is
three independent bot file messages to the configured Vicky `open_id` and must
use domain-level idempotency. Do not link `dashboard-payload.json` to the user.
