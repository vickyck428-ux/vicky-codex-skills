---
name: amazon-inventory-clearance
description: Analyze Amazon FBA excess, aged, stranded, and slow-moving inventory; classify each SKU as 紧急清退、主动清货、停补观察、健康维持或待补货; separate potential excess, fee risk, and clearance target quantities; and create an auditable read-only XLSX action plan. Use when the user asks for 库存清货、滞销库存、超量库存、库龄费、FBA老库存、Outlet/移除/清算建议、女包清库存，或按SKU制定清货计划。
---

# Amazon 库存清货

只做只读分析和建议。不要改价格、创建促销、提交移除/清算、调整广告或创建货件。

## 选择范围

1. 用户未指定店铺/站点时，先查询授权店铺并确认顺序。
2. 每次只分析一个 `sellerId + marketplace`，完成后再处理下一站点。
3. 先隔离标题、产品组或 SKU 命中 `pencil case/pouch`、`pen case/pouch/bag` 的记录；这些记录只进入“历史遗留清退”，不进入清货建议、销售、利润、女包库存、成功率、选品或补货指标。其余 SKU 再用 `product_group` 和 `is_womens_bag` 输出女包摘要；不确定时标记人工确认。

## 标准操作

1. 读取 [references/input-schema.md](references/input-schema.md)。
2. 指定店铺、站点、计算日期和费用快照日。
3. 采集 7/15/30/60/90 天及前 15 天销量、FBA 库存报告、库龄报告和可选成本表。
4. 运行原始数据模式：

```bash
NODE_PATH="<bundled-node-modules>" node scripts/generate_clearance_plan.cjs \
  --api-json api-products.json \
  --inventory-report inventory.csv \
  --age-report inventory-age.csv \
  --cost cost.xlsx \
  --seller-id 56321 \
  --marketplace US \
  --as-of-date YYYY-MM-DD \
  --fee-snapshot-date YYYY-MM-DD \
  --output clearance-plan.xlsx
```

`--inventory-report`、`--age-report`、`--fee-snapshot-date` 或 `--cost` 缺失时仍生成受限预警版；`--cost` 可省略。

5. 手工标准表继续使用兼容模式：

```bash
NODE_PATH="<bundled-node-modules>" node scripts/generate_clearance_plan.cjs \
  --input inventory-input.xlsx \
  --seller-id 56321 \
  --marketplace US \
  --as-of-date YYYY-MM-DD \
  --output clearance-plan.xlsx
```

6. 读取 [references/clearance-policy.md](references/clearance-policy.md)，检查工作簿公式、状态互斥、数量上限和数据问题后交人工审阅。

## 数据纪律

- SKU 主集合取基础商品、90 天销量、FBA 库存报告和库龄报告的并集。
- 已知 SKU 在某销量窗口缺行时记 0。
- FBA 可售、预留、在途和总库存只取 FBA 库存报告。API 库存仅用于对账。
- FBA 报告缺行时库存保持空白；不得采用 `999/1000` 等疑似占位或非 FBA 数量。
- 缺库存时清货目标留空并标记 `需要人工确认-缺库存`。
- 缺经济数据时风险判断仍可保留，但数量标记 `暂定-缺经济数据`，不得承诺净回收。

## 决策纪律

- 状态优先级：`紧急清退 > 主动清货 > 停补观察 > 待补货 > 健康维持`。
- 库龄与供给天数分开判断；110–115 天是课程预警，不是平台强制线。
- 费用日、Outlet 资格、折扣、费率和渠道报价每次运行重新核实。
- 一个 SKU 进入前三种状态后，不得同时建议采购。
- 竞品 FBA 转仓风险只作为关联证据展示，不参与清货主状态、库龄、超量数量或清货目标数量计算。
- `route_clearance_review` 对单纯竞品 `FBM→FBA` 固定为 `false`。只有本店库存另行命中超量、滞销或库龄门禁时，才允许进入清货分析。
- 分阶段建议必须有复查点和停止条件；任何外部执行均需另行人工审批。

## 输出要求

- 生成 `清货建议`、`总览`、`女包摘要`、`历史遗留清退`、`数据问题`、`规则参数`、`来源`七个工作表。
- 区分 `潜在超量数量`、`费用风险数量` 和 `清货目标数量`。
- `清货目标数量` 仅在紧急清退、主动清货时填写；停补观察、待补货、健康维持为 0；库存未知时为空。
- 同时输出 `风险判断置信度`、`经济性置信度`、`数量状态` 和逐 SKU 数据问题。
- `数据问题`汇总实际 SKU 数；`来源`记录店铺、站点、窗口、快照日期、输入文件和费用日依据。
