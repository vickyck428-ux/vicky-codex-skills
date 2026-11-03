---
name: walmart-out-of-stock-copy
description: Generate Walmart out-of-stock email and SMS copy with verified visible alternative links and polite cancellation wording, or a confirmation reply after a requested cancellation is completed. Copy only; do not send messages or change orders.
---

# Walmart 缺货退款文案

根据当前订单或用户提供的信息生成可复制的英文文案。商品、买家姓名、颜色和链接使用当前任务已确认的信息，不写死历史案例内容。从订单截图提取可确认的姓名和商品信息，不自行补全截断标题；商品可用已确认的简短名称，如 `clutch` 或 `bag`。没有姓名时使用 `Hi,`。

## 缺货通知

默认同时提供邮件版和短信版，各放入独立的 text 代码块，方便整段复制。用户只要一种格式或正在修改已选格式时，只提供该格式。

### 邮件版

```text
Hi [Buyer Name],

This is your Walmart seller. We’re sorry, but the [Product Name] you ordered is out of stock in [Ordered Color]. [Alternative Color] is available—would you like it instead? Here’s the photo:

[Verified Alternative URL]

If you’d prefer not to switch to [Alternative Color], could you please cancel the order through your Walmart account? This is the quickest way to receive a full refund.

Thank you for understanding!
Vicky
```

### 短信版

```text
Hi [Buyer Name], this is your Walmart seller. Sorry, the [Product Name] you ordered is out of stock in [Ordered Color]. Would you like [Alternative Color] instead? Photo: [Verified Alternative URL]

If you’d prefer not to switch to [Alternative Color], could you please cancel the order through your Walmart account? This is the quickest way to receive a full refund. Thank you for understanding!
```

- 邮件统一署名 `Vicky`；短信先介绍卖家身份，默认不加署名。
- 取消退款使用上述委婉请求，不写成命令，也不重复强调“主动后台取消”。默认完整文案包含退款选项；用户明确只要缺货通知或不提退款时省略。
- 无已确认替代款时，删除替代颜色、询问和链接句；退款句改为 `Could you please cancel the order through your Walmart account? This is the quickest way to receive a full refund.`
- 不知道订购颜色时只说商品缺货，不补猜颜色。

## 订单已取消后的回复

适用条件：客户已要求取消，且用户明确说明已取消或当前订单状态已确认取消。只收到取消请求不代表已经取消，不能提前使用完成式。

此场景只提供以下简短回复，不重复输出缺货邮件和短信，不再要求客户取消，不再推荐替代色。使用当前买家姓名，统一署名 `Vicky`，放在一个 text 代码块中：

```text
Hi [Buyer Name],

We’ve canceled your order as requested. We’re very sorry for the inconvenience and appreciate your understanding.

Vicky
```

已取消不等于退款已到账；不额外声称退款已完成或承诺到账时间。

## 图片与短链接

- 文案直接显示可复制的裸 URL，不用 Markdown 锚文本隐藏链接。邮件链接单独一行，短信放在 `Photo:` 后。
- 用户提供图片链接时，优先使用同一图片已验证可访问的短地址。Walmart 图片可尝试将 `/seo/商品描述_图片标识.jpeg` 改为 `/asr/图片标识.jpeg`，保留完整图片标识（UUID、哈希和扩展名），去除不必要的尺寸和背景参数。
- 改写后实际验证请求成功、响应为图片且仍对应同一商品及替代颜色；必要时查看图片核对，不凭格式宣称可用。当前任务已验证的同一地址可复用。
- 短地址无法验证或验证失败时，使用已确认可用的原地址并简短说明；不编造短网址，不擅自使用第三方短链服务。
- 按 SKU 或标题查商品时，在指定店铺核对对应子体，不把父体标题颜色当作子体颜色。没有用户指定图片链接时，优先使用已核实的对应替代色商品页面链接；只有图片与替代款关系已确认时才提供图片链接。使用商品页面链接时，相应调整 `Photo:` 等引导文字。

## 信息核对与边界

- 不编造颜色、库存恢复时间、退款到账时间、替代商品或订单信息，不把历史示例库存当作实时库存。
- 只生成文案，不发送邮件、短信或平台消息，不取消订单、不退款、不更换商品、不操作库存。询问替代款意愿不表示已经完成换款或获得换款授权。
