# Production gates

## Source and market

- Expand the real 1688 child matrix. Keep `skuId`, `specId`, every dimension, price, inventory, and the child's own image.
- Block production if a sellable child lacks a stable identity or dedicated image.
- Remove supplier marketing, competitor brands, seller IDs, unverified claims, and year/newness hype from facts. Preserve truthful style terms such as Y2K or 1990s.
- Amazon US/UK/DE exact-match checks are independent. A visual candidate is not an exact match. If no exact match is confirmed, record `未确认同款 / FBA未知`.
- If an exact match is confirmed, close all Offers evidence before classifying FBA, FBM, or Amazon Retail.

## IPR and human release

- `通过并开始侵权` creates or resumes an IPR task; it does not authorize a workbook.
- The automatic closure queue always uses `lc-ipr-risk-screening-free`. Keep `lc-ipr-risk-screening` installed only as an on-demand US tool; invoke it solely after the user explicitly requests a paid check for one Amazon US ASIN or URL.
- Never fall back from the free queue to the paid Skill because of quota, incomplete evidence, errors, or retries. Record the free result or blocker and wait for a separate user instruction.
- The operator may release an attempted visible result that is low, medium, incomplete, waiting for manual evidence, or retryable.
- Untouched, queued, or actively running tasks cannot be released. High, very high, and `RISK_STOPPED` are hard blocks.
- A brand, site, structure, visible text, material fact, image, or rule-version change invalidates the IPR release; price or inventory alone does not.

## Copy and images

- Rufus research may use 1-20 relevant Amazon US competitors and remains brand-neutral.
- Amazon and Walmart render separate platform formats from the neutral research.
- Visual input rejects Listing, Bullet, search terms, Rufus Q&A, and copy-created image plans.
- Copy edits rerun only the affected renderer; image edits rerun only requested child/image slots. Product-fact changes invalidate both.

## Workbook

- The final checkbox is single-use and immediately cleared when claimed.
- Bind the request to current brand, site, children, facts, copy, images, template, and review hashes.
- If any bound input changes, do not generate from the stale request.
- After generation, upload the attachment to the existing Feishu record and read it back. The state is `待人工上传`, never automatically completed.
