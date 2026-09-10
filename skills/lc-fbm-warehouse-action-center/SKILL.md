---
name: lc-fbm-warehouse-action-center
description: 将 Amazon 与 Walmart 的 FBM 已出单记录或订单报表转换为 WFS/FBA 首发和补货动作。用于FBM成交转仓、订单历史回跑、发货需求总表或已存在动作的补1件；不用于售前选品、共享候选池、T1审批、采购到货、装箱、Shipment ID或Listing工作簿。
---

# FBM成交转仓与补货中心

## 生产入口

固定使用 `SHIPPING_ORCHESTRATOR_ROOT` 指向的现有运行器，先读取其中的配置和脚本，不要另建平行实现。

输入目录：

- Amazon：`${SHIPPING_ORDER_INPUT_ROOT}/Amazon/`
- Walmart：`${SHIPPING_ORDER_INPUT_ROOT}/Walmart/`

唯一前台输出为飞书 Base `发货需求总表`。除非用户明确要求，不生成Excel。

## 执行流程

1. 先运行 `npm test`；失败时停止写飞书并报告失败项。
2. 运行 `npm run backfill:actions` 做只读回跑。
3. 核对 `mismatches` 为空后才允许写飞书。
4. 写入前运行 `node scripts/snapshot_action_base.mjs --output-dir <本次输出目录>` 保存快照。
5. 运行 `node scripts/setup_action_base.mjs` 幂等补齐字段和六个视图。
6. 运行 `node scripts/feishu_sync_actions.mjs --input <回跑JSON>`，确认 `create_count/update_count`。
7. 用户已授权本批写入时，增加 `--apply`；禁止用逐行并发写入。
8. 需要补图时运行 `resolve_public_images.mjs`，再用 `feishu_sync_actions.mjs --apply --upload-images` 串行上传已核验图片。
9. 写入后使用飞书云端查询核对总数、渠道、品牌、状态和原因分布；不要用单页记录列表推断全表结论。

## 订单与路由规则

- Amazon数字TXT按内容和外部账号映射识别；不得把 Seller ID 写入 Skill。
- Amazon `Pending/Cancelled`不触发；已交运状态触发。
- Walmart从外部配置的 `Ship Node ID -> Walmart品牌` 映射识别店铺；不得把真实节点 ID 写入 Skill。
- Walmart `Acknowledged/Shipped/Delivered`有效；取消、退款、拒绝无效。
- Walmart US Baguery FBM → 同店WFS + Vocuer US FBA。
- Walmart US StyleSack FBM → 同店WFS + Benpo Bar US FBA。
- Walmart CA FBM → 同店WFS-CA，不跨站。
- Amazon US/UK/DE FBM → 同账号、同站点FBA。
- 每条首次动作建议量固定为1。

严格采用两阶段处理：

1. 仅FBM成交创建动作。
2. WFS/FBA销量只能更新已经存在的同Seller SKU、同账号、同站点、同渠道动作为“待补1件”；不得把普通仓配订单批量创建成任务。

若仓配销量找不到已有FBM动作，保留未关联信号并报告，不猜SKU、不为凑数量强行建行。只有用户明确批准例外时才新增动作。

## 飞书展示

六个视图固定为：

1. ① 今日要做
2. ② WFS要发
3. ③ FBA要发
4. ④ 待加购
5. ⑤ 待补货
6. ⑥ 全部记录

可见前列固定为：商品名称、产品图片、为什么选择它、下一步应该怎么做、当前状态、来源品牌、目标账号、目标渠道、目标站点、Seller SKU、规格/变体、建议发仓数、最近成交日、成交证据数。

- 冻结前4列。
- `为什么选择它`、`当前状态`和品牌使用彩色单选标签。
- 缺图记录整行淡黄色。
- `加购状态`和`动作状态`保留为隐藏后台字段，不删除、不合并。
- 客户姓名、电话、地址和其他PII不得写入Base。

下一步优先级固定为：补图片 → 基础风险筛查 → 生成Listing → 补1688精确变体 → 生成/确认加购预览 → 发仓或补货。

缺1688精确变体时显示“待手动加购”，继续保留动作，不进入异常清单。

## 图片门禁

- Amazon只按精确ASIN核验。
- Walmart只按精确GTIN/UPC，并同时核对商品标题和品牌。
- 只允许匿名公开HTTP读取；禁止使用用户Chrome登录Amazon、Walmart或Google账号查图。
- 永久拦截Seller Central、Vendor Central、账号中心和登录页；遇验证码、登录或风控立即停止。
- 无法确认时保持空图和“待补图片”，禁止使用相似图冒充。
- 按内容哈希去重，飞书附件串行上传。

## 安全边界

- 只生成和更新动作提醒；不得自动发布Listing、采购、加购、创建货件、结算、下单或付款。
- 自动加购仍需先生成preview，只有用户回复“确认加购＋preview_id”后才能补精确变体差额。
- 缺基础风险、利润、图片或1688精确变体的记录只留在发货需求总表，不进入正式WFS审批、采购或发仓。
- 基础筛查通过必须注明“不代表保证不侵权”。
- 保持文件哈希、订单行、状态版本和action key幂等；重复报表不得重复创建动作。

## 每日提醒

使用现有 `fbm-12-00` 自动任务和 `scripts/send_report_reminder.mjs`。每天12:00（Asia/Shanghai）私聊Vicky；按文件内容识别数字Amazon TXT和Walmart店铺ID。周一在同一条消息追加库存、Listing与最近7天订单报告清单，不创建第二个提醒。
