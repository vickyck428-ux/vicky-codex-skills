# 多平台带货策略

按用户指定平台选择策略；未指定时默认 `douyin`。平台策略只影响表达方式、比例、口播、文字层和 CTA，不改变商品事实。

## 平台索引

| platform | 平台 | 默认比例 | 口播风格 | 文字层 | CTA |
| --- | --- | --- | --- | --- | --- |
| `douyin` | 抖音 | `9:16` | 快节奏、强钩子、痛点直给 | 少量卖点贴纸 | 立即下单/点小黄车 |
| `xiaohongshu` | 小红书 | `9:16` | 种草分享、真实体验、生活方式 | 轻贴纸、关键词 | 收藏/同款可入 |
| `shipinhao` | 视频号 | `9:16` | 稳重清楚、适合泛人群 | 少量大字重点 | 需要的可以看看 |
| `taobao` | 淘宝 | `9:16` | 货架转化、参数与场景并重 | 卖点标签/规格提示 | 进店/领券/下单 |
| `pinduoduo` | 拼多多 | `9:16` | 直接、实惠、使用价值 | 高对比卖点贴纸 | 拼/囤/入手 |
| `tiktok_shop` | TikTok Shop | `9:16` | English or bilingual, demo-first | Short punch labels | Shop now |
| `amazon` | Amazon | `1:1` | proof-first, benefit-led | Minimal feature callouts | Check details |
| `shopify` | Shopify | `9:16` | brand tone, lifestyle demo | Clean premium callouts | Shop now |

## 默认选择

- 中文请求且未指定平台：用 `douyin`。
- 英文或跨境请求且未指定平台：用 `tiktok_shop`。
- Amazon A+、商品页、PDP、主图视频：用 `amazon`。

## 文字层原则

- 有口播时默认 `sparse_stickers`，只保留少量卖点贴纸、场景标签、CTA 锁屏，不做逐句字幕。
- 用户明确要字幕时才用 `caption_driven`。
- 平台文字不稳定时优先把卖点放入口播，屏幕文字只描述为贴纸/标签意图。

## 合规原则

- 不写未提供证据的价格、折扣、排名、认证、医疗、安全、抗菌、永久、100% 等硬声明。
- 跨境平台避免夸大功效和竞品比较，表达为 visible benefit 或 user-supplied fact。
- 不生成平台 UI、水印、真实店铺名、未经提供的品牌 Logo。
