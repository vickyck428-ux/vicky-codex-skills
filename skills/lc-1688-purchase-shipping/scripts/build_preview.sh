#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 --manifest MANIFEST.json --output-dir DIR [--columns 4] [--page-size 12]" >&2
}

manifest=""
output_dir=""
columns=4
page_size=12

while [[ $# -gt 0 ]]; do
  case "$1" in
    --manifest)
      manifest="${2:-}"
      shift 2
      ;;
    --output-dir)
      output_dir="${2:-}"
      shift 2
      ;;
    --columns)
      columns="${2:-}"
      shift 2
      ;;
    --page-size)
      page_size="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "$manifest" || -z "$output_dir" ]]; then
  usage
  exit 2
fi
if ! [[ "$columns" =~ ^[1-9][0-9]*$ && "$page_size" =~ ^[1-9][0-9]*$ ]]; then
  echo "--columns and --page-size must be positive integers" >&2
  exit 2
fi

script_dir="$(cd "$(dirname "$0")" && pwd)"
manifest="$(cd "$(dirname "$manifest")" && pwd)/$(basename "$manifest")"
manifest_dir="$(dirname "$manifest")"
mkdir -p "$output_dir"
output_dir="$(cd "$output_dir" && pwd)"
cards_dir="$output_dir/单品截图"
pages_dir="$output_dir/分页预览"
mkdir -p "$cards_dir" "$pages_dir"

python3 "$script_dir/manifest_tool.py" validate "$manifest" --require-images >/dev/null

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required" >&2
  exit 2
fi
if [[ -n "${FFMPEG_BIN:-}" && -x "${FFMPEG_BIN}" ]]; then
  ffmpeg_bin="${FFMPEG_BIN}"
elif command -v ffmpeg >/dev/null 2>&1; then
  ffmpeg_bin="$(command -v ffmpeg)"
else
  echo "ffmpeg is required" >&2
  exit 2
fi

font_file=""
for candidate in \
  "/System/Library/Fonts/STHeiti Medium.ttc" \
  "/System/Library/Fonts/STHeiti Light.ttc" \
  "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"; do
  if [[ -f "$candidate" ]]; then
    font_file="$candidate"
    break
  fi
done
if [[ -z "$font_file" ]]; then
  echo "No CJK-capable font found" >&2
  exit 2
fi

temp_dir="$(mktemp -d)"
trap 'rm -rf "$temp_dir"' EXIT
cards=()

while IFS= read -r item_json; do
  index="$(jq -r '.source_index' <<<"$item_json")"
  status="$(jq -r '.purchase_status' <<<"$item_json")"
  quantity="$(jq -r '.ordered_qty' <<<"$item_json")"
  supplier="$(jq -r 'if (.supplier|length) > 24 then .supplier[0:24] + "…" else .supplier end' <<<"$item_json")"
  name="$(jq -r 'if (.product_name|length) > 25 then .product_name[0:25] + "…" else .product_name end' <<<"$item_json")"
  spec="$(jq -r 'if (.spec|length) > 32 then .spec[0:32] + "…" else .spec end' <<<"$item_json")"
  image_path="$(jq -r '.product_image' <<<"$item_json")"
  if [[ "$image_path" != /* ]]; then
    image_path="$manifest_dir/$image_path"
  fi

  item_temp="$temp_dir/$index"
  mkdir -p "$item_temp"
  printf '%s\n' "明细 $index  |  $status" >"$item_temp/header.txt"
  printf '%s\n' "$name" >"$item_temp/name.txt"
  printf '%s\n' "规格：$spec" >"$item_temp/spec.txt"
  printf '%s\n' "数量：$quantity" >"$item_temp/quantity.txt"
  printf '%s\n' "供应商：$supplier" >"$item_temp/supplier.txt"

  card_path="$cards_dir/${index}_商品卡.png"
  filter="scale=960:700:force_original_aspect_ratio=decrease,"
  filter+="pad=1000:1180:(ow-iw)/2:20:color=white,"
  filter+="drawbox=x=20:y=750:w=960:h=410:color=0xF5F5F5:t=fill,"
  filter+="drawtext=fontfile='${font_file}':textfile='${item_temp}/header.txt':fontcolor=0xD95F02:fontsize=34:x=50:y=780,"
  filter+="drawtext=fontfile='${font_file}':textfile='${item_temp}/name.txt':fontcolor=0x111111:fontsize=36:x=50:y=845,"
  filter+="drawtext=fontfile='${font_file}':textfile='${item_temp}/spec.txt':fontcolor=0x333333:fontsize=30:x=50:y=920,"
  filter+="drawtext=fontfile='${font_file}':textfile='${item_temp}/quantity.txt':fontcolor=0x111111:fontsize=34:x=50:y=995,"
  filter+="drawtext=fontfile='${font_file}':textfile='${item_temp}/supplier.txt':fontcolor=0x555555:fontsize=27:x=50:y=1070"

  "$ffmpeg_bin" -nostdin -hide_banner -loglevel error -y \
    -i "$image_path" -vf "$filter" -frames:v 1 "$card_path"
  cards+=("$card_path")
done < <(jq -c '.items[] | select(.include != false)' "$manifest")

if [[ ${#cards[@]} -eq 0 ]]; then
  echo "No included items found" >&2
  exit 1
fi

page_number=1
for ((start = 0; start < ${#cards[@]}; start += page_size)); do
  remaining=$((${#cards[@]} - start))
  count=$page_size
  if ((remaining < page_size)); then
    count=$remaining
  fi
  inputs=()
  filter_complex=""
  layout=""
  for ((offset = 0; offset < count; offset++)); do
    inputs+=(-i "${cards[$((start + offset))]}")
    filter_complex+="[$offset:v]scale=360:400:force_original_aspect_ratio=decrease,"
    filter_complex+="pad=360:400:(ow-iw)/2:(oh-ih)/2:color=white[c$offset];"
    x=$(((offset % columns) * 360))
    y=$(((offset / columns) * 400))
    if [[ -n "$layout" ]]; then
      layout+="|"
    fi
    layout+="${x}_${y}"
  done
  labels=""
  for ((offset = 0; offset < count; offset++)); do
    labels+="[c$offset]"
  done
  filter_complex+="${labels}xstack=inputs=${count}:layout=${layout}:fill=white[out]"
  page_path="$pages_dir/预览页_$(printf '%03d' "$page_number").jpg"
  "$ffmpeg_bin" -nostdin -hide_banner -loglevel error -y \
    "${inputs[@]}" -filter_complex "$filter_complex" -map "[out]" \
    -frames:v 1 -q:v 2 "$page_path"
  page_number=$((page_number + 1))
done

echo "Generated ${#cards[@]} product cards and $((page_number - 1)) preview pages in $output_dir"
