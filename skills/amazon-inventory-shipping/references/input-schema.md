# Input Schema

## Minimal test-launch model

The script recognizes Chinese and English column aliases. Do not require the user to rename an existing sheet.

### Required values

| Canonical field | Common accepted headers | Rule |
|---|---|---|
| `sku` | `SKU`, `sku`, `商品SKU`, `卖家SKU` | One row per exact variant |
| `asin` | `ASIN`, `asin`, `子ASIN`, `child_asin` | Use the Amazon.com child ASIN |
| `launch_date` | `上架日期`, `首次上架日期`, `launch_date`, `sale_start_date` | First date the SKU was sellable |
| `cumulative_valid_units` | `累计有效出单件数`, `累计出单量`, `累计销量`, `cumulative_valid_units`, `cumulative_orders` | Count units, excluding cancelled orders |

### Optional values

| Canonical field | Common accepted headers | Blank behavior |
|---|---|---|
| `current_stock` | `当前库存`, `可售库存`, `FBA库存`, `current_stock` | 0 |
| `inbound_on_way` | `在途数量`, `在途库存`, `inbound_on_way`, `inbound` | 0 |
| `variant_note` | `规格备注`, `规格`, `variant`, `spec` | Blank |
| `product_image` | `产品图片`, `图片`, `product_image`, `image_url` | Fetch from Amazon |
| `selected` | `是否选中`, `入选`, `selected` | Every row is selected |

False selection values are `0`, `false`, `no`, `n`, `否`, and `不选`.

### Appended output fields

- `上架天数`
- `日均出单`
- `发货分档`
- `目标库存`
- `建议发货数量`
- `计算说明`
- `数据检查`
- `产品名称`
- `Amazon图片状态`
- `Amazon主图链接`
- `Amazon图片本地路径`
- `1688匹配状态`
- `1688供应商`
- `1688链接`
- `供应商价格`
- `起订量`
- `筛选说明`

## Date and validation behavior

- Use the run date unless `--as-of-date YYYY-MM-DD` is supplied.
- Accept real Excel dates, ISO dates, `YYYY/MM/DD`, and common Chinese date strings.
- Mark missing/invalid required values as `需要人工确认`.
- Treat negative stock, inbound, or sales values as 0 and record a warning.
- Preserve duplicate SKUs but flag them in `数据检查`.

## Legacy coverage-days model

The legacy `generate_shipping_plan.py` script accepts `sku`, `daily_sales`, `current_stock`, `inbound_on_way`, `lead_time_days`, `safety_stock_days`, `target_days_override`, `carton_qty`, and `min_ship_qty`.
