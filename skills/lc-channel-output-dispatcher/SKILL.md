---
name: lc-channel-output-dispatcher
description: Route Feishu-verified 1688 decisions into separate Amazon and Walmart output batches after the user selects current channel-specific brand/site fields. Use for 已确认决策后的多渠道批次生成、恢复、修复或核对；do not use for early selection, WFS first-sale/T1/packing stages, automatic publishing, or unconfirmed cost-master writes.
---

# 老陈渠道输出分流

Resolve the state-machine entry from `SELECTIONCTL` or from the active closure configuration. Do not use 店小秘 or a hard-coded user path.

## Automatic trigger

1. Run only after the product has a complete decision, its `FEISHU` stage is `DONE`, and `02.确认生成表格` is checked with valid choices.
2. Invoke `./selectionctl dispatch-outputs [--job-id <job>]` after every Feishu flush. Repeated runs must not duplicate routes or batches.
3. Create independent routes when one product qualifies for more than one channel. Group the same job, site, route, and brand into batches of at most 20 parent products.
4. Write every batch to Feishu `08 渠道输出批次`. A local batch is not complete until its record and attachments can be read back.

## Product approval gate

- Keep four separate `02` views: `Amazon FBA 可做款`, `Amazon FBM 可做款`, `Walmart WFS 可做款`, and `Walmart 自发货可做款`.
- In `02`, the user selects `本次生成渠道` and the platform-specific brand field; Amazon additionally requires `Amazon目标站点`, then checks `确认生成表格`.
- Amazon only accepts `Amazon品牌 = Vocuer | BenPo bar`; Walmart only accepts `Walmart品牌 = StyleSack | Baguery`. Historical `目标品牌` is display-only and must not drive routing.
- A confirmation for one platform never authorizes another platform. Split mixed-platform batches into separate previews and confirmations.
- Amazon sites allow US, UK, and DE. Validate every selected site against its own decision; never substitute another country.
- Walmart ignores `Amazon目标站点` and always uses US.
- Only choices consistent with `系统主建议` may be routed. Invalid or incomplete choices remain `配置不完整` and do not create `08` rows.

## Downstream Skill routing

- `Walmart自发货`: use `$walmart-1688-listing` with the batch `1688_links.txt`, chosen brand account, and official Walmart workbook template. Never use 店小秘 and never publish automatically.
- `Walmart WFS` has two different outputs that must not be confused:
  - Listing content and draft-upload workbook still use `$walmart-1688-listing`.
  - An approved T1 physical-shipment record with `channel=WALMART_WFS` must route to `$lc-walmart-wfs-shipping-manifest`, which produces the US consolidation workbook and store-separated platform mappings. It must preserve `candidate_id`, 1688 `detail_id`, Walmart SKU, product-group ID, exact variant, approval record, carton, and Shipment ID relationships.
- `Amazon FBM`: use `$lc-amazon-listing-asin` for listing content and its Excel output. Do not invent an official Seller Central flat-file when the required category template is unavailable.
- `Amazon FBA`: use `$lc-amazon-listing-asin` first; invoke `$amazon-inventory-shipping` only after SKU, ASIN, launch quantity, and shipping inputs exist.
- A downstream Skill must consume the batch manifest and preserve exact `offer_id` and SKU relationships.

Before starting generation, run `./selectionctl output-running --batch-id <id>`. After validation, run:

```text
./selectionctl output-complete --batch-id <id> --workbook <path> --validation <path> --status GENERATED
```

Use `PARTIAL_FAILED`, `FAILED`, or `BLOCKED_CONFIG` with `--error` when appropriate. Never mark a batch generated without a real workbook and validation evidence.

## Amazon 成本主档同步

Amazon 批次的 `batch_manifest.json` 包含 `cost_registry_sync`。当生成结果已经明确建立 Seller SKU 与精确 1688 变体关系时，必须在 `output-complete` 前执行：

1. 生成包含 Seller SKU、ASIN、精确变体单件采购成本、多件装换算数量、包装数据、1688 链接/订单号、生效日期和“精确变体已确认”的成本映射表。
2. 使用 `${INVENTORY_AI_RUNNER}/upsert_sku_cost_registry.mjs` 生成 `cost-registry-preview.json`。
3. 预览中只要有价格区间、SKU 未分配、变体未确认、多件装换算不清或来源缺失，保留为数据问题，不得猜成本或写入主档。
4. 预览无阻止项后，展示 `preview_id`、源文件哈希、主档哈希和逐项变更。只有用户明确回复“确认处理/确认上传 + 对应 preview_id”后，才可对同一预览使用 `--apply-preview`；确认不匹配或输入哈希变化必须重新生成预览。

成本主档由 `SKU_COST_REGISTRY` 指向，主键固定为 `seller_sku`。不得依赖聊天记忆保存成本，也不得在每周库存运行时重建或覆盖主档。

## Output contract

- Store files under `runs/channel-output/<batch-code>/`.
- Keep `batch_manifest.json`, `batch_input.xlsx`, `1688_links.txt`, generated workbook, validation report, and Amazon batches' `cost-registry-preview.json`.
- `publish_automatically` must remain `false`. Automatic trigger means automatic preparation and generation, not automatic marketplace publication.
- On retry, reuse the same batch code and update the same Feishu record.
- `08` is a system batch ledger. The user must never copy product rows into it manually; link each generated batch back to `02.输出批次`.
