# Size & Scale Policy

Read this file before prompt writing. Create one shared `Size & Scale Lock` for the whole set.

## Priority

1. If the user provides product dimensions, size chart, garment size, shoe size, bag dimensions, jewelry dimensions, model height/weight, body measurements, or fit notes, use those facts to lock product-to-body scale.
2. If the uploaded image visibly confirms product type or length, preserve that visible type: maxi, midi, mini, cropped, oversized, fitted, low-top, high-top, tote, crossbody, small pouch, stud earrings, pendant, watch, handheld device, and so on.
3. If no exact scale data is provided, use category-normal adult visual proportions only. Do not invent numerical sizes, dimensions, model measurements, product capacities, package quantities, or exact garment lengths.
4. When precision matters for purchase decisions, mention in delivery notes that scale is visually inferred and should be confirmed against the size chart or actual dimensions.

## Category Defaults Without Size Data

- Apparel: keep the visible garment category and fit logic. Full-length/maxi dresses remain full-length or near-floor on an adult model; midi dresses remain mid-calf; mini dresses remain above knee; crop tops remain cropped; oversized/fitted garments preserve their visible ease.
- Shoes: use normal adult foot scale and preserve sole thickness, toe shape, upper height, collar height, and visual bulk.
- Bags: use normal adult hand/shoulder/body scale. Do not turn a normal bag into a mini bag or travel bag without evidence.
- Jewelry and watches: use normal adult body-part scale. Do not enlarge small accessories into statement props unless the product visibly is oversized.
- Beauty, electronics, home goods, and handheld products: use believable hand/body scale and physical contact. Do not add exact capacity, dimensions, or package count.

## Prompt Wording

For unknown scale, include:

```text
Size & Scale Lock: no exact dimensions, size chart, model height, or body measurements were provided. Use category-normal adult proportions only. Treat product-to-body scale as a reasonable visual inference. Do not invent numerical measurements, size labels, height, capacity, package quantity, or exact garment length. Preserve the visible product type and fit logic from the reference image.
```

For known scale, include the supplied facts exactly and avoid extrapolating beyond them.
