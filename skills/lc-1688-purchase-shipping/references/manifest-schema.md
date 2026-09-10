# 截图识别清单规范

使用 UTF-8 JSON。路径既可写成相对清单文件所在目录的相对路径，也可写绝对路径。

## 顶层结构

```json
{
  "schema_version": 1,
  "batch": {
    "batch_id": "260728-01",
    "source_batch_fingerprint": "由 prepare 生成",
    "source_files": ["/absolute/path/IMG_0001.PNG"],
    "generated_at": "2026-07-29T10:00:00+08:00"
  },
  "items": [],
  "excluded": []
}
```

`source_files` 必须包含参与识别的所有原始截图。`source_batch_fingerprint` 对文件内容计算，不依赖输入顺序。

## items

每个可购买规格一项：

```json
{
  "source_index": "001",
  "detail_id": "可省略，由 prepare 生成",
  "include": true,
  "payment_status": "已下单",
  "purchase_status": "待收货",
  "product_name": "商品名称",
  "spec": "颜色 / 尺寸 / 款式",
  "ordered_qty": 5,
  "supplier": "供应商",
  "order_no": null,
  "order_date": null,
  "source_screenshot": "/absolute/path/IMG_0001.PNG",
  "product_image": "/absolute/path/001_product.png",
  "occurrence_index": 1,
  "issues": [],
  "notes": ""
}
```

规则：

- `source_index`、`product_name`、`spec`、`supplier`、`payment_status`、`purchase_status` 必填。
- `ordered_qty` 必须为大于 0 的整数，禁止用字符串或估算区间。
- `payment_status` 仅允许 `已下单`、`待付款`。
- `purchase_status` 仅允许 `待付款`、`待发货`、`已发货`、`运输中`、`待取件`、`待收货`、`已签收`、`已取消`。
- `product_image` 必须是该行干净商品图；`source_screenshot` 必须是识别来源。
- 历史数据已有 `detail_id` 时保留；新数据由 `prepare` 生成。
- 同一签名确有多笔明细时显式设置 `occurrence_index`。滚动重叠不属于多笔明细，必须删除。

## 识别疑点

`issues` 中的阻塞项会使 `validate` 失败：

```json
{
  "code": "uncertain_qty",
  "message": "截图右侧数量被浮层遮挡",
  "blocking": true
}
```

常用代码：

- `uncertain_title`
- `uncertain_spec`
- `uncertain_qty`
- `missing_product_image`
- `image_mapping_uncertain`
- `possible_duplicate`

用户确认并修正后，删除已解决的阻塞项；不要仅把 `blocking` 改为 `false` 来绕过检查。

## excluded

将不应计入采购数量的截图证据记录在这里：

```json
{
  "source_screenshot": "/absolute/path/IMG_0002.PNG",
  "product_name": "蓝绿色波点包",
  "reason": "shopping_cart",
  "notes": "仅出现在购物车/详情浮层，没有订单证据"
}
```

`reason` 建议使用：

- `shopping_cart`
- `detail_only`
- `scroll_overlap`
- `cancelled_before_purchase`
- `user_excluded`

## 飞书载荷

`payload` 命令只生成 dry-run 载荷，不连接飞书。载荷包括：

- `match_field`: 固定为 `明细ID`；
- `fields`: 文字、数字、单选、日期和布尔字段；
- `attachments`: 本地 `商品主图`、`源订单截图` 路径。

真正写入时必须先实时读取飞书字段结构，并按 `明细ID` 决定更新或新增。
