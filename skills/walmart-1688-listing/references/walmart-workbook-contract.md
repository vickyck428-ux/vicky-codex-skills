# Walmart workbook contract

Use this contract whenever reading, modifying, validating, or regenerating a Walmart official upload workbook.

## Template authority

- Start from the current untouched Walmart category template or the most recent output already proven to preserve the same official structure.
- Never start from a Walmart error-annotated return workbook.
- Preserve every sheet, including the hidden lookup sheet, workbook defined names, styles, relationships, merged cells, data validations, formulas, and template version metadata.
- Do not rename `Product Content And Site Exp` or change template rows 1 through 6.

## Header and metadata rows

- Treat row 4 as the visible attribute header, row 5 as the hidden Walmart attribute metadata, row 6 as the field definition, and row 7 as the first product row for the current handbag template.
- Require every nonblank row-4 header to have nonblank row-5 metadata.
- Keep data rows below the instruction rows; never paste product values into rows 1 through 6.
- Preserve official field names and closed-list spelling exactly.

## Repeated image fields

- Put the SKU-specific color image in `Main Image URL` and require a faithful seamless-white-background primary image.
- Add common approved images after the main image, with at most nine total images per SKU.
- Prefer at least four distinct eligible images and report a warning when fewer than four exist.
- Create one complete `Additional Image URL (+)` column for each secondary image, up to eight columns.
- Keep the visible header identical in every repeated column. Keep row-5 metadata exactly `productSecondaryImageURL` and copy the row-6 definition.
- Put one public HTTPS image URL in each cell. Never join URLs with semicolons, commas, spaces, or line breaks and never rename headers to `Additional Image URL 2`.
- Insert complete columns through `src/template-preserver.mjs`; shift all later cells, column definitions, merged references, validation ranges, active-cell references, and same-sheet validation formula references.
- Do not mix another color's dedicated image into the current SKU. If a color has no dedicated image, block it rather than substituting a public image silently.

## Dropdown and evidence rules

- Scan every data-validation rule before filling the template.
- Choose only a value present in the official closed list and supported by parsed product evidence or an explicit configured default.
- Leave unsupported optional dropdowns blank and remove placeholders such as `2265`.
- For the handbag template, use evidence-based `Handbag Style (+)`; default to `Bucket` only when configured. Use `No` for `Has Written Warranty` and `All-Season` for `Season (+)` unless explicit evidence overrides them.

## Dimensions, weight, and fulfillment

- Prefer supplier-evidenced package dimensions and weight. Convert dimensions to `in` and weight to `lb`.
- Round assembled depth, height, and width to at most two decimals. Round assembled weight to at most two decimals. Keep `Shipping Weight (lbs)` at at most three decimals.
- Treat `Shipping Weight (lbs)` and `product_package_weight` as separate exporter fields. Populate required shipping weight from package weight when available, otherwise item weight. Clearing the rejected package orderable group must not clear shipping weight.
- When required package dimensions are unavailable, use the configured fallback and retain `MISSING_PACKAGE_DIMENSIONS`; do not describe the fallback as supplier evidence.
- Use the selected account's Fulfillment Center ID. Never use a different account's ID and never describe it as a brand ID.
- For template version `5.0.20260501-19_21_29`, keep data cells for `swatchVariantAttribute`, `swatchImageUrl`, `product_package_weight`, `product_package_dimensions_depth`, `product_package_dimensions_width`, and `product_package_dimensions_height` blank. Preserve their official headers and metadata rows. Continue storing the complete package facts in the evidence report and using them for freight calculations; retain supported assembled dimensions and weight in the upload sheet.

## Delivery gate

- Block delivery if the output is not an official preserved workbook.
- Block delivery if a nonblank header lacks attribute metadata, an additional-image definition is missing, a repeated-image count differs from the image manifest, or per-SKU image order differs.
- Block delivery if any image URL is not one public HTTPS URL per cell, total images exceed nine, a public read-back fails, the main image is not compliant, or an image uses an unsupported final format such as GIF or WebP.
- Block delivery if merged-cell or data-validation counts change. For the current verified handbag template, require 24 merged groups and 54 data validations.
- Block delivery if any formula contains `#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?`, or `#N/A`.
- Block delivery if an evidence-backed row has blank `Shipping Weight (lbs)`, if assembled dimensions exceed two decimal places, or if assembled weight exceeds two decimal places.
- Render the repeated-image area and inspect SKU, main image, and all secondary-image columns before delivery.

## Walmart error recovery

- Read the returned workbook's row error summary and cell comments only as diagnostics.
- If malformed or empty Walmart comment authors break the normal renderer, inspect comments with read-only `openpyxl` or raw OOXML. Do not repair the returned workbook for reuse.
- When the same precision error appears on a composite dimension's `Measure` and `Unit` cells, fix the numeric measure precision first and keep a valid `in` or `lb` unit.
- Correct the source data or mapping, then regenerate from the untouched verified template.
- If Walmart reports missing attribute metadata, first check rows 4 through 6, repeated columns, shifted validation formulas, hidden-sheet state, and the template version.
- Read row 2 columns A and B and all product rows before changing the tool. If Walmart reports a field name as invalid, clear only that field's data from a clean workbook and add its mapped exporter field to `defaults.rejectedTemplateFields`; do not delete or rename the official header.
