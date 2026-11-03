---
name: github-skill-safe-sync
description: Safely inspect and synchronize all Codex skills from Vicky's and Laochen's GitHub repositories into the current machine or Harness skill root. Use for scheduled checks, installations, updates, rollback, or cross-machine consistency checks for these two repositories.
---

# GitHub Skill Safe Sync

Synchronize the complete `skills/` inventories from these repositories:

- `https://github.com/vickyck428-ux/vicky-codex-skills` (`main`)
- `https://github.com/chenqinglin2019-tech/Laochen-Amazon-project` (`main`)

Treat each repository's actual top-level directories under `skills/` containing
`SKILL.md` as authoritative. Do not rely on README inventories. The two
repositories currently have no overlapping skill directory names; re-check this
on every run and stop conflicting names for review instead of choosing a winner.

## Target discovery

Resolve the skill root from the runtime that will consume the skills. Prefer
`$CODEX_HOME/skills` when `CODEX_HOME` is set, otherwise use `~/.codex/skills`.
For Harness, inspect its configuration or container mounts and update the actual
mounted skill root. Do not assume `/root/config`, `/root/.codex/skills`, and a
macOS user's `.codex/skills` are the same directory. If two consumers resolve to
the same real path, update it once.

## Local edits take precedence

Before comparing or replacing any installed skill, read
`<CODEX_HOME>/skill-sync-policy/protected-skills.json` (default
`~/.codex/skill-sync-policy/protected-skills.json`). This policy is outside the
replaceable skill tree and must never be reset from an upstream checkout.

- `walmart-out-of-stock-copy` and `github-skill-safe-sync` are locally protected.
  Keep their entire installed trees when upstream differs; report a held local
  customization, not a repaired drift. Never auto-unprotect them or treat an
  upstream commit advance as authorization to discard local edits.
- On the local host, run `python3 <CODEX_HOME>/skill-sync-policy/check_candidate.py
  --skill NAME --installed INSTALLED_DIR --candidate STAGED_DIR` before each
  replacement. A nonzero exit blocks that skill. Missing or invalid policy or
  guard blocks writes until resolved. The guard is read-only.
- On other hosts, apply the same protected-name hold even if the local guard is
  unavailable; do not overwrite these skills. Do not copy macOS paths into a
  remote runtime.
- For other skills, distinguish upstream changes from local edits using the last
  successfully installed upstream baseline. Upstream unchanged plus local
  difference means KEEP LOCAL. Both sides changed means stage a three-way merge
  and retain local until conflicts are resolved and validated. Without a reliable
  baseline, hold differing existing files instead of assuming upstream wins.
- Normal sync must not rewrite the protection policy, guard, or snapshots.
  Removing protection requires an explicit user request. Future authorized edits
  to a protected skill remain protected even when snapshot hashes change.

## First-time protection setup

Only during an explicitly authorized setup or repair, copy
`scripts/check_candidate.py` and `scripts/protected-skills.json` to the consuming
runtime's `<CODEX_HOME>/skill-sync-policy/` directory. Preserve any existing
policy entries; never reset an existing policy during routine synchronization.
Validate the guard using `python3 scripts/test_guard.py` before installing it.
The guard and policy live outside the replaceable skill directory. This initial
setup is distinct from normal sync, which must stop writes if protection is
missing. An explicitly authorized migration may install the user-confirmed
version after backup, then protect it from future automatic replacements.

## Safe synchronization

1. Fetch both default branches and record each exact commit SHA. Enumerate every
   top-level skill directory containing `SKILL.md`.
2. Apply the local-edit protection rules above, then compare the candidate subtree
   with the installed subtree. If content is
   unchanged, make no write and produce no routine notification.
3. Stage each changed or missing skill separately. Never delete unrelated or
   local-only skills.
4. Preserve local secrets, credentials, runtime dependencies, and user-created
   data. This includes `.env`, `.env.local`, `config.json`,
   `config.local.json`, `design_templates.user.json`, `node_modules`, browser
   runtimes, caches, and run/output directories when present. Never print secret
   values. Upstream examples may be refreshed; real local values must survive.
5. Validate the staged skill before installation: parse YAML frontmatter and
   JSON/YAML assets, compile Python where applicable, and run the narrowest
   repository-provided test suite. Reuse preserved runtime dependencies when
   needed, but do not perform live generation, authentication, marketplace
   writes, purchases, listing publication, or other production actions.
6. A failing skill is isolated: keep its installed version, record the failed
   candidate commit and concise failure, and continue checking the other skills.
7. For every passing changed skill permitted by the local-edit guard, make a timestamped rollback copy under
   `<skill-root>/.backups/`, then replace the subtree atomically and restore the
   preserved local files. Verify the installed tree and imports after replacement.
8. Keep distinct skills distinct even when their purpose is related. In
   particular, `lc-amazon-listing-asin` and `lc_amazon_listing` are separate
   upstream directories and may coexist.

Do not silently rename legacy upstream skills whose frontmatter uses underscores
or non-kebab-case names. Report the validator warning and preserve the upstream
directory/name until the repository owner changes it.

## Scheduled-run report

Stay quiet when both commit SHAs and all installed subtrees are unchanged.
Notify only when a skill was installed or updated, a validation failed, a name
conflict appeared, credentials blocked a fetch, or user action is required.
Include the host, skill root, both commit SHAs, updated/new/held lists, backup
locations, and test summary without exposing credentials.
