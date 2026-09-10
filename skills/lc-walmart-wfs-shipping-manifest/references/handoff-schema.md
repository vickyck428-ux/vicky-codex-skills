# WFS交接数据契约

## 必填主键

- `source_type`：`WALMART_FBM_FIRST_ORDER`或`AMAZON_TO_WFS_M7`。
- `source_record_key`：沃订单号或M7 candidate_key。
- `candidate_id`、`product_group_key`、`market=US`、`store_name`、`sku`。
- `handoff_key`：系统幂等键，不得使用商品标题生成。

## 商品与证据

- `item_id`、`gtin`、`title`、`variant`、`image_ref`。
- `supplier_detail_id`、`supplier_order_no`。
- `source_order_id`、`source_order_date`、`screenshot_fingerprint`、`screenshot_refs`。
- `evidence_observed_at`、`evidence_version`。

沃FBM来源还必须有`paid=true`、`fulfilled=true`、`cancelled=false`、`refunded=false`、`tracking_issue=false`、`infringement=false`和具体变体。

## 利润门禁

完整利润输入包括售价、实际重量、包装长宽高、产品成本、头程、关税、平台佣金、WFS费、仓储、条码包装和清货预留。没有真实退货损耗时由接口按售价12%预留。

- 完整且贡献利润不低于70元：可进入审批。
- 缺字段：`NEEDS_DATA`。
- 利润低于70元：`BLOCKED`。

## 审批和进度

- `approval_status`：`NOT_READY/PENDING/APPROVED/RETURNED/REJECTED`。
- `feishu_record_id`：`WFS选品审批`中的飞书记录ID。
- `purchase_feishu_record_id`：确认采购后创建或关联的`采购发货明细`记录ID；审批通过但未确认采购时必须为空。
- `workflow_status`：`NEEDS_DATA/PENDING_APPROVAL/APPROVED_WAITING_PURCHASE/PURCHASED_WAITING_RECEIPT/RECEIVED_WAITING_MEASUREMENT/READY_TO_PACK/PLATFORM_SHIPMENT_CREATED/LABELED/HANDED_OVER/RECEIVED_BY_WFS/BUYABLE/T1_OBSERVATION/EXPIRED/REJECTED`。
- `planned_qty`永远为1。
- 生成采购明细的双门禁是`approval_status=APPROVED`且`purchase_status=PURCHASED`，任一不满足都不得创建。
- `estimated_weight_kg`默认0.4，仅用于积重预测。
- `actual_weight_kg/length_cm/width_cm/height_cm`是正式分箱门禁。
- `carton_no`不得跨店复用；`platform_shipment_id`必须按店铺独立。
