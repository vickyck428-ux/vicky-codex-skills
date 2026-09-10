---
name: amazon-handbag-selection-orchestrator
description: Orchestrate one read-only refined-handbag selection run across multiple independent discovery methods and produce deduplicated stable, trend, and long-tail pools. Use for 单次精铺女包全方法选品、女包候选库或多来源女包整合；do not use for annual-goal supervision, 1688 pipeline operation, Sorftime ten-direction research, or a single explicitly supplied atomic dataset.
---

# Amazon 精铺女包选品总控

保持七种发现方法独立；类目竞争环境调研只做最终市场闸门。不得相加不同 Skill 的分数，也不得用多来源数量抵消利润、供给或侵权致命项。

## 开始前

1. 确认目标站点、价格带、经营模式、首批损失上限和数据日期；缺省使用 Amazon US、`$19.99–49.99`。
2. 运行 `scripts/input_validator.py <输入目录>`，先输出可运行方法和缺口。
3. 读取 `references/input-contract.md` 解释输入；读取 `references/handbag-taxonomy.json` 标准化结构。
4. 第一版只读分析，不采购、不创建 Listing、不投广告、不发货。
5. 永久禁止登录或操作用户的 Amazon 卖家后台；永久禁止在用户浏览器中登录或使用 Amazon 前台买家账号，避免账号关联。只能使用用户主动导出的离线文件，以及不携带用户 Amazon 登录态的公开第三方资料。

## 固定工作流

### 1. 建立产品签名

用 `包型 × 材质 × 功能 × 场景 × 风格 × 人群` 描述候选。运行 `scripts/normalize_candidates.py` 可从标题生成初步签名；无法判断的维度留空，不猜测。

### 2. 独立运行发现方法

按可用数据分别调用：

- `$amazon-blue-ocean-screening`：给细分市场排序；
- `$amazon-cross-platform-selection`：找同市场平台供给空缺；
- `$amazon-aba-selection`：找真新词、增长词和窗口；
- `$amazon-keyword-selection`：找流量经济性成立的产品需求；
- `$amazon-software-product-selection`：从商品库找具体 ASIN；
- `$amazon-social-media-selection`：找早期趋势与痛点；
- `$amazon-competitor-store-selection`：从能力相近卖家归纳重复成功模式。

每种方法单独保存原始证据、数据日期、内部结论和缺口。数据不足时输出 `NEEDS DATA`，不得按通过处理。

### 3. 产品级去重

按结构和核心需求去重，不按名称或关键词去重。父子体、颜色差异、轻微装饰差异通常合并；包型、核心功能或使用场景不同才保留为独立候选。

### 4. 选择市场闸门

只把证据较强且供应链可能成立的前 1–3 个细分市场交给 `$lc_amazon_market_research`。市场四表不足时保留候选，但状态最高只能为 `优先补数据`。

### 5. 应用六道产品门槛

按顺序判断：真实需求、Amazon 供给、流量经济性、单件利润、供应链物流、IP/合规/退货。完整口径见 `references/decision-gates.md`。

任一项为 `不通过`，总状态为 `淘汰`；存在 `待验证`，总状态不得高于 `优先补数据`；六项均通过才可标记 `值得打样/小批测试`。

### 6. 分池和测试纪律

- 稳健长销：默认首批约 10 件；
- 早期趋势：默认 3–5 件；
- 高利润长尾：默认 2–3 件；
- 监控：设置复查日期和触发指标；
- 淘汰：保存决定性原因，防止重复研究。

读取 `references/testing-and-exit.md` 设置最大损失、观察周期、补货条件和退出条件。

## 统一候选记录

按 `references/candidate-schema.md` 保存；至少包含候选 ID、产品签名、发现方法、来源、证据日期、目标词、同款/替代品/履约、价格成本利润、预估 ACoS、评论/广告/季节/IP/物流风险、六道门槛、经营池、状态、下一步和置信度。

## 利润纪律

必须同时报告广告前毛利率、广告前单件利润、盈亏平衡 ACoS、预估 ACoS 和广告后贡献利润。成本缺失时只生成公式和 `暂定` 状态，不得给采购结论。

## 输出

每次建立独立项目目录，保存：

1. 七种方法独立结果；
2. 类目市场闸门结果；
3. 去重候选总表；
4. 最多 6 张正式产品卡；
5. 淘汰清单；
6. 数据缺口与运行日志。

最终候选必须能反查原始文件或公开 URL。没有候选通过时如实交付 0 款，不凑数。

## 资源

- `references/handbag-taxonomy.json`：女包结构和中英文别名；
- `references/candidate-schema.md`：统一候选字段；
- `references/input-contract.md`：输入文件与方法映射；
- `references/decision-gates.md`：六道门槛和致命项；
- `references/testing-and-exit.md`：测品、补货和退出规则；
- `scripts/input_validator.py`：输入文件验收；
- `scripts/normalize_candidates.py`：标题到产品签名的初步标准化；
- `assets/精铺女包选品空白模板.xlsx`：可复制的标准工作簿。
