---
name: xinghe-ecommerce-selling-video-2-0
description: Generate conversion-focused ecommerce selling videos with people, hands, voiceover, demonstrations, UGC, or real-use scenes. Use for 带货视频、真人/手模/口播/演示或转化型内容；do not use for reference-video recreation or a premium 15-second cinematic no-overlay main-image promo.
---

# 星河电商带货视频2.0

直接生成以转化为目的的电商带货短视频。默认全品类、多平台、真人/手模/真实场景带货、中文口播、15 秒、9:16、480p。这个技能不是提示词工具；信息足够时要产出 brief、分镜、视觉分镜图，并提交 Seedance 生成成片。

## Scope

- 唯一核心模式：`product_selling_video`
- 输入：产品图、产品名、卖点、目标平台、可选目标人群/风格
- 输出：本地 `.mp4` 成片、任务 ID、brief、文字分镜、视觉分镜图、prompt、manifest
- 不做参考视频复刻。用户给参考视频时，只能当作风格灵感或口头要求；不要下载、抽帧、ASR、OCR、blueprint、逐镜头还原或复刻节奏迁移。需要复刻时改用 `xinghe-viral-video-remix-2-0`（显示名：星河爆款短视频二创2.0）。

## Defaults

- 模型：`doubao-seedance-2-0-fast-260128`
- 清晰度：`480p`
- 比例：中文电商默认 `9:16`；Amazon 默认 `1:1`
- 时长：`15`
- 音频：默认开启 Seedance 原生音频与口播
- 人物/场景：按类目选择真人主播、模特、手模或画外音配真实使用场景；不要纯商品静物旋转
- 字幕：默认不要逐句字幕；有口播时用少量贴纸/卖点标签，避免字幕和贴纸重复
- 分镜图：正常付费生成前强制生成并提交 `storyboard_sheet.png`
- 输出：下载到产品素材目录或用户指定目录

## References

按需读取，不要一次性加载全部：

- 平台策略：`references/platform-strategy.md`
- brief 契约：`references/selling-brief-contract.md`
- 分镜图契约：`references/storyboard-contract.md`
- 分镜图生图 helper：`references/storyboard_image_generation.md`
- 服装鞋包：`references/category-fashion.md`
- 美妆个护：`references/category-beauty.md`
- 食品饮料：`references/category-food.md`
- 家居百货：`references/category-home.md`
- 3C 数码家电：`references/category-digital.md`
- 珠宝配饰：`references/category-accessory.md`
- 母婴宠物：`references/category-family.md`
- 运动户外：`references/category-sports.md`
- 通用兜底：`references/category-general.md`
- 质检清单：`references/quality-check.md`

## Workflow

1. 识别平台：抖音、小红书、视频号、淘宝、拼多多、TikTok Shop、Amazon、Shopify；未指定时中文默认抖音，英文/跨境默认 TikTok Shop。
2. 识别类目：服装、美妆、食品、家居、四件套/床品、收纳、清洁、3C、珠宝配饰、母婴宠物、运动户外、通用。
3. 读取对应平台策略、brief 契约、分镜契约和一个类目模板。
4. 从产品图和用户给定信息提取安全卖点。不要编造功效、认证、排名、价格、折扣、材质、保修、专利等硬声明。
5. 运行 `scripts/build_selling_brief.py` 生成 `selling_brief.json`。
6. brief 必须包含 `presenter_mode`、`result_showcase_type`、`product_identity_locks`、`physical_scene_constraints`、`must_show_result_frame`。
7. 运行 `scripts/build_storyboard.py` 生成 `storyboard.json` 和 `storyboard.md`。
8. 每个 shot 必须包含商品身份锁、物理接触锁、空间锚点锁和单动作规则。
9. 运行 `scripts/build_storyboard_image_prompts.py` 生成 `storyboard_sheet_prompt.txt`。
10. 按 `references/storyboard_image_generation.md` 的生图优先级生成单张 `storyboard_sheet.png`：先用 `scripts/generate_storyboard_image.py`，脚本优先调用本地 helper `%LOCALAPPDATA%\ApiCodexOneClick\tools\generate-image.ps1`；helper 不可用或失败时走 `https://xinghe.xin/v1/images/edits` / `generations`，模型 `gpt-image-2`；只有脚本/helper/API 都失败时，才用内置 `image_gen` 兜底。如果用户只要求 dry-run，可以停在 prompt/manifest。
11. 运行 `scripts/generate_selling_video.py`，同时传入产品图和 `storyboard_sheet.png`。没有分镜图时不要付费生成，除非用户明确要求诊断跳过。
12. 返回 MP4 路径、task id、模型、平台、比例、时长、brief、storyboard、storyboard sheet、prompt、manifest 和 warnings。

## Commands

从环境或当前 Skill 目录解析运行路径：

```bash
PYTHON_BIN="${CODEX_BUNDLED_PYTHON:-python3}"
SKILL_ROOT="${CODEX_HOME:-$HOME/.codex}/skills/xinghe-ecommerce-selling-video-2-0"
```

生成带货 brief：

注意：只有用户明确给出卖点时才添加 `--selling-point`。没有用户卖点时，不要照抄任何示例词；只根据产品图可见事实写保守描述。

```bash
"$PYTHON_BIN" "$SKILL_ROOT/scripts/build_selling_brief.py" \
  --product-name "产品名" \
  --platform douyin \
  --category beauty \
  --target-audience "上班族" \
  --output-dir "/path/to/out"
```

生成文字分镜：

```bash
"$PYTHON_BIN" "$SKILL_ROOT/scripts/build_storyboard.py" \
  --brief-json "/path/to/out/selling_brief.json" \
  --output-dir "/path/to/out/storyboard"
```

生成视觉分镜图提示词：

```bash
"$PYTHON_BIN" "$SKILL_ROOT/scripts/build_storyboard_image_prompts.py" \
  --storyboard-json "/path/to/out/storyboard/storyboard.json" \
  --output-dir "/path/to/out/storyboard"
```

按 helper 优先级生成视觉分镜图：

```bash
"$PYTHON_BIN" "$SKILL_ROOT/scripts/generate_storyboard_image.py" \
  --storyboard-json "/path/to/out/storyboard/storyboard.json" \
  --reference-image "/path/to/product.png" \
  --output-dir "/path/to/out/storyboard"
```

生图优先级：`generate_storyboard_image.py` → 本地 `generate-image.ps1` helper → `xinghe.xin/v1/images/edits|generations` + `gpt-image-2` → 内置 `image_gen` 最后兜底。

dry-run 验证生成 payload，不提交付费任务：

```bash
"$PYTHON_BIN" "$SKILL_ROOT/scripts/generate_selling_video.py" \
  --brief-json "/path/to/out/selling_brief.json" \
  --storyboard-json "/path/to/out/storyboard/storyboard.json" \
  --image-path "/path/to/product.png" \
  --storyboard-image "/path/to/out/storyboard/storyboard_sheet.png" \
  --output-dir "/path/to/out" \
  --dry-run
```

正常生成：

```bash
"$PYTHON_BIN" "$SKILL_ROOT/scripts/generate_selling_video.py" \
  --brief-json "/path/to/out/selling_brief.json" \
  --storyboard-json "/path/to/out/storyboard/storyboard.json" \
  --image-path "/path/to/product.png" \
  --storyboard-image "/path/to/out/storyboard/storyboard_sheet.png" \
  --output-dir "/path/to/out" \
  --output-name "产品名_15s_480p_带口播.mp4"
```

## API Key

本技能使用火山方舟 API Key，环境变量名为 `ARK_API_KEY`。不要让用户把密钥粘贴到聊天里。

临时配置当前 zsh 会话：

```bash
export ARK_API_KEY="你的火山方舟密钥"
```

需要长期使用时，在本机安全地将变量写入用户的 zsh 配置；不要把密钥写进 Skill 文件或聊天记录。配置后重启 Codex，使新进程读取环境变量。

```bash
source ~/.zshrc
```

## Prompt Rules

- 首秒必须出现商品或明确痛点。
- 默认是真人带货、手模演示或画外音配真实使用场景；不要只做静物旋转。
- 每条视频至少 3 个镜头必须有人物动作、真实使用过程或完成结果画面。
- 每个镜头只做一个主要动作。
- 每个镜头都要包含商品一致性约束、物理接触约束和空间锚点约束。
- 产品图是身份参考；分镜图是导演参考。
- 产品照片是唯一商品身份来源；分镜图只指导镜头、动作、空间和结果画面，不得重新设计商品。
- 生成视觉分镜图时，优先使用 `scripts/generate_storyboard_image.py` 和本地 helper/API 路径；内置 `image_gen` 只作为最后兜底，不作为默认首选。
- 服装必须上身展示；四件套/床品必须铺在真实床上；收纳/清洁必须有前后对比；食品必须有入口/热气/切面/拉丝等感官结果；美妆必须有上手/上脸/质地或使用后状态。
- 口播必须短、自然、带转化意图，不堆参数。
- 不要把命令示例、占位符、模板说明、类目提示词当作真实卖点、口播或屏幕文字。
- 有口播时不要逐句字幕；只保留少量贴纸、卖点标签或 CTA。
- 不生成平台 UI、水印、未提供的品牌 Logo、复制文案或乱码文字。
- 不写未证实的医疗、安全、抗菌、认证、排名、价格、折扣、专利、保修和绝对化承诺。

## Quality Gate

付费生成前确认：

- `selling_brief.json` 存在且 `mode = product_selling_video`
- `storyboard.json` 和 `storyboard.md` 存在
- `storyboard_sheet.png` 存在
- `storyboard_sheet.png` 优先由 `scripts/generate_storyboard_image.py`、本地 helper 或 HTTP API 生成；只有这些路径失败时才使用内置 `image_gen` 兜底
- 产品图和分镜图都会作为 `reference_image` 提交
- shot 总时长等于 brief 时长
- brief 包含人物/场景策略、结果展示类型、商品身份锁、物理空间锁和必拍结果画面
- 平台策略、类目模板、口播、文字层和 CTA 已匹配
- 每条视频至少 3 个镜头不是纯静物：要有人物动作、真实使用过程或完成结果场景
- 每个镜头只有一个主要动作，避免穿帮
- 没有参考视频复刻流程
- 没有 unsupported claims 或 duplicate subtitle layer

## Troubleshooting

- 像图片动效：强化动作、拿取、旋转、使用过程和场景切换。
- 商品跑款：减少参考图数量，强化 `product_identity_constraints`，使用一张主产品图加一张细节图。
- 空间穿帮：减少单镜头动作，强化床头/桌面/地面/身体比例等空间锚点。
- 漂浮/穿模：明确手、身体、床、桌面、食材、家具与产品的真实接触关系。
- 带货感弱：加强首秒痛点、动作演示、场景证明和 CTA。
- 文字乱码：降低硬性文字要求，把卖点放入口播，屏幕只保留短贴纸意图。
- 人脸问题：使用匿名成人模特、手模或脖子以下身体展示，不要求同一张脸。
