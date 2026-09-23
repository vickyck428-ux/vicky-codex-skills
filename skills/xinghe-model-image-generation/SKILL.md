---
name: xinghe-model-image-generation
description: Generate realistic white-background ecommerce model images from uploaded product photos with a unified model identity. Use when users ask for 模特图, 真人模特图, 产品上身图, 手持图, 试穿图, 佩戴图, 换模特, 模特展示, or pure-white-background product model photography. Default to direct image generation unless the user explicitly asks for prompts, SOP, or planning only.
---

# 星河模特图生成4.0

根据用户上传的产品图，直接生成适配产品风格的真人电商模特图。默认一次生成 `8` 张不同角度、不同姿态、不同构图和不同产品展示方式的方图；默认尺寸为 `1:1`；默认背景为纯白影棚背景，不做生活场景。默认先生成 `1` 张模特全身基准图，再用这张基准图统一模特形象生成其余角度。

## Global Priority

When rules conflict, follow this order:

1. User's explicit request: quantity, size, platform, background color, model gender/age range, body type, ethnicity/nationality, pose, style, and prompt-only versus direct generation.
2. Safety and compliance: use adult models only; do not sexualize minors; do not invent medical effects, certifications, test data, sales, reviews, discounts, brand authorization, or unsupported product claims.
3. Product truth and product identity: preserve visible product silhouette, color, material, texture, pattern/logo/nameplate placement, structure, proportions, and wearing/holding/contact logic.
4. Size and body-scale truth: use provided product dimensions, size chart, model height/weight, or fit notes when available; when absent, use category-normal adult body scale only and do not invent exact measurements.
5. Default model ethnicity/nationality: use an adult Chinese model by default unless the user explicitly requests another ethnicity, nationality, region, or multiple models.
6. Positive facial expression and mood: default to a sunny, positive, approachable, confident, naturally warm expression unless the user explicitly requests another mood. Avoid cold, gloomy, tired, angry, blank, sad, overly stern, or overly dramatic expressions.
7. Model identity consistency: after the first full-body model reference image is generated, preserve the same adult Chinese model identity, face/body type, skin tone, hairstyle, styling logic, outfit logic, facial expression direction, and model proportions across the remaining images unless the user explicitly requests multiple models.
8. Model realism and commercial quality: natural living-person feel, real skin texture, believable hands/body/face, natural positive expression, realistic product contact, and no over-smoothed plastic skin.
9. Pure-white-background rule: use a consistent seamless pure white studio background by default unless the user explicitly requests another background.
10. Category-specific composition: adapt the 8-image structure to the product category. Apparel, shoes, bags, handheld goods, beauty, jewelry, and small electronics should not share one rigid pose list.
11. Variation across the set: vary angle, crop, pose, product interaction, lighting, and composition without changing product identity, model identity, Chinese adult model direction, positive facial mood, or plausible product-to-body scale.

## Default Behavior

- If the user uploads product photos and asks for model images, generate directly by default. Do not stop at a prompt pack and do not ask whether to proceed.
- If the user explicitly asks for prompts, SOP, workflow, or planning only, do not call image generation; provide structured prompts or instructions.
- Default count: `8` images total: `1` full-body model reference image first, then `7` additional angle/detail images using both the product image and the full-body model reference.
- Default size: square `1:1`; use `1024x1024` with the helper when available.
- Default model: adult Chinese model with a sunny, positive, approachable, naturally warm expression. User-specified ethnicity, nationality, region, gender, age range, or mood overrides this default.
- Default background: seamless pure white studio background with a minimal realistic contact shadow. Do not use light gray, warm off-white, beige, pink, gradient color, or brand-color backgrounds unless the user explicitly requests them.
- Do not create lifestyle scenes such as bedroom, street, cafe, office, bathroom, outdoor, living room, kitchen, gym, or travel scene unless the user explicitly asks for those.
- Do not add promotional text, price, badges, fake labels, watermarks, platform UI, or decorative typography unless the user explicitly asks.

## Core Workflow

1. Identify product category and display mode from the uploaded image and user request.
2. Extract one shared `Product Identity Lock`: silhouette, proportions, color/material, texture, print/logo/nameplate placement, structural parts, accessories, and how the product should be worn, held, carried, placed, or touched.
3. Read [references/size-scale-policy.md](references/size-scale-policy.md) and create a `Size & Scale Lock` before prompt writing.
4. Read [references/category-composition-matrix.md](references/category-composition-matrix.md) and [references/model-image-planning.md](references/model-image-planning.md), then create a category-adapted two-stage 8-image model-photo plan unless the user specified another count.
5. Read [references/prompt-contract.md](references/prompt-contract.md) and write the first prompt as the full-body model reference image. Every prompt must start with `square 1:1 ecommerce model product image`.
6. Read [references/generation-tools.md](references/generation-tools.md) and generate the first full-body model reference image directly through the deployment helper first. Use built-in `image_gen` only as the final fallback.
7. After the first image is saved, create a short text `Model Identity Lock` from the result: adult Chinese model direction, age range, face/hair impression, skin tone, body type, outfit logic, expression intensity, and lighting family. Use both the saved image reference and this text lock for the remaining images.
8. Use both the original product image and the saved full-body model reference image as references for the remaining images. The remaining prompts must explicitly preserve the same model identity, outfit logic, body type, skin tone, hairstyle, pure white background, expression intensity, and `Size & Scale Lock`.
9. Save every successful output to a local path, verify file existence where possible, and display the generated images with Markdown image syntax.
10. Use [references/quality-control.md](references/quality-control.md) only as an optional manual review checklist. Do not automatically regenerate unless the user explicitly asks to redo, regenerate, fix, or replace specific images.

## Product Identity Lock

Before generation, create and reuse the same product lock in every prompt:

- Overall silhouette, proportions, open/closed state, and visible volume relationships.
- Primary and secondary colors, color-area ratio, material appearance, texture, reflectivity, transparency, textile grain, leather grain, knit texture, plastic, metal, paper, liquid, cream, or other visible finish.
- Pattern, logo, printed text, label, nameplate, embroidery, decoration, and relative placement. Do not invent unreadable small text.
- For visible brand marks, labels, buttons, screens, or small text: preserve the approximate position, scale, and visual presence. Do not invent new claims, certifications, parameters, volume, model numbers, or random readable text. If exact logo/text clarity is required, prefer close-up roles where the mark occupies enough pixels.
- Structural parts such as straps, zippers, seams, buttons, buckles, handles, caps, lids, ports, bases, soles, fasteners, closures, tags, or packaging.
- Product scale and physical relationship to the model's body, hands, clothing, face, hair, wrist, feet, bag, or props.
- Contact, gravity, occlusion, perspective, shadow, fabric drape, hand grip, fit, and wearing/carrying logic.

The reference image locks product identity only. It does not lock the original background, camera angle, crop, lighting, placement, or white-background product-photo composition.

## Size & Scale Lock

If the user provides product dimensions, size chart, garment size, model height/weight, body measurements, shoe size, bag dimensions, jewelry dimensions, or fit notes, use those details to lock product-to-body scale. If no scale data is provided, do not invent exact numbers. Use category-normal adult proportions and mark scale as a reasonable visual inference.

Default category scale:

- Apparel: preserve the visible garment type and length. Maxi dresses stay maxi/near-floor, mini dresses stay mini, cropped tops stay cropped, and oversized/fitted items keep their visible fit logic.
- Shoes: use normal adult foot scale and preserve sole thickness, toe shape, upper height, and visual bulk.
- Bags: use normal adult hand/shoulder/body scale and do not turn a normal bag into a mini bag or travel bag unless provided.
- Jewelry and watches: use normal adult body-part scale and do not enlarge them into props.
- Handheld goods, beauty, electronics, and home goods: use believable hand/body scale, without adding exact capacity, dimensions, or package quantity.

When scale is inferred, final notes should briefly say that size/body scale is visually inferred and should be confirmed against the size chart or real dimensions when precision matters.

## Model Identity Lock

After the first full-body model reference image is generated, reuse it as a visual reference for every remaining image. Preserve:

- the same adult Chinese model identity and facial structure when the face appears;
- the same sunny, positive, approachable facial mood, with only natural micro-variation in smile intensity;
- the same body type, skin tone, limb proportions, and athletic/styling character;
- the same hairstyle, hair color, makeup level, and outfit logic;
- the same footwear wearing relationship and product scale on the body;
- the same clean pure white studio background and lighting family.

Only change camera distance, crop, angle, pose, product orientation, and close-up focus according to each image role.

Also maintain a text version of the lock for prompts:

- adult Chinese model direction and approximate adult age range;
- face impression, hairstyle, hair color, skin tone, makeup level, and body type;
- outfit color family and styling logic;
- expression level: default soft smile or standard friendly smile, not exaggerated laughter;
- pure white lighting family and product-to-body scale.

## Model Realism Lock

Every prompt should require:

- Adult real human model, natural sunny and positive facial expression, approachable warmth, believable posture, natural hands, correct fingers, realistic joints, and anatomically plausible body proportions.
- Natural skin pores, fine skin texture, subtle imperfections, realistic makeup, real hair texture, and no wax/plastic/AI-smoothed skin.
- Commercial studio photography quality, sharp focus, realistic shadows, accurate perspective, clean edges, and product clearly visible.
- Styling that fits the product category: apparel uses believable fit and drape; jewelry/accessories use body-scale close-ups and full styling logic; bags use carrying/shoulder/hand poses; beauty and small goods use natural hand/face interaction; home or small electronics use hand-held model presentation on a pure background.

## Expression Scale

Use a natural commercial expression by default:

- Default: soft smile or standard friendly smile, sunny, positive, approachable, and energetic.
- Optional when requested: very subtle smile, broader cheerful smile, or more refined calm smile.
- Avoid by default: exaggerated laugh, fake smile, cold luxury stare, blank face, tired face, angry face, sad face, stern face, or theatrical expression.

## Output Format

For direct generation tasks, keep the final response concise and include:

- Generated image count.
- Aspect ratio, pure white background style, and whether the first generated image was used as the model identity reference.
- Local file paths for every generated image.
- Markdown image previews using absolute local paths.
- Optional review items or information needing confirmation, only when relevant.

If neither the deployment helper nor built-in image generation can save files, do not claim completion. Explain the failure and provide the prompt pack as a fallback.
