# Channel isolation

## Amazon

- Sites: US, UK, DE. Search, exact-match evidence, all Offers, IPR jurisdiction, account, template, and attachment are site-scoped.
- Brands: `Vocuer`, `BenPo bar`; no default. A product selects one brand per platform route.
- Seller SKU includes the brand namespace. Listing title starts with the selected brand and excludes the sibling Amazon brand.
- GTIN exemption leaves Product ID blank and uses the registered official template for the exact brand-site route.
- A missing account or template blocks only that workbook route; market research and neutral Rufus research may continue.

## Walmart

- Brands: `StyleSack`, `Baguery` only.
- Keep SS/BG SKU prefixes, separate account and fulfillment-center routing, and the shared persistent UPC-A registry.
- Every real child receives one stable UPC-A keyed by source offer and child identity.
- Preserve the official workbook's hidden sheets, merged ranges, validations, one main image, and six repeated additional-image columns.

## Assets

- Neutral assets can be reused only when product-fact and source-image hashes match.
- Branded, localized, or platform-text assets are derived per brand/site and cannot cross brands.
- Europe remains one parent row with independent UK/DE fields and decisions; do not rebuild its state machine.
# IPR provider routing

- Amazon US, Amazon UK/DE, and Walmart automatic routes use the free IPR queue.
- The paid `lc-ipr-risk-screening` Skill is US-only and manual-on-demand. It must not be called by the 09:00 watchdog or by `closurectl run`.
- A paid report may supplement the US evidence display after an explicit request, but it does not auto-release a workbook and does not replace the user's final review.
