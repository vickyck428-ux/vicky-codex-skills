# Platform presets

Select one normalized platform value. Aliases are accepted by the scripts, but manifests always store the normalized value.

| Market | Platform | CLI value | Ratio | Default voiceover | Direction |
|---|---|---|---|---|---|
| General | Unspecified ecommerce | `generic` | `1:1` | `zh-CN` | centered product, safe crop, immediate clarity |
| Domestic | Taobao | `taobao` | `1:1` | `zh-CN` | polished product clarity for a Taobao main video |
| Domestic | Tmall | `tmall` | `1:1` | `zh-CN` | premium controlled brand presentation |
| Domestic | JD | `jd` | `1:1` | `zh-CN` | trustworthy feature clarity |
| Domestic | Pinduoduo | `pinduoduo` | `1:1` | `zh-CN` | immediate product recognition and simple visible action |
| Domestic | Douyin | `douyin` | `9:16` | `zh-CN` | first-frame motion and vertical safe-center composition |
| Domestic | Xiaohongshu | `xiaohongshu` | `9:16` | `zh-CN` | natural lifestyle texture and vertical safe-center composition |
| Cross-border | Amazon | `amazon` | `16:9` | `en-US` | trustworthy product proof, honest use context, inspection-friendly framing |
| Cross-border | TikTok Shop | `tiktok-shop` | `9:16` | `en-US` | mobile-first first-frame product recognition and safe-center vertical framing |
| Cross-border | Shopify | `shopify` | `1:1` | `en-US` | refined brand-owned product-page media |
| Cross-border | AliExpress | `aliexpress` | `1:1` | `en-US` | fast detail, accessory, scale, and practical-use clarity |
| Cross-border | Temu | `temu` | `1:1` | `en-US` | immediate product recognition and simple value perception |

Supported aliases:

- Domestic: `淘宝`, `天猫`, `京东`, `拼多多`, `pdd`, `抖音`, `小红书`, `red`
- Cross-border: `亚马逊`, `amz`, `tiktok`, `tiktokshop`, `tiktok shop`, `tk`, `独立站`, `速卖通`, `ali`, `特穆`

Never create platform UI, badges, prices, captions, discount stickers, watermarks, certification marks, or promotional text inside the generated video or storyboard image.
