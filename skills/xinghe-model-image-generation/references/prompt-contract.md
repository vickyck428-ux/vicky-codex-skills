# Prompt Contract

Each final image must be generated independently. Do not place multiple model photos on one canvas unless the user explicitly asks for a collage, and even then the full collage must be produced directly by the image-generation tool, not assembled locally.

## Required Prompt Blocks

Every image prompt must include:

1. First line: `square 1:1 ecommerce model product image`.
2. Reference instruction: use uploaded product images only to lock product identity; do not copy source background, camera angle, crop, lighting, or white-background product-photo composition.
3. `Product Identity Lock`: silhouette, proportions, colors, material, texture, logo/pattern/nameplate placement, structural-part relationships, and do-not-change list.
4. `Size & Scale Lock`: use provided dimensions/size chart/model measurements if available; otherwise use category-normal adult visual scale and do not invent exact sizes, heights, lengths, capacities, or measurements.
5. `Model Ethnicity/Nationality Lock`: adult Chinese model by default unless the user explicitly requests another ethnicity, nationality, region, or multiple models; preserve the same Chinese adult model identity across the full set.
6. `Text/Logo Lock`: preserve visible brand mark, label, button, screen, or small-text position and visual presence without inventing new readable claims, certifications, specs, capacity, model number, or random text.
7. `Expression & Mood Lock`: sunny, positive, approachable, confident, naturally warm facial expression; default soft smile or standard friendly smile; bright but realistic eyes; no cold, gloomy, tired, angry, blank, sad, overly stern, exaggerated laughter, fake smile, or theatrical expression unless requested by the user.
8. `Model Realism Lock`: adult real human model, natural living-person feel, visible skin pores, natural hands, realistic body anatomy, believable positive expression, no plastic skin, no over-smoothing.
9. `Pure White Background Lock`: seamless pure white studio background, consistent white balance, minimal realistic contact shadow, no colored background, no lifestyle scene, no room/outdoor/street/cafe/office/kitchen/bathroom setting.
10. `Current Image Role`: use the category-adapted role from `category-composition-matrix.md` or the user's requested role.
11. `Model Direction`: Chinese adult model by default, gender presentation, age range as adult, styling, hair/makeup, sunny positive expression, body pose, and mood that fits the product.
12. `Product Display Method`: worn, carried, held, applied, adjusted, presented, opened, button/port/lid shown, body-contact detail, or scale proof according to category.
13. `Composition Difference`: explain how this image differs from the previous image in crop, angle, pose, lighting, product orientation, product interaction, or detail emphasis.
14. `Quality Lock`: premium commercial studio photography, sharp focus, realistic skin texture, clean edges, accurate perspective, realistic shadows, crisp product detail.
15. Negative constraints: no child/teen model, no sexualized minor, no watermark, no promotional text, no price, no fake certification, no fake reviews, no fake sales, no unsupported claims, no extra product accessories, no product redesign, no distorted hands, no impossible body pose, no invented product measurements, no cold/gloomy/blank/sad/angry/tired expression, no ethnicity/nationality switch after the model reference is created.

## Two-Stage Model Identity Rule

For default direct generation, do not generate all 8 images from the product image alone.

Stage 1:

- Generate image 1 first as the `Model Identity Reference`.
- The first prompt must create a full-body adult model image on a seamless pure white studio background.
- The first prompt must define a product-appropriate adult Chinese model, outfit logic, hairstyle, body type, sunny positive expression, and lighting family.
- After image 1 is generated, write a compact text `Model Identity Lock` from the image and reuse it in every later prompt along with the image reference.

Stage 2:

- For images 2 through 8, pass both the original product image and the saved `Model Identity Reference` as references when the active generation tool supports multiple reference images.
- If the active tool can include only one generated reference image, prioritize the saved `Model Identity Reference` and write the product identity lock in full detail.
- Every stage-2 prompt must say: `Keep the same adult Chinese model identity from the full-body model reference: same face when visible, same body type, skin tone, hairstyle, outfit logic, sunny positive facial mood, and white studio lighting.`
- Stage-2 prompts may change pose, crop, camera distance, angle, and product display method, but must not change the model into a different person.

The text `Model Identity Lock` should include: adult Chinese model, approximate adult age range, face impression, hairstyle/hair color, skin tone, makeup level, body type, outfit color family, default expression intensity, and pure white lighting family.

## Size & Scale Prompt Rule

Every prompt must include the same `Size & Scale Lock`. If exact scale information is absent, use wording like:

```text
Size & Scale Lock: no exact size chart, dimensions, model height, or body measurements were provided. Use category-normal adult proportions only. Treat product-to-body scale as a reasonable visual inference. Do not invent numerical measurements, size labels, height, capacity, package quantity, or exact garment length. Preserve the visible product type and fit logic from the reference image.
```

For apparel, add the visible garment type and expected length/fitting relationship. For example, a full-length dress should stay full-length or near-floor on an adult model, with the waist, bodice, straps, sleeves, hem, and garment volume positioned plausibly on the body.

## Product Reference Rule

When product images are provided, prefer passing them as reference images through the deployment helper. If reference input is unavailable, write the product identity details explicitly into every prompt.

If the reference image is a white-background product photo, every prompt must include:

```text
Use the reference image only to lock product identity. Do not replicate the white-background product photo as a white-background single-product image. Create a real adult model ecommerce studio photo on a seamless pure white background, with a new camera angle, natural model pose, and believable product wearing/holding/contact.
```

## Text, Logo, and Label Rule

Preserve the location and visual presence of visible logos, labels, buttons, screen areas, and small text, but do not invent new readable claims or specs. For small text that cannot be reliably reproduced, prefer a realistic label-like mark or partially readable detail rather than fabricated copy.

If the user says the logo or label must be clear, assign at least one close-up role where the mark is large enough to inspect. Do not claim exact text accuracy unless it is visibly correct in the generated output.

## No On-Image Copy By Default

Default model images should contain no text. Add on-image text only when the user explicitly requests it. If text is requested, use only user-provided or visible facts and keep it short.

## Prompt Pack Output

When the user asks for prompts only, provide:

- Shared product identity lock.
- Shared size and scale lock.
- Shared model ethnicity/nationality lock.
- Shared text/logo lock.
- Shared model realism lock.
- Shared expression and mood lock.
- Shared pure white background lock.
- Two-stage model identity plan: first full-body model reference prompt, then follow-up prompts that reuse that model reference.
- One numbered prompt per requested image.
- Size recommendation: `1024x1024` or square `1:1`.

Do not call image generation in prompt-only mode.
