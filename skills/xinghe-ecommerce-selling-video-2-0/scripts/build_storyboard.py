#!/usr/bin/env python3
"""Build a product-selling storyboard from a selling brief."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ALLOWED_CAPTION_MODES = {"voiceover_only", "sparse_stickers", "caption_driven", "no_readable_text"}
RISK_TERMS = [
    "100%", "永久", "治愈", "治疗", "医用", "抗菌", "抑菌", "第一", "最强", "全网最低",
    "guaranteed", "cure", "medical", "antibacterial", "certified", "best", "number one",
]


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("brief must be a JSON object")
    return data


def timeline_items(items: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict) and "start" in item and "end" in item:
                normalized = dict(item)
                normalized["start"] = float(item["start"])
                normalized["end"] = float(item["end"])
                result.append(normalized)
    return result


def overlapping_text(start: float, end: float, items: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for item in items:
        item_start = float(item.get("start", 0))
        item_end = float(item.get("end", 0))
        if max(0.0, min(end, item_end) - max(start, item_start)) > 0:
            text = str(item.get("text", "")).strip()
            if text:
                lines.append(text)
    return " / ".join(lines)


def validate_duration(shots: list[dict[str, Any]], duration: float) -> None:
    total = 0.0
    for index, shot in enumerate(shots, 1):
        start = float(shot.get("start", 0))
        end = float(shot.get("end", 0))
        if end <= start:
            raise ValueError(f"shot_plan[{index}] has invalid timing")
        total += end - start
    if abs(round(total, 3) - round(duration, 3)) > 0.01:
        raise ValueError(f"shot_plan duration must total {duration:g}s; got {total:g}s")


def find_risky_terms(text: str) -> list[str]:
    lowered = text.lower()
    found: list[str] = []
    for term in RISK_TERMS:
        token = term.lower()
        if re.fullmatch(r"[a-z0-9 -]+", token):
            if re.search(rf"\b{re.escape(token)}\b", lowered):
                found.append(term)
        elif token in lowered:
            found.append(term)
    return sorted(set(found))


def caption_mode(brief: dict[str, Any]) -> str:
    policy = brief.get("caption_layer_policy") if isinstance(brief.get("caption_layer_policy"), dict) else {}
    mode = str(policy.get("mode") or "").strip()
    if mode in ALLOWED_CAPTION_MODES:
        return mode
    voiceover = timeline_items(brief.get("adapted_voiceover"))
    return "sparse_stickers" if voiceover else "caption_driven"


def build_storyboard(brief: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    if brief.get("mode") != "product_selling_video":
        raise ValueError("brief.mode must be product_selling_video; reference remake briefs are not supported")
    shots = brief.get("shot_plan")
    if not isinstance(shots, list) or not shots:
        raise ValueError("brief.shot_plan must be a non-empty list")
    duration = float(brief.get("duration", 15))
    if duration < 4 or duration > 15:
        raise ValueError("duration must be between 4 and 15 seconds")
    validate_duration(shots, duration)
    voice = timeline_items(brief.get("adapted_voiceover"))
    text = timeline_items(brief.get("adapted_on_screen_text"))
    mode = caption_mode(brief)
    constraints = str(brief.get("product_identity_constraints") or "").strip()
    physical_constraints = str(brief.get("physical_scene_constraints") or "").strip()
    result_requirement = str(brief.get("must_show_result_frame") or "").strip()
    if not constraints:
        raise ValueError("product_identity_constraints must not be empty")
    warnings = list(brief.get("warnings") or [])
    panels: list[dict[str, Any]] = []
    for index, shot in enumerate(shots, 1):
        if not isinstance(shot, dict):
            raise ValueError(f"shot_plan[{index}] must be an object")
        start = float(shot["start"])
        end = float(shot["end"])
        voice_line = overlapping_text(start, end, voice)
        text_line = overlapping_text(start, end, text)
        combined = " ".join(str(v) for v in shot.values()) + " " + voice_line + " " + text_line
        risky = find_risky_terms(combined)
        if risky:
            warnings.append(f"Panel {index} contains proof-sensitive terms to review/remove: {', '.join(risky)}")
        panels.append({
            "panel": index,
            "time": {"start": start, "end": end, "duration": round(end - start, 3)},
            "story_purpose": shot.get("purpose", ""),
            "visual_composition": shot.get("visual", ""),
            "framing": shot.get("framing", ""),
            "camera_movement": shot.get("camera", ""),
            "product_action": shot.get("action", ""),
            "model_or_host_role": shot.get("model_or_host_role", ""),
            "sticker_overlay_intent": shot.get("sticker_overlay", ""),
            "sound_effect_intent": shot.get("sound_effect", ""),
            "voiceover": voice_line,
            "on_screen_text_intent": text_line,
            "caption_layer_policy": mode,
            "product_fidelity_constraint": shot.get("product_fidelity") or constraints,
            "physical_scene_constraint": shot.get("physical_scene") or physical_constraints,
            "space_anchor": shot.get("space_anchor", ""),
            "result_frame_requirement": shot.get("result_frame_requirement") or result_requirement,
            "single_action_rule": shot.get("single_action_rule", "Only one main action in this shot."),
            "continuity_note": "Keep product identity, physical contact, scale, camera direction, and scene anchors continuous across adjacent panels.",
            "risk_note": "No reference-video remake, no copied captions, no unsupported claims, no platform UI, no pure still-life rotation, no floating, no object intersection.",
        })
    storyboard = {
        "mode": "product_selling_video",
        "product_name": brief.get("product_name", ""),
        "platform": brief.get("platform", ""),
        "platform_name": brief.get("platform_name", ""),
        "category": brief.get("category", ""),
        "objective": f"Create a conversion-focused {brief.get('platform_name') or brief.get('platform')} ecommerce selling video for {brief.get('product_name')}.",
        "duration": duration,
        "ratio": brief.get("ratio", "9:16"),
        "resolution": brief.get("resolution", "480p"),
        "voiceover_language": brief.get("voiceover_language", "zh-CN"),
        "presenter_mode": brief.get("presenter_mode", ""),
        "result_showcase_type": brief.get("result_showcase_type", ""),
        "product_identity_locks": brief.get("product_identity_locks", []),
        "physical_scene_constraints": physical_constraints,
        "must_show_result_frame": result_requirement,
        "caption_layer_policy": {
            "mode": mode,
            "rule": "Use exactly one readable text layer. With voiceover, use sparse stickers or CTA labels, not line-by-line subtitles.",
        },
        "panels": panels,
        "negative_constraints": brief.get("negative_constraints", []),
        "warnings": warnings,
    }
    return storyboard, warnings


def markdown(storyboard: dict[str, Any]) -> str:
    lines = [
        f"# Product Selling Storyboard: {storyboard.get('product_name', '')}",
        "",
        f"Platform: {storyboard.get('platform_name') or storyboard.get('platform')}",
        f"Category: {storyboard.get('category')}",
        f"Duration: {storyboard.get('duration')}s",
        f"Ratio: {storyboard.get('ratio')}",
        "",
        "## Panels",
    ]
    for panel in storyboard["panels"]:
        time = panel["time"]
        lines.extend([
            "",
            f"### Panel {panel['panel']} | {time['start']:.2f}-{time['end']:.2f}s",
            f"- Purpose: {panel['story_purpose']}",
            f"- Visual: {panel['visual_composition']}",
            f"- Framing: {panel['framing']}",
            f"- Camera: {panel['camera_movement']}",
            f"- Action: {panel['product_action']}",
            f"- Model/host: {panel['model_or_host_role']}",
            f"- Sticker/overlay: {panel['sticker_overlay_intent']}",
            f"- Sound: {panel['sound_effect_intent']}",
            f"- Voiceover: {panel['voiceover']}",
            f"- Text intent: {panel['on_screen_text_intent']}",
            f"- Product fidelity: {panel['product_fidelity_constraint']}",
            f"- Physical scene: {panel['physical_scene_constraint']}",
            f"- Space anchors: {panel['space_anchor']}",
            f"- Must-show result: {panel['result_frame_requirement']}",
            f"- Single action: {panel['single_action_rule']}",
            f"- Risk: {panel['risk_note']}",
        ])
    lines.extend(["", "## Quality Gate", "- [ ] storyboard_sheet.png exists before paid generation", "- [ ] product image and storyboard sheet are both submitted", "- [ ] every panel has one clear action", "- [ ] at least three panels include person/hand action, real use, or completed result scene", "- [ ] no product drift, floating, clipping, impossible scale, or broken space continuity", "- [ ] no unsupported claims or duplicate subtitle layer"])
    if storyboard.get("warnings"):
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {warning}" for warning in storyboard["warnings"])
    return "\n".join(lines) + "\n"


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Build storyboard files from a product-selling brief")
    p.add_argument("--brief-json", required=True)
    p.add_argument("--output-dir", required=True)
    return p


def main() -> None:
    args = parser().parse_args()
    try:
        brief = load_json(Path(args.brief_json).expanduser().resolve())
        storyboard, warnings = build_storyboard(brief)
        out = Path(args.output_dir).expanduser().resolve()
        out.mkdir(parents=True, exist_ok=True)
        json_path = out / "storyboard.json"
        md_path = out / "storyboard.md"
        json_path.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")
        md_path.write_text(markdown(storyboard), encoding="utf-8")
        print(json.dumps({"ok": True, "storyboard_json": str(json_path), "storyboard_md": str(md_path), "warnings": warnings}, ensure_ascii=True, indent=2))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "stage": "storyboard", "error": str(exc)}, ensure_ascii=True, indent=2))
        raise SystemExit(2)


if __name__ == "__main__":
    main()
