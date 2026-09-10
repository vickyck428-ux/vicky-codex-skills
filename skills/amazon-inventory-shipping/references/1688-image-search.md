# Amazon Image Capture and 1688 Search

Use this workflow only for rows that have a valid child ASIN.

## Browser workflow

1. Use the user's existing logged-in Chrome session.
2. Open `https://www.amazon.com/dp/<ASIN>` and verify that the visible ASIN/variant matches the row.
3. Capture the product title and main-image URL. Prefer the full-resolution URL exposed by the main image; otherwise save a screenshot cropped to the product.
4. Store the image locally in a temporary working folder using the SKU as the filename.
5. Open 1688 image search and upload that image.
6. Collect 3-10 visually relevant candidates when available. Do not select by price before checking structure, material, size, pack quantity, and variant notes.
7. Save the candidate rows and run `scripts/select_supplier_candidates.cjs`.

If Amazon fails, set `Amazon图片状态=抓取失败`, leave supplier fields blank, and continue with the next SKU. If 1688 requests CAPTCHA, ask the user to complete or approve solving it; do not bypass it.

## Candidate-sheet interface

Include these columns:

- `SKU` or `sku`
- `ASIN` or `asin`
- `供应商名称` or `supplier_name`
- `1688链接` or `supplier_1688_url`
- `价格` or `supplier_price`
- `起订量` or `min_order_qty`
- `同款确认` or `same_product`: true only after structure/specification review
- `店铺状态` or `store_status`: use `正常`, `异常`, or `未知`
- `厂家状态` or `factory_status`: use `已确认`, `未确认`, or `未知`
- `候选备注` or `candidate_notes`

## Automatic filtering

1. Reject candidates missing a valid price, URL, or supplier name.
2. Reject candidates marked as a different product or an abnormal store.
3. Calculate the median price among the remaining comparable candidates.
4. Reject a candidate when its price is below 60% of that median.
5. Select the lowest-priced remaining candidate.
6. Mark the result `已匹配` only when the product is confirmed and the store is normal.
7. Mark the result `需要人工确认` when no reliable candidate remains or factory identity is not confirmed.

The result is a purchasing reference. Never place an order automatically.
