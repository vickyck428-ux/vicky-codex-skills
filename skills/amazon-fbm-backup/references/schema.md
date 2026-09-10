# FBM 备份提醒输入结构

JSON 顶层可为数组或 `{ "sku_pairs": [] }`。

## SkuPair

- `asin`
- `fba_sku` 或 `seller_sku`
- `fba_available`
- `weighted_daily_sales`
- `b1`
- `fba_days_of_supply`：可省略，由脚本计算
- `timely_fba_inbound_sufficient`
- `clearance_status`
- `captured_at`

国内库存、FBM 货源、包装、采购成本、佣金、价格和 Offer 状态都不属于输入。
