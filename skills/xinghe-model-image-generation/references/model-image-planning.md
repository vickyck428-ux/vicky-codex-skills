# Model Image Planning

Use this file after reading `category-composition-matrix.md`. Build a concise two-stage model-photo plan that keeps the product and model identity consistent while varying angle, crop, pose, and white-background presentation.

## Default Set

Default to 8 square images unless the user specifies another quantity. All images use the same seamless pure white studio background.

Use two stages:

1. Generate the first full-body image as the `Model Identity Reference`.
2. Generate all remaining images with both references: the original product image plus the saved `Model Identity Reference`.

The first image must define the model's adult Chinese identity, body type, skin tone, hairstyle, outfit logic, sunny positive facial mood, and clean white studio lighting. The remaining images must preserve that same Chinese adult model identity, positive expression direction, and background while changing only angle, crop, pose, product orientation, and interaction.

1. Full-body model identity reference: model faces camera or stands in a clean three-quarter pose, full body visible when useful, product clearly worn/held/carried/displayed, pure white studio background.
2. Side half-body angle: 30-60 degree body turn, product visible from side or oblique angle.
3. Full-body or wider crop: show product scale, fit, carrying relationship, or overall styling.
4. Back, side-back, or over-shoulder angle: useful for apparel, bags, hair accessories, outerwear, footwear, or items with rear/side structure.
5. Product detail close-up with model: hands, wrist, shoulder, neckline, waist, foot, face-adjacent, or body-contact crop, depending on product.
6. Handheld or interaction shot: model naturally holds, adjusts, carries, applies, opens, closes, or presents the product.
7. Dynamic pose: walking-step, turning, hair movement, garment drape, bag swing, hand gesture, or subtle motion, while background stays pure.
8. Premium campaign hero: stronger light, refined styling, memorable silhouette, clean pure background, product remains the main commercial focus.

## Category Adaptation

Use `category-composition-matrix.md` as the role source. The notes below are only secondary reminders:

- Apparel: emphasize fit, drape, seams, fabric thickness, sleeve/waist/hem relationship, front/side/back, and natural movement.
- Shoes: emphasize standing/walking pose, side profile, sole/upper detail, and realistic foot contact.
- Bags: emphasize handheld, shoulder, crossbody, side/back carrying, strap length, hardware, closure, and scale.
- Handheld goods/drinkware: emphasize hand scale, grip logic, lid/button/logo/detail clarity, two-hand presentation, and face-adjacent hero; avoid too many redundant full-body shots.
- Jewelry/watches/accessories: use face, neck, ear, wrist, hand, waist, or hair-adjacent crops plus one wider styling shot.
- Beauty/skincare: use hand, face-adjacent, shoulder-up, application gesture, cap/pump/texture logic when visible, and clean skin realism.
- Small electronics/home goods: use hand-held or model-presented studio shots, scale proof, button/port orientation when visible, and clean shadow.
- Non-wearable products: prioritize hand model, face-adjacent presentation when appropriate, tabletop-free pure-background holding poses, and clear scale.

## Variation Rules

- Keep at least five meaningfully different compositions in an 8-image set.
- Vary at least three subject scales: full/wide, half-body, close-up/detail.
- Vary camera angle, product orientation, model pose, lighting direction, and product interaction, while preserving the same model identity.
- Do not let all images become the same centered model with the same hand pose and same crop.
- Do not change the product's SKU, color, decoration, logo placement, structure, package count, or function to create variation.
- Do not change model identity, face, body type, skin tone, hairstyle, or outfit logic after the first full-body reference image.
- Do not sacrifice product clarity for pose variation. For small or handheld products, more close/half-body crops are usually better than repeated full-body poses.

## Pure White Background Rules

Default background:

- seamless pure white studio background;
- white cyclorama or white paper sweep;
- minimal realistic contact shadow;
- consistent white balance and lighting family across the full set.

Avoid:

- light gray, warm off-white, beige, pink, colored gradients, brand-color backgrounds, or mixed background colors unless the user explicitly requests them;
- bedrooms, bathrooms, cafes, streets, parks, beaches, offices, kitchens, living rooms, gyms, malls, cars, hotels, and travel scenes;
- complex props, furniture, decorative plants, windows, shelves, carpets, lifestyle clutter, or narrative environments;
- heavy graphic posters, platform UI, fake badges, fake packaging claims, or promotional text.

## Model Defaults

Use adult models only. If the user does not specify model traits, default to an adult Chinese commercial model, then infer fitting gender presentation, styling, hair, makeup, body type, and styling character from the product category and style while avoiding stereotypes. Default facial mood is sunny, positive, confident, approachable, and naturally warm, with a relaxed smile or soft smile. Keep the model realistic and natural, with visible skin texture and plausible hands/body anatomy. Avoid cold luxury detachment, gloomy editorial mood, blank stare, tired face, angry face, sad face, exaggerated laughing, or theatrical expression unless the user requests it.
