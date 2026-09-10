---
name: amazon-competitor-monitor
description: Build and maintain Amazon same-product competitor mappings, compare displayed price plus shipping, and alert on Coupon, fulfillment, stock, delivery, or Sponsored changes. Use for 竞品搜图、同款 ASIN 建库、竞品价格监控或履约变化；do not use for own-store price writes or Coupon creation.
---

# Amazon 竞品监控

只做前台只读采集、映射维护和异常提醒。不得修改本店价格、广告、Listing 或库存。

## 硬规则

- 本店永久禁用 Coupon：不得推荐、创建、执行或把 Coupon 写入本店操作建议。
- 可以读取同行 Coupon，但只记录并监控变化。统一有效价为 `displayed_price + shipping`，禁止再次扣除 Coupon。
- 页面字段缺失、变体不确定或数据冲突时，置信度为低；只提示人工复核，不生成价格同步建议。
- 广告只写“观察到的 Sponsored 位置、关键词和第三方估算”，不得推断真实预算或竞价。
- 每次只处理一个 `sellerId + marketplace`。未指定时先列店并确认。

## 建库与复查频率

1. 每月首次运行，用商品主图或用户图片搜图，建立 `CompetitorMapping`。
2. 必须打开详情页确认精确子变体，搜索卡片只能作为候选。
3. 固定美国 ZIP `75201` 和同一买家环境。重要异常再用 `10001`、`90001` 复核。
4. 分级：
   - A：完全同款、同材质/尺寸/关键功能和同一子变体；
   - B：高度相似，可替代但存在明确差异；
   - C：风格或使用场景相近，仅作市场参照。
5. A 每日 10:00；B 每周一；C 每月复查。
6. 用户按 `lineage_key + 竞品 ASIN` 把 B 提升为 A 后，保留原始 B 级和差异证据，并从下一次每日运行起按有效 A 级监控；选品阶段 lineage 使用 `candidate_id`，建 SKU 后继续携带该 `candidate_id`。
7. FBA 转仓风险覆盖基础等级频率：高风险每日、中风险每周两次、低风险每周一次；从进入选品池持续到本店库存售完或停止经营。

前台数据优先使用浏览器桥和用户已登录环境。读取 [references/schema.md](references/schema.md) 和 [references/monitor-policy.md](references/monitor-policy.md)。

## 运行确定性比较

采集结果规范化为 JSON 后运行：

```bash
node scripts/monitor_competitors.cjs \
  --current competitor-current.json \
  --previous competitor-previous.json \
  --output competitor-events.json \
  --run-mode daily
```

`run-mode` 取 `daily`、`weekly` 或 `monthly`，分别比较 A、B、C 级。脚本不访问店铺，也不发送通知。

## 提醒条件

仅在下列情况生成 `AlertEvent`：

- 同行到手价绝对变化至少 `$0.50`，或相对变化至少 `3%`；
- 同行 Coupon 新增、取消或金额变化；
- FBA/FBM 状态变化；
- 卖家级 FBA 转仓风险变为高风险；
- 缺货或恢复；
- 配送时间变化至少 3 天；
- 新增 A 级完全同款。

价格同步只是“是否人工跟价”的复核建议。低置信度事件不生成同步价格。

## 输出

- 更新后的竞品映射和快照；
- A/B 竞品截图、判级原因、差异点和证据链接；
- 异常事件、旧值、新值、采集时间、置信度、建议动作；
- 数据缺口和需要二次 ZIP 复核的项目；
- 可供库存 AI 周报 `竞品变化` 工作表导入的 JSON。
- `SellerFulfillmentProfile`、幂等履约历史、FBA 转仓风险、订货前缩量复核建议和监控频率。

## 应用阶段

1. 选品初筛：高风险进入“假设对手转 FBA 后仍能否盈利”的压力测试，不直接淘汰。
2. 下单前 24–48 小时：刷新 Seller ID、其他 Offers、同父体变体和卖家 FBA 档案。
3. 已下单/在途：按风险频率监控，所有采购变更仍需人工确认。
4. 本店开售后：确认转 FBA 才路由调价和补货复算；清货仍由本店库存门禁独立决定。
