---
name: image-host-upload
description: Upload explicitly reviewed local product images to a configured private image host over SSH and return public URLs. Use only after showing the exact files, target account, and target host and receiving current confirmation; do not infer standing consent from a listing workflow.
---

# Image Host Upload

Run `scripts/upload_images.sh` for uploads. The host settings live in `~/.config/codex/image-host.env`; this file contains only connection settings and references the existing SSH private key. Never print the private-key contents.

## Workflow

1. Confirm that each local image exists and that `IMAGE_HOST_SSH_HOST` is a real SSH-reachable public IP or hostname, not the public image URL unless that URL supports SSH.
2. Run `scripts/upload_images.sh --check` before the first upload in a task. Stop and report the SSH error if it fails.
3. Show the exact local file list, target account, SSH host, remote root, and public base URL. Obtain the user's current confirmation for that exact target and file set.
4. Upload only the confirmed local files:

   ```bash
   scripts/upload_images.sh /absolute/path/product-1.png /absolute/path/product-2.jpg
   ```

5. Return the printed HTTPS URLs. Uploaded files use a UUID-based name under `products/YYYY/MM/`, so existing images are not overwritten.

Use `--folder <safe-name>` only when the user requests another URL category. Do not delete or enumerate files on the host.

## Configuration

Keep the key at its local path and keep the configuration mode `600`. Required settings are `IMAGE_HOST_SSH_HOST`, `IMAGE_HOST_SSH_USER`, `IMAGE_HOST_SSH_KEY`, `IMAGE_HOST_REMOTE_ROOT`, and `IMAGE_HOST_PUBLIC_BASE_URL`.
