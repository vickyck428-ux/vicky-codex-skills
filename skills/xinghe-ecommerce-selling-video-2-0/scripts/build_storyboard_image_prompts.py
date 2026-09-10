#!/usr/bin/env python3
"""Create one visual storyboard sheet prompt for product-selling videos."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("storyboard JSON must be an object")
    return data


def layout_for_count(count: int) -> tuple[str, str]:
    cols = count if count <= 4 else 3 if count <= 6 else 4
    rows = math.ceil(count / cols)
    size = "2048x1536" if cols >= rows else "1536x2048"
    return f"{cols} columns x {rows} rows", size


def short(value: Any, limit: int = 140) -> str:
    text = str(value or "").replace("\n", " ").strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "..."


def build_prompt(storyboard: dict[str, Any]) -> tuple[str, str]:
    panels = storyboard.get("panels")
    if not isinstance(panels, list) or not panels:
        raise ValueError("storyboard.panels must be a non-empty list")
    layout, size = layout_for_count(len(panels))
    caption_policy = storyboard.get("caption_layer_policy") if isinstance(storyboard.get("caption_layer_policy"), dict) else {}
    lines: list[str] = []
    for panel in panels:
        time = panel.get("time", {}) if isinstance(panel.get("time"), dict) else {}
        lines.append("\n".join([
            f"Frame {panel.get('panel')}: {time.get('start')}-{time.get('end')}s",
            f"Purpose: {short(panel.get('story_purpose'), 90)}",
            f"Visual: {short(panel.get('visual_composition'), 160)}",
            f"Framing/camera: {short(panel.get('framing'), 80)} / {short(panel.get('camera_movement'), 80)}",
            f"Action: {short(panel.get('product_action'), 120)}",
            f"Model or hand role: {short(panel.get('model_or_host_role'), 100)}",
            f"Physical contact: {short(panel.get('physical_scene_constraint'), 140)}",
            f"Space anchors: {short(panel.get('space_anchor'), 120)}",
            f"Required result: {short(panel.get('result_frame_requirement'), 120)}",
            f"Sticker/text: {short(panel.get('sticker_overlay_intent') or panel.get('on_screen_text_intent'), 120)}",
            f"Voiceover: {short(panel.get('voiceover'), 100)}",
            f"Sound: {short(panel.get('sound_effect_intent'), 80)}",
        ]))
    prompt = f"""Create one single director storyboard sheet image for a product-selling ecommerce short video.

Target canvas size: {size}. Arrange exactly {len(panels)} frame cells in reading order using a clean {layout} grid. This is one storyboard sheet, not separate images.

Product: {storyboard.get('product_name')}
Platform: {storyboard.get('platform_name') or storyboard.get('platform')}
Category: {storyboard.get('category')}
Video ratio: {storyboard.get('ratio')}
Objective: {storyboard.get('objective')}

Style: polished ecommerce previsualization, clean director storyboard, product-first composition, clear lighting, readable shot notes, no platform UI, no watermark. Product photos are the only true product identity source. This storyboard sheet only plans camera, action, physical space, contact relationship, composition, sticker placement, sound cues, voiceover intent, result frame, and CTA flow. Do not redesign the product in the storyboard sheet.

Readable text policy: {caption_policy.get('mode', 'sparse_stickers')}. {caption_policy.get('rule', 'Use exactly one readable text layer.')} Show sparse stickers or CTA labels only; do not show line-by-line subtitles unless caption_driven mode is selected.

Frame cells:
{chr(10).join(lines)}

Sheet requirements:
- One cell per panel, exactly {len(panels)} cells.
- Show panel number and timecode in each cell.
- Show product location, action, framing, camera direction, text/sticker zone, and CTA.
- Mark the person/hand role, physical contact relationship, space anchors, and required result frame in every cell.
- Keep product color, shape, packaging, label position, material, accessories, size ratio, and visible structure consistent across all cells.
- Keep physical space coherent: stable bed/table/floor/wall/furniture/body anchors, correct perspective, believable scale, no floating, no clipping, no product passing through hands/body/furniture.
- At least three cells must show a real person, hand model, actual use action, or completed result scene. Do not make a product-only still-life rotation sheet.
- If people appear, use anonymous adult lifestyle model or hand model only; do not imply face identity matching or celebrity likeness.
- Do not add unsupported medical, safety, ranking, certification, price, discount, patent, or warranty claims.
- Do not make a reference-video remake or copied style sheet.
"""
    return prompt, size


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Build a storyboard sheet prompt")
    p.add_argument("--storyboard-json", required=True)
    p.add_argument("--output-dir", required=True)
    return p


def main() -> None:
    args = parser().parse_args()
    try:
        storyboard = load_json(Path(args.storyboard_json).expanduser().resolve())
        prompt, size = build_prompt(storyboard)
        out = Path(args.output_dir).expanduser().resolve()
        out.mkdir(parents=True, exist_ok=True)
        txt = out / "storyboard_sheet_prompt.txt"
        js = out / "storyboard_sheet_prompt.json"
        txt.write_text(prompt, encoding="utf-8")
        js.write_text(json.dumps({"prompt": prompt, "suggested_filename": "storyboard_sheet.png", "suggested_size": size}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"ok": True, "prompt_path": str(txt), "json_path": str(js), "suggested_size": size}, ensure_ascii=True, indent=2))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "stage": "storyboard_sheet_prompt", "error": str(exc)}, ensure_ascii=True, indent=2))
        raise SystemExit(2)


if __name__ == "__main__":
    main()
