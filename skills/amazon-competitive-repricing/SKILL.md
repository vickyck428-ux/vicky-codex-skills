---
name: amazon-competitive-repricing
description: Run one Amazon clearance-and-repricing workflow that keeps inventory clearance and price calculation as separate internal modules but delivers one workbook. Use for 运行美国站清货与调价、亚马逊清货与调价、FBA 跟价、清货价格、竞品图片搜同款、B级当做A级、最大亏损、经营保本线、人工改价回传或定期调价报告。
---

# Amazon 清货与调价

向用户提供一个入口和一张综合表；内部仍按“清货门禁 → 调价计算”顺序运行。只处理清货与调价，不计算补货数量。

## 硬规则

- 每次只处理一个 `sellerId + marketplace`。默认指令是“运行美国站清货与调价”。
- 最新 FBA Inventory Report 和 Inventory Age/Inventory Health Report 是强制入口。库龄快照超过 7 天时不得生成正式建议。
- `$amazon-inventory-clearance` 是清货状态和建议清货数量的唯一正式来源；不得改写其公式，也不得由本 Skill 自行判定“主动清货”或“紧急清退”。
- 发现老库存、超量、库龄费风险、供给超过 90 天或长期零销量，却没有有效清货结论时，返回 `CLEARANCE_REVIEW_REQUIRED`；不搜竞品、不生成正式降价。
- 本店 Coupon 永久禁用。不得推荐、创建、执行或把 Coupon 写入本店动作方案，除非用户以后亲自明确撤销。
- 允许读取并记录同行 Coupon 作为证据，但按用户确认口径不从竞品页面显示价中另行扣减。
- `price_write=FORBIDDEN`。不启用自动定价，不自动修改 Standard Price、Sale Price、List Price、Price Discount 或促销。
- Vocuer 店铺、Amazon 登录态、卖家精灵和 Seller Central 只允许在紫鸟账号“中国账号-陈雨曦 - 宝贝咪-Vocuer”的美国站环境操作；禁止在普通 Chrome、Codex 内置浏览器或其他环境打开，禁止复制登录态、Cookie 或账号资料。
- 缺 Seller Central Fee Preview 的精确佣金或 FBA 配送费时，正式建议价必须为空。
- FBA 报告缺少某 SKU 时标记“无有效 FBA 库存记录”，不得自动当作库存为 0。
- 不制造 List Price。只有真实、合规且可验证的历史参考价才可展示划线价建议。

## 运行流程

1. 完整读取 [references/input-schema.md](references/input-schema.md)，校验店铺、站点、SKU、ASIN、报告日期和文件时效。
2. 调用 `$amazon-inventory-clearance` 生成同一 SKU、ASIN 和库龄快照日的清货结论。清货模块保留状态和数量所有权。
3. 笔袋类商品仍参与清货判断，但固定显示“排除调价”。标题或类目命中 `pencil case|pencil pouch|pen case|pen pouch|笔袋|文具袋` 时，不搜竞品、不生成建议售价。
4. 非笔袋 SKU 通过清货门禁后，读取采购成本；头程缺失时默认人民币 10 元。
5. 读取运行日 USD/CNY，并增加 2% 不利波动缓冲。读取当前 Seller SKU/ASIN 对应的精确佣金和 FBA 配送费。
   - 使用 `inventory-ai-runner/parse_fee_preview.mjs` 读取 CSV、TXT 或 XLSX Fee Preview；
   - Seller SKU 精确匹配优先，只有当前映射中 ASIN 唯一时才允许 ASIN 回填；
   - MFN/FBM 费用行、非 USD、重复冲突或不完整行不得标记为精确费用。
6. 计算两条底线：
   - 现金底线：采购成本、头程、精确佣金和 FBA 配送费；
   - 经营保本线：现金底线再加入已知仓储、退货准备金、广告及其他变动成本。
7. 经营成本完整时，正常商品不得低于经营保本线；缺失时可显示现金底线，但必须标记“经营利润待确认”。主动清货最多亏落地成本 15%，紧急清退最多亏 30%。
8. 只用 Amazon StyleSnap 上传本店原主图找同款；结果明显无关时允许本地免费裁剪后重搜。禁止关键词搜款、付费图片搜索 API、图片生成和付费抠图。
9. 必须通过紫鸟内的 Amazon 详情页及卖家精灵插件核对精确变体、FBA/FBM、配送时间和实际到手价。FBA 到手价等于页面当前显示价；FBM 到手价等于页面显示价加运费。搜索结果截图本身不能作为正式定价证据。
   - Seller 级 FBA 转仓风险统一读取 `$amazon-competitor-monitor` 结果，本 Skill 不重新评分。
   - 仅高风险提示不得直接改价；确认精确 A 级竞品 `FBM→FBA` 后，必须用第二 ZIP、详情页卖家和子体履约复核，再重算竞争到手价与配送差距。
   - 选品阶段只有 `candidate_id` 时只保存风险证据；映射 Seller SKU 后才能进入本店 SKU 调价复核。
10. 按 [references/repricing-policy.md](references/repricing-policy.md) 确认 A/B/C 等级。B→A 只对 `Seller SKU + 竞品 ASIN` 生效并保留原始 B 级和差异。
11. A 级 FBM 只有配送时间已知或明确中国直发时才可计算正式 FBA 溢价；配送未知只作参考。
    - 本店为 FBA 时按竞品绝对配送天数分层；不得因 `own_delivery_days` 为空而把溢价归零。
    - 可用 `no_raise_this_run=true` 临时禁止本次涨价；该限制只影响本次计算，不改变后续默认涨价规则。
12. 运行确定性计算：

```bash
node scripts/calculate_repricing.cjs \
  --input repricing-input.json \
  --output repricing-decision.json \
  --as-of-date YYYY-MM-DD
```

13. 使用库存工作流的一份 `inventory-actions.json` 保存状态，生成一份 `Vocuer-US-清货与调价表-YYYYMMDD.xlsx`。不得另建清货或调价平行状态文件。
14. 无论竞品是否转为 FBA，清货路由仍由 `$amazon-inventory-clearance` 独立决定；本 Skill 不得借竞品风险创建主动清货结论。

## 综合工作簿

统一工作簿固定包含：

- `今日操作`：只放可执行动作或明确需补资料的动作；正式建议价为空时不得改价；
- `全部商品决策`：全部 SKU 的清货状态、数量、竞品和调价结论；
- `竞品确认`：A/B 等级、ASIN、差异、履约、价格、截图和 B→A 选择；
- `待补数据`：费用、成本、库存、图片、履约和竞品缺失项；
- `规则与来源`：快照、时效、底线、观察期、来源和永久 Coupon 禁令。

正式建议必须同时满足：库龄证据不超过 7 天、竞品证据不超过 4 天、精确费用齐全、采购成本齐全、精确变体和履约已确认。每行显示价格可信度、有效期截止、现金底线、经营保本线、经营成本完整性、无法跟价原因和下一复查日期。

## 回传 Excel

当用户上传同一份综合表并说“按我的竞品确认重新计算”时，先运行两阶段回传：

```bash
node "${INVENTORY_AI_RUNNER}/import_clearance_repricing_feedback.mjs" \
  --workbook <回传.xlsx> \
  --snapshot <inventory-actions.json> \
  --cost-registry "${SKU_COST_REGISTRY}" \
  --output <feedback-preview.json>
```

先展示预览。只有用户明确确认该 `preview_id` 后才能使用 `--apply-preview ... --confirmation-id ...`。允许更新的内容只有：

- 当前仍缺失的采购成本、来源和生效日；已有非空成本不得覆盖；
- 指定 `Seller SKU + 竞品 ASIN` 的 B→A 决定；
- 用户已经在 Seller Central 手工完成的实际改价记录。

回传不得直接触发 Amazon 改价，也不得改变永久 Coupon 禁令。应用后重新运行清货与调价计算，旧表中的公式或手填建议价不作为执行依据。

## 定期运行

- 复用现有每日 10:00 heartbeat，不新建第二个调价自动化。
- 每日复查已确认 A 级竞品；无实质变化只留 Codex 记录。
- 周一使用最新库存、库龄和 Fee Preview 生成全量综合表。
- 周四仅在关键变化时生成变化表。
- 飞书与当前 Codex 调价任务交付同一份综合表，并以现有 `inventory-actions.json` 记录发送幂等键。

## 人工改价指引

只在 `今日操作` 中“是否可以操作=是”且“正式建议价”非空时，提示用户前往 `Manage All Inventory → SKU → Edit → Offer` 修改 Standard Price。若 Sale Price 正在覆盖，必须先清除 Sale Price 和日期。所有提示均注明“只读建议，未执行改价”。

## 校验

- 运行 `node scripts/calculate_repricing.cjs --self-test`。
- 运行统一工作簿和回传导入器测试。
- 校验笔袋有清货结论但无建议售价，Fee Preview 缺失时建议价为空，B→A 不影响其他 SKU/竞品。
- 校验过期数据自动失效、Sale Price 覆盖提示正确、阻断改价不混入可执行动作。
- 校验本店 Coupon 调用数为 0、Amazon 自动改价调用数为 0。
- 修改前后核对 `$amazon-inventory-clearance` 文件哈希，必须完全一致。
