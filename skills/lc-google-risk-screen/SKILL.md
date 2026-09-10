---
name: lc-google-risk-screen
description: Screen each imported 1688 parent product with one representative image in Google Lens, classify websites, review landing-page false matches, preserve screenshots and URLs on errors, and hard-stop confirmed high-risk products. Use for handbag image-search infringement screening, Google evidence repair, website-rule changes, or retrying a failed Google stage.
---

# Lc Google Risk Screen

Run through `selectionctl resume` or retry only the `GOOGLE` stage.

## Search and evidence

- Search one representative image per parent; do not repeat colors with the same structure.
- Inspect all available product/gallery images instead of assuming image 1 or image 2 is best. Prefer a clear frontal product view; otherwise prefer a complete, centered product on a clean white background, then fall back to the ordinary main image. Preserve the selected URL and selection reason in the local result evidence.
- Keep all result cards locally. Sync only brand/designer/luxury/known-retailer evidence and error evidence to Feishu.
- Cache only successful or manually confirmed terminal outcomes by `representative image fingerprint + rule version`. Reuse that baseline result across Amazon/Walmart and matching US/UK/DE product rows. A changed image fingerprint or rule version invalidates the cache.
- Never cache 403, CAPTCHA, empty results, page-layout errors, browser failures, or any other retryable outcome as a pass.
- Ignore open/social/wholesale platforms for elimination. Treat Amazon, Walmart, and eBay as marketplaces requiring review, not infringement proof.
- A brand/retailer domain is only a candidate. Open the landing page and compare the actual product before a high-risk conclusion.

## Error invariant

For 403, CAPTCHA, empty results, page-layout errors, or any exception, save screenshot, URL, timestamp, and error type before refresh, navigation, tab close, browser close, or retry. If the screenshot was not saved, the failure record is invalid.

Do not detect HTTP 403 by a loose substring such as `403.` in the whole result snapshot because product IDs and landing-page URLs can contain the same digits. Confirm a real Google error page from its error heading/body, response status, or missing-results state before recording `GOOGLE_403`.

- Use one or two products per browser micro-batch with a bounded 15–30 second interval. Rebuild the next queue from SQLite offer IDs after each micro-batch; never continue by a stale manifest index after a retry or partial success.
- Wait for the Google home page and either the accessible `Search by image` control or a validated fallback selector before upload. A missing control is a page-readiness error, not CAPTCHA.
- On one CDP navigation/screenshot timeout, discard the stale tab binding, create a fresh tab in the same browser, and retry only that offer. Do not restart the store or open parallel sessions to evade rate limits.
- Record a Google error only when the screenshot file actually exists. If browser capture fails, do not enqueue a fake screenshot path or write `05`; leave the product retryable/pending and record a local diagnostic until a valid screenshot can be captured before navigation.
- After a successful retry, retain prior error evidence for audit but mark it superseded/resolved and exclude it from active risk, failure counts, and current user-facing evidence.

## Outcomes

- Confirmed same/highly similar brand or known-retailer product: `RISK_STOPPED`; skip Amazon and all channel routes.
- Candidate or false-match uncertainty: `MANUAL_REVIEW`; Amazon may collect auxiliary data but no strong channel conclusion.
- No confirmed risk: `GOOGLE_DONE`.

Google Lens is an initial screen, never a guarantee of non-infringement. Write evidence to SQLite and Outbox only; do not write Feishu directly.
