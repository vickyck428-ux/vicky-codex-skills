---
name: lc-walmart-wfs-shipping-manifest
description: 管理 Walmart WFS 审批后交接，并在 T1 已批准、采购、到仓、实测、装箱或取得 Shipment ID 后生成店铺隔离的发货工作簿。用于WFS待审批、箱单或发货表；不用于售前找款、共享池、普通FBM订单动作或Listing草稿上传。
---

# WFS发货表交接

## 安全边界

- 只生成候选、审批记录、进度建议和文件。
- 不自动采购、上架、创建平台货件、上传模板、贴标或修改平台商品状态。
- 每个首次测试产品组固定T1 1件；同一产品组只能进入一个沃美国店。
- 美国两店可共用国家运输批次，但平台Shipment ID、箱号、标签和库存记录必须分开。

## 工作流

1. 完整读取 [handoff-schema.md](references/handoff-schema.md)。生成表格时再读取 [workbook-schema.md](references/workbook-schema.md)。
2. 判断来源：
   - 沃FBM订单截图：使用`WALMART_FBM_FIRST_ORDER`。
   - 亚美畅销款门禁候选：使用`AMAZON_TO_WFS_M7`。
3. 截图入口必须提取店铺、订单号、日期、付款/履约/取消状态、SKU、Item ID、商品、具体颜色或变体和截图引用。看不清的字段写空并列入`missing_inputs`，不得推测。
4. 使用`candidate_id`、`1688 detail_id`、Walmart SKU或产品组ID关联候选与成本主档；不得仅凭商品标题匹配。
5. 将完整利润参数交给运营接口计算。利润不足70元为阻断；利润明细不完整为`NEEDS_DATA`。
6. 调用运营接口`sync_wfs_shipping_handoff`幂等写入。交接键由来源、市场、店铺、来源记录、SKU和变体组成。
7. 将待审批记录同步到 `config/ops-integrations.json` 指向的“1688采购与发货总表 / WFS选品审批 / 02 WFS待审批”。只有`批准T1 1件`可调用`review_wfs_shipping_handoff`并进入待采购；`退回补资料`和`拒绝`必须保存意见。
8. 每次同步优先运行项目内 `node scripts/wfs-feishu-sync.mjs`：它按交接键幂等写候选、读取人工审批，并且只有飞书“采购状态=已采购”后才在“采购发货明细”创建或关联实物记录。审批通过本身不得创建采购明细。
9. 实际采购、到仓、实测、分箱或平台Shipment ID发生后，才调用`sync_wfs_shipping_progress`。不得把建议或审批当成已采购。
10. 到仓前按0.4kg估算100kg进度。生成正式箱单前必须有实际重量、长宽高、箱号、国家运输批次和店铺独立Shipment ID。
11. 读取管理接口返回的`wfsShippingHandoffs`，保存为输入JSON，运行`build_wfs_manifest.mjs`生成工作簿。

## 接口调用

使用项目内`node scripts/ops-bridge.mjs post <action> '<json>'`。不得输出`.dev.vars`或令牌。

沃FBM截图交接示例：

```bash
node scripts/ops-bridge.mjs post sync_wfs_shipping_handoff '{"sourceType":"WALMART_FBM_FIRST_ORDER","sourceRecordKey":"ORDER-123","candidateId":"candidate-id","productGroupKey":"group-id","market":"US","storeName":"美国站1","sku":"SKU-BLACK","itemId":"item-id","gtin":"012345678905","title":"Shoulder bag","variant":"Black","sourceOrderId":"ORDER-123","sourceOrderDate":"2026-08-10","paid":true,"fulfilled":true,"cancelled":false,"refunded":false,"trackingIssue":false,"infringement":false,"evidenceObservedAt":1786320000000,"screenshotFingerprint":"sha256:...","screenshotRefs":["/absolute/path/order.png"],"profit":{"salePriceRmb":300,"actualWeightLb":1,"lengthIn":16,"widthIn":12,"heightIn":4,"productCostRmb":50,"inboundFreightRmb":20,"dutyRmb":5,"referralFeeRmb":45,"wfsFeeRmb":35,"storageFeeRmb":2,"barcodePackagingRmb":3,"clearanceReserveRmb":4}}'
```

审批与进度示例：

```bash
node scripts/ops-bridge.mjs post review_wfs_shipping_handoff '{"handoffKey":"<key>","decision":"APPROVE","comment":"批准T1 1件"}'
node scripts/ops-bridge.mjs post sync_wfs_shipping_progress '{"handoffKey":"<key>","workflowStatus":"READY_TO_PACK","receivedQty":1,"actualWeightKg":0.46,"lengthCm":31,"widthCm":24,"heightCm":8,"cartonNo":"US1-C001","transportBatchKey":"WFS-US-202608","platformShipmentId":"<store-shipment-id>"}'
```

飞书统一同步：

```bash
node scripts/wfs-feishu-sync.mjs --dry-run
node scripts/wfs-feishu-sync.mjs
```

审批表的人工输入仅限审批动作/意见、采购确认、到仓数、实测重量尺寸、箱号、国家运输批次和Shipment ID。`Walmart计划数`、`Walmart待发数`、`数量校验`和`总状态`为“采购发货明细”的公式字段，禁止手工写入。已有Walmart SKU时不得勾选“新建Walmart Listing”。

## 生成工作簿

先调用`load_workspace_dependencies`取得Node和`node_modules`路径，再运行：

```bash
CODEX_BUNDLED_NODE_MODULES="<loader node_modules>" "<loader node>" scripts/build_wfs_manifest.mjs --input <handoffs.json> --output-dir <output-dir> --batch <transport_batch_key>
```

输入可为`{"wfsShippingHandoffs":[...]}`、`{"handoffs":[...]}`或记录数组。脚本必须：

- 输出一份内部合运总表。
- 分开生成美国站1和美国站2的平台映射文件。
- 未提供当前WFS官方模板时，文件名必须包含“待映射”，不得声称已是官方导入模板。
- 未实测、未批准、缺箱号或两个店共用箱号的记录进入异常表，不进入正式平台映射。

若用户提供当前官方模板和映射JSON，使用`--store1-template/--store2-template`与`--platform-mapping`输出按原模板填充的文件。模板版本变化时只更新映射，不改变内部主表。
