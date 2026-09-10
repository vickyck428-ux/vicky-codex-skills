---
name: lc-amazon-market-check
description: Check Amazon US/UK/DE image-search candidates, confirm exact same products with the Volcano vision model, enrich confirmed ASINs with public Amazon and SellerSprite fulfillment/sales/rank data, and calculate data-completeness-safe channel inputs. Use after Google screening or when retrying Amazon FBA/FBM/SellerSprite enrichment.
---

# Lc Amazon Market Check

Reuse `$lc-amazon-data-crawl`; do not create another Amazon crawler.

## Scope

- Default to the first 10 Amazon image-search results; use 48 only when the product flag is explicitly enabled.
- Use `doubao-embedding-vision-251215` only for same-product confidence.
- Use public Amazon pages and SellerSprite for FBA, FBM, Amazon Retail, 30-day sales, BSR, reviews, and launch date.
- Aggregate fulfillment and sales only from confirmed same-product ASINs.

## Completeness gate

Treat `****`, plugin timeout, SellerSprite logout, Amazon buyer-login prompts, blank fulfillment, or required sales/rank fields as incomplete. Put only the affected confirmed ASIN/product in the enrichment retry queue and set `AMAZON_DATA_INCOMPLETE`.

Never log in to, request, store, or use an Amazon buyer account. A buyer-login page is a forbidden page, not a manual login pause.

Do not generate strong Amazon FBA or Walmart WFS conclusions from incomplete data. Write results to SQLite and Outbox only; do not write Feishu directly.

## Parser and reconciliation safeguards

- Support and test both SellerSprite table rows and current `.quick-view.quick-view-ext` cards. A plugin node count greater than zero with zero parsed rows is selector/schema drift, not proof that SellerSprite has no data.
- Separate completeness by field group: public fulfillment/BSR/review/seller fields may be usable while 30-day sales remains masked. Preserve usable fields, mark masked sales explicitly, and keep WFS or other sales-dependent conclusions incomplete.
- Store concrete incomplete reasons per ASIN: masked sales, plugin logout, plugin timeout, buyer-login prompt ignored, missing fulfillment, missing BSR, or selector mismatch. Do not collapse every case into one generic message.
- Never satisfy missing sales by Amazon buyer login. Retry the public page, repair selectors, or keep the sales-dependent decision incomplete.
- Amazon evidence collected before Google reaches `GOOGLE_DONE`/`MANUAL_REVIEW` is provisional. After Google completes, reuse and reconcile it; a later `RISK_STOPPED` invalidates all Amazon/channel recommendations without deleting the audit evidence.
