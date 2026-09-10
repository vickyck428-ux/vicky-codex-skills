# WFS发货工作簿

内部总表固定包含：

1. `批次总览`：两店件数、预计/实际重量、100kg完成度和异常数。
2. `美国站1待发`、`美国站2待发`：候选、来源、SKU、GTIN、变体、T1数量、箱号和Shipment ID。
3. `按箱拣货`：店铺、箱号、商品、变体、SKU、数量。
4. `箱内SKU明细`：每箱SKU数、件数、实际重量和尺寸。
5. `采购到货缺口`：已批准但未采购、未到仓或未实测的记录。
6. `异常与缺失数据`：未审批、缺利润/条码/变体/实测/箱号/Shipment ID及跨店箱号冲突。
7. `证据索引`：来源记录、订单号、截图、候选ID、1688 detail ID和证据时间。

正式平台映射只包含：审批通过、实际到货至少1件、已实测、已分配箱号和店铺独立Shipment ID的记录。两个店分别输出文件。

平台模板映射JSON示例：

```json
{
  "sheet": "Sheet1",
  "headerRow": 1,
  "columns": {
    "sku": "SKU",
    "gtin": "GTIN",
    "planned_qty": "Quantity",
    "carton_no": "Carton ID",
    "platform_shipment_id": "Shipment ID"
  }
}
```
