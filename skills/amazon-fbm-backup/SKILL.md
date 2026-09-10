---
name: amazon-fbm-backup
description: Predict FBA stockout risk and generate read-only FBM backup reminders without pricing, profit, quantity, or Offer actions. Use for FBA 断货备份、FBM 备份提醒或中国直发兜底提醒。
---

# Amazon FBM 备份提醒

只输出 FBA 断货风险和 FBM 备份提醒。

## 硬规则

- 本店永久禁用 Coupon。
- 不读取国内库存或 FBM 货源。
- 中国直发 FBM 物流政策值固定为 98 元，但不得据此计算利润、亏损、成本底线或目标价。
- 不输出激活、关闭、改价或改数量步骤。
- 不创建、激活或修改任何 Offer。
- 清货、停补 SKU 不生成备份提醒。

读取 [references/schema.md](references/schema.md) 和 [references/fbm-policy.md](references/fbm-policy.md)。

## 生成提醒

```bash
node scripts/generate_fbm_backup_preview.cjs \
  --input fbm-input.json \
  --output fbm-reminder.json
```

输出仅允许：

- `URGENT_BACKUP_REMINDER`
- `BACKUP_REMINDER`
- `NO_REMINDER`
- `DATA_ISSUE`

不得出现价格、利润、成本底线、建议数量或 Seller Central 人工操作步骤。
