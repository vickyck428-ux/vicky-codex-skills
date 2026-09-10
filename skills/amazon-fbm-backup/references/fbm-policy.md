# FBM 备份提醒规则

## 覆盖天数

```text
FBA支撑天数 = FBA可售 ÷ (加权日销 × B1)
```

加权日销为 0 时只写数据问题，不生成 FBM 备份提醒。

## 提醒优先级

1. 清货、停补 SKU：`NO_REMINDER`。
2. 核心库存字段缺失：`DATA_ISSUE`。
3. FBA 可售为 0 且及时在途不足：`URGENT_BACKUP_REMINDER`。
4. FBA 支撑不超过 5 天且及时在途不足：`BACKUP_REMINDER`。
5. 其他：`NO_REMINDER`。

## 固定政策

- 中国直发 FBM 物流政策值固定为 98 元，只作政策记录。
- 不计算利润、亏损、成本底线或目标价。
- 不输出 Offer 激活、关闭、改价或改数量步骤。
- 不执行任何 FBM Offer 操作。
- 本店 Coupon 永久禁用。
