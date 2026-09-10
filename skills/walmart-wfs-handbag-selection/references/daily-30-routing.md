# 每日30款保存与分流

## 正式结果口径

- 每个工作日输出30个独立产品组：`MAINSTREAM` 15款、`STYLE` 15款。
- 同 Parent ASIN、重复 ASIN、相似图片或同一1688商品只算一个产品组。
- 30款都必须通过沃FBM基础门禁并保存为FBM候选；不自动发布。
- 从30款中最多选择4款作为沃美WFS优先候选，允许0–3款。
- 沃美国站1最多2款、站2最多2款；同一产品组只能进入一个店。
- WFS每款只建议T1 1件。审批不等于采购，系统不得自动采购或创建货件。

## FBM基础门禁

正式 `SUCCESS` 批次的30款必须具备：候选ID、独立产品组ID、1688商品ID或链接、商品名称、图片引用、基础利润，以及品牌/IP、禁限售、供应和包装检查。资料不全时保持 `PENDING`，不得用弱款或虚构数据凑30款。

美国和加拿大可复用同一产品，但必须分别记录需求和缺口。加拿大未核验时写 `NEEDS_REVIEW`，不得复制美国结论。

## WFS硬门禁

只有以下全部通过时，才能把 `manual_wfs_choice` 写为 `WFS`：

- Amazon US售价至少25美元；父体30天销量150–600；具体颜色/子体销量大于0。
- 排除促销冲高、断货恢复、广告冲高和季节尾声。
- Walmart US为 `STRONG_GAP`，或有需求证据的 `WEAK_SUPPLY`。
- Listing质量分至少80；完整预计贡献利润至少70元。
- 侵权、专利、供应、包装、条码和原产国检查全部通过。
- 证据不超过7天。

`INITIAL_GAP` 只走FBM。Walmart SKU或UPC/GTIN缺失时，可以保留WFS候选，但不能进入正式WFS审批交接。

## 优先级与物流

采购优先级依次为：稳定款补货、T3/T5升级、沃FBM有效首单T1、亚美畅销缺口T1。100kg只是国家运输渠道条件，合格重量不足时继续等待，不设硬期限，也不用弱款凑重。两店可以共用国际运输批次，但平台货件、标签、箱号、Shipment ID和库存记录必须分开。

## 便携结果包

Mac mini缺少Node、飞书权限或原电脑目录时，运行：

```bash
python3 scripts/portable_batch.py init --output "$HOME/Documents/wfs-daily-YYYYMMDD" --date YYYY-MM-DD
```

Codex填写 `daily_results.csv` 和图片后，把 `submission.json` 的 `status` 改为 `SUCCESS`，再运行：

```bash
python3 scripts/portable_batch.py check --batch-dir "$HOME/Documents/wfs-daily-YYYYMMDD"
python3 scripts/portable_batch.py pack --batch-dir "$HOME/Documents/wfs-daily-YYYYMMDD"
```

把生成的ZIP交回原运营电脑。便携模式不直接写飞书，也不依赖Node/npm。
