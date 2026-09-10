# Architecture and authorities

## Runtime authority

1. Read the configured `runtimeRoot`; otherwise resolve `.selection-runtime-root` from the selection project.
2. Treat `runtimeRoot/data/selection_pipeline.sqlite3` as the product, variant, audit, IPR, outbox, and channel-output authority.
3. Project copies of SQLite are development fixtures only and must not overwrite Runtime.

## Components

- `1688-fbm-workflow`: Feishu-facing US/Europe/Walmart production orchestration, copy/image reviews, template generation, attachment readback, and unified daily entry point.
- `selection-pipeline`: persistent 1688 import, dedupe, source backfill, Amazon site audits, IPR tasks, channel approvals, and outbox.
- `1688-walmart-tool`: exact 1688 parsing, Walmart copy/workbook structure, UPC registry, and template preservation.
- `amazon-data-crawl-runner`: guarded Amazon candidate collection and Embedding-to-Mini same-product cascade. It is not a publication service.

## Data flow

`1688 source -> products/skus/variant_assets/product_facts_master -> site market evidence -> human review/IPR evidence -> channel approval -> Rufus research + isolated visual input -> copy/images review -> final workbook switch -> Feishu attachment readback -> manual platform upload result`

The Feishu writer is idempotent. Resolve existing table IDs or unique exact table names; block ambiguity rather than creating duplicates.
