---
name: xinghe-main-video-promo-2-0
description: Generate a stable 15-second premium ecommerce main-image promotional film with cinematic camera movement and no overlay text. Use for 精品主图宣传片、电影感商品片或无叠字成片；do not use for people-led selling demos, UGC/voiceover conversion videos, or reference-video recreation.
---

# Xinghe Main-Image Video Promo 2.0

Generate one product-faithful premium ecommerce promotional video for domestic or cross-border ecommerce. Default to 15 seconds, 480p, one paid Seedance request, platform-specific ratio, advanced cinematic camera movement, premium music/sound design, platform-specific default voiceover language, and no overlay text. Domestic platforms default to Mandarin Chinese voiceover; cross-border platforms default to American English voiceover.

## Required Inputs

- Product name.
- At least one local JPG, JPEG, PNG, or WebP product image. Treat the first image as the strict product identity reference. Treat later product images, in order, as alternate view, detail view, then usage reference.

Optional inputs are platform, category, user-supplied selling points, audience, voiceover language, voiceover style, voiceover script, cinematic level, model presence, benchmark style notes, written storyboard file, storyboard image references, automatic storyboard image generation, and audio/voiceover disablement. Never invent missing product claims.

## Workflow

1. Inspect every product image conservatively and record only visible facts. Protect the first image's shape, color, packaging, logo position, label layout, printed text placement, material, parts, and included accessories.
2. Read `references/platform-presets.md` and choose the platform ratio, market, and default voiceover language. If no platform is supplied, use generic ecommerce and `1:1`.
3. Read `references/category-routes.md`. Select a route from the product name, visible evidence, and user facts. If confidence is low, use `other`; do not guess safety-sensitive use.
4. Prefer `--input-json` for long or multilingual inputs on Windows. Otherwise use CLI arguments directly.
5. Build a written director storyboard shot list with product-appropriate shot count. Use `--storyboard-only` when the user wants review before video submission.
6. When a storyboard control image is needed, use `--generate-storyboard-image` or generate it manually from `storyboard-image-prompt.txt` by following the storyboard image tool-selection rules below.
7. Run the unified video command. It validates inputs, creates prompt/manifest/checklist artifacts, submits exactly once unless `--storyboard-only`, `--dry-run`, or `needs_imagegen_fallback` is used, polls, and downloads the MP4.
8. Report paths, task id, model, platform, category, ratio, resolution, duration, voiceover language, audio status, and any warnings. Do not automatically retry. Let the user judge the video.

## Recommended JSON Input

```json
{
  "product_name": "Minimal rose-gold bezel solitaire necklace",
  "image_paths": ["C:/path/primary.png", "C:/path/detail.png"],
  "storyboard_image_paths": ["C:/path/director-storyboard.png"],
  "image_notes": "Visible product facts only.",
  "platform": "tmall",
  "category": "auto",
  "selling_points": "Only user-provided or visible product facts.",
  "audience": "Premium ecommerce shoppers.",
  "voiceover_language": "zh-CN",
  "voiceover_style": "premium Mandarin Chinese advertising narration, refined, restrained, trustworthy",
  "voiceover_script": "Optional user-provided narration intent.",
  "cinematic_level": "luxury",
  "model_presence": "auto",
  "storyboard_file": "C:/path/approved-storyboard.md",
  "generate_storyboard_image": true,
  "storyboard_image_output_name": "director-storyboard.png",
  "benchmark_style_notes": "Target scene/style notes from a benchmark ad.",
  "output_dir": "C:/path/out"
}
```

```powershell
python "<skill>/scripts/generate_product_video.py" `
  --input-json "C:/path/input.json"
```

## Unified Command

```powershell
python "<skill>/scripts/generate_product_video.py" `
  --product-name "<name>" `
  --image-path "<primary.jpg>" `
  --image-path "<optional-detail.jpg>" `
  --storyboard-image-path "<director-storyboard.png>" `
  --image-notes "<visible facts>" `
  --platform tmall `
  --category auto `
  --selling-points "<only user-provided facts>" `
  --audience "<optional audience>" `
  --voiceover-language zh-CN `
  --voiceover-style "premium Mandarin Chinese advertising narration, refined and restrained" `
  --voiceover-script "<optional narration intent>" `
  --cinematic-level luxury `
  --model-presence auto `
  --generate-storyboard-image `
  --benchmark-style-notes "<benchmark scene/style notes>" `
  --output-dir "<output-directory>"
```

Supported platforms: `generic`, `taobao`, `tmall`, `jd`, `pinduoduo`, `douyin`, `xiaohongshu`, `amazon`, `tiktok-shop`, `shopify`, `aliexpress`, `temu`.

Supported aliases include `淘宝`, `天猫`, `京东`, `拼多多`, `抖音`, `小红书`, `亚马逊`, `amz`, `tiktok`, `tiktokshop`, `tk`, `独立站`, `速卖通`, `ali`, `temu`, and `特穆`.

Supported categories: `auto`, `beauty-personal-care`, `apparel-accessories`, `food-beverage`, `home-kitchen`, `electronics-appliances`, `mother-baby-toys`, `pet-supplies`, `tools-auto`, `other`.

Supported voiceover languages: `zh-CN`, `en-US`, `ja-JP`, `ko-KR`, `fr-FR`, `de-DE`, `es-ES`, `auto`. Domestic platforms default to `zh-CN`; cross-border platforms default to `en-US`. Explicit `--voiceover-language` always wins.

Supported cinematic levels: `premium`, `clean`, `luxury`. Default is `premium`. Use `luxury` for slower, more polished product films and `clean` for conservative catalog-like videos.

Supported model presence: `auto`, `none`, `hands`, `lifestyle-model`. Default is `auto`. Use `lifestyle-model` only when the product benefits from stronger user experience and category-appropriate partial model presence.

Use `--storyboard-only` to create `seedance-storyboard.md`, prompt, manifest, and checklist without submitting a paid video task. Use `--storyboard-file` to turn an approved written storyboard into the final video prompt. Use `--storyboard-image-path` or JSON `storyboard_image_paths` to upload director storyboard control images together with the product image. Use `--generate-storyboard-image` to first try Xinghe storyboard image generation and fall back to the Agent `imagegen` workflow when Xinghe is unavailable. Use `--benchmark-style-notes` to pass scene/style analysis from a benchmark video.

Add `--no-voiceover` to keep premium music and sound design without spoken narration. Add `--no-generate-audio` for silent output. Use `--dry-run` to perform validation and create artifacts without making a paid API request.

## Storyboard Rules

- Use a director-designed storyboard instead of a fixed shot count. Choose the number of shots from product needs, usually 4-8 shots in 15 seconds.
- Typical structure is context entry, product establishment, first contact, sensory/detail proof, experience/use moment, and product memory/hero. Omit or merge shots when the product does not need them.
- Generate or approve a written director storyboard before video generation when the product needs logic, experience, model presence, or premium scene continuity. The final prompt must follow the storyboard exactly.
- The written storyboard must be a director shot list, not only a visual reference note. Every shot card must include time, director intent, scene style, main subject, composition, action beat, camera movement, lighting/premium cue, sound/voiceover timing, transition, product consistency lock, and do-not rules.
- When creating storyboard images, generate them from the written shot cards. The storyboard image is a director control sheet that helps the video model understand shot order, narrative logic, scene design, camera movement, and rhythm; it does not replace the written shot list.
- Every storyboard image must contain one visual panel per shot. Each panel must include the shot picture plus readable compact director labels for shot number, time range, camera movement, main action beat, and scene/style cue. Use camera arrows and professional notation where useful.
- Keep storyboard-image labels functional, not promotional. Allow only shot labels, timing, camera/action/style notes, and direction marks. Do not add slogans, selling captions, price text, badges, platform UI, random text, or extra brand names.
- When storyboard images are supplied, upload them with the product image and treat them as storyboard control images for narrative logic, scene style, shot order, composition, camera logic, rhythm, mood, and per-shot visual design. The first product image remains the only product identity source.

## Storyboard Image Tool Selection

Default to the Xinghe local image helper for storyboard control image generation. Use `--generate-storyboard-image` when the user wants the skill command to create a director storyboard image before video submission. The script writes `storyboard-image-prompt.txt`, tries Xinghe once, and adds the generated image as `storyboard_reference_1` when successful.

Xinghe helper path:

```text
$env:XINGHE_IMAGE_GENERATOR
%LOCALAPPDATA%\ApiCodexOneClick\tools\generate-image.ps1
```

Xinghe rules:

- If product images, storyboard references, competitor references, or benchmark references are available, pass all relevant reference images through `-ReferenceImage`; the helper routes the request to `https://xinghe.xin/v1/images/edits`.
- If the storyboard image is generated from text only, omit `-ReferenceImage`; the helper routes the request to `https://xinghe.xin/v1/images/generations`.
- The fallback model is the deployment-configured `gpt-image-2`.
- The API key is the key written by the deployment tool. Do not ask the user for it, print it, save it in artifacts, or repeat it in chat.
- Write the complete storyboard image prompt to a UTF-8 prompt file and call the helper with `-PromptFile`; do not pass long storyboard prompts directly as command-line text.
- Call the helper once per storyboard image and save the output into the current output directory.
- The final response must show the generated storyboard image with a local absolute path.

If Xinghe is unavailable or fails, do not submit the paid Seedance task. The script writes `storyboard_image_status: needs_imagegen_fallback`, `storyboard_image_prompt_path`, and `storyboard_image_target_path` into the manifest/result. Then the Agent must call the built-in `imagegen` tool using the same prompt and product reference image, save the image to the target path, and rerun the video command with `--storyboard-image-path`.

PowerShell Xinghe example:

```powershell
$helper = $env:XINGHE_IMAGE_GENERATOR
if (-not $helper) { $helper = Join-Path $env:LOCALAPPDATA 'ApiCodexOneClick\tools\generate-image.ps1' }
$promptFile = "<absolute prompt file path>"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $helper `
  -PromptFile $promptFile `
  -ReferenceImage "C:\path\to\product.png", "C:\path\to\reference.png" `
  -OutputDir "<absolute output directory>" `
  -Size "1536x1024" `
  -FileName "director-storyboard.png"
```

For text-only storyboard generation, remove the `-ReferenceImage ...` argument.

## Stability Rules

- Make the video feel premium through stable gimbal movement, slow push-ins, controlled orbit, macro rack focus, shallow depth of field, refined highlight sweep, and polished final lockup.
- Add believable user ritual, tactile interaction, ambient detail, and emotional memory so the video feels experienced rather than merely displayed.
- Use model presence only when helpful and category-safe. For beauty/skincare, `auto` may include clean hands, cheek/neck/shoulder side profile, or mirror-adjacent application. Do not show before/after changes or skin transformation.
- The first reference image overrides all other references if they conflict. Preserve the exact silhouette, proportions, colors, logo placement, label layout, printed text placement, packaging structure, controls, accessories, and included parts.
- Default audio must include platform-appropriate advertising voiceover plus premium instrumental ambience and refined product sound design. Domestic platforms default to Mandarin Chinese; cross-border platforms default to American English. Voiceover may speak only visible facts and user-supplied selling points.
- If using `--voiceover-script`, treat it as narration intent rather than a guaranteed frame-accurate TTS script. Keep it short and compliant.
- Keep one coherent physical location, minimal secondary props, and a held final hero frame so the result works across categories and ecommerce platforms. Human/model shots must never obscure or replace the product.
- Do not request captions, prices, badges, slogans, UI, watermarks, or added text. Existing package text may remain naturally on the product.
- Do not make medical, efficacy, safety, nutritional, compatibility, durability, ranking, warranty, certification, or performance claims unless explicitly supplied by the user. Treat `FDA approved`, `clinically proven`, `guaranteed`, `No.1`, `cure`, `治愈`, `根治`, `第一`, `最强`, `保证`, and `认证` as review warnings.
- Do not retry automatically. On drift, suggest a clearer primary image, explicit category, shorter action, fewer references, `--no-voiceover`, or `--no-generate-audio`.

## Ark Setup

Require `ARK_API_KEY` in the process or Windows user environment. Never ask the user to paste the key into chat.

```powershell
[Environment]::SetEnvironmentVariable("ARK_API_KEY", "your_key", "User")
```

The default model is `doubao-seedance-2-0-fast-260128`. Override with `ARK_SEEDANCE_MODEL` or `--model` only when the account exposes another compatible model.
