#!/usr/bin/env bash
set -euo pipefail

CONFIG_FILE="${IMAGE_HOST_CONFIG:-$HOME/.config/codex/image-host.env}"
FOLDER="products"

usage() {
  printf 'Usage: %s [--check] [--folder safe-name] <image> [image ...]\n' "$0" >&2
  exit 2
}

CHECK_ONLY=0
while (($#)); do
  case "$1" in
    --check) CHECK_ONLY=1; shift ;;
    --folder) (($# >= 2)) || usage; FOLDER="$2"; shift 2 ;;
    --help|-h) usage ;;
    --*) usage ;;
    *) break ;;
  esac
done

[[ -f "$CONFIG_FILE" ]] || { printf 'Missing config: %s\n' "$CONFIG_FILE" >&2; exit 1; }
case "$FOLDER" in
  *[!A-Za-z0-9_-]*|'') printf 'Invalid folder name: %s\n' "$FOLDER" >&2; exit 2 ;;
esac

while IFS='=' read -r key value; do
  value="${value%$'\r'}"
  case "$key" in
    IMAGE_HOST_SSH_HOST|IMAGE_HOST_SSH_USER|IMAGE_HOST_SSH_KEY|IMAGE_HOST_REMOTE_ROOT|IMAGE_HOST_PUBLIC_BASE_URL)
      printf -v "$key" '%s' "$value"
      ;;
  esac
done < "$CONFIG_FILE"

for key in IMAGE_HOST_SSH_HOST IMAGE_HOST_SSH_USER IMAGE_HOST_SSH_KEY IMAGE_HOST_REMOTE_ROOT IMAGE_HOST_PUBLIC_BASE_URL; do
  [[ -n "${!key:-}" ]] || { printf 'Missing %s in %s\n' "$key" "$CONFIG_FILE" >&2; exit 1; }
done

[[ -f "$IMAGE_HOST_SSH_KEY" ]] || { printf 'SSH key not found: %s\n' "$IMAGE_HOST_SSH_KEY" >&2; exit 1; }
[[ "$IMAGE_HOST_REMOTE_ROOT" =~ ^/[A-Za-z0-9._/-]+$ ]] || { printf 'Invalid IMAGE_HOST_REMOTE_ROOT\n' >&2; exit 1; }
[[ "$IMAGE_HOST_SSH_USER" =~ ^[A-Za-z_][A-Za-z0-9_-]*$ ]] || { printf 'Invalid IMAGE_HOST_SSH_USER\n' >&2; exit 1; }

SSH_TARGET="${IMAGE_HOST_SSH_USER}@${IMAGE_HOST_SSH_HOST}"
SSH_OPTS=(-i "$IMAGE_HOST_SSH_KEY" -o BatchMode=yes -o StrictHostKeyChecking=accept-new)

if ((CHECK_ONLY)); then
  ssh "${SSH_OPTS[@]}" -- "$SSH_TARGET" "test -d '$IMAGE_HOST_REMOTE_ROOT' && test -w '$IMAGE_HOST_REMOTE_ROOT'"
  printf 'Image host SSH connection and write access are ready.\n'
  exit 0
fi

(($#)) || usage

year="$(date +%Y)"
month="$(date +%m)"
remote_dir="${IMAGE_HOST_REMOTE_ROOT%/}/${FOLDER}/${year}/${month}"
relative_dir="${FOLDER}/${year}/${month}"
ssh "${SSH_OPTS[@]}" -- "$SSH_TARGET" "mkdir -p '$remote_dir'"

base_url="${IMAGE_HOST_PUBLIC_BASE_URL%/}"
for image in "$@"; do
  [[ -f "$image" ]] || { printf 'Image not found: %s\n' "$image" >&2; exit 1; }
  extension="${image##*.}"
  extension="$(printf '%s' "$extension" | tr '[:upper:]' '[:lower:]')"
  case "$extension" in
    jpg|jpeg|png|webp|gif|avif|svg) ;;
    *) printf 'Unsupported image extension: %s\n' "$image" >&2; exit 2 ;;
  esac
  filename="$(uuidgen | tr '[:upper:]' '[:lower:]').${extension}"
  remote_path="${remote_dir}/${filename}"
  scp "${SSH_OPTS[@]}" -- "$image" "${SSH_TARGET}:${remote_path}"
  printf '%s/%s/%s\n' "$base_url" "$relative_dir" "$filename"
done
