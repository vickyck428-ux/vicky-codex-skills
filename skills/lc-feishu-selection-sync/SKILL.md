---
name: lc-feishu-selection-sync
description: Serve as the only Feishu Base writer for the product-selection pipeline, idempotently synchronizing task batches, 02 product decisions, 04 Amazon matches, 05 Google evidence, 08 channel output batches, recommendations, and attachments through a SQLite Outbox with retries and read-back verification. Use when writing, repairing, reconciling, grouping by task/date, or verifying selection and output results in Feishu.
---

# Lc Feishu Selection Sync

Use `./selectionctl sync-feishu --job-id <job>` or `--watch`.

## Single-writer rules

- Other Skills and stage workers must never call Feishu write APIs directly.
- Reuse the configured Feishu master Base. Create one `01 任务入口` record per submission and keep all parent products in the same `02 商品决策` table; never create a daily table or erase historical rows unless the user explicitly asks.
- Consume SQLite `outbox` in batches of 10 or every 30 seconds.
- Keep attachments in their own queue and preserve product-level confirmation.
- Upsert `02` by offer ID, `04` by product + site + ASIN, and `05` by product + country + landing URL.
- Upsert `08 渠道输出批次` by output batch code. Attach its manifest, input workbook, generated upload workbook, and validation report without duplicating filenames.
- Read user choices from `02`: `本次生成渠道`, `目标品牌`, `Amazon目标站点`, and `确认生成表格`. Validate them against `系统主建议`; do not create a batch from `08` edits or require manual copying.
- Retry transient EOF, timeout, rate-limit, and write conflicts with bounded backoff. Do not silently change user/bot identity.

## Batch organization

- Link every `02` product to the current `01` record through `关联任务`.
- Write `批次内序号` as the stable 1-based source order within that task; never use the global Base row number.
- Treat `导入日期` as a read-only system creation date.
- Set `重复铺货状态` to `未检查`, `非重复`, `重复-跳过`, or `重复-保留来源`. Keep a minimal source row for skipped duplicates so the task remains auditable.
- When a new task starts, update only the `当前任务` view filter to the new `01` record ID.
- Keep the first `全部商品` view grouped by `关联任务` as the in-place collapsible historical view. Do not create a separate `按任务批次` view or daily product tables.
- Map `RETRYABLE_ERROR` / `BLOCKED_LOGIN` to `数据完整性=抓取失败`, and `AMAZON_DATA_INCOMPLETE` to `数据完整性=缺失` with channel recommendation `未判断`. Keep these records in the automatic retry/data-incomplete view; do not convert them to `MANUAL_REVIEW` after Feishu read-back.
- Reserve `人工复核` for completed evidence that still has material risk or same-product ambiguity.
- Write user-facing review routing to `02.待复核渠道` with values `Amazon FBA`, `Amazon FBM`, `Walmart自发货`, and `Walmart WFS`; one product may hold multiple values. Write the Google/channel reason to `02.待复核信息` and keep Google website, evidence URL, screenshot, and decision reason visible in every review view.
- Preserve four channel review views: `亚马逊 FBA 待复核`, `亚马逊 FBM 待复核`, `沃尔玛自发货待复核`, and `沃尔玛 WFS 待复核`. Filter out records whose `人工审核结论` is `通过` or `淘汰`. Do not group these user-facing views by Google status.
- Existing rows with blank new fields remain valid. Do not delete and recreate them; fill missing values only when their original task is resumed or reconciled.
- Keep the user-facing Base root limited to `01 任务入口`, `02 商品决策`, and `08 渠道输出批次`. Keep `03` through `07` inside `后台数据（系统使用）`; moving them must not change their table IDs.
- Preserve four compact action views in `02`: Amazon FBA, Amazon FBM, Walmart WFS, and Walmart self-fulfilled. Channel batch status and files remain in `08` and link back through `02.输出批次`.

## Success gate

After all prior Outbox items are sent, read back the remote product and evidence records. Confirm:

- `02` business key and decision fields;
- correct `关联任务`, `批次内序号`, and `重复铺货状态` for newly imported products;
- required `04/05` records;
- every required image attachment is visible remotely;
- data completeness and channel recommendations are present.

Only then finish `FEISHU`, pass through `FEISHU_SYNCED`, and assign a ready route. Local crawl completion without this verification is only “本地完成，待回写”.

## Progress and repair safeguards

- Treat import-time `02` upsert plus main-image upload as `IMPORT_FEISHU_CHECKPOINT` behavior in Outbox/remote refs, not as final `FEISHU=DONE`. Do not introduce a new product state; final FEISHU state remains governed by the Success gate above.
- Before marking `FEISHU=DONE`, verify stage contiguity: Google must be terminal; risk-stopped products need no Amazon stage, while all other products require terminal Amazon completeness status and the appropriate decision record.
- Status counters must report final read-back confirmation separately from import checkpoint confirmation. `pending_writeback_products` must be derived from eligible terminal products and can never be hidden by an early import sync.
- If a successful retry supersedes a Google/Amazon error, keep the historical evidence row but mark it resolved and omit it from active errors, current screenshots, and failure totals.
- A sent Outbox row without the expected stage/checkpoint marker is a reconciliation item. Recover the marker by remote read-back; do not resend or duplicate the Feishu record.
