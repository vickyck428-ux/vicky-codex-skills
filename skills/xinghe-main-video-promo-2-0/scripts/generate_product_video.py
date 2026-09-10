#!/usr/bin/env python3
"""Unified all-category ecommerce product-video entry point."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

from ark_seedance_api import ArkError, DEFAULT_MODEL, generate_video
from build_product_promo_prompt import CATEGORIES, CINEMATIC_LEVELS, MODEL_PRESENCE, PLATFORMS, VOICEOVER_LANGUAGES, resolved_args, write_artifacts


def checklist_text(manifest: dict, result: dict | None) -> str:
    audio_status = "silent" if not manifest["generate_audio"] else ("voiceover + premium music/sfx" if manifest["voiceover"] else "premium music/sfx only")
    task_status = result["status"] if result else "dry-run, no paid generation submitted"
    return f"""# Human Review Checklist

- [ ] Product shape, proportions, color, and material match the first primary reference image.
- [ ] Logo position, package structure, label layout, and printed text placement remain unchanged.
- [ ] No invented accessories, brands, text, prices, promotional badges, or platform UI appear.
- [ ] Product handling matches the real visible structure, with no dangerous or impossible operation.
- [ ] Storyboard shots are coherent, premium camera movement is stable, and the product does not duplicate, deform, flicker, or disappear.
- [ ] Voiceover language is {manifest['voiceover_language']} and mentions only visible facts or user-supplied selling points.
- [ ] No invented efficacy, specifications, certifications, rankings, guarantees, or promises appear.
- [ ] Music and sound design feel premium, with no lyrics, sung vocals, or hard-sell delivery.
- [ ] The video fits {manifest['platform']} and uses the {manifest['ratio']} ratio.

Task status: {task_status}
Audio status: {audio_status}

If review fails, let the user decide whether to regenerate. Suggested fixes: provide a clearer primary image, reduce actions, add detail views, specify the category, use --input-json, disable voiceover, or disable audio. The skill must not retry automatically.
"""


def xinghe_helper_path() -> Path:
    configured = os.environ.get("XINGHE_IMAGE_GENERATOR")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(os.environ.get("LOCALAPPDATA", "")) / "ApiCodexOneClick" / "tools" / "generate-image.ps1"


def write_manifest(manifest: dict) -> None:
    Path(manifest["manifest_path"]).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def try_generate_storyboard_image(manifest: dict, output_dir: Path) -> tuple[bool, dict]:
    helper = xinghe_helper_path()
    target = output_dir / manifest.get("storyboard_image_output_name", "director-storyboard.png")
    if not helper.is_file():
        return False, {
            "storyboard_image_status": "needs_imagegen_fallback",
            "storyboard_image_target_path": str(target),
            "storyboard_image_error": f"Xinghe image helper not found: {helper}",
        }
    command = [
        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(helper),
        "-PromptFile", manifest["storyboard_image_prompt_path"],
        "-ReferenceImage", *[item["path"] for item in manifest["images"] if not item["role"].startswith("storyboard_reference")],
        "-OutputDir", str(output_dir),
        "-Size", "1536x1024",
        "-FileName", target.name,
    ]
    try:
        completed = subprocess.run(command, text=True, capture_output=True, timeout=900)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, {
            "storyboard_image_status": "needs_imagegen_fallback",
            "storyboard_image_target_path": str(target),
            "storyboard_image_error": f"Xinghe image helper failed to run: {exc}",
        }
    if completed.returncode != 0:
        return False, {
            "storyboard_image_status": "needs_imagegen_fallback",
            "storyboard_image_target_path": str(target),
            "storyboard_image_error": completed.stderr.strip() or completed.stdout.strip() or "Xinghe image helper returned a non-zero exit code",
        }
    if not target.is_file():
        return False, {
            "storyboard_image_status": "needs_imagegen_fallback",
            "storyboard_image_target_path": str(target),
            "storyboard_image_error": f"Xinghe image helper completed but did not create {target}",
        }
    return True, {
        "storyboard_image_status": "xinghe_generated",
        "storyboard_image_path": str(target),
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Generate one stable all-category ecommerce main video")
    p.add_argument("--input-json", help="UTF-8 JSON input file. CLI arguments override matching JSON fields.")
    p.add_argument("--product-name")
    p.add_argument("--image-path", action="append")
    p.add_argument("--storyboard-image-path", action="append")
    p.add_argument("--image-notes")
    p.add_argument("--selling-points")
    p.add_argument("--audience")
    p.add_argument("--platform")
    p.add_argument("--category", choices=["auto", *CATEGORIES])
    p.add_argument("--resolution", choices=["480p", "720p", "1080p", "2K"])
    p.add_argument("--duration", type=int, choices=[15])
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--output-dir")
    p.add_argument("--output-name", default="xinghe-main-video-promo-2-0.mp4")
    p.add_argument("--interval", type=int, default=30)
    p.add_argument("--timeout", type=int, default=900)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--voiceover-language", choices=VOICEOVER_LANGUAGES)
    p.add_argument("--voiceover-style")
    p.add_argument("--voiceover-script")
    p.add_argument("--cinematic-level", choices=CINEMATIC_LEVELS)
    p.add_argument("--model-presence", choices=MODEL_PRESENCE)
    p.add_argument("--storyboard-file")
    p.add_argument("--benchmark-style-notes")
    p.add_argument("--storyboard-only", action="store_true")
    p.add_argument("--generate-storyboard-image", action="store_true")
    p.add_argument("--storyboard-image-output-name", default="director-storyboard.png")
    audio = p.add_mutually_exclusive_group()
    audio.add_argument("--generate-audio", dest="generate_audio", action="store_true")
    audio.add_argument("--no-generate-audio", dest="generate_audio", action="store_false")
    voice = p.add_mutually_exclusive_group()
    voice.add_argument("--voiceover", dest="voiceover", action="store_true")
    voice.add_argument("--no-voiceover", dest="voiceover", action="store_false")
    p.set_defaults(generate_audio=None, voiceover=None)
    return p


def main() -> None:
    raw_args = build_parser().parse_args()
    output_dir = Path(raw_args.output_dir or ".").resolve()
    result_path = output_dir / "seedance-result.json"
    checklist_path = output_dir / "seedance-review-checklist.md"
    try:
        args = resolved_args(raw_args)
        output_dir = Path(args.output_dir).resolve()
        result_path = output_dir / "seedance-result.json"
        checklist_path = output_dir / "seedance-review-checklist.md"
        manifest = write_artifacts(args)
        blocked_for_storyboard_image = False
        if args.generate_storyboard_image and not args.storyboard_image_path:
            ok, storyboard_update = try_generate_storyboard_image(manifest, output_dir)
            if ok:
                args = argparse.Namespace(**{**vars(args), "storyboard_image_path": [storyboard_update["storyboard_image_path"]]})
                manifest = write_artifacts(args)
                manifest.update(storyboard_update)
                write_manifest(manifest)
            else:
                manifest.update(storyboard_update)
                write_manifest(manifest)
                blocked_for_storyboard_image = True
        result = None
        if not raw_args.dry_run and not raw_args.storyboard_only and not blocked_for_storyboard_image:
            result = generate_video(prompt=Path(manifest["prompt_path"]).read_text(encoding="utf-8"),
                                    image_paths=[Path(item["path"]) for item in manifest["images"]],
                                    output=output_dir / raw_args.output_name, model=raw_args.model, ratio=manifest["ratio"],
                                    resolution=args.resolution, duration=args.duration, generate_audio=args.generate_audio,
                                    interval=raw_args.interval, timeout=raw_args.timeout)
        payload = {"ok": True, "dry_run": raw_args.dry_run or raw_args.storyboard_only or blocked_for_storyboard_image,
                   "storyboard_only": raw_args.storyboard_only, "manifest": manifest, "generation": result,
                   "blocked_for_storyboard_image": blocked_for_storyboard_image,
                   "checklist_path": str(checklist_path)}
        output_dir.mkdir(parents=True, exist_ok=True)
        checklist_path.write_text(checklist_text(manifest, result), encoding="utf-8")
        result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({**payload, "result_path": str(result_path)}, ensure_ascii=True, indent=2))
    except (ValueError, ArkError, OSError) as exc:
        error_payload = exc.as_dict() if isinstance(exc, ArkError) else {"ok": False, "stage": "preflight", "error": str(exc)}
        output_dir.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(error_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({**error_payload, "result_path": str(result_path)}, ensure_ascii=True, indent=2))
        raise SystemExit(2)


if __name__ == "__main__":
    main()
