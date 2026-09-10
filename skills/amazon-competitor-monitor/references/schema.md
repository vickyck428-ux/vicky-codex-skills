# 竞品监控数据结构

## Snapshot

每行是一条精确子变体快照。选品阶段允许没有 Seller SKU：

- `subject_type`：`CANDIDATE` 或 `SKU`。
- `subject_id`：当前主体 ID；选品阶段等于 `candidate_id`，上架后等于 Seller SKU。
- `candidate_id`：选品候选唯一 ID；建 SKU 后仍需保留，用于接续历史。
- `own_sku`：本店 Seller SKU；选品阶段可为空。
- `lineage_key`：有 `candidate_id` 时固定为 `CANDIDATE:<candidate_id>`，否则为 `SKU:<own_sku>`。
- `competitor_asin`：竞品子 ASIN。
- `variant`：颜色、尺寸等精确子变体。
- `original_grade`：首次图片和详情页判定的 `A`、`B`、`C`。
- `effective_grade`：实际监控等级；用户可把精确一条 B 级映射提升为 A。
- `grade`：兼容字段，规范化后等于 `effective_grade`。
- `user_promoted_to_a`、`user_confirmed_at`。
- `price`：页面售价，美元数值。
- `coupon_amount`：同行 Coupon 折现金额；没有为 0。
- `shipping`：运费；免费为 0。
- `effective_price`：可省略，由脚本按 `displayed_price + shipping` 计算。`coupon_amount` 只作为证据和变化提醒，禁止再次从显示价扣除。
- `fulfillment`：`FBA`、`FBM` 或 `UNKNOWN`。
- `delivery_days`：当前买家环境预计送达天数。
- `in_stock`：是否可下单。
- `inventory_observed`：页面可见库存提示；不可见留空。
- `competitor_seller_id`：竞品稳定 Amazon Seller ID；正式卖家级风险判断的主键。
- `seller_name`：页面卖家名称，仅作展示；不得在已有稳定 ID 时按名称合并。
- `seller_identity_status`：`STABLE_ID`、`NAME_ONLY`、`NAME_CONFLICT_WITH_STABLE_ID` 或 `MISSING`。
- `competitor_parent_asin`、`product_family_id`：同父体或同系列识别；缺失时不得猜测。
- `rating`、`reviews`：评分和评论数。
- `sponsored`：是否观察到 Sponsored 展示。
- `observed_keyword`、`observed_position`：观察关键词和位置。
- `zip`：采集 ZIP，主环境固定 `75201`。
- `variant_confirmed`、`page_fields_complete`、`data_conflict`：置信度门控。
- `grade_reason`、`difference_points`。
- `screenshot_path`、`evidence_url`、`captured_at`、`source_url`。
- `fba_transition_risk`：`HIGH`、`MEDIUM`、`LOW` 或 `REVIEW`。
- `fba_transition_assessment_status`：`FORMAL` 或 `PROVISIONAL`；缺稳定 Seller ID 时只能 provisional。
- `selection_evidence_status`：`COMPLETE` 或 `NEEDS_EVIDENCE`；缺精确 ASIN、稳定 Seller ID 或精确履约时只能待补证。
- `fba_transition_risk_reasons`、`fba_monitor_cadence`、`recommended_order_action`。

JSON 顶层可为数组，或：

```json
{
  "seller_id": "56321",
  "marketplace": "US",
  "captured_at": "2026-07-26T10:00:00+08:00",
  "competitors": []
}
```

## CompetitorMapping

- `subject_type`、`subject_id`、`candidate_id`、`lineage_key`
- `own_sku`
- `competitor_asin`
- `variant`
- `original_grade`、`effective_grade`
- `user_promoted_to_a`、`user_confirmed_at`
- `grade_reason`、`difference_points`
- `screenshot_path`、`evidence_url`
- `fulfillment`
- `first_seen_at`
- `last_confirmed_at`
- `source_url`

用户决定使用稳定键 `lineage_key + competitor_asin`。建 SKU 前后只要保留同一个 `candidate_id`，B→A 决定和履约历史都会接续；原始 B 级和差异证据不得覆盖或删除。

## AlertEvent

- `event_type`
- `subject_type`、`subject_id`、`candidate_id`、`lineage_key`
- `own_sku`
- `competitor_asin`
- `variant`
- `grade`
- `old_value`
- `new_value`
- `captured_at`
- `confidence`
- `recommendation`
- `requires_secondary_zip_check`
- `competitor_seller_id`、`seller_name`
- `fba_transition_risk`、`fba_transition_risk_reasons`
- `route_repricing_review`、`route_replenishment_recalculation`、`route_clearance_review`

## SellerFulfillmentProfile

- `seller_key`：稳定 ID 使用 `ID:<seller_id>`；名称级临时档案使用 `NAME_ONLY:<normalized_name>`。
- `competitor_seller_id`、`seller_name`、`seller_identity_status`。
- `first_seen_at`、`last_seen_at`。
- `first_seen_fba_at`、`last_seen_fba_at`、`first_seen_fbm_at`、`last_seen_fbm_at`。
- `observed_asin_count`、`historical_fba_asin_count`、`historical_fbm_asin_count`。
- `current_fba_asin_count`、`current_fbm_asin_count`、`fba_asin_ratio`。
- `fulfillment_transition_count`、`fbm_to_fba_transition_count_90d`。

## FulfillmentHistory

以 `seller_key + competitor_asin + fulfillment + captured_at` 幂等保存。历史只追加和去重，不能用本次快照覆盖过去状态。

## CollectionQueue

每条竞品输出一条只读采集任务，包含 `DETAIL_EXACT_OFFER`、`OTHER_OFFERS`，并按缺口追加 `CAPTURE_STABLE_SELLER_ID`、`CAPTURE_PARENT_AND_SIBLING_VARIANTS`、`CHECK_SELLER_RELATED_ASINS`。高风险使用主 ZIP `75201` 和二次 ZIP `10001`、`90001`；浏览器环境固定为 `ZINIAO_VOCUER_US_ONLY`，写入模式固定 `READ_ONLY`。
