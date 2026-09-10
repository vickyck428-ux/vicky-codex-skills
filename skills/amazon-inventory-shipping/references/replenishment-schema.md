# 完整补货输入字段

一个 `seller_sku` 一行。脚本读取首个 CSV/XLSX 工作表。

## 身份和状态

| 规范字段 | 说明 |
|---|---|
| `seller_sku` | 必填，精确变体 |
| `asin`、`product_title` | 商品识别 |
| `product_group`、`is_womens_bag` | 女包摘要 |
| `clearance_status` | 清货 Skill 的主状态；前三类禁止补货 |

## 销量

- `units_7d`、`units_15d`、`units_30d`：累计窗口。
- `units_prev_15d`：前 15 天，不包含最近 15 天。
- `units_90d`：长期参考。
- `seasonal_product`、`yoy_growth_ratio`：季节品优先使用去年同期趋势。
- `b1_override`、`b2_override`：有明确预测时分别覆盖健康库存和下一周期成长系数。
- `promotion_overlap`：促销与统计窗口重叠时填“是”。

后台窗口中没有某个已知 SKU 时销量可填 0；数据没有成功读取时留空。

## 最后入仓与入仓后销量

- `last_fba_receipt_date`：实际 FBA 入仓日期；不得使用货件名称或普通 `update_time` 推断。
- `last_fba_receipt_units`：该次实际入仓件数，必须为正数。
- `post_restock_units`：从入仓次日至计算日的实际已发货件数，不是订单数或页面销量估算。
- `receipt_evidence_status`：仅接受 `SYSTEM_CONFIRMED` 或 `USER_CONFIRMED`。
- `receipt_evidence_source`、`receipt_confirmed_at`：来源和确认时间。

运行链路支持 `--receipts <json>`。人工确认写入唯一 `inventory-actions.json.replenishment_receipt_confirmations`；更新且可靠的系统记录覆盖较旧人工确认。

## FBA 精确同款复核

- `fba_competitor_check_status`：`COMPLETE_NO_FBA_EXACT_COMPETITOR`、`FBA_EXACT_COMPETITOR_FOUND` 或 `INCOMPLETE`。
- `confirmed_fba_competitor_count`、`lowest_fba_competitor_landed_price`、`fastest_fba_competitor_delivery_days`。
- `fba_competitor_evidence`：竞品 ASIN、精确变体、到手价、配送、抓取时间和截图。

竞品证据来自 `$amazon-competitor-monitor`；B/C 级、FBM 或缺货同行只展示，不触发精确 FBA 同款门禁。

## 库存与成本

- `supply_instock`、`supply_reserved`、`supply_inbound`、`supply_total`。
- `inbound_ready_date`：现有在途预计到仓可售日期；晚于规划期的在途不计入 `I`。
- `unit_contribution`：已核算单件贡献利润；缺失时数量为“暂定”。
- `long_tail_approved`：已确认的高利润长尾款可放宽连续销量条件。

有 `supply_total` 且有在途明细时，按 `supply_total - 全部在途 + 规划期内可到达在途` 计算，避免重复并排除来不及到达的库存。没有 `supply_total` 时才汇总可售、预留和符合日期条件的在途。

## 周期与运输

| 字段 | 含义 |
|---|---|
| `procurement_days` | C，采购周期；当前同时计算 7 天和 14 天，正式默认 14 天 |
| `prep_days` | D，质检、贴标、装箱 |
| `review_cycle_days` | F，补货复查周期 |
| `safety_factor` | N，1.0–1.4 |
| `express_days`、`air_days`、`sea_days` | 各方式到仓可售天数 |
| `express_cost_per_unit`、`air_cost_per_unit`、`sea_cost_per_unit` | 运输成本 |
| `moq`、`carton_qty` | 最小采购量与整箱数量 |

生产周期固定为 0。国内库存和生产中库存不是输入字段，不读取、不计入有效库存。空白采购周期使用 14 天正式默认值并降低置信度；累计至少 5 批实际采购记录后改用第 80 百分位。
