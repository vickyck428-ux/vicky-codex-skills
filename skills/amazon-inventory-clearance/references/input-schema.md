# 输入与合并规则 v1.1

## 原始数据模式

`generate_clearance_plan.cjs`接受：

- `--api-json`：基础商品及 7/15/30/60/90 天、前 15 天窗口。
- `--inventory-report`：Amazon FBA 库存报告；可缺失。
- `--age-report`：Amazon Inventory Age/Health 报告；可缺失。
- `--cost`：按 `seller_sku` 或 ASIN 匹配的 CSV/XLSX；可缺失。
- `--seller-id`、`--marketplace`、`--as-of-date`、`--fee-snapshot-date`：运行范围和快照依据。

SKU 主集合为基础商品、90 天销量、库存报告、库龄报告的并集。已知 SKU 在销量窗口缺行时记 0。

## FBA 库存唯一来源

以下字段只允许从 `--inventory-report` 取得：

- `supply_instock` ← `available`
- `supply_reserved` ← `Total Reserved Quantity`
- `supply_inbound` ← `inbound-quantity`
- `supply_total` ← `Inventory Supply at FBA`

API 的 `supplyInstock`、`supplyInbound`、`supplyTotal`只写入 `api_supply_*`诊断列。FBA 报告缺行时正式库存字段保持空白；`999/1000`等疑似占位值标记后隔离。

## 标准表兼容模式

`--input inventory.csv|xlsx`继续读取首个工作表。一个 `seller_sku` 一行；中文和英文别名均可。可从 `assets/amazon-inventory-clearance-template.xlsx`开始填写。

核心字段：

- 身份：`seller_sku`、`asin`、`product_title`、`product_group`、`is_womens_bag`
- 销量：`units_7d`、`units_15d`、`units_30d`、`units_60d`、`units_90d`、`units_prev_15d`
- 经营：`revenue_30d`、`ad_cost_30d`
- FBA：`supply_instock`、`supply_reserved`、`supply_inbound`、`supply_total`
- 库龄：`oldest_age_days`、`next_snapshot_aged_units`、`aged_181_210`至`aged_365_plus`
- 风险：`estimated_aged_surcharge`、`stranded_units`、`unfulfillable_units`、`next_fee_snapshot_date`
- 经济：`unit_landed_cost`、`amazon_fees_per_unit`、`unit_contribution`、`external_resale_value`、`removal_fee_per_unit`
- 周期：`procurement_days`、`prep_days`、`sea_days`、`review_cycle_days`、`safety_factor`、`long_tail_approved`

## 库龄映射

- `oldest_age_days`：取最高非零 Amazon 库龄分段的下限，并将依据写入 `oldest_age_basis`。
- `next_snapshot_aged_units`：汇总报告中的 `quantity-to-be-charged-ais-*` 字段。
- `estimated_aged_surcharge`：汇总 `estimated-ais-*` 字段，不自行套费率。
- `aged_365_plus`：汇总 366–455 天和 456+ 天。
- `unfulfillable_units`：优先取库龄报告，缺失时取 FBA 库存报告同名字段。

库龄报告缺行时 `age_report_present=否`，不把缺失当 0。

## 成本表

按 `seller_sku` 优先、ASIN 次之匹配。支持规范经济字段，也保留 `purchase_cost_cny`、`fba_first_leg_cost_cny`。

人民币采购价不能自动等同美元落地成本。若缺 `unit_contribution`，数量状态仍为 `暂定-缺经济数据`。

## 诊断字段

- `inventory_report_present`、`age_report_present`、`cost_data_present`
- `api_supply_instock`、`api_supply_inbound`、`api_supply_total`
- `api_inventory_suspect`、`api_inventory_mismatch`
- `inventory_reconciliation_issue`
- `inventory_snapshot_date`、`age_snapshot_date`、`sales_window_end_date`
- `seller_id`、`marketplace`、`input_data_notes`

所有缺项保留 SKU，并在逐 SKU `数据问题`和汇总工作表中列出。
