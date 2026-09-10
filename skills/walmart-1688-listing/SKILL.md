---
name: walmart-1688-listing
description: Parse 1688 products and generate or repair Walmart Listing draft/upload workbooks with exact SKU and image mappings. Use for Listing草稿、1688转Walmart上架表、上传工作簿或退回表修正；do not use for WFS candidate selection, FBM first-sale actions, T1 approval, packing, Shipment ID, or unconfirmed image upload.
---

# Walmart 1688 Listing

Use the deterministic tool at `${WALMART_1688_TOOL_ROOT}` for parsing, image upload, validation, and spreadsheet output. Use Codex reasoning only for English copy and exact dimension-value translation.

## Required inputs

Obtain:

- One `detail.1688.com/offer/...` URL, or an `.xlsx`, `.csv`, or `.txt` file containing multiple links.
- The target brand/account for every new run. If the user provides a new link without naming the brand, ask one concise question before parsing: `StyleSack` or `Baguery`. Never infer the account from the previous run. Preserve brand display capitalization exactly. Resolve account slugs and Fulfillment Center IDs from the external account config; never store real IDs in the Skill.
- The current Walmart official category template once. Reuse the verified `walmartTemplate` path in local config for later runs until the user supplies a newer template.
- A one-column UPC `.xlsx` or `.csv` pool only when `upc.mode` is `pool`; default `generated` mode does not require a UPC file.
- A local business config copied from `config.example.json`; image-host SSH settings are loaded from `~/.config/codex/image-host.env` and must not be duplicated in the project config.

Do not invent missing runtime inputs. Do not request or expose private SSH keys in chat.

## Workflow

1. Load the workspace spreadsheet runtime and ensure the tool directory has a `node_modules` symlink to the provided runtime.
2. Run:

   `node src/cli.mjs parse --url <single-link> --output <run-dir>`

   Include the target account, for example `--account stylesack` or `--account baguery`.

   For a batch file, use `node src/cli.mjs parse --input <links-file> --output <run-dir>`.

3. Read `parsed_products.json` and `validation_report.xlsx`.
   - The parser automatically retries through the configured Tencent Cloud SSH host if the local request receives a login or risk-control page. Both paths are script-only and do not use a browser or 1688 API.
   - Stop blocked products from moving forward.
   - Never reconstruct SKU relationships from color text. Trust only parsed `skuProps`, `skuInfoMap`, `specId`, and `skuId` mappings.
   - Treat zero inventory as a valid SKU with inventory `0`.
4. Generate `listing_content.json` following `references/schemas.md`.
   - Read `references/us-listing-content-policy.md` before writing or validating copy and images. Apply a newer official rule or a stricter current category-template rule when available.
   - Use only `titleZh`, parsed attributes, dimensions, images, weights, and prices as product evidence.
   - Write a brief English title beginning with the configured brand and never exceeding 150 characters, counting spaces and punctuation. Follow any stricter template limit. For the current handbag template, target at most 90 characters and surface `TITLE_EXCEEDS_TEMPLATE_SEO_RECOMMENDATION` above 100.
   - Prefer brand, product type, key attribute, size or count, then the main differentiator. Use proper capitalization; do not use all caps, repeated keywords, multiple brands, irrelevant product types, URLs, retailer names, promotional claims, unsupported years, or non-English text other than an official brand or item name.
   - Select one or two evidence-backed primary keywords and use them naturally without repetition or stuffing.
   - Start the English description with the exact title and write one paragraph of at least 150 words. Apply any higher category minimum and include every available translated color, size, style, and quantity option. Do not impose a maximum unless the current template defines one.
   - Write exactly five distinct Key Features, which is within Walmart's allowed three to 10. Keep each at most 80 characters including spaces and put the most important feature first.
   - Translate every raw dimension value exactly once. Preserve meaningful distinctions such as `Black No Chain` versus `Black With Chain`; do not collapse them to the same English value.
   - Use only periods and commas as punctuation. Remove Chinese, supplier promotions, retailer references, URLs, emojis, special formatting, unsupported authenticity or quality claims, and calendar years unless the product type's official Content Standard requires the year. Preserve supported decade terms such as `1900s`, `1990s`, and `2000s`.
5. Run the uploader check before any upload:

   `node src/cli.mjs check-uploader --account <account>`

   If the check fails, stop and report the missing authorization/configuration. Do not create remote directories or alter the server.
6. Inspect all image candidates from `image_review.skeleton.json` before upload.
   - Download or render the candidate images and reject any with obvious Chinese text, Hello Kitty, cartoons, or other suspected third-party IP.
   - Use actual images of the exact product. Reject stock photos, placeholders, duplicates, retailer logos, text overlays, promotional claims, non-English text, and accessories that are not included.
   - Target 2200 by 2200 pixels, RGB, 8 bits per pixel, 1:1 square, and 5 MB or less. Use JPEG, JPG, PNG, or BMP; convert eligible GIF or WebP sources to JPEG or PNG. Record a warning below the 1500 by 1500 zoom threshold and never hide low source quality.
   - Treat the first image of every SKU as its Walmart primary image. Inspect its background before upload. If it is already a clean white background, keep the original. Otherwise, use the image-editing tool to isolate the exact product and replace only the background with solid white `#FFFFFF`.
   - Preserve the complete product, original colors, texture, proportions, logos, straps, handles, chains, and included accessories. Do not add text, props, borders, watermarks, or unsupported product details. Reinspect the edited image for clipping, halos, missing parts, deformation, or color shifts; retry the edit or block the SKU when the result is not faithful.
   - Reuse one verified white-background primary image across size variants that share the same exact color image. Keep secondary images unchanged unless they fail the normal IP or content review.
   - Prefer at least four distinct eligible images per listing and record a warning when fewer than four exist.
   - Keep at most nine approved images per SKU. If none remain, block that SKU and report it instead of writing it to Walmart.
   - Save the completed review as `image_review.json`. Do not approve an unrelated image. A white-background derivative is allowed only when its original source image is in the parsed candidate list and the source-to-derivative relationship remains traceable in the run artifacts.

7. After the uploader check and image review, show the exact files, target Walmart account, SSH target host, remote root, and public URL base. Run `upload` only after the user gives current confirmation for that exact file set and target; no standing consent applies:

   `node src/cli.mjs upload --parsed <parsed_products.json> --review <image_review.json> --account <account> --output <parsed_uploaded.json>`

   Require every uploaded HTTPS URL to pass the tool's public read-back check before treating the image as uploaded.

8. Export:

   `node src/cli.mjs export --parsed <parsed_uploaded.json> --content <listing_content.json> --config <config> --account <account> --output <final-dir>`

   Pass `--template <walmart-template.xlsx>` only to override the configured verified template for that run.

   Set `upc.mode` to `pool` and add `--upcs <upcs.xlsx>` to retain formal UPC-pool compatibility.

   The exporter automatically expands `Additional Image URL (+)` to one complete repeated column per approved secondary image, up to eight secondary images. It duplicates the full official column metadata and shifts every later cell, column definition, merge, validation range, and same-sheet validation formula reference. Do not add image columns manually after export.

   Read `references/walmart-workbook-contract.md` before changing template-writing or OOXML-preservation logic. Treat every rule in its delivery gate as blocking.

9. Inspect the final validation report and workbook previews under `<final-dir>/qa/`. Deliver only when no intended upload row is blocked.

   Block delivery for any violation of `references/us-listing-content-policy.md`, including a title over 150 characters, a description under 150 words or split into multiple paragraphs, a Key Feature over 80 characters, unsupported claims, content-to-product mismatch, or a noncompliant primary image.

   The exporter must write values through the normal spreadsheet layer, then transplant only the populated data rows into the untouched official XLSX package. A plain import-and-reexport can remove Walmart's merged attribute groups and hidden-sheet state, causing populated composite fields to be reported as missing.

   Require the exporter result to report `preserved: true`, the expected repeated-image column count, unchanged merge and validation counts, no missing attribute metadata, exact per-SKU image order, and no formula errors.

   For handbag template version `5.0.20260501-19_21_29`, keep `defaults.rejectedTemplateFields` set to `swatchVariantAttribute`, `swatchImage`, `packageWeightLb`, `packageDepthIn`, `packageWidthIn`, and `packageHeightIn`. Walmart's processed error workbooks rejected nonblank `swatchImageUrl`, `product_package_dimensions_height`, and then `product_package_dimensions_depth`; omit the entire package orderable group to prevent sequential backend rejection. Do not restore it until a newer official template passes an online upload test.

   These rejections apply only to the package orderable group. Treat `Shipping Weight (lbs)` as a separate required field. Populate it from evidence-backed package or item weight even while `product_package_weight` remains blank.

10. Before final export, scan the selected Walmart template's data-validation rules and enumerate every dropdown field. For each product row, select only values supported by parsed evidence and the template's closed-list options; clear placeholder values such as `2265`. Leave fields blank when the product evidence does not justify a closed-list choice. Recheck the saved workbook for remaining placeholder values and invalid manual entries.

11. When Walmart returns an error-marked workbook:
   - Read row 2 columns A and B, every populated product row, and every cell comment as diagnostics only.
   - If the normal workbook renderer fails because Walmart wrote malformed or empty comment authors, fall back to read-only `openpyxl` or raw OOXML inspection. Do not sanitize or rewrite the returned workbook merely to inspect it.
   - Treat precision comments attached to both `Measure` and `Unit` cells in one assembled-dimension group as a composite-field error. Correct the numeric measure precision first; do not change a valid `in` or `lb` unit only because the unit cell repeats the same comment.
   - Regenerate from the untouched verified template or the most recent structure-verified clean output. Never use the returned workbook as the new template.

## Invariants

- For `skuPrice`, use the SKU record's effective price.
- For `rangePrice`, use only the tier covering quantity `1`; never use the lowest bulk price as one-piece cost.
- Bind a color image only through `skuProps.value.imageUrl`. Reuse it across sizes of the same color.
- Put the exact color image first and require that first image to have a clean solid-white background. Automatically create and verify a faithful white-background derivative when needed, then place common product images after it; exclude known images belonging to other colors and keep at most nine.
- Treat accurate, truthful, non-misleading, rights-compliant content as a delivery gate. Never invent or exaggerate size, color, quantity, material, ingredients, features, benefits, limitations, certifications, authenticity, reviews, or endorsements.
- Fill every evidence-supported attribute using the correct field type and unit. Leave unsupported optional fields blank instead of inserting placeholders or fabricated values.
- Treat the official Walmart category template as the authority for field limits. SKU must be alphanumeric, at most 50 characters, and remain unique across historical runs.
- Treat parsed 1688 cost as RMB by default. Convert with 6.8 only when the configured source currency is explicitly USD; then apply the pricing formula independently to every SKU and end the result in `.99`.
- Write parsed package dimensions and weight to matching template columns. If Walmart rejects blank assembled dimensions as required, use the configured `missingRequiredDimensionIn` fallback with `in` units and retain the missing-evidence warning; do not present the fallback as supplier evidence.
- Retain all evidence-backed package weight and dimensions in `evidence.xlsx` and use them for freight calculations. For template version `5.0.20260501-19_21_29`, omit the entire package orderable group from upload data through `rejectedTemplateFields` because Walmart progressively rejects its populated metadata fields; keep evidence-backed assembled dimensions and weight in their supported upload columns.
- Round `Assembled Product Depth`, `Assembled Product Height`, and `Assembled Product Width` to at most two decimal places and use `in`.
- Round `Assembled Product Weight` to at most two decimal places and use `lb`.
- Populate required `Shipping Weight (lbs)` from package weight when available, otherwise item weight, rounded to at most three decimal places. Map it independently from `product_package_weight`; rejecting or clearing the package orderable group must never clear `Shipping Weight (lbs)`.
- Freight calculation uses the configured YunExpress table: with complete package dimensions and weight, charge the larger of actual weight and `L×W×H/8000` volume weight. If dimensions are missing but weight is known, calculate by actual weight with a `98 RMB` floor; if weight is also missing, use `98 RMB`. Do not infer dimensions from product photos without evidence.
- When dimensions appear only in detail images, inspect at most the first three likely specification images as an OCR fallback. Record the image URL and OCR evidence; if the text is unclear, keep the conservative freight rule and report `MISSING_PACKAGE_DIMENSIONS`.
- For assembled product dimensions and package dimensions, use image OCR only when a clear numeric label is visible. Prefer evidence-backed values and choose `in` for dimensions or `lb` for weight. When the current Walmart template/backend makes assembled dimensions mandatory and evidence is still unavailable, use the explicit configured fallback and record `MISSING_PACKAGE_DIMENSIONS`.
- Fill `Fulfillment Center ID` from `defaults.fulfillmentCenterId`. If it is absent, keep it blank and report `MISSING_FULFILLMENT_CENTER_ID` for one-time store setup.
- For the handbag template, default `Handbag Style (+)` to `Bucket`, `Has Written Warranty` to `No`, and `Season (+)` to `All-Season`, unless the verified product evidence or the user explicitly overrides them.
- Add repeated `Additional Image URL (+)` fields through the implemented OOXML whole-column insertion in `src/template-preserver.mjs`. Keep every repeated row-4 header, row-5 `productSecondaryImageURL` metadata cell, and row-6 definition identical; put one HTTPS URL in each data cell. Shift all later cells, column definitions, merges, validations, metadata references, and validation formulas. Never join URLs with separators, rename repeated headers, or move only visible values.
- When Walmart returns an error-marked workbook, read the row error summary and cell comments, then regenerate from the untouched current official template. Do not use the returned workbook as the next base template because its annotations can break importers and preserve prior structural corruption.
- Before delivery, verify the official workbook still contains its hidden lookup sheet, original merged attribute groups, and data validations. For the current handbag template this means 24 merged groups and 54 validations; a mismatch blocks delivery.
- If the configured original template path has been moved, use the most recent structure-verified clean output as the recovery base and update `walmartTemplate`. Never fall back to a Walmart error-annotated return file.
- Before export, verify that every nonblank header in `Product Content And Site Exp` has a nonblank attribute-metadata cell. If any metadata is missing, block the export instead of producing a workbook that Walmart will reject.
- Select the account profile explicitly. Never reuse one account's Fulfillment Center ID for another account. IDs come only from the external account config and are not brand IDs.
- Compare the template's `inventory_fulfillmentCenterID` lookup with the selected account before export. If it contains another account's ID, never substitute that wrong ID. Keep the selected account's configured ID, report `TEMPLATE_ACCOUNT_LOOKUP_MISMATCH`, and prefer a clean template downloaded under the selected account when one is available.
- Block a color variant with no dedicated image.
- Keep product/SKU failures isolated so other links continue.
- Do not publish to Walmart. Produce review-ready files only.
- Generated UPCs are only 12-digit UPC-A values passing GS1 Mod-10 logic. Mark them as `Unregistered / Generated` and include `UNREGISTERED_GENERATED_UPC_RISK`; never call them GS1-registered, globally unique, or guaranteed Walmart-compliant.

## Outputs

Expect `parsed_products.json`, `walmart_upload.xlsx`, `validation_report.xlsx`, `image_manifest.xlsx`, `upc_assignments.xlsx`, and `evidence.xlsx`.
