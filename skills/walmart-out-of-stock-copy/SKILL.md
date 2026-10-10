---
name: walmart-out-of-stock-copy
description: Generate tactful Walmart out-of-stock buyer messages in email and SMS formats, including an available alternative color and reference link when confirmed, with a full-refund cancellation option. Use for copy only; do not send messages or change orders.
---

# Walmart 缺货退款文案

根据当前订单或用户提供的信息，生成可直接复制的英文邮件版和短信版。商品、买家姓名、颜色和链接必须使用当前任务已确认的信息，不写死品牌、买家或订单号。

当用户提供 Walmart 订单截图并说明缺货时，直接提取可确认的买家姓名和商品名称，不重复确认；标题被截断时不自行补全。没有买家姓名时使用 `Hi,`。

## 短信最终模板

短信开头必须先介绍卖家身份：`Hi [Buyer Name], this is your Walmart seller.`，随后致歉并说明缺货。商品可用已确认的简短名称（如 `bag`），避免冗长标题。

用户提供或查询确认有替代颜色时，在同一条短信中说明该颜色可选、询问买家意愿，并附准确对应的商品或图片链接。用户要求退款或沿用完整模板时，最后提供通过 Walmart 账户取消并获取全额退款的选项。有替代款时使用 `If you prefer a full refund`，不同时要求买家必须取消。

```text
Hi [Buyer Name], this is your Walmart seller. We’re sorry, but the [Product Name] you ordered is out of stock in [Ordered Color]. [Alternative Color] is available—would you like it instead? View photos: [Alternative URL] If you prefer a full refund, please cancel through your Walmart account for the quickest refund. Thank you for understanding!
```

输出为一条自然连贯、可复制的短信，链接使用完整裸 URL，不使用 Markdown 链接语法；默认不加署名。没有已确认替代款时，删除替代颜色、询问及链接句；不知道订购颜色时只说商品缺货。

用户于 2026-10-09 确认的最终版本如下，仅为本次案例留档，不作为其他订单的事实来源：

```text
Hi Tracy, this is your Walmart seller. We’re sorry, but the bag you ordered is out of stock in Yellow. Khaki is available—would you like it instead? View photos: https://www.walmart.com/ip/18638814167 If you prefer a full refund, please cancel through your Walmart account for the quickest refund. Thank you for understanding!
```

## 邮件模板

邮件依次称呼买家、介绍 Walmart seller 身份、说明缺货并致歉、提供取消路径和最快全额退款说明，以 `Thank you for understanding!` 结束并统一署名 `Vicky`。

```text
Hi [Buyer Name],

This is the Walmart seller of the [Product Name] you ordered. We’re very sorry, but it’s currently out of stock.

Would you mind canceling the order through your Walmart account? This is the quickest way to receive your full refund.

Thank you for understanding!

Vicky
```

已确认有替代款时，在缺货说明后加入替代颜色、参考链接和意愿询问，并把取消说明改为买家不想选择替代款时的退款选项。

## 信息核对与边界

- 用户要求按 SKU 或标题查商品时，先在指定店铺核对对应子体；不能把父体标题中的颜色当作子体颜色。优先使用对应替代色的商品页面链接；只有已确认图片对应替代款时才提供图片链接。
- 不编造商品颜色、库存恢复时间、退款到账时间、替代商品或订单信息；不把历史示例的可售状态当作实时库存。
- 只输出文案，不发送邮件、短信或平台消息，不取消订单、不退款、不更换商品、不操作库存。询问替代款意愿不表示已经完成换款或获得换款授权。
- 用户只要求“跟他说缺货”时先提供缺货通知；只有用户要求退款或沿用完整模板时，才加入取消订单和退款说明。
- 默认同时提供邮件版和短信版；用户明确只要一种格式，或正在修改已选定格式时，只提供该格式。
