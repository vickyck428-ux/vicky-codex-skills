---
name: walmart-out-of-stock-copy
description: Generate tactful Walmart out-of-stock buyer messages in email and SMS formats, with a full-refund cancellation instruction. Use when the user asks for copy only; do not send messages or change orders.
---

# Walmart 缺货退款文案

根据用户提供的买家姓名和商品名称，生成可直接复制的英文邮件版和短信版。商品名称必须使用当前订单或用户提供的信息，不要写死任何品牌、商品、买家或订单号。

当用户提供类似的 Walmart 订单截图并说明“没货了”或“缺货”时，直接从截图提取买家姓名和商品名称，按本技能输出邮件版和短信版，不需要再次确认。若截图中的商品名称被截断，只使用能够确认的商品名称，不自行补全未显示的内容。

## 固定表达结构

邮件版按以下顺序组织：

1. 称呼买家。
2. 说明自己是该商品的 Walmart seller。
3. 礼貌说明商品目前缺货并致歉。
4. 请求买家通过 Walmart 账户取消订单。
5. 说明这是获得全额退款最快的方式。
6. 使用固定句子 `Thank you for understanding!`，并在邮件末尾统一署名 `Vicky`，不根据站点更换署名。

推荐模板：

```text
Hi [Buyer Name],

This is the Walmart seller of the [Product Name] you ordered. We’re very sorry, but it’s currently out of stock.

Would you mind canceling the order through your Walmart account? This is the quickest way to receive your full refund.

Thank you for understanding!

Vicky
```

短信版保留缺货、取消路径和最快全额退款三个重点，删减解释，保持自然礼貌；短信版不添加署名，除非用户另有要求。

## 边界

- 只输出文案；除非用户另行明确授权并且具备对应工具，不发送邮件、短信或平台消息，也不取消订单、不操作退款。
- 不编造商品颜色、库存恢复时间、退款到账时间、替代商品或订单信息。
- 用户只要求“跟他说缺货”时，先提供缺货通知；只有用户要求退款或沿用完整模板时，才加入取消订单和退款说明。
- 默认同时提供邮件版和短信版；如果用户明确只要一种格式，则只提供该格式。
