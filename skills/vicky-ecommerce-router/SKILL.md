---
name: vicky-ecommerce-router
description: Route ambiguous Amazon selection, Xinghe image/video, and Walmart WFS requests to exactly one primary Skill. Use when an ecommerce request could match multiple local Skills or when the user asks which workflow should trigger first; do not override an explicitly named $skill.
---

# Vicky 电商总分流

只判断任务当前所处的阶段，并转交一个主 Skill。不要在本 Skill 内重复执行业务流程，也不要同时加载多个总控。

## 最高优先级

1. 用户显式写出 `$skill-name` 时，直接尊重该选择。
2. 没有显式选择时，运行 `python3 scripts/route_request.py --text "<用户请求>"`。
3. 结果为 `ROUTED` 时只调用 `primary_skill`。
4. 结果为 `NEEDS_CLARIFICATION` 时只问返回的一个问题；根据回答在给出的两个 Skill 中选择一个。
5. 若没有命中固定路由，不猜测；按普通 Skill 发现机制处理。

## 固定边界

- 1688 全链路、恢复、迁移或状态核对优先于普通 Amazon 选品。
- 年度目标、每日监督或方法轮换优先于单次女包选品。
- Sorftime 或“十个跨平台方向”只进入 `$xinghe-crossborder-product-selection`。
- 图片以用户交付物为准：参考图二创、完整 Amazon 套系、场景图、模特图、国内电商详情、跨境详情模块、单张营销创意、普通商品编辑互斥。
- 视频以输入和成片目标为准：参考视频复刻、带货演示、15 秒精品宣传片互斥。
- WFS 按售前候选、共享池、已出单动作、T1/采购/到仓/装箱/Shipment ID、Listing 工作簿依次识别。

完整路由说明见 [routes.md](references/routes.md)。修改规则后运行：

```bash
python3 scripts/test_router.py
```
