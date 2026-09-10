# Mac mini installation and recovery

## Install

1. Verify the archive and sidecar SHA-256 with `closurectl package verify <archive>`.
2. Run `deploy/install.command`. It installs versioned code, sanitized configuration, templates, and Skills under the target user's home.
3. Configure secrets through macOS Keychain and authorize `lark-cli`; never copy plaintext secrets into the package.
4. The installer installs the single watchdog definition but leaves it disabled and unloaded.

## State transfer

- Export with `closurectl state export --output-dir <dir>`. The AES-256 DMG password is stored under Keychain service `LC_1688_STATE_MIGRATION_KEY` unless supplied interactively.
- Import with `closurectl state import --dmg <file>`. Import verifies the sidecar hash, every internal file hash, SQLite integrity, and foreign keys.
- Import stops and disables the watchdog, backs up the destination database and runs, rewrites the old Runtime root to the target Runtime root, and leaves automation paused.

## Acceptance and enablement

Run `closurectl doctor`, `closurectl status`, a dry run, and one real multi-child Amazon US/Walmart pilot. Confirm the unchecked workbook gate creates no workbook and the checked gate produces an attachment that reads back byte-identically. Only then run `closurectl watchdog enable`.

Rollback uses the timestamped Runtime import backup. Do not copy browser profiles, cookies, API keys, `.venv`, `node_modules`, logs, or stale workbooks between Macs.
