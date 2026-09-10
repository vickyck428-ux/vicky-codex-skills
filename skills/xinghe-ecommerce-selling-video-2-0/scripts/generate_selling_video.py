#!/usr/bin/env python3
"""Generate or dry-run a product-selling Seedance video with storyboard gate."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib import error, request
from urllib.parse import urlparse


BASE_URL = os.environ.get("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3").rstrip("/")
DEFAULT_MODEL = os.environ.get("ARK_SEEDANCE_MODEL", "doubao-seedance-2-0-fast-260128")
TASKS_PATH = "/contents/generations/tasks"
ALLOWED_RATIOS = {"21:9", "16:9", "4:3", "1:1", "3:4", "9:16", "adaptive"}
ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


class GenerationError(Exception):
    pass


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def api_key() -> str:
    key = os.environ.get("ARK_API_KEY")
    if not key and os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as env_key:
                key, _ = winreg.QueryValueEx(env_key, "ARK_API_KEY")
        except OSError:
            key = None
    if not key:
        raise GenerationError("ARK_API_KEY is not set. Configure it locally; never paste it into chat.")
    return key


def headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key()}", "Content-Type": "application/json"}


def request_json(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(BASE_URL + path, data=body, headers=headers(), method=method)
    try:
        with request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise GenerationError(f"HTTP {exc.code}: {detail}") from exc


def image_path_to_data_url(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def validate_image(path: Path, role: str) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise ValueError(f"{role} image not found: {resolved}")
    if resolved.suffix.lower() not in ALLOWED_IMAGE_SUFFIXES:
        raise ValueError(f"{role} image must be JPG, JPEG, PNG, or WebP: {resolved}")
    return resolved


def extract_nested(data: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str):
            return value
    nested = data.get("data")
    if isinstance(nested, dict):
        return extract_nested(nested, keys)
    return None


def extract_video_url(data: Any) -> str | None:
    if isinstance(data, dict):
        for key in ("video_url", "url", "output_url"):
            value = data.get(key)
            if isinstance(value, str) and value.startswith(("http://", "https://")):
                return value
        for value in data.values():
            found = extract_video_url(value)
            if found:
                return found
    elif isinstance(data, list):
        for value in data:
            found = extract_video_url(value)
            if found:
                return found
    return None


def output_path(output: str | None, output_dir: str | None, output_name: str | None, url: str) -> Path:
    if output:
        return Path(output).expanduser().resolve()
    directory = Path(output_dir or ".").expanduser().resolve()
    if output_name:
        name = output_name
    else:
        parsed = Path(urlparse(url).path).name or "xinghe_selling_video.mp4"
        name = parsed if parsed.lower().endswith(".mp4") else f"{parsed}.mp4"
    return directory / name


def download_url(url: str, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    req = request.Request(url, method="GET")
    try:
        with request.urlopen(req, timeout=300) as resp:
            output.write_bytes(resp.read())
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise GenerationError(f"Download HTTP {exc.code}: {detail}") from exc
    return output


def text_items(items: Any) -> str:
    if not isinstance(items, list):
        return ""
    lines: list[str] = []
    for item in items:
        if isinstance(item, dict):
            lines.append(f"{item.get('start')}-{item.get('end')}s: {item.get('text', '')}")
    return "\n".join(lines)


def build_prompt_from_brief(brief: dict[str, Any], storyboard: dict[str, Any] | None) -> str:
    if brief.get("mode") != "product_selling_video":
        raise ValueError("Only product_selling_video briefs are supported; reference remake is out of scope for this skill.")
    shots = brief.get("shot_plan")
    if not isinstance(shots, list) or not shots:
        raise ValueError("brief.shot_plan must be a non-empty list")
    duration = int(float(brief.get("duration", 15)))
    ratio = str(brief.get("ratio", "9:16"))
    if ratio not in ALLOWED_RATIOS:
        raise ValueError(f"Unsupported ratio: {ratio}")
    shot_lines: list[str] = []
    for index, shot in enumerate(shots, 1):
        shot_lines.append(
            "\n".join([
                f"Shot {index} | {shot.get('start')}-{shot.get('end')}s",
                f"Purpose: {shot.get('purpose', '')}",
                f"Visual: {shot.get('visual', '')}",
                f"Framing: {shot.get('framing', '')}",
                f"Camera: {shot.get('camera', '')}",
                f"Action: {shot.get('action', '')}",
                f"Model/hand role: {shot.get('model_or_host_role', '')}",
                f"Physical scene: {shot.get('physical_scene', brief.get('physical_scene_constraints', ''))}",
                f"Space anchors: {shot.get('space_anchor', '')}",
                f"Required result frame: {shot.get('result_frame_requirement', brief.get('must_show_result_frame', ''))}",
                f"Single action rule: {shot.get('single_action_rule', 'Only one main action in this shot.')}",
                f"Sticker/overlay: {shot.get('sticker_overlay', '')}",
                f"Sound cue: {shot.get('sound_effect', '')}",
                f"Product fidelity: {shot.get('product_fidelity', brief.get('product_identity_constraints', ''))}",
            ])
        )
    caption_policy = brief.get("caption_layer_policy") if isinstance(brief.get("caption_layer_policy"), dict) else {}
    voice_policy = brief.get("voiceover_policy") if isinstance(brief.get("voiceover_policy"), dict) else {}
    storyboard_note = (
        "Use the provided storyboard sheet as director guidance for shot order, composition, camera movement, product action, sticker placement, sound-cue intent, and CTA flow. "
        "Do not use the storyboard sheet as product identity; product photos override it for exact product appearance."
    )
    if storyboard and storyboard.get("panels"):
        storyboard_note += f" The storyboard has exactly {len(storyboard['panels'])} panels and must match the shot plan."
    return f"""Create one finished ecommerce product-selling short video.

Mode: product_selling_video only. Do not recreate or copy any reference video. Do not download, analyze, OCR, ASR, blueprint, or shot-match a reference video.
Product: {brief.get('product_name')}
Platform: {brief.get('platform_name') or brief.get('platform')}
Category: {brief.get('category')}
Duration: exactly {duration} seconds.
Ratio: {ratio}.
Resolution intent: {brief.get('resolution', '480p')}.
Audio intent: {'native voiceover enabled' if voice_policy.get('enabled', True) else 'music and natural product sounds only'}.
Voiceover style: {voice_policy.get('style', '')}
Caption layer policy: {caption_policy.get('mode', 'sparse_stickers')}. Use exactly one readable text layer. With voiceover, do not render line-by-line subtitles; use sparse stickers, feature badges, or CTA lockups only.

Product identity constraints:
{brief.get('product_identity_constraints', '')}

Product identity locks:
{json.dumps(brief.get('product_identity_locks', []), ensure_ascii=False)}

Physical scene constraints:
Presenter mode: {brief.get('presenter_mode', '')}
Result showcase type: {brief.get('result_showcase_type', '')}
Must-show result frame: {brief.get('must_show_result_frame', '')}
{brief.get('physical_scene_constraints', '')}

Human selling requirement:
This is a real ecommerce selling video, not a still-life product render. By default show a real anonymous adult presenter, fashion model, lifestyle model, hand model, or a real use scene with voiceover. At least three shots must contain a person/hand action, actual product use process, or completed result scene. Do not make a product-only rotation video.

Physics and space rules:
Use one main action per shot. Keep believable scale, contact, gravity, perspective, and scene continuity. Product must not float, pass through hands/body/furniture, change size, change color, change logo/label/pattern/material, or jump to a different physical space without a clear cut.

Storyboard sheet usage:
{storyboard_note}

Selling points:
{json.dumps(brief.get('selling_points', []), ensure_ascii=False)}

Shot timeline:
{chr(10).join(shot_lines)}

Voiceover script:
{text_items(brief.get('adapted_voiceover')) or 'No spoken voiceover requested.'}

On-screen text / sticker intent:
The following lines are production intent, not exact text to render. Do not render planning notes or instruction language as on-screen text. Render only concise user-provided selling points or platform CTA when provided; otherwise use non-readable graphic callouts.
{text_items(brief.get('adapted_on_screen_text'))}

Negative constraints:
{json.dumps(brief.get('negative_constraints', []), ensure_ascii=False)}

Final quality target: conversion-focused, real human selling feel, product-first but not static, clear first-second hook, visible use process, completed result frame, conservative claims, stable product appearance, physically correct space, no duplicate subtitle layer, no random text, no watermark, no platform UI.
"""


def build_content(prompt: str, product_images: list[Path], storyboard_images: list[Path]) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for path in product_images:
        content.append({"type": "image_url", "image_url": {"url": image_path_to_data_url(path)}, "role": "reference_image"})
    for path in storyboard_images:
        content.append({"type": "image_url", "image_url": {"url": image_path_to_data_url(path)}, "role": "reference_image"})
    return content


def generate(args: argparse.Namespace) -> dict[str, Any]:
    product_images = [validate_image(Path(p), "product") for p in (args.image_path or [])]
    storyboard_images = [validate_image(Path(p), "storyboard") for p in (args.storyboard_image or [])]
    if not product_images:
        raise ValueError("At least one --image-path product image is required.")
    if not storyboard_images and not args.allow_missing_storyboard:
        raise ValueError("A visual storyboard sheet is required. Pass --storyboard-image storyboard_sheet.png before paid generation.")
    brief = load_json(Path(args.brief_json).expanduser().resolve()) if args.brief_json else None
    storyboard = load_json(Path(args.storyboard_json).expanduser().resolve()) if args.storyboard_json else None
    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text(encoding="utf-8-sig")
    elif brief:
        prompt = build_prompt_from_brief(brief, storyboard)
    else:
        raise ValueError("Use --brief-json or --prompt-file.")
    ratio = args.ratio or (str(brief.get("ratio")) if brief else "9:16")
    duration = int(float(args.duration or (brief.get("duration") if brief else 15)))
    resolution = args.resolution or (str(brief.get("resolution")) if brief else "480p")
    output_dir = Path(args.output_dir or ".").expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = output_dir / "seedance_selling_prompt.txt"
    manifest_path = output_dir / "generation_manifest.json"
    prompt_path.write_text(prompt, encoding="utf-8")
    manifest = {
        "mode": "product_selling_video",
        "dry_run": args.dry_run,
        "model": args.model,
        "ratio": ratio,
        "resolution": resolution,
        "duration": duration,
        "prompt_path": str(prompt_path),
        "product_images": [str(p) for p in product_images],
        "storyboard_images": [str(p) for p in storyboard_images],
        "brief_json": str(Path(args.brief_json).expanduser().resolve()) if args.brief_json else None,
        "storyboard_json": str(Path(args.storyboard_json).expanduser().resolve()) if args.storyboard_json else None,
        "warnings": [],
    }
    if args.dry_run:
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return {**manifest, "manifest_path": str(manifest_path)}
    payload: dict[str, Any] = {
        "model": args.model,
        "content": build_content(prompt, product_images, storyboard_images),
        "ratio": ratio,
        "resolution": resolution,
        "duration": duration,
        "generate_audio": args.generate_audio,
    }
    submitted = request_json("POST", TASKS_PATH, payload)
    task_id = extract_nested(submitted, ("id", "task_id", "taskId"))
    if not task_id:
        raise GenerationError(f"Task id not found in response: {json.dumps(submitted, ensure_ascii=False)}")
    deadline = time.time() + args.timeout
    final: dict[str, Any] | None = None
    while True:
        data = request_json("GET", f"{TASKS_PATH}/{task_id}")
        status = (extract_nested(data, ("status", "state")) or "unknown").lower()
        print(json.dumps({"task_id": task_id, "status": status}, ensure_ascii=False), file=sys.stderr)
        if status in {"succeeded", "success", "completed", "failed", "cancelled", "canceled"}:
            final = data
            break
        if time.time() >= deadline:
            raise GenerationError(f"Timed out while polling task {task_id}. Last status: {status}")
        time.sleep(args.interval)
    video_url = extract_video_url(final)
    manifest.update({"task_id": task_id, "result": final, "video_url": video_url})
    if video_url:
        save_to = output_path(args.output, args.output_dir, args.output_name, video_url)
        saved = download_url(video_url, save_to)
        manifest.update({"saved": str(saved), "bytes": saved.stat().st_size})
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {**manifest, "manifest_path": str(manifest_path)}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Generate a product-selling Seedance video with storyboard gate")
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument("--brief-json")
    source.add_argument("--prompt-file")
    p.add_argument("--storyboard-json")
    p.add_argument("--image-path", action="append")
    p.add_argument("--storyboard-image", action="append")
    p.add_argument("--allow-missing-storyboard", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--ratio", choices=sorted(ALLOWED_RATIOS))
    p.add_argument("--resolution", choices=["480p", "720p", "1080p", "2K"])
    p.add_argument("--duration", type=int)
    p.add_argument("--generate-audio", dest="generate_audio", action="store_true")
    p.add_argument("--no-generate-audio", dest="generate_audio", action="store_false")
    p.set_defaults(generate_audio=True)
    p.add_argument("--interval", type=int, default=30)
    p.add_argument("--timeout", type=int, default=900)
    p.add_argument("--output")
    p.add_argument("--output-dir")
    p.add_argument("--output-name")
    return p


def main() -> None:
    args = parser().parse_args()
    try:
        result = generate(args)
        print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))
    except (OSError, ValueError, json.JSONDecodeError, GenerationError) as exc:
        print(json.dumps({"ok": False, "stage": "generate_selling_video", "error": str(exc)}, ensure_ascii=False, indent=2))
        raise SystemExit(2)


if __name__ == "__main__":
    main()
