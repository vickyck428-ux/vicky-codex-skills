---
name: dianxiaomi-walmart-draft-batch
description: Process Walmart draft products in 店小秘 with a fixed batch workflow. Use when the user asks to edit, standardize, or batch-handle 店小秘 Walmart 采集箱/草稿商品, including title cleanup, Brand filling, SKU rewriting, price recalculation, image trimming, default attribute filling, and saving to 待发布 without using 1688.
---

# Dianxiaomi Walmart Draft Batch

## Overview

Follow a fixed workflow for 店小秘 Walmart draft products.
Do not use 1688. Use only the information visible in 店小秘 plus the fixed pricing formula and defaults below.

## Scope and Order

- Enter from `Walmart > 采集箱`.
- Switch the list from `100条/页` to `300条/页` before batch handling.
- Process only the products visible on the current page.
- Do not switch to other store tabs during the batch.
- Follow the current list order from top to bottom.
- Finish one product before opening the next product.

## Workflow

Process one product at a time in this order:

- Open the draft/edit page for one Walmart product.
- Complete the mandatory translation gate below before doing any title, pricing, attribute, image, or logistics work.
- Fill `Brand` with the current store account exactly.
- Fill `Variant Group ID` with a unique combination of ASCII digits and English letters for the product.
- Rewrite title, description, and five bullet points in English.
- Rewrite every SKU manually.
- Recalculate price for every variant.
- Trim images for every SKU.
- Fill required attributes and defaults.
- Fix red errors.
- Save with `保存` by default. Do not move the product to `待发布` unless the user explicitly requests that destination.
- Do not click `发布`.
- If a leave-page confirmation appears after saving, choose `离开` only after the save result has been confirmed.

If a save attempt fails, remain on the product, fix every visible red error, and retry `保存` until success or a documented blocker is reached.

## Mandatory First Step: Translation Gate

- Treat translation as the first step for every product, with no exceptions.
- Open the `一键翻译` dropdown and click the explicit `普通翻译 → 中文 → 英文` menu item. Do not treat merely opening the dropdown or clicking the top-level button as a completed translation.
- Wait until the translation process has fully finished, and do not continue while a loading state, progress prompt, or unfinished generated result remains.
- After translation finishes, inspect the complete variant section and explicitly confirm the translated `变体主题` selection.
- Do not trust the button click alone: the translation control can finish while row-level Color values, variant labels, or SKU fields still remain Chinese.
- Verify every visible Color value is English only. A bilingual value or any remaining Chinese value means translation has not passed.
- Verify every SKU is English letters, ASCII digits, and allowed ASCII separators only. A SKU containing any Chinese character, including a Chinese color or Chinese numeral, means translation has not passed.
- Verify `Variant Group ID` is present, uses only ASCII digits and English letters, and must not be reused by another product in the batch.
- If any customer-facing field, variant label, Color value, variant theme, or SKU still contains Chinese, run the same `普通翻译 → 中文 → 英文` action again, wait for completion, and re-check the entire product. Repeat until no Chinese remains or the page reports a concrete translation failure.
- Do not start the second step until all variant-theme values, Colors, and SKUs pass this gate.

## Page-Specific Filling Notes

- The five Key Feature editors are separate rich-text frames. Fill one point into each editor in order; do not fill only the first editor or rely on a hidden backing textarea.
- Read each rich-text editor body back after filling and confirm that five distinct values are present in five distinct editors.
- The variant grid can show `productId不能为空`, `运输重量不能为空或0`, or a non-default `Size Descriptor` only after the first save attempt. Treat these as blocking errors: obtain UPC/product IDs through the page's actual UPC option or number pool, set every backend shipping weight to `1`, and set every `Size Descriptor` to `Regular` before retrying.
- Do not invent UPC/product IDs when the page offers an actual number-pool or automatic-acquisition option. Use the page option and verify every row afterward.
- Re-read inputs after any modal, translation, or row update; input indexes can shift when the page rerenders.
- Count a product as complete only after the page reports a successful save and a subsequent readback shows the edited values persisted.

## Save and Window Handling

- If `保存` succeeds, verify the success state/readback, then close the current product edit tab.
- Do not use a move-to-pending-publish action as a substitute for a successful save.
- If a product keeps failing to save or the page remains abnormal after reasonable fixes, leave that product tab open and continue with the next product.
- If image cleanup would leave the product with no valid images, leave that product tab open for the user to handle manually, do not save it, and continue with the next product.
- At the end of a batch run, all successfully completed product edit tabs should be closed.
- Any unresolved save-failure products should remain open as the manual follow-up set.

## Content Rules

- Keep all customer-facing text in English.
- Format the title as `product name + style + main attributes`.
- Do not force the title to start with the brand name.
- Keep the customer-facing `Product Name`/title between `90` and `100` characters inclusive; target `95–100` characters whenever the visible product facts support it.
- Do not treat a short title as acceptable merely because it is under the platform maximum. Rework titles below `90` characters before continuing.
- Put the full final title in the first sentence of the long description.
- Keep the long description at `150` or more English words.
- Fill all `5` Key Feature inputs separately: one selling point in each editor, in order from Key Feature 1 through Key Feature 5.
- Never put all five selling points into the first Key Feature editor as a numbered list, bulleted list, or multi-line block.
- Leave no Key Feature editor empty, and do not duplicate the same point across editors.
- Keep each Key Feature at or below `80` characters.
- Remove Chinese and supplier-style marketing wording.
- Do not keep year terms like `2025` or `2020`.
- Do not use `爆款`、`跨境`、`精品`、`新品`、`最新...`.
- Use a natural, non-promotional tone.

## Brand, SKU, and Images

- Set `Brand` to the current store account exactly, for example `StyleSack`.
- Set `Variant Group ID` to a unique ASCII alphanumeric value, for example `VG28000712992209479A`; never use Chinese characters, Chinese numerals, spaces, or punctuation.
- Do not use the original SKU.
- Rewrite SKU as `数字 + 英文字符 + 店铺缩写`.
- Keep SKU short and globally unique.
- If variant colors become English after `一键翻译`, keep using the translated English values.
- If selected variant-theme values are still Chinese after `一键翻译`, do not treat translation as done; re-run translation or manually correct them to English before saving.
- For each SKU, keep only the first `9` images.
- Do not stop after handling only the first visible SKU groups.
- For any multi-SKU product, scroll through the full image section and check every SKU or color group one by one until all groups have been reviewed.
- Treat image cleanup as complete only when every SKU group on that product has been checked and reduced to the target image count or intentionally left open under an exception rule.
- The first main image is normally preserved, but if it clearly contains obvious infringement risk such as third-party IP, character, logo, or trademark elements, delete it too.
- Delete from the back first.
- If the remaining `9` images still contain obvious Chinese text, delete those images too.
- If any of the remaining images contain obvious third-party IP, character, logo, or trademark elements, delete those images too.
- Treat clearly recognizable items such as `Hello Kitty`, Disney-style characters, branded logos, or obvious licensed-character accessories as high-risk and remove them.
- Only remove obvious infringement-risk images; do not spend extra time on borderline style-similarity judgment.
- It is acceptable to end with fewer than `9` images after deleting Chinese images.
- Every SKU or variant must keep at least one main image and must not end up without images.
- If deleting obvious Chinese or obvious infringement-risk images would leave a SKU or variant with no images at all, stop editing that product, leave its tab open, do not save it, and continue with the next product.

## Pricing Formula

- Treat the current 店小秘 USD price as `成本USD`.
- Use exchange rate `6.8`.
- Use fixed total shipping cost `98 RMB`.
- Shipping breakdown:
  - `90 RMB` first-leg shipping
  - `8 RMB` domestic 1688-origin shipping cost
- Calculate sale price with:
  - `售价USD = ((成本USD × 6.8) + 98 + 1.05 × MAX(35, (成本USD × 6.8) × 1.15)) / 5.88`
- Keep `2` decimal places.
- After calculating the sale price, adjust the final cents to `.99`.
- Do not leave arbitrary cents such as `.75`, `.42`, `.18`, or `.89`.
- Apply the formula to every variant price.
- Do not leave variant prices equal to cost USD.

## Required Defaults

- `Size Descriptor = Regular`
- `Country of Origin - Substantial Transformation = China`
- `Condition = New`
- `Small Parts Warning Code = 0 - No warning applicable`
- `Fulfillment Lag Time = 7`
- `Gender = Female`
- `Age Group = Adult`
- `Number of Pockets = 1` when unknown
- `Count / Count Per Pack / Multipack Quantity = 1`
- `Material` must be added after input.
- `Fabric Care Instructions` must be added after input.
- Use `Spot clean with damp cloth` for `Fabric Care Instructions` when no better text is available.
- If the product material is not `PU`, first uncheck the blue checkbox in front of the default `PU`, then type the actual material into the input directly below, and finally click the `添加` button on the right. Verify that the actual material appears as selected after adding it.
- For checkbox-style attribute groups, do not assume the prechecked options are correct.
- For every product, read every blue-checked option in every checkbox-style attribute group and compare it with the visible product evidence before saving. Treat the blue state as a preselection, not as proof that it is correct.
- If any blue-checked option conflicts with the product name, full description, five Key Features, variant data, or visible images, uncheck it, enter or select the appropriate value, click `添加` where the field provides an add button, and verify the corrected option is now selected.
- Do this attribute-by-attribute on every product, including Material, Color, Closure Style, Carrying Type, Handbag Style, Gender, warning codes, and other checkbox-style fields; never skip the check because a default is already blue.
- For `Color Category`, derive the allowed checked colors from the product's actual variant/color information. Compare every blue-checked color against that evidence; uncheck each color that is not represented by the product, and check/add each represented color that is missing.
- Apply the same evidence comparison to `Carrying Type`, `Handbag Style`, and `Age Group`: inspect the blue selections, keep only options supported by the product's nature and visible copy, and uncheck unsupported defaults before saving.
- Carrying Type and Handbag Style are not fixed defaults; you may uncheck already selected options and reselect the closest matching option based on the visible product information.
- Choose color, closure style, carrying type, and handbag style from the closest visible product information.

### Country of Origin Selection

- For `Country of Origin - Substantial Transformation`, open the selector, use its search box to enter `China`, and select the `China` result.
- After selection, read the closed selector's displayed value and confirm it visibly shows `China`; an empty `请选择`/blank display does not count as selected.
- Do not continue to the next field until the displayed value is confirmed as `China`.

## Spec and Logistics Rules

- Use visible 店小秘 copy as the normal content source; the only exception is an explicitly user-provided offline 1688 HTML/text file handled by the extractor below.
- Never open 1688.
- Do not navigate to 1688 in an automated browser or use a network scraper for it.
- If the user has manually completed any required 1688 verification and saved an individual product page as local HTML/text, an optional offline extractor may be supplied through `WALMART_1688_EXTRACTOR`.
- Run that extractor only against the user-provided local file. It must remain offline and must never use browser cookies, credentials, or network requests.
- Use an extracted size or weight only when its `evidence` field shows an explicit source value. If the extractor reports no explicit value, retain the normal `1` fallback for that field.
- Do not use the existing 店小秘 attribute-area values as factual product references; treat them as internal defaults that may be inaccurate.
- Read product facts from `Product Name`, the full long description, every `Key Feature` field, visible image content, and variant/theme information.
- Use those sources to decide how to refill the attribute area; do not infer product facts from the prefilled attribute-area content itself.
- Treat prefilled dimensions and weight as untrusted unless the visible copy explicitly states them.
- For width, weight, depth, height, and similar visible spec fields:
  - If the visible copy explicitly gives a value, use that value.
  - Otherwise fill `1`.
- When an explicit source value includes units, convert it to the Walmart field unit before entering it: centimeters to inches by dividing by `2.54`; grams to pounds by dividing by `453.59237`; kilograms to pounds by multiplying by `2.20462262`.
- If the source value has no clear unit, is ambiguous, or cannot be tied to the product's visible detail-page evidence, do not guess or reuse the prefilled value; enter `1` in the relevant field.
- Apply the same rule to `Assembled Product Width`, `Assembled Product Weight`, `Assembled Product Depth`, and `Assembled Product Height`: use visible 店小秘 product information when clearly available; otherwise fill all of them with `1`.
- Package size defaults to `1 × 1 × 1 in`.
- Package weight defaults to `1 lb`.
- Backend shipping weight defaults to `1 lb`.

## Variant, Inventory, and UPC Rules

- Keep existing UPC values when they are already present.
- If UPC is missing, use the actual available page option instead of inventing one.
- Inventory can keep the current page value.
- Check and update every variant price separately.

## Completion Check

- Confirm before saving:
  - No red errors remain.
  - Brand matches store account.
  - Variant Group ID is non-empty, ASCII alphanumeric only, and unique in the batch.
  - Product Name/title length is between `90` and `100` characters, preferably `95–100`.
  - Title/description/bullets are English only.
  - All five Key Feature editors are non-empty and English only, with exactly one distinct point in each editor.
  - The first Key Feature editor does not contain the other four points.
  - The mandatory translation gate passed before later editing began.
  - Selected variant-theme values, every Color value, and every SKU contain no Chinese.
  - Forbidden year and marketing words are removed.
  - Prices are recalculated with the fixed formula.
  - Images are trimmed per SKU.
  - Every SKU still has at least one main image.
  - Every blue-selected checkbox-style attribute was checked against product evidence; mismatches were unselected and corrected values were added and verified.
  - All dimension and weight fields were re-read from visible product-detail evidence, converted to `in`/`lb` when source units were explicit, or reset to `1` when evidence or units were missing.
  - The Country of Origin selector visibly displays `China`, not a blank placeholder.
  - Required defaults are filled.
- After a successful `保存` and verified readback, close the tab.
- If saving still fails after fixes, keep the tab open and continue the batch.

## Fallback Rules

- If visible information is incomplete, do not stop to ask the user.
- Continue the current product with the confirmed defaults and best-effort English rewrite.
- For a non-`PU` product, do not leave the default `PU` checkbox selected; complete the uncheck → enter actual material → `添加` sequence before saving.
- If no clear visible spec value exists, fill the spec field with `1`.
- If saving fails, read the page error, try to fix the blocking red errors, and retry.
- If the product still cannot be saved after reasonable fixes, leave the page open and continue with the next product.
