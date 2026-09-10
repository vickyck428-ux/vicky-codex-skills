#!/usr/bin/env python3
"""Deterministic routing, validation, JSON input, and prompt construction."""

from __future__ import annotations

import argparse
import json
import re
import struct
from pathlib import Path
from typing import Any

PLATFORMS = {
    "generic": ("1:1", "centered product, safe crop, immediate ecommerce clarity"),
    "taobao": ("1:1", "polished product clarity for a Taobao main video"),
    "tmall": ("1:1", "premium controlled brand presentation for Tmall"),
    "jd": ("1:1", "trustworthy feature clarity for JD"),
    "pinduoduo": ("1:1", "immediate product recognition and simple action for Pinduoduo"),
    "douyin": ("9:16", "first-frame motion, fast reveal, vertical safe-center composition for Douyin"),
    "xiaohongshu": ("9:16", "natural lifestyle texture and vertical safe-center composition for Xiaohongshu"),
    "amazon": ("16:9", "trustworthy Amazon product video style: clear product proof, honest use context, clean inspection-friendly framing"),
    "tiktok-shop": ("9:16", "mobile-first TikTok Shop product video style: immediate product recognition, strong first-frame motion, safe-center vertical framing"),
    "shopify": ("1:1", "brand-owned Shopify product-page media style: refined product story, reusable product-page framing, calm premium credibility"),
    "aliexpress": ("1:1", "AliExpress product video style: fast product understanding, visible details, accessories, scale, and practical use context"),
    "temu": ("1:1", "Temu product video style: immediate product recognition, clear value perception, simple action, and no price or promo graphics"),
}

DOMESTIC_PLATFORMS = {"generic", "taobao", "tmall", "jd", "pinduoduo", "douyin", "xiaohongshu"}
CROSSBORDER_PLATFORMS = {"amazon", "tiktok-shop", "shopify", "aliexpress", "temu"}

PLATFORM_ALIASES = {
    "general": "generic",
    "通用": "generic",
    "淘宝": "taobao",
    "tao bao": "taobao",
    "天猫": "tmall",
    "京东": "jd",
    "jingdong": "jd",
    "拼多多": "pinduoduo",
    "pdd": "pinduoduo",
    "抖音": "douyin",
    "douyin shop": "douyin",
    "小红书": "xiaohongshu",
    "red": "xiaohongshu",
    "亚马逊": "amazon",
    "amz": "amazon",
    "tiktok": "tiktok-shop",
    "tiktokshop": "tiktok-shop",
    "tiktok shop": "tiktok-shop",
    "tk": "tiktok-shop",
    "独立站": "shopify",
    "速卖通": "aliexpress",
    "ali": "aliexpress",
    "特穆": "temu",
}

CATEGORIES = {
    "beauty-personal-care": ("clean premium vanity with stone tray, soft towel, and refined reflections", "a hand picks up the product and uses only its clearly visible closure or dispenser", "soft beauty key light, macro lens, shallow depth of field, slow luxury push-in", "no invented ingredients, skin transformation, efficacy or medical claims"),
    "apparel-accessories": ("minimal wardrobe, clean pedestal, or premium dressing area", "a person naturally wears, fastens, carries, or moves the item without changing its construction", "soft directional light, detail pan, stable full-item framing, elegant fabric motion", "no changed cut, color, logo, hardware, body shape, or impossible fit"),
    "food-beverage": ("warm premium kitchen or dining surface with minimal matching tableware", "a hand presents the sealed pack; open, pour, or serve only when the visible package supports it", "warm appetizing light, package macro, gentle dolly, subtle steam only when physically appropriate", "no invented ingredients, nutrition, taste, health, or origin claims"),
    "home-kitchen": ("tidy premium home or kitchen with correct product scale", "a hand places, opens, organizes, wipes, or operates one clearly visible function", "bright natural interior light, steady dolly, detail close-up, soft highlight sweep", "no wrong scale, unsafe heat, invented components, or unsupported performance"),
    "electronics-appliances": ("clean premium desk, living room, or kitchen counter with no fake screens", "a hand connects or operates only a clearly visible port, button, or control", "crisp commercial light, controlled orbit, mechanical macro, refined specular highlights", "no fake UI, impossible ports, water exposure, or unsupported speed and power claims"),
    "mother-baby-toys": ("clean nursery or play surface with uncluttered safe space", "an adult hand places the product or demonstrates one simple visible mechanism", "soft daylight, stable framing, gentle low-angle detail, calm premium rhythm", "no unattended hazardous use, invented small parts, age, safety, or development claims"),
    "pet-supplies": ("clean home or calm outdoor pet setting with premium lifestyle texture", "a hand places, clips, rolls, or brushes only when that function is visually evident", "friendly daylight, stable low angle, short follow movement, soft background separation", "no unsafe restraint, forced animal behavior, invented parts, or veterinary claims"),
    "tools-auto": ("organized premium workbench, garage, or vehicle-safe context", "a protected hand grips, aligns, tightens, or mounts the product only when its use is evident", "strong side light, mechanical macro, stable tracking, cinematic metal highlights", "no missing protective equipment, dangerous operation, sparks, invented compatibility, or strength claims"),
    "other": ("neutral seamless premium studio with one matching surface", "a hand picks up and places the product while revealing one visible feature without guessing its function", "clean commercial light, slow push-in, short controlled orbit, shallow depth of field", "no guessed use, invented parts, unsupported claims, or unknown product applied to a person"),
}

KEYWORDS = {
    "beauty-personal-care": [
        "beauty", "serum", "cream", "shampoo", "perfume", "cosmetic", "skincare",
        "美妆", "护肤", "精华", "面霜", "乳液", "洗发水", "香水", "口红", "美容", "个护",
    ],
    "apparel-accessories": [
        "apparel", "dress", "shirt", "shoe", "sneaker", "handbag",
        "backpack", "watch", "jewelry",
        "服饰", "衣服", "连衣裙", "衬衫", "鞋", "运动鞋", "包", "手提包", "背包", "手表", "首饰", "珠宝",
    ],
    "food-beverage": [
        "food", "snack", "drink", "coffee", "tea", "biscuit", "juice", "beverage",
        "食品", "零食", "饮料", "咖啡", "茶", "饼干", "果汁", "坚果", "糖果",
    ],
    "home-kitchen": [
        "furniture", "kitchen", "storage", "cup", "mug", "pan", "lamp", "sofa", "homeware",
        "家居", "厨房", "收纳", "杯", "马克杯", "锅", "灯", "沙发", "清洁", "厨具",
    ],
    "electronics-appliances": [
        "electronic", "phone", "earbud", "speaker", "appliance", "camera", "keyboard", "charger",
        "电子", "手机", "耳机", "音箱", "电器", "相机", "键盘", "充电器", "数据线", "蓝牙",
    ],
    "mother-baby-toys": [
        "baby", "infant", "toy", "block", "stroller", "kids",
        "母婴", "婴儿", "宝宝", "玩具", "积木", "童车", "儿童", "孩子",
    ],
    "pet-supplies": [
        "pet", "cat", "dog", "leash", "bowl", "litter",
        "宠物", "猫", "狗", "牵引绳", "宠物碗", "猫砂", "梳毛",
    ],
    "tools-auto": [
        "tool", "wrench", "drill", "auto", "car", "outdoor", "camping",
        "工具", "扳手", "电钻", "车载", "汽车", "户外", "露营", "五金", "汽配",
    ],
}

VOICEOVER_LANGUAGES = {
    "zh-CN": "Mandarin Chinese",
    "en-US": "American English",
    "ja-JP": "Japanese",
    "ko-KR": "Korean",
    "fr-FR": "French",
    "de-DE": "German",
    "es-ES": "Spanish",
    "auto": "the most appropriate language for the product and audience",
}

CINEMATIC_LEVELS = {
    "premium": "premium advertising-film cinematography: stable gimbal movement, shallow depth of field, elegant slow push-ins, controlled orbit, macro rack focus, refined highlight sweep, soft commercial contrast",
    "clean": "clean commercial cinematography: steady camera, clear product framing, soft light, simple macro detail, restrained movement",
    "luxury": "luxury advertising-film cinematography: deliberate slow motion, glossy highlights, sculpted light, precise macro details, quiet high-end rhythm, hero-grade final lockup",
}

MODEL_PRESENCE = {
    "auto": "use the safest category-appropriate human presence: hands for most products, and partial lifestyle model presence only when the category naturally supports it",
    "none": "no human model; use product, environment, and tactile prop movement only",
    "hands": "hands may appear for tactile interaction, dispensing, holding, placing, fastening, or demonstrating one visible function",
    "lifestyle-model": "a tasteful lifestyle model may appear in partial framing when appropriate: hands, shoulder, cheek side profile, jawline, neck, or soft reflection; avoid full face focus unless clearly needed",
}

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
RISK_TERMS = [
    "cure", "heal", "treatment", "guaranteed", "permanent", "best", "number one", "no.1",
    "absolute", "strongest", "no side effects", "fda approved", "clinically proven", "medical grade",
    "治愈", "根治", "第一", "最强", "保证", "永久", "无副作用", "认证",
]
PLACEHOLDER_RE = re.compile(r"\[[A-Z_]+\]|category-relevant|appropriate to the product|daily use scene", re.I)


def image_dimensions(path: Path) -> tuple[int, int] | None:
    """Read common image dimensions without third-party dependencies."""
    with path.open("rb") as handle:
        head = handle.read(32)
        if head.startswith(b"\x89PNG\r\n\x1a\n") and len(head) >= 24:
            return struct.unpack(">II", head[16:24])
        if head[:2] == b"\xff\xd8":
            handle.seek(2)
            while True:
                marker_start = handle.read(1)
                if not marker_start:
                    return None
                if marker_start != b"\xff":
                    continue
                marker = handle.read(1)
                while marker == b"\xff":
                    marker = handle.read(1)
                if marker in {b"\xd8", b"\xd9"}:
                    continue
                length_raw = handle.read(2)
                if len(length_raw) != 2:
                    return None
                length = struct.unpack(">H", length_raw)[0]
                if marker and marker[0] in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
                    data = handle.read(5)
                    return (struct.unpack(">H", data[3:5])[0], struct.unpack(">H", data[1:3])[0]) if len(data) == 5 else None
                handle.seek(max(0, length - 2), 1)
        if head.startswith(b"RIFF") and head[8:12] == b"WEBP" and len(head) >= 30:
            chunk = head[12:16]
            if chunk == b"VP8X":
                return (1 + int.from_bytes(head[24:27], "little"), 1 + int.from_bytes(head[27:30], "little"))
        return None


def keyword_hits(text: str, words: list[str]) -> int:
    lowered = text.lower()
    hits = 0
    for word in words:
        token = word.lower()
        if re.search(r"[a-z0-9]", token):
            if re.search(rf"\b{re.escape(token)}\b", lowered):
                hits += 1
        elif token in lowered:
            hits += 1
    return hits


def normalize_platform(value: str | None) -> str:
    platform = (value or "generic").strip()
    lowered = platform.lower()
    normalized = PLATFORM_ALIASES.get(platform) or PLATFORM_ALIASES.get(lowered) or lowered
    return normalized


def platform_market(platform: str) -> str:
    return "crossborder" if platform in CROSSBORDER_PLATFORMS else "domestic"


def default_voiceover_language(platform: str) -> str:
    return "en-US" if platform_market(platform) == "crossborder" else "zh-CN"


def default_voiceover_style(language: str) -> str:
    if language == "zh-CN":
        return "premium Mandarin Chinese advertising narration, refined, restrained, trustworthy, not hard-sell"
    if language == "auto":
        return "premium ecommerce advertising narration, refined, restrained, trustworthy, not hard-sell"
    return "premium English ecommerce advertising narration, refined, restrained, trustworthy, not hard-sell"


def infer_category(product_name: str, image_notes: str = "") -> str:
    text = f"{product_name} {image_notes}".strip()
    scores = {category: keyword_hits(text, words) for category, words in KEYWORDS.items()}
    best = max(scores, key=scores.get)
    top_score = scores[best]
    second_score = max((score for category, score in scores.items() if category != best), default=0)
    if top_score <= 0 or top_score == second_score:
        return "other"
    return best


def validate_images(image_paths: list[str]) -> tuple[list[Path], list[str]]:
    if not image_paths:
        raise ValueError("At least one --image-path is required")
    paths, warnings = [], []
    for value in image_paths:
        path = Path(value).expanduser().resolve()
        if not path.is_file():
            raise ValueError(f"Image not found: {value}")
        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported image format: {path.suffix}; use JPG, JPEG, PNG, or WebP")
        if path.stat().st_size == 0:
            raise ValueError(f"Image is empty: {path}")
        if path.stat().st_size > 20 * 1024 * 1024:
            warnings.append(f"Large image may be rejected by the API: {path.name}")
        dimensions = image_dimensions(path)
        if not dimensions:
            warnings.append(f"Could not verify image dimensions: {path.name}")
        elif min(dimensions) < 512:
            warnings.append(f"Low-resolution reference may reduce product fidelity: {path.name} ({dimensions[0]}x{dimensions[1]})")
        paths.append(path)
    return paths, warnings


def image_roles(paths: list[Path]) -> list[dict[str, str]]:
    names = ["primary_identity", "alternate_view", "detail_view", "usage_reference"]
    return [{"path": str(path), "role": names[min(index, len(names) - 1)]} for index, path in enumerate(paths)]


def storyboard_image_roles(paths: list[Path]) -> list[dict[str, str]]:
    return [{"path": str(path), "role": f"storyboard_reference_{index}"} for index, path in enumerate(paths, start=1)]


def claim_warnings(text: str) -> list[str]:
    lowered = text.lower()
    warnings = [f"Potential unsupported claim requires user verification: {term}" for term in RISK_TERMS if term.lower() in lowered]
    if "100%" in text:
        warnings.append("Potential unsupported claim requires user verification: 100%")
    return warnings


def load_input_json(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    input_path = Path(path).expanduser().resolve()
    try:
        data = json.loads(input_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid --input-json: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("--input-json must contain a JSON object")
    data["__input_json_dir"] = str(input_path.parent)
    return data


def json_value(data: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in data:
            return data[name]
        alt = name.replace("-", "_")
        if alt in data:
            return data[alt]
    return None


def as_list(value: Any, field: str) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    raise ValueError(f"{field} must be a string or list of strings")


def parse_bool(value: Any, field: str) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in {0, 1}:
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y", "on"}:
            return True
        if lowered in {"false", "0", "no", "n", "off"}:
            return False
    raise ValueError(f"{field} must be a boolean")


def resolve_json_paths(values: list[str] | None, base_dir: str | None) -> list[str] | None:
    if not values or not base_dir:
        return values
    base = Path(base_dir)
    return [str((base / value).resolve()) if not Path(value).expanduser().is_absolute() else value for value in values]


def resolve_json_path(value: str, base_dir: str | None) -> str:
    if not value or not base_dir:
        return value
    path = Path(value).expanduser()
    return str((Path(base_dir) / path).resolve()) if not path.is_absolute() else value


def resolved_args(args: argparse.Namespace) -> argparse.Namespace:
    data = load_input_json(args.input_json)
    json_dir = json_value(data, "__input_json_dir")
    image_path = args.image_path or resolve_json_paths(as_list(json_value(data, "image_path", "image_paths"), "image_path"), json_dir)
    storyboard_image_path = args.storyboard_image_path or resolve_json_paths(
        as_list(json_value(data, "storyboard_image_path", "storyboard_image_paths"), "storyboard_image_path"), json_dir)
    json_output_dir = json_value(data, "output_dir") or ""
    raw_platform = getattr(args, "platform", None) or json_value(data, "platform") or "generic"
    platform = normalize_platform(raw_platform)
    voiceover_language = (
        getattr(args, "voiceover_language", None)
        or json_value(data, "voiceover_language")
        or default_voiceover_language(platform)
    )
    voiceover_style = (
        getattr(args, "voiceover_style", None)
        or json_value(data, "voiceover_style")
        or default_voiceover_style(voiceover_language)
    )
    generate_storyboard_image_value = getattr(args, "generate_storyboard_image", None)
    if generate_storyboard_image_value is None:
        generate_storyboard_image_value = parse_bool(json_value(data, "generate_storyboard_image"), "generate_storyboard_image") if json_value(data, "generate_storyboard_image") is not None else False
    values = {
        "product_name": args.product_name or json_value(data, "product_name") or "",
        "image_path": image_path or [],
        "storyboard_image_path": storyboard_image_path or [],
        "image_notes": args.image_notes if args.image_notes is not None else (json_value(data, "image_notes") or ""),
        "selling_points": args.selling_points if args.selling_points is not None else (json_value(data, "selling_points") or ""),
        "audience": args.audience if args.audience is not None else (json_value(data, "audience") or ""),
        "platform": platform,
        "market": platform_market(platform),
        "category": args.category or json_value(data, "category") or "auto",
        "resolution": args.resolution or json_value(data, "resolution") or "480p",
        "duration": args.duration or int(json_value(data, "duration") or 15),
        "output_dir": args.output_dir or resolve_json_path(json_output_dir, json_dir),
        "generate_audio": args.generate_audio if args.generate_audio is not None else (parse_bool(json_value(data, "generate_audio"), "generate_audio") if json_value(data, "generate_audio") is not None else True),
        "voiceover": args.voiceover if args.voiceover is not None else (parse_bool(json_value(data, "voiceover"), "voiceover") if json_value(data, "voiceover") is not None else True),
        "voiceover_language": voiceover_language,
        "voiceover_style": voiceover_style,
        "voiceover_script": args.voiceover_script or json_value(data, "voiceover_script") or "",
        "cinematic_level": args.cinematic_level or json_value(data, "cinematic_level") or "premium",
        "model_presence": args.model_presence or json_value(data, "model_presence") or "auto",
        "storyboard_file": args.storyboard_file or json_value(data, "storyboard_file") or "",
        "benchmark_style_notes": args.benchmark_style_notes or json_value(data, "benchmark_style_notes") or "",
        "generate_storyboard_image": bool(generate_storyboard_image_value),
        "storyboard_image_output_name": getattr(args, "storyboard_image_output_name", None) or json_value(data, "storyboard_image_output_name") or "director-storyboard.png",
    }
    if values["generate_audio"] is False:
        values["voiceover"] = False
    validate_choices(values)
    return argparse.Namespace(**values)


def validate_choices(values: dict[str, Any]) -> None:
    if values["platform"] not in PLATFORMS:
        raise ValueError(f"Unsupported platform: {values['platform']}")
    if values["category"] not in {"auto", *CATEGORIES}:
        raise ValueError(f"Unsupported category: {values['category']}")
    if values["resolution"] not in {"480p", "720p", "1080p", "2K"}:
        raise ValueError(f"Unsupported resolution: {values['resolution']}")
    if int(values["duration"]) != 15:
        raise ValueError("Only 15-second videos are supported")
    if values["voiceover_language"] not in VOICEOVER_LANGUAGES:
        raise ValueError(f"Unsupported voiceover language: {values['voiceover_language']}")
    if values["cinematic_level"] not in CINEMATIC_LEVELS:
        raise ValueError(f"Unsupported cinematic level: {values['cinematic_level']}")
    if values["model_presence"] not in MODEL_PRESENCE:
        raise ValueError(f"Unsupported model presence: {values['model_presence']}")


def model_direction(category: str, model_presence: str) -> str:
    base = MODEL_PRESENCE[model_presence]
    if model_presence == "auto" and category == "beauty-personal-care":
        return (
            f"{base}. For beauty and skincare, include tasteful experiential presence: clean hands, a soft side-profile cheek/neck/shoulder moment, "
            "or a mirror-adjacent application gesture. Keep skin natural and do not show before/after transformation, wrinkle removal, whitening change, or medical effect."
        )
    if model_presence == "auto" and category in {"apparel-accessories", "pet-supplies", "tools-auto"}:
        return f"{base}. Let human presence show scale and use, but keep the product dominant and unchanged."
    return base


def storyboard_shots(category: str, model_presence: str) -> list[dict[str, str]]:
    common_entry = {
        "name": "Context Entry",
        "goal": "establish the product world and make the viewer understand where the product belongs.",
        "subject": "product already visible in a coherent environment; human presence optional and secondary.",
        "composition": "product occupies a hero-safe area with label direction preserved and clean negative space.",
        "action": "one gentle environmental cue only, such as light movement, hand entering frame, reflection, fabric movement, or setting reveal.",
        "camera": "one slow push-in or short slider move only.",
        "premium": "sculpted soft light, restrained palette, shallow depth, clean atmosphere.",
        "avoid": "hide the product, start with a full-face model, add text, add extra products, or change packaging.",
    }
    common_hero = {
        "name": "Product Memory Hero",
        "goal": "leave a clear ecommerce product memory and inspection-ready final frame.",
        "subject": "unchanged product alone as the final anchor.",
        "composition": "front three-quarter hero lockup, label direction preserved, product readable.",
        "action": "product rests still; only subtle light sweep, reflection, fabric settling, or final shimmer may move.",
        "camera": "near-static hold or extremely slow push only.",
        "premium": "clean silhouette, controlled highlights, calm sound accent, final frame suitable for inspection.",
        "avoid": "add text, badges, slogans, prices, platform UI, extra brand names, or let model/hands remain final subject.",
    }
    if category == "beauty-personal-care":
        shots = [
            common_entry,
            {
                "name": "Product Establishment",
                "goal": "make the exact bottle/package identity clear before any lifestyle action.",
                "subject": "unchanged product on premium vanity surface.",
                "composition": "label-facing three-quarter angle, product dominant, botanical/water elements secondary.",
                "action": "one slow turn, light reveal, or hand approach without lifting yet.",
                "camera": "controlled orbit or short lateral slide only.",
                "premium": "green glass glow, gold/white material contrast, clean luxury spacing.",
                "avoid": "obscure the label, add duplicate bottles, invent ingredients, or change bottle shape.",
            },
            {
                "name": "First Contact",
                "goal": "create tactile desire and a believable skincare ritual start.",
                "subject": "unchanged product and one clean hand; anonymous partial lifestyle presence only if helpful.",
                "composition": "hand supports scale but product remains dominant and readable.",
                "action": "one action only: pick up, rotate slightly, or prepare visible dropper/closure.",
                "camera": "short slider or gentle follow move only.",
                "premium": "quiet luxury handling, soft reflection, precise hand movement.",
                "avoid": "perform multiple actions, cover the label, focus on full face, or require model identity continuity.",
            },
            {
                "name": "Sensory Macro",
                "goal": "give a close sensory reason to trust the texture and material.",
                "subject": "visible detail: dropper, cap, collar, glass, label area, liquid/glass highlight, or package texture.",
                "composition": "macro framing, detail fills frame while staying faithful to the reference.",
                "action": "one detail action only: dropper lift, cap turn, light through glass, texture catchlight, or fingertip contact.",
                "camera": "macro rack focus or tiny push-in only.",
                "premium": "precise highlights, clean reflections, controlled depth, tactile realism.",
                "avoid": "invent liquid behavior, change printed text, add ingredient visuals, or show impossible physics.",
            },
            {
                "name": "Ritual Experience",
                "goal": "add human experience without claiming visible skin results.",
                "subject": "product plus clean hand, hand-back, neck/shoulder, side profile, or mirror-adjacent anonymous presence.",
                "composition": "partial framing only; product remains visually connected to the gesture.",
                "action": "one safe skincare gesture: dispense to hand, hover near cheek/neck, or close the ritual moment; show ritual, not transformation.",
                "camera": "stable gentle push or short follow movement only.",
                "premium": "quiet pause, breathable negative space, natural skin texture, refined bathroom/vanity atmosphere.",
                "avoid": "show before/after results, skin improvement, wrinkle removal, whitening change, full-face performance, or efficacy proof.",
            },
            common_hero,
        ]
    elif category == "apparel-accessories":
        shots = [
            common_entry,
            {"name": "Form Reveal", "goal": "show silhouette, scale, and construction.", "subject": "unchanged item with partial body or hand for scale.", "composition": "full item readable with clean wardrobe/pedestal context.", "action": "one lift, turn, drape, fastening, or carry gesture.", "camera": "slow pan or slider move only.", "premium": "fabric/hardware catchlight, controlled styling, elegant spacing.", "avoid": "change cut, color, logo, fit, or hardware."},
            {"name": "Material Detail", "goal": "show tactile quality.", "subject": "visible seam, texture, zipper, buckle, stitch, logo area, or hardware.", "composition": "macro detail with context edge.", "action": "one fingertip touch, fabric movement, clasp, or strap motion.", "camera": "macro push or rack focus only.", "premium": "soft directional light and crisp texture.", "avoid": "invent parts or add extra logos."},
            {"name": "Use Moment", "goal": "make wearing/carrying feel natural.", "subject": "anonymous partial body; item remains dominant.", "composition": "crop away from full face unless needed.", "action": "one natural carry, step, fastening, or placement.", "camera": "stable follow or short lateral move.", "premium": "quiet fashion editorial rhythm.", "avoid": "impossible body fit or identity continuity requirement."},
            common_hero,
        ]
    elif category == "food-beverage":
        shots = [
            common_entry,
            {"name": "Pack Reveal", "goal": "make product recognition immediate.", "subject": "sealed pack/bottle/can unchanged.", "composition": "label readable on clean dining/kitchen surface.", "action": "one hand presents or rotates package.", "camera": "short push or slide.", "premium": "warm appetizing light, clean tableware secondary.", "avoid": "invent ingredients, nutrition claims, or change package text."},
            {"name": "Texture Detail", "goal": "show material/serving cue only if visible and suitable.", "subject": "package detail, seal, pour edge, condensation, or table setting.", "composition": "macro product-first frame.", "action": "one open/pour/serve gesture only when physically supported; otherwise hand placement.", "camera": "macro rack focus.", "premium": "warm highlights and restrained motion.", "avoid": "unsafe opening, fake ingredients, or unsupported health claims."},
            {"name": "Serving Moment", "goal": "create appetite and use context.", "subject": "product plus tableware/hand; no people eating full-face.", "composition": "product remains present in frame.", "action": "one serve, pour, or place action.", "camera": "stable follow.", "premium": "clean steam/condensation only when plausible.", "avoid": "mouth close-ups that distract from product."},
            common_hero,
        ]
    else:
        shots = [
            common_entry,
            {"name": "Product Establishment", "goal": "make the exact product identity and scale clear.", "subject": "unchanged product in category-safe setting.", "composition": "front three-quarter readable product view.", "action": "one hand approach, placement, or slow turn.", "camera": "controlled push or short orbit.", "premium": "clean lighting, stable product silhouette.", "avoid": "guess unknown function or add invented parts."},
            {"name": "Visible Detail", "goal": "show one real feature without guessing function.", "subject": "material, closure, texture, control, seam, port, surface, or package feature.", "composition": "macro detail with product context.", "action": "one tactile contact or light reveal.", "camera": "macro rack focus or tiny push.", "premium": "precise highlight and calm pace.", "avoid": "invent performance, compatibility, or hidden features."},
            {"name": "Safe Use Cue", "goal": "make the product feel usable while staying conservative.", "subject": "product plus hand or environment.", "composition": "product remains dominant and readable.", "action": "one place, pick-up, align, open, or demonstrate visible mechanism only.", "camera": "stable follow movement.", "premium": "realistic handling and quiet rhythm.", "avoid": "dangerous operation, unsafe use, or unsupported claims."},
            common_hero,
        ]
    if model_presence == "none":
        for shot in shots:
            shot["subject"] = shot["subject"].replace("human presence optional and secondary", "no human presence").replace("one clean hand", "no human model")
            shot["avoid"] = f"{shot['avoid']} Do not show a human model."
    return shots


def shot_scene_style(category: str, shot_name: str, benchmark_style_notes: str) -> str:
    benchmark = benchmark_style_notes.strip()
    benchmark_text = f" Match the benchmark style cues: {benchmark}" if benchmark else ""
    if category == "beauty-personal-care":
        base = {
            "Context Entry": "pale botanical luxury world, water-glass surface, soft green reflections, natural window light.",
            "Product Establishment": "premium vanity or glass plinth scene, controlled green highlights, clean negative space.",
            "First Contact": "quiet skincare ritual atmosphere, clean hand styling, refined bathroom/vanity mood.",
            "Sensory Macro": "macro beauty commercial style, glossy glass, precise catchlights, shallow depth of field.",
            "Ritual Experience": "anonymous lifestyle skincare moment, natural skin texture, soft mirror/shoulder/hand framing.",
            "Product Memory Hero": "inspection-ready ecommerce hero, calm green glow, polished final lockup.",
        }
    elif category == "apparel-accessories":
        base = {
            "Context Entry": "quiet fashion editorial setup, restrained wardrobe surface, premium material mood.",
            "Form Reveal": "clean dressing or pedestal scene, item silhouette and scale are immediately readable.",
            "Material Detail": "macro fashion detail style with crisp texture, stitching, hardware, or logo area.",
            "Use Moment": "partial-body lifestyle scene, elegant movement, product remains the visual anchor.",
            "Product Memory Hero": "minimal fashion product hero, clean silhouette, no competing props.",
        }
    elif category == "food-beverage":
        base = {
            "Context Entry": "premium dining or kitchen world, appetizing but restrained warm light.",
            "Pack Reveal": "clean tabletop scene, package label readable, tableware secondary.",
            "Texture Detail": "macro serving or package-detail scene, realistic condensation/steam only when plausible.",
            "Serving Moment": "natural serving ritual, product remains present, no distracting mouth close-up.",
            "Product Memory Hero": "clean packshot hero, appetizing atmosphere, readable final frame.",
        }
    else:
        base = {
            "Context Entry": "neutral premium studio environment with one coherent surface and restrained props.",
            "Product Establishment": "clean commercial product stage, exact silhouette and scale readable.",
            "Visible Detail": "macro product-detail scene with precise highlight and faithful material texture.",
            "Safe Use Cue": "realistic hand or environment use cue, conservative and physically plausible.",
            "Product Memory Hero": "inspection-ready final ecommerce hero frame with clean product silhouette.",
        }
    return f"{base.get(shot_name, 'coherent premium ecommerce scene matched to the product category.')}{benchmark_text}"


def shot_sound_timing(index: int, count: int, shot_name: str, voiceover: bool = True) -> str:
    if index == 1:
        voice = "first short voiceover line may set the mood after the visual hook" if voiceover else "no voiceover"
        return f"soft ambience fade-in, subtle riser, {voice}; leave room for visual recognition."
    if index == count:
        voice = "final voiceover phrase lands before the hero hold" if voiceover else "no voiceover"
        return f"refined final shimmer, music resolves cleanly, {voice}; final second must feel calm."
    if "Macro" in shot_name or "Detail" in shot_name or "Texture" in shot_name:
        return "quiet tactile sound, tiny whoosh or focus accent; voiceover should pause or use one concise phrase."
    if "Experience" in shot_name or "Use" in shot_name or "Serving" in shot_name:
        return "gentle handling sound and warm musical lift; voiceover may describe only visible or user-supplied facts."
    return "premium instrumental bed continues, one tasteful transition accent; keep narration sparse."


def shot_transition(index: int, count: int, shot_name: str) -> str:
    if index == count:
        return "hold into final hero frame; no extra scene after this shot."
    if "Macro" in shot_name or "Detail" in shot_name or "Texture" in shot_name:
        return "cut on focus pull or highlight sweep into the next wider experience shot."
    return "simple commercial cut or soft match cut; no morph, warp, transformation, or fast montage."


def identity_lock(product_name: str) -> str:
    return (
        f"{product_name} remains the same object from the first product image: same silhouette, proportions, color, material, "
        "package structure, logo/label/text placement, closure, accessories, and scale relationship."
    )


def build_storyboard(product_name: str, image_notes: str, selling_points: str, audience: str,
                     platform: str, category: str, model_presence: str, cinematic_level: str,
                     benchmark_style_notes: str = "", voiceover: bool = True) -> str:
    ratio, platform_direction = PLATFORMS[platform]
    setting, action, camera, avoid = CATEGORIES[category]
    human_text = model_direction(category, model_presence)
    cinematic_text = CINEMATIC_LEVELS[cinematic_level]
    shots = storyboard_shots(category, model_presence)
    shot_count = len(shots)
    shot_duration = 15 / shot_count
    shot_blocks = []
    for index, shot in enumerate(shots, start=1):
        start = (index - 1) * shot_duration
        end = index * shot_duration
        shot_blocks.append(f"""Shot {index} - {shot['name']}
Time: {start:.1f}-{end:.1f}s
Director intent: {shot['goal']}
Scene style: {shot_scene_style(category, shot['name'], benchmark_style_notes)}
Main subject: {shot['subject']}
Composition: {shot['composition']}
Action beat: {shot['action']}
Camera movement: {shot['camera']}
Lighting / premium cue: {shot['premium']}
Sound / voiceover timing: {shot_sound_timing(index, shot_count, shot['name'], voiceover)}
Transition: {shot_transition(index, shot_count, shot['name'])}
Product consistency lock: {identity_lock(product_name)}
Do not: {shot['avoid']}""")
    return f"""# Storyboard: {product_name}

Purpose: create a controlled 15-second {ratio} ecommerce advertising video with clear story logic, premium visual rhythm, and product-first consistency.
Storyboard role: this is the director shot list. Use it as the written foundation for the storyboard control image and the final video prompt.
Shot count decision: use {shot_count} shots because this product/category benefits from this amount of visual logic. Do not force a fixed five-shot template.

Platform: {platform} - {platform_direction}
Category: {category}
Audience: {audience or 'Broad ecommerce shoppers; keep the context neutral and inclusive.'}
Product facts: {image_notes or 'Use only directly visible facts from the reference images.'}
User-provided selling points: {selling_points or 'None; communicate only visible design, texture, usage experience, and scene value.'}
Cinematic treatment: {cinematic_text}
Benchmark / target style: {benchmark_style_notes or 'No external benchmark supplied; use category-appropriate premium ecommerce styling.'}
Human/model policy: {human_text}
Safety boundary: {avoid}

Director shot-card schema: every shot below defines time, director intent, scene style, main subject, composition, action beat, camera movement, lighting/premium cue, sound/voiceover timing, transition, product consistency lock, and do-not rules. The storyboard image must visually match these shot cards; the video model must follow both the written shot cards and the storyboard control image.

Storyboard control image requirements: create one director storyboard sheet with one panel per shot. Every panel must contain the actual shot image plus readable director labels for shot number, time range, camera movement, main action beat, and scene/style cue. Use small professional notation, camera arrows, and compact labels; do not use marketing copy, slogans, prices, badges, platform UI, or unrelated text. The visual panel, timing label, and camera/action labels must all match the written shot card.

{chr(10).join(shot_blocks)}
"""


def build_storyboard_image_prompt(product_name: str, platform: str, category: str, storyboard: str,
                                  image_notes: str = "", benchmark_style_notes: str = "") -> str:
    ratio, platform_direction = PLATFORMS[platform]
    return f"""Create one professional director storyboard control sheet for a 15-second ecommerce product video.

Canvas: 1536x1024, clean white or light neutral production-board background.
Product: {product_name}
Platform: {platform}, final video ratio {ratio}. Direction: {platform_direction}
Category: {category}
Visible product facts to preserve from the reference image: {image_notes or 'Use only visible product facts from the product reference image.'}
Benchmark / target style notes: {benchmark_style_notes or 'Use the written storyboard and category-appropriate premium ecommerce styling.'}

Use the product reference image only to preserve product identity. The first product image is the identity source: keep the same silhouette, proportions, color, material, package structure, logo/label/text placement, closures, accessories, and scale relationship. Do not redesign, relabel, recolor, duplicate, or add accessories.

Storyboard sheet requirements:
- Use one visual panel per shot from the written storyboard.
- Each panel must show the intended frame, not a mood-only reference.
- Add compact functional labels only: shot number, time range, camera movement, main action beat, and scene/style cue.
- Use small professional director notation such as push-in arrows, orbit arrows, rack-focus marks, or hold marks when helpful.
- Keep the product dominant and readable in every panel where it appears.
- Do not add marketing slogans, selling captions, prices, discount badges, platform UI, subtitles, watermark, random text, or extra brand names.
- The labels are director notes only; they must not look like ecommerce promotional copy.

Written storyboard to visualize:
{storyboard}
"""


def load_storyboard(path: str | None) -> str:
    if not path:
        return ""
    storyboard_path = Path(path).expanduser().resolve()
    if not storyboard_path.is_file():
        raise ValueError(f"Storyboard file not found: {path}")
    return storyboard_path.read_text(encoding="utf-8-sig")


def audio_direction(generate_audio: bool, voiceover: bool, voiceover_language: str, voiceover_style: str,
                    voiceover_script: str = "") -> str:
    if not generate_audio:
        return "Generate silent video with no audio and no voiceover."
    if not voiceover:
        return (
            "Generate premium instrumental background music and refined product sound design only. "
            "Use soft risers, subtle whooshes, tactile handling sounds, and elegant final shimmer. "
            "No speech, no voiceover, no vocals, no lyrics, no jingle, and no spoken brand name."
        )
    language = VOICEOVER_LANGUAGES[voiceover_language]
    script_text = (
        f"Use this user-provided voiceover script as the intended narration, keeping its meaning and language: {voiceover_script}. "
        if voiceover_script else
        "Create the narration as 3 to 5 short premium ad lines, one line per main visual beat, with natural pauses and no dense talking. "
    )
    return (
        f"Generate advertising-film voiceover in {language}. Voiceover style: {voiceover_style}. "
        f"{script_text}"
        "The voiceover must be concise, polished, trustworthy, and synchronized with the storyboard shots; keep it calm and premium, not loud or salesy. "
        "Speak only user-supplied selling points and directly visible product facts; do not invent claims, prices, certifications, rankings, guarantees, or performance promises. "
        "Add premium instrumental ambience and refined product sound design: soft cinematic bed, tasteful risers, subtle whooshes, tactile handling sounds, and elegant final shimmer. "
        "No sung vocals, no lyrics, no jingle, no shouty hard-sell delivery."
    )


def build_prompt(product_name: str, image_notes: str, selling_points: str, audience: str,
                 platform: str, category: str, generate_audio: bool, roles: list[dict[str, str]],
                 voiceover: bool = True, voiceover_language: str = "auto",
                 voiceover_style: str = "premium ecommerce advertising narration, refined, restrained, trustworthy, not hard-sell",
                 voiceover_script: str = "",
                 cinematic_level: str = "premium", model_presence: str = "auto",
                 storyboard: str = "", benchmark_style_notes: str = "") -> str:
    ratio, platform_direction = PLATFORMS[platform]
    setting, action, camera, avoid = CATEGORIES[category]
    role_text = "; ".join(f"{item['role']}: {Path(item['path']).name}" for item in roles)
    storyboard_ref_count = sum(1 for item in roles if item["role"].startswith("storyboard_reference"))
    storyboard_ref_text = (
        "Storyboard control images are provided after product references and must be uploaded with the product image. "
        "Use them to understand the director storyboard, shot order, composition, scene style, camera logic, rhythm, mood, and per-shot visual design. "
        "never copy their product details over the primary identity image."
        if storyboard_ref_count else
        "No storyboard control images are supplied; follow the written storyboard only."
    )
    audio_text = audio_direction(generate_audio, voiceover, voiceover_language, voiceover_style, voiceover_script)
    cinematic_text = CINEMATIC_LEVELS[cinematic_level]
    human_text = model_direction(category, model_presence)
    return f"""Create one 15-second {ratio} premium ecommerce advertising main-image video for {product_name}.

PRODUCT IDENTITY IS NON-NEGOTIABLE. The first reference image is the primary identity source and overrides every later reference. Preserve the exact product silhouette, proportions, color, material, package structure, visible logo position, label layout, printed text placement, closures, controls, accessories, and included parts. Later references provide alternate/detail/use context only and must never override the first image. Do not redesign, duplicate, morph, recolor, relabel, repackage, change scale, add accessories, or alter printed package text.

Reference roles: {role_text}
Storyboard reference policy: {storyboard_ref_text}
Visible facts supplied after image inspection: {image_notes or 'No notes supplied; use only directly visible facts from the references.'}
User-supplied selling points: {selling_points or 'None. Communicate only design, texture, usage experience, and scene value visible from the references.'}
Audience: {audience or 'Broad ecommerce shoppers; keep the context neutral and inclusive.'}
Platform direction: {platform_direction}.
Category route: {category}. Use {setting}. {camera}. Safety rule: {avoid}.
Cinematic level: {cinematic_level}. Apply {cinematic_text}. Keep the rhythm premium, stable, and ad-film polished instead of fast montage. Use one coherent physical location and keep all props minimal, relevant, and secondary to the product.
Benchmark / target style notes: {benchmark_style_notes or 'Use the storyboard scene style and category-appropriate premium ecommerce styling.'}
Human presence / experience rule: {human_text}. Add tactile, sensory, and lifestyle context so the video feels experienced rather than displayed, but never let the model, hands, props, or atmosphere obscure or replace the product.

Storyboard-controlled commercial, simple cuts only:
Follow this storyboard exactly. The director-designed shot count is intentional and may vary by product. Each shot card has time, director intent, scene style, main subject, composition, action beat, camera movement, lighting cue, sound/voiceover timing, transition, product consistency lock, and do-not rules. Do not improvise extra scenes or force a fixed five-shot template.

{storyboard}

Execution discipline: use the storyboard timings exactly, keep one coherent location, and never add extra shots. Use the category setting ({setting}), safe action ({action}), and camera style ({camera}) only where they fit the storyboard. If any instruction conflicts, obey product identity and storyboard timing first.

{audio_text}

Negative constraints: no captions, no subtitles, no prices, no promotion badges, no slogans, no platform UI, no watermark, no random letters, no extra brand names, no changed packaging text, no product duplication, no deformed hands, no impossible physics, no fast montage, no transformation transition, no unsupported medical, efficacy, safety, nutritional, compatibility, durability, ranking, warranty, or performance claims. Existing text may remain only where naturally printed on the product.
"""


def write_artifacts(args: argparse.Namespace) -> dict:
    args = resolved_args(args) if hasattr(args, "input_json") else args
    platform = normalize_platform(getattr(args, "platform", "generic"))
    if platform != getattr(args, "platform", "generic") or not hasattr(args, "market"):
        args = argparse.Namespace(**{**vars(args), "platform": platform, "market": platform_market(platform)})
    if not getattr(args, "voiceover_language", None):
        args = argparse.Namespace(**{**vars(args), "voiceover_language": default_voiceover_language(args.platform)})
    if not getattr(args, "voiceover_style", None):
        args = argparse.Namespace(**{**vars(args), "voiceover_style": default_voiceover_style(args.voiceover_language)})
    if not hasattr(args, "generate_storyboard_image"):
        args = argparse.Namespace(**{**vars(args), "generate_storyboard_image": False})
    if not hasattr(args, "storyboard_image_output_name"):
        args = argparse.Namespace(**{**vars(args), "storyboard_image_output_name": "director-storyboard.png"})
    if args.generate_audio is False and args.voiceover:
        args = argparse.Namespace(**{**vars(args), "voiceover": False})
    if not args.product_name.strip():
        raise ValueError("Product name cannot be empty")
    if not args.output_dir:
        raise ValueError("--output-dir is required")
    paths, warnings = validate_images(args.image_path)
    storyboard_paths, storyboard_warnings = validate_images(args.storyboard_image_path) if args.storyboard_image_path else ([], [])
    category = infer_category(args.product_name, args.image_notes or "") if args.category == "auto" else args.category
    roles = image_roles(paths)
    roles.extend(storyboard_image_roles(storyboard_paths))
    warnings.extend(storyboard_warnings)
    warnings.extend(claim_warnings(args.selling_points or ""))
    storyboard = load_storyboard(args.storyboard_file) or build_storyboard(
        args.product_name, args.image_notes or "", args.selling_points or "", args.audience or "",
        args.platform, category, args.model_presence, args.cinematic_level, args.benchmark_style_notes, args.voiceover)
    storyboard_image_prompt = build_storyboard_image_prompt(
        args.product_name, args.platform, category, storyboard, args.image_notes or "", args.benchmark_style_notes)
    prompt = build_prompt(args.product_name, args.image_notes or "", args.selling_points or "", args.audience or "",
                          args.platform, category, args.generate_audio, roles, args.voiceover,
                          args.voiceover_language, args.voiceover_style, args.voiceover_script,
                          args.cinematic_level, args.model_presence, storyboard, args.benchmark_style_notes)
    placeholders = PLACEHOLDER_RE.findall(prompt)
    if placeholders:
        raise ValueError(f"Prompt contains unresolved placeholders: {placeholders}")
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = output_dir / "seedance-ecommerce-prompt.txt"
    storyboard_path = output_dir / "seedance-storyboard.md"
    storyboard_image_prompt_path = output_dir / "storyboard-image-prompt.txt"
    manifest_path = output_dir / "seedance-input-manifest.json"
    prompt_path.write_text(prompt, encoding="utf-8")
    storyboard_path.write_text(storyboard, encoding="utf-8")
    storyboard_image_prompt_path.write_text(storyboard_image_prompt, encoding="utf-8")
    storyboard_status = "provided" if storyboard_paths else ("not_requested" if not getattr(args, "generate_storyboard_image", False) else "requested")
    manifest = {"product_name": args.product_name, "platform": args.platform, "category": category,
                "market": getattr(args, "market", platform_market(args.platform)),
                "ratio": PLATFORMS[args.platform][0], "resolution": args.resolution,
                "duration": args.duration, "generate_audio": args.generate_audio,
                "voiceover": args.voiceover, "voiceover_language": args.voiceover_language,
                "voiceover_style": args.voiceover_style, "voiceover_script": args.voiceover_script,
                "cinematic_level": args.cinematic_level, "model_presence": args.model_presence,
                "benchmark_style_notes": args.benchmark_style_notes,
                "images": roles, "warnings": warnings, "storyboard_path": str(storyboard_path),
                "storyboard_image_prompt_path": str(storyboard_image_prompt_path),
                "storyboard_image_status": storyboard_status,
                "storyboard_image_output_name": getattr(args, "storyboard_image_output_name", "director-storyboard.png"),
                "prompt_path": str(prompt_path)}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {**manifest, "manifest_path": str(manifest_path)}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Build and preflight an all-category ecommerce Seedance prompt")
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
    p.add_argument("--output-dir")
    p.add_argument("--voiceover-language", choices=VOICEOVER_LANGUAGES)
    p.add_argument("--voiceover-style")
    p.add_argument("--voiceover-script")
    p.add_argument("--cinematic-level", choices=CINEMATIC_LEVELS)
    p.add_argument("--model-presence", choices=MODEL_PRESENCE)
    p.add_argument("--storyboard-file")
    p.add_argument("--benchmark-style-notes")
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
    args = parser().parse_args()
    try:
        print(json.dumps(write_artifacts(args), ensure_ascii=True, indent=2))
    except ValueError as exc:
        print(json.dumps({"ok": False, "stage": "preflight", "error": str(exc)}, ensure_ascii=True))
        raise SystemExit(2)


if __name__ == "__main__":
    main()
