---
name: lc-1688-channel-closure
description: Operate, diagnose, migrate, or resume the persistent 1688 handbag workflow across Amazon and Walmart. Use for 1688统一导入、全链路恢复、迁移、渠道闭环或状态核对；do not use for generic Amazon selection, annual-goal supervision, a one-off handbag candidate study, or automatic marketplace publication.
---

# 1688 Multi-channel Closure

Use the installed `closurectl` as the first entry point. Run `closurectl doctor` before changing configuration and `closurectl status` before reporting progress.

## Authority and completion

- Resolve the active runtime from the closure configuration or `.selection-runtime-root`. The active Runtime SQLite database is authoritative; never replace it with a project-copy database.
- Reuse configured Feishu tables and stable task keys. Do not create replacement tables because a field or view is missing.
- Distinguish market analysis, production inputs, copy/images, workbook attachment readback, and manual platform acceptance. Empty tables, tests, manifests, `READY_FOR_SKILL`, and local files are not closure completion.
- Never call an Amazon or Walmart publish API. A generated workbook is always `待人工上传` until the operator records the real platform result.

## Route by task

- Read [references/architecture.md](references/architecture.md) when locating code, SQLite, Feishu, templates, or runtime state.
- Read [references/channels.md](references/channels.md) before changing brands, sites, accounts, templates, SKU namespaces, or shared assets.
- Read [references/gates.md](references/gates.md) before advancing a product, regenerating copy/images, handling IPR results, or claiming the workbook checkbox.
- Read [references/macmini.md](references/macmini.md) for installation, state export/import, watchdog control, and rollback.
- Read [references/troubleshooting.md](references/troubleshooting.md) for CAPTCHA, 403/429/5xx, parser drift, Feishu schema drift, missing templates, and failed attachment readback.

## Non-negotiable operating rules

- Preserve the existing Europe production state machine. UK and DE remain independent.
- Amazon brands are `Vocuer` or `BenPo bar`, with no default. Walmart brands are `StyleSack` or `Baguery`. Reject cross-platform brands and cross-brand assets.
- A production parent requires real `skuId + specId` children and dedicated variant images. Missing children may have a market result but cannot enter copy, image, or workbook production.
- Rufus demand research is brand-neutral. Listing renderers may read it; visual generation may not. Visual input is limited to verified facts, real source images, child mapping, platform/brand visual rules, and image revision requests.
- Require exactly one main image plus six secondary images for each real color. Share only neutral, fact-matched assets; derive any branded or localized image.
- IPR screening provides evidence for the operator. An attempted visible non-high result may be manually released; untouched/running tasks cannot. `HIGH`, `VERY_HIGH`, or `RISK_STOPPED` remains blocked.
- `生成上传表` is the only workbook switch. When unchecked, produce no workbook. Claim it once, clear it immediately, bind it to current hashes, and require a new check after material changes or platform errors.

## Mutation boundary

Read-only diagnosis and previews may run directly. Require the user's current explicit authorization before `closurectl run --apply`, state import, Feishu schema writes, workbook generation, or watchdog enablement. Installation must leave the watchdog paused by default.
