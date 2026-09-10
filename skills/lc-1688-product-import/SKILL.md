---
name: lc-1688-product-import
description: Import 1688 single-product or whole-store Excel/CSV data into the persistent product-selection state database, preserving parent products, exact skuProps/skuInfoMap/specId/skuId relationships, representative images, and cross-store duplicate-listing detection. Use when the user supplies a 1688 link,采购助手 export, store export, or asks to import/deduplicate 1688 products before selection.
---

# Lc 1688 Product Import

Use the project importer through `$lc-product-selection-orchestrator` or `selectionctl start`.

## Invariants

- Store one row per parent product and all true variants in SQLite `skus`.
- Parse SKU relationships only from `skuProps`, `skuInfoMap`, `specId`, and `skuId`. Never infer them from color text.
- Mark SKU data `MISSING` or `INVALID` when the export lacks the real relationship; do not invent variants.
- Missing/invalid SKU relationships do not block parent-level Google Lens or Amazon market screening when the offer link and representative image are valid. They do block SKU-level listing, purchasing, inventory, and shipping outputs until the source is re-exported or the real `skuProps`/`skuInfoMap`/`specId`/`skuId` relationship is recovered.
- Choose one representative image per parent. Reuse it across colors with the same structure; add another only when the structure changes.
- Preserve every available gallery image URL and its source label/order in the raw product input for downstream Google Lens selection. Do not discard later images merely because a main image already exists; downstream Lens should prefer a frontal view or clean white-background image independent of gallery position.
- Download the representative image URL from Excel into the persistent local image cache before hashing. A download failure must remain explicit and must not be treated as a unique-product conclusion.
- Deduplicate before Google in this order: exact offer ID, exact main-image hash, conservative perceptual image signature, then the configured visual embedding model for ambiguous candidates. Auto-skip only high-confidence matches; ordinary similar silhouettes use `重复-保留来源` and require review. Record method, confidence, candidate, and `duplicate_of_offer_id`; do not discard history.
- Cache visual embeddings by image content hash. All confirmed duplicates inherit the canonical product's Google risk-cache key so the product group is screened only once.
- Preserve source rows and raw input JSON for audit.

## Completion

Finish `IMPORT` idempotently with key `job + offer ID + site + IMPORT`, create the main-image attachment item, and set `IMPORTED`. Enqueue Google for every non-duplicate with a valid representative image even when `sku_status` is `MISSING`/`INVALID`; write the SKU warning into completeness and keep downstream SKU outputs blocked. If the representative image itself is missing, set a concrete retry/error reason instead of leaving an unexplained `GOOGLE=PENDING` row.

Never write Feishu directly; enqueue through `$lc-feishu-selection-sync`.
