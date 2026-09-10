# 统一候选模型

## 目录

1. 身份与结构
2. 证据与方法
3. Amazon 市场
4. 经济性与供应链
5. 风险与决策
6. 状态规则

## 1. 身份与结构

- `candidate_id`：稳定唯一编号；
- `candidate_name`：人类可读名称；
- `product_signature`：包型 × 材质 × 功能 × 场景 × 风格 × 人群；
- `bag_shape`、`material`、`functions`、`scenes`、`styles`、`audiences`；
- `representative_asin`、`representative_offer_id`；
- `dedupe_key`：规范化结构，不含颜色和普通装饰。

## 2. 证据与方法

- `discovery_methods`：只记录实际运行的方法；
- `source_type`、`source_path_or_url`、`evidence_date`；
- `evidence_summary`、`evidence_limitations`；
- `independent_evidence_count`；
- `data_freshness`：当前/历史/过期风险；
- `confidence`：高/中/低。

同一转载链、同一商家多个账号或同一数据库派生结果不计为独立证据。

## 3. Amazon 市场

- `target_marketplace`；
- `target_keywords`；
- `exact_matches`、`substitutes`；
- `fba_supply`、`local_fbm_supply`、`remote_fbm_supply`；
- `review_dependency`、`ad_dependency`；
- `crowding_speed`、`seasonality`、`window_end_date`；
- `market_gate_project`。

未知数量写空并标记待验证，不写 0。

## 4. 经济性与供应链

- `target_price`、`purchase_cost`、`landed_cost`；
- `referral_fee`、`fba_fee`、`storage_cost`、`return_allowance`；
- `coupon_discount`、`cpc`、`conversion_rate`；
- `estimated_cpa`、`estimated_acos`、`break_even_acos`；
- `pre_ad_profit`、`post_ad_contribution`；
- `moq`、`carton_qty`、`unit_weight`、`package_dimensions`；
- `sample_days`、`production_days`、`prep_days`、`shipping_days`、`amazon_receive_days`；
- `estimated_sellable_date`。

## 5. 风险与决策

- `demand_gate`、`supply_gate`、`traffic_gate`、`profit_gate`、`supply_chain_gate`、`ip_gate`；
- 每道门取值：`通过/部分验证/待验证/不通过`；
- `fatal_reason`；
- `pool`：稳健/趋势/长尾/监控/淘汰；
- `decision`：值得打样/小批测试/优先补数据/监控/淘汰；
- `suggested_test_qty`、`max_test_loss`、`review_date`、`next_action`。

## 6. 状态规则

1. 任一道门为 `不通过`：`淘汰`。
2. 无不通过但存在 `待验证`：最高为 `优先补数据`。
3. 只有部分验证：最高为 `监控`，除非已明确列出可控的小批验证方案。
4. 六道门全部通过：才可标记 `值得打样/小批测试`。
5. 证据过期不会自动淘汰，但必须降低置信度并要求复查。
