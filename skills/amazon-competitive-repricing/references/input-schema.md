# 输入规范

## 数据优先级

1. 最新 Amazon Inventory Age / Inventory Health 库龄表；
2. `$amazon-inventory-clearance` 对风险 SKU 输出的正式状态和建议清货数量；
3. 官方 API 或后台经营数据；
4. 用户成本与当前官方费用；
5. Amazon 前台和第三方历史价格。

第五层只能确定参考区间，不能覆盖前四层结论。

正式调价范围默认排除标题或类目命中 `pencil case`、`pencil pouch`、`pen case`、`pen pouch`、`笔袋`、`文具袋` 的 SKU。排除项只计数并留审计原因，不进入搜图、竞品和价格计算。

默认在 `${INVENTORY_INPUT_ROOT}/库龄/YYYY-MM-DD/` 中寻找最新报告。
以行内 `Inventory age snapshot date` 为准，而不是文件修改时间、文件夹日期或 Listing 上架日。

## 规范化 JSON

```json
{
  "seller_id": "56321",
  "marketplace": "US",
  "sku": "OZ-S1IA-VJCA",
  "asin": "B0GHFVQSGM",
  "as_of_date": "2026-07-29",
  "inventory": {},
  "clearance_decision": {},
  "performance": {},
  "costs": {},
  "fees": {},
  "pricing": {},
  "competitors": []
}
```

### inventory

- `seller_sku`、`asin`
- `inventory_age_snapshot_date`
- `available`、`reserved`、`inbound`
- `unfulfillable`、`stranded`
- `age_0_90`、`age_91_180`
- `age_181_270`、`age_271_365`、`age_366_455`、`age_456_plus`
- `quantity_to_be_charged_181_plus`
- `estimated_aged_surcharge`
- `sell_through`
- `days_of_supply`
- `estimated_excess_quantity`
- `fba_minimum_inventory_level`
- `total_supply_including_open_shipments`
- `inventory_health_status`
- `alert`

库龄表常用原字段可映射为：

- `available` ← `available`
- `age_0_90` ← `inv-age-0-to-90-days`
- `age_91_180` ← `inv-age-91-to-180-days`
- 后续库龄段同理；
- `unfulfillable` ← `unfulfillable-quantity`
- `inbound` ← `inbound-quantity`
- `reserved` ← `Total Reserved Quantity`
- `days_of_supply` ← `days-of-supply`
- `estimated_excess_quantity` ← `estimated-excess-quantity`
- `inventory_health_status` ← `fba-inventory-level-health-status`
- `total_supply_including_open_shipments` ← `Total Days of Supply (including units from open shipments)`；若该列实际为天数，不要映射为数量，改用 `available + inbound`。

多个 AIS 数量和金额字段分别求和后写入
`quantity_to_be_charged_181_plus` 与 `estimated_aged_surcharge`。

### clearance_decision

清货状态和数量只能从 `$amazon-inventory-clearance` 的正式输出读取。健康库存或缺货风险可省略本对象；发现老库存、超量、库龄费风险、供给超过 90 天或 60 天零销量时必须提供：

- `seller_sku`、`asin`
- `status`：`紧急清退`、`主动清货`、`停补观察`、`健康维持`、`待补货`
- `recommended_clearance_quantity`：非负整数
- `confidence`：`高`、`中`、`低`
- `reasons`：至少一条清货判断原因
- `inventory_age_snapshot_date`
- `source_file`：清货方案工作簿的本地路径或可审计来源标识

`reasons` 可从清货方案对应行的风险数量、供给天数、库龄和建议动作整理成可审计说明，但不得借此重新计算或覆盖正式状态。

`seller_sku`、`asin` 和 `inventory_age_snapshot_date` 必须与本次调价输入完全一致。低置信度、来源缺失或任一身份字段冲突时，只能计算暂定价。

状态映射：

- `主动清货`且清货数量大于 0 → `ACTIVE_CLEARANCE`
- `紧急清退`且清货数量大于 0 → `URGENT_EXIT`
- `紧急清退`且清货数量为 0 → `INVENTORY_EXIT_ONLY`，不降低正常可售库存售价
- `停补观察` → `OBSERVE`
- `健康维持` → `HEALTHY_HOLD`
- `待补货` → 只有近期有销量且存在低库存信号时才进入 `LOW_STOCK_PROTECTION`

潜在清货风险存在但本对象缺失时，返回 `CLEARANCE_REVIEW_REQUIRED`，停止竞品分析。

### performance

- `units_7d`、`units_30d`、`units_60d`、`units_90d`
- `sessions_30d`
- `orders_30d`
- `revenue_30d`

已知 SKU 在一个已成功返回的销售窗口没有行时，该窗口销量记为 0。
查询本身失败或字段不存在时保持 `null`，不能猜成 0。

### costs

- `procurement_cost_cny`：用户提供，缺失时不能计算可执行底价；
- `first_leg_cost_cny`：默认 10；
- `usd_cny_rate`：运行日汇率；
- `fx_safety_buffer_pct`：默认 0.02。

保守换算：

```text
保守汇率 = USD/CNY × (1 - 2%)
美元落地成本 = (采购成本 + 头程) ÷ 保守汇率
```

### fees

- `exact`：是否为当前 SKU 的准确或官方估算费用；
- `source`：正式价格默认要求 Seller Central Fee Preview；
- `referral_fee_rate`：小数，例如 15% 写为 `0.15`；
- `fulfillment_fee`
- `storage_per_unit`
- `return_reserve_per_unit`
- `future_ad_cost_per_order`
- `other_variable_fee_per_unit`

`exact` 不为 `true`、佣金率缺失或配送费缺失时，正式建议价必须为空。仓储、退货准备金、广告及其他变动成本必须分别提供；四项全部为非负数时经营成本才算完整，否则只显示现金底线并标记“经营利润待确认”。

Seller Central Fee Preview 可为 CSV、制表符 TXT 或 XLSX。按 Seller SKU 精确匹配；只有当前 SKU 映射中 ASIN 唯一时才允许 ASIN 回填。MFN/FBM 行、非 USD 行、重复 SKU 费用冲突或无法同时取得佣金率与 FBA 配送费的行一律不作为正式费用。

### pricing

- `standard_price`
- `sale_price`
- `sale_start_date`、`sale_end_date`
- `current_effective_price`
- `own_fulfillment`
- `own_delivery_days`
- `no_raise_this_run`：可选布尔值；为 `true` 时只对本次运行禁止建议涨价，不改变后续默认规则
- `reference_price_validated`
- `price_discount_eligible`
- `price_discount_fee_known`
- `price_discount_fee`
- `own_coupon_active`

`current_effective_price` 优先使用前台实际可购买价格；同时保留标准价和 Sale Price，防止写错字段。

### competitors[]

- `asin`、`variant`
- `exact_variant_confirmed`：是否已打开详情页核对当前精确子变体；用户按键确认 B→A 时视为确认该指定配对
- `original_grade`：智能体首次判定的 `A`、`B`、`C`
- `effective_grade`：实际用于监控和定价的等级
- `user_promoted_to_a`：仅当原始等级为 B 且用户勾选“当做 A 级竞品”时为 `true`
- `user_confirmed_at`
- `grade`：兼容字段，规范化后等于 `effective_grade`
- `confirmation_status`：`USER_CONFIRMED`、`TEMP_A`、`AGENT_CONFIRMED`
- `price_role`：`PRIMARY`、`LOWER_BOUND`、`REFERENCE`、`EXCLUDED`
- `grade_reason`、`difference_points`
- `price`、`coupon_amount`、`shipping`
- `fulfillment`：`FBA`、`FBM`、`PRIME`、`UNKNOWN`
- `delivery_days`
- `direct_from_china`
- `in_stock`
- `captured_at`
- `screenshot_path`、`source_url`

用于正式定价的 A 级竞品还必须满足：`exact_variant_confirmed=true`；FBA/Prime 履约已确认，或 FBM 已提供 `delivery_days`/`direct_from_china=true`。StyleSnap 搜索结果截图不能单独满足这些门禁。

稳定复核键为 `seller_sku + competitor_asin`。用户把某条 B 级记录提升为 A 时，只改变该键的 `effective_grade` 和确认状态，永久保留原始 B 级、判级原因和差异说明。

同行有效到手价采用用户确认口径；同行 Coupon 只记录，不另行扣减：

```text
FBA/Prime：页面当前显示售价
FBM：页面当前显示售价 + 运费
```

## 阻断条件

以下情况仍可给风险说明，但不能给“可执行价”：

- 库龄快照超过 7 天或日期在未来；
- 库龄行缺失、SKU/ASIN 冲突；
- 潜在清货风险存在但缺少正式 `clearance_decision`；
- 清货结论的 SKU、ASIN、库龄快照日或来源与调价输入不一致；
- 清货结论置信度为低，或主动清货没有正数清货数量；
- 可售库存缺失；
- 用户采购成本缺失；
- 汇率或准确 Amazon 单件费用缺失；
- 当前有效售价缺失；
- 用于定价的竞品价格超过 4 天未复核；
- 没有新鲜、已确认的 A 级竞品；只有 B 级时只能等待用户确认，不能生成正式目标价；
- A 级竞品未确认精确变体，或履约信息不足；
- 价格或变体存在无法解释的冲突。

正式建议的 `price_valid_until` 取“库龄快照日 + 7 天”与“定价竞品采集日 + 4 天”两者较早者。超过该日期后旧建议自动失效。
