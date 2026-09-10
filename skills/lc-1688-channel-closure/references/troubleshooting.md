# Troubleshooting

- `AMAZON_REFERENCE_CRAWLER_HASH_MISMATCH`: stop. Validate the crawler syntax, doctor, and cascade dry-run; update the dependency lock only for the verified bytes.
- CAPTCHA, 403, abnormal traffic, or login wall: save URL/time/evidence, open the affected site's circuit breaker, and continue other sites. Do not bypass, rotate proxies, or retry the hard block in the same run.
- Timeout, 429, 500, 502, 503: use the configured single retry and then persist a retryable result/checkpoint.
- Parser or source-page drift: keep the source item blocked; do not invent children, images, or facts.
- Feishu field drift: resolve the existing table, add only missing managed fields idempotently, and refuse ambiguous or incompatible fields. Never create a replacement table silently.
- Missing template/account: block only the exact brand-site workbook route. Do not fall back across brand or site.
- Attachment readback failure: keep the workbook unaccepted, preserve the prior attachment, and require a new final checkbox after correction.
- `READY_FOR_SKILL`: queued external production only. Check actual copy/image outputs, hashes, attachments, and manual platform result before reporting completion.
