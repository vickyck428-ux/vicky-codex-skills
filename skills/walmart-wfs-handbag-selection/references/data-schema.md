# 数据结构

## 关键词主表

稳定字段：

- `keyword`：规范化关键词，唯一。
- `pool`：`MAINSTREAM` 或 `STYLE`。
- `family`、`scenario`：包型/风格族与使用场景。
- `pilot_selected`、`pilot_order`：10个深度试跑词及顺序。
- `source`：关键词来源。

运行字段：`validation_status` 和10项关键词指标。成功运行日期与冷却时间以运行账本为准，不写入 Skill 模板。

## 运行账本

SQLite 表：

- `runs`：`run_id`、日期、模式、状态、页数、原始记录、唯一ASIN、新增、变化、历史重复、疑似同款、合格数、报告哈希和错误。
- `run_keywords`：运行词、池、family、`BENCHMARK/DISCOVERY`、页深、状态、完成页数、记录数和下次可运行时间。
- `products`：ASIN主档、Parent ASIN、标题指纹、品牌、来源词、首末发现时间、价格销量、Walmart/IP/供应链状态、图片指纹和独立商品组。
- `observations`：每次运行每个ASIN一条观察，含变化原因、是否合格及疑似同款。
- `deliveries`：渠道、报告类型、日期、报告哈希、幂等键、发送状态和消息ID。

迁移时必须整体复制 SQLite 文件及其有效 WAL/SHM 状态；推荐先停止写入并执行 SQLite backup，而不是仅复制正在写入的主文件。

## Walmart 核验记录

每个市场分别保存以下信息：精确同款数、近似款数、WFS近似款数、价格、配送和评价供给、关键词/替代词/图片搜索完成状态、Assortment Growth、Search Insights、图片缺口证据、核验时间和备注。

状态只能为 `INITIAL_GAP`、`STRONG_GAP`、`WEAK_SUPPLY`、`NEEDS_REVIEW`、`SUPPLY_DENSE`，或尚未核验的内部状态。US 与 CA 不得互相覆盖。

## 日报

必需字段：

- 运行日期、模式、状态、运行词、请求/完成页数、原始记录数、唯一ASIN数；
- 当日新增独立商品数、关键变化数、历史重复数、疑似同款数；
- `INITIAL_GAP`、`STRONG_GAP`、`WEAK_SUPPLY`、`NEEDS_REVIEW` 分项数量；
- 已确认机会数、合格候选数、阻塞原因、报告哈希；
- `marketplace_mutations_performed=false`。

报告投递幂等键格式保持 `日期 + 报告类型 + 报告哈希`。相同键不得重复发送。

## 便携结果包

便携目录固定包含：

- `submission.json`：`schema_version`、`mode=DAILY`、`status=PENDING/SUCCESS`、`run_date`、`run_id`、创建人和安全标记。
- `daily_results.csv`：固定49列，保存30个独立产品组及Amazon、Walmart US/CA、FBM、WFS、利润、供应、包装、条码和图片证据。
- `images/`：CSV通过相对路径引用的商品或核验证据图。
- `validation.json`：数量、15/15、FBM状态、WFS数量/店铺分配、错误和警告。

只有 `DAILY/SUCCESS`、30款、每池15款且基础门禁完整的结果包允许进入原运营电脑的商品池同步。最多4款可标记WFS，每个美国店最多2款。

## 外部配置边界

Skill 配置只保存路径、固定门槛和市场邮编。以下必须在外部运行目录或系统认证存储中：账号、Cookie、令牌、飞书ID、商品历史、关键词运行日期、冷却、断点、日志、CSV/XLSX及发送记录。
