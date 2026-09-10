#!/usr/bin/env python3
"""Build a product-selling video brief for Xinghe ecommerce Seedance generation."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any


PLATFORMS: dict[str, dict[str, str]] = {
    "douyin": {"name": "抖音", "ratio": "9:16", "voice": "快节奏中文带货女声，首秒强钩子", "cta": "点小黄车看看"},
    "xiaohongshu": {"name": "小红书", "ratio": "9:16", "voice": "自然种草分享口吻，真实体验感", "cta": "喜欢可以收藏同款"},
    "shipinhao": {"name": "视频号", "ratio": "9:16", "voice": "清楚稳重的中文讲解，适合泛人群", "cta": "需要的可以看看"},
    "taobao": {"name": "淘宝", "ratio": "9:16", "voice": "货架转化口播，卖点和场景并重", "cta": "进店下单更方便"},
    "pinduoduo": {"name": "拼多多", "ratio": "9:16", "voice": "直接实用的中文口播，突出省心和价值", "cta": "需要就直接拼"},
    "tiktok_shop": {"name": "TikTok Shop", "ratio": "9:16", "voice": "short English ecommerce voiceover, demo-first", "cta": "Shop now"},
    "amazon": {"name": "Amazon", "ratio": "1:1", "voice": "concise English benefit-led product demo", "cta": "Check the details"},
    "shopify": {"name": "Shopify", "ratio": "9:16", "voice": "clean brand-style ecommerce voiceover", "cta": "Shop now"},
}

CATEGORY_HINTS: dict[str, dict[str, str]] = {
    "fashion": {"hook": "上身或搭配效果", "demo": "走动、转身、整理衣摆或包身", "proof": "面料、版型、走线或容量细节"},
    "beauty": {"hook": "产品实物和使用状态", "demo": "上手、上脸、涂抹、喷洒或发丝演示", "proof": "质地、光泽、泡沫、粉质或包装细节"},
    "food": {"hook": "成品食欲画面", "demo": "打开、冲泡、加热、倒出或入口", "proof": "热气、拉丝、酥脆、爆汁或配料细节"},
    "home": {"hook": "生活使用场景", "demo": "收纳、清洁、摆放、前后对比", "proof": "结构、材质、防滑、防水或省空间细节"},
    "bedding": {"hook": "铺在床上的卧室氛围效果", "demo": "铺床、整理被角、摆放枕头、抚平床面", "proof": "被套厚度、床单平整度、枕套包裹、面料褶皱和触感细节"},
    "storage": {"hook": "收纳前后的空间变化", "demo": "放入、抽拉、分类、整理、前后对比", "proof": "容量、分区、开合结构、桌面/柜体边缘和物品位置"},
    "cleaning": {"hook": "脏污清洁前后变化", "demo": "擦拭、刷洗、喷洒、冲洗、前后对比", "proof": "脏污位置、清洁接触、湿润痕迹、表面变化和手部动作"},
    "digital": {"hook": "产品外观和功能高光", "demo": "插拔、开关、连接、操作或场景使用", "proof": "接口、按键、灯效、屏幕或材质细节"},
    "accessory": {"hook": "佩戴氛围和搭配效果", "demo": "佩戴、摆动、转角度、反光", "proof": "光泽、纹理、镶嵌、金属或细节近景"},
    "family": {"hook": "照护或互动场景", "demo": "亲子、宠物、整理、喂养或护理动作", "proof": "圆角、柔软、易清洁、结构安全感"},
    "sports": {"hook": "运动或户外使用画面", "demo": "跑跳、拉伸、收纳、搭建或携带", "proof": "扣具、支撑、防滑、面料或轻量细节"},
    "general": {"hook": "商品外观和主要用途", "demo": "真实使用动作", "proof": "材质、结构、细节或前后对比"},
}

CATEGORY_RULES: dict[str, dict[str, str]] = {
    "fashion": {
        "presenter_mode": "真人模特上身展示 + 自然带货口播",
        "result_showcase_type": "穿戴效果型",
        "result_frame": "必须展示真人上身后的整体效果，包含正面、侧身、走动或转身，衣服真实贴合身体。",
        "physical": "衣服必须真实穿在成人模特身上；肩线、领口、袖口、腰线、裙摆/裤脚跟随身体动作自然变化；鞋底接触地面；不能悬浮、不能穿模、不能像贴图。",
        "anchors": "身体比例、肩线、腰线、膝盖/脚踝位置、鞋底接触地面、背景地平线保持连续。",
        "role": "anonymous adult fashion model wearing the product; face may be soft or secondary; product fit is the focus",
    },
    "home": {
        "presenter_mode": "手模/生活方式真人演示 + 画外音带货",
        "result_showcase_type": "场景完成型或使用前后型",
        "result_frame": "必须展示产品进入真实家庭空间后的完成效果；床品/四件套要铺完整张床，收纳/清洁要展示前后变化。",
        "physical": "产品必须与床、桌面、柜体、地面、墙面或手部真实接触；床品必须覆盖床面，被套有厚度和褶皱，枕套包裹枕头，收纳物品必须真实放入容器；不能漂浮、不能穿过家具。",
        "anchors": "床头、床垫边缘、枕头位置、床头柜、桌面边缘、柜体边缘、墙面和地面透视线保持稳定。",
        "role": "anonymous adult hand model or lifestyle model arranging the product in a real home space",
    },
    "bedding": {
        "presenter_mode": "生活方式真人铺床演示 + 画外音带货",
        "result_showcase_type": "场景完成型",
        "result_frame": "必须展示四件套/床品铺完整张床后的卧室氛围效果；床单、被套、枕套位置正确，被子有厚度和自然褶皱。",
        "physical": "床品必须真实铺在床垫上；床单覆盖床面，被套覆盖床面大部分区域，枕套只包裹枕头且位于床头；手部整理被角和抚平床面时必须真实接触布料；不能漂浮、不能穿过床架、不能变成另一套花色。",
        "anchors": "床头、床垫四边、两个枕头、被子边缘、床头柜、墙面、地面透视线保持稳定，床品与床体尺寸比例自然。",
        "role": "anonymous adult hand model or lifestyle model making the bed in a real bedroom; product-on-bed result is the focus",
    },
    "storage": {
        "presenter_mode": "手模整理收纳演示 + 画外音带货",
        "result_showcase_type": "使用前后型",
        "result_frame": "必须展示收纳前杂乱状态、手部整理过程和收纳后整洁结果；空间锚点前后保持不变。",
        "physical": "收纳产品必须真实放在桌面、柜子、车内或地面上；物品必须真实放入、抽出或分类；抽屉/盖子/格子开合方向符合结构；不能漂浮、不能穿过柜体或桌面。",
        "anchors": "桌面边缘、柜体边缘、抽屉位置、车内中控/座椅、物品前后位置和相机角度保持连续。",
        "role": "anonymous adult hand model organizing items with the product in a real storage scene",
    },
    "cleaning": {
        "presenter_mode": "手模清洁演示 + 画外音带货",
        "result_showcase_type": "使用前后型",
        "result_frame": "必须展示清洁前脏污、手部真实清洁过程和清洁后变化，不夸大效果。",
        "physical": "清洁工具或清洁产品必须与脏污表面真实接触；擦拭、刷洗、喷洒、冲洗方向符合物理逻辑；液体、泡沫、污渍变化自然；不能让工具穿过表面或污渍瞬间消失。",
        "anchors": "脏污位置、台面/地面/墙面边缘、手部比例、工具位置、光源方向保持连续。",
        "role": "anonymous adult hand model cleaning a real surface with the product; before-after result is the focus",
    },
    "beauty": {
        "presenter_mode": "真人上手/上脸演示 + 达人口播或画外音",
        "result_showcase_type": "感官体验型 + 使用前后型",
        "result_frame": "必须展示质地上手/上脸/上发过程和使用后状态，不夸大医疗或永久功效。",
        "physical": "手指、刷具、喷头或产品质地必须与皮肤/头发/手背真实接触；膏体、泡沫、粉质、喷雾要符合物理状态；不要让质地漂浮或穿过皮肤。",
        "anchors": "手部比例、脸部/发丝位置、产品瓶身方向、桌面或镜前环境保持连续。",
        "role": "anonymous adult beauty presenter or hand model applying the product; product and texture remain the focus",
    },
    "food": {
        "presenter_mode": "手模制作/入口展示 + 画外音带货",
        "result_showcase_type": "感官体验型",
        "result_frame": "必须展示打开、制作、入口、热气、切面、拉丝、倒杯或酥脆等可见感官结果。",
        "physical": "食物、餐具、杯子、包装和手部必须真实接触；液体倒流、热气、拉丝、切面、咬开动作符合物理逻辑；不要漂浮食物或凭空变形包装。",
        "anchors": "桌面、盘子/杯子位置、包装位置、手部比例、食物切面方向保持连续。",
        "role": "anonymous adult hand model preparing or tasting the product; mouth/face can be partial and product remains primary",
    },
    "digital": {
        "presenter_mode": "手模操作演示 + 画外音讲解",
        "result_showcase_type": "操作演示型 + 信任证明型",
        "result_frame": "必须展示插拔、连接、开关、操作、桌面/车内/通勤场景中的实际使用结果。",
        "physical": "手必须真实握住或操作产品；接口、线材、按键、屏幕、设备连接方向符合真实结构；不要让线材穿过桌面或设备。",
        "anchors": "手掌比例、桌面边缘、设备位置、接口方向、车内/办公空间参照物保持连续。",
        "role": "anonymous adult hand model operating the product in a real desk, car, travel, or home scene",
    },
    "accessory": {
        "presenter_mode": "真人佩戴展示 + 画外音或轻口播",
        "result_showcase_type": "穿戴效果型",
        "result_frame": "必须展示佩戴后的整体氛围、近景光泽和搭配效果。",
        "physical": "饰品必须真实佩戴在耳朵、脖颈、手腕、手指、头发或衣物上；扣具、链条、镜架、表带与身体/衣物接触真实；不能漂浮。",
        "anchors": "脸部/脖颈/手腕/手指比例、衣领位置、光源方向和反光角度保持连续。",
        "role": "anonymous adult model wearing the accessory; face is secondary and product detail is primary",
    },
    "family": {
        "presenter_mode": "家长/手模/宠物互动演示 + 画外音",
        "result_showcase_type": "场景完成型 + 信任证明型",
        "result_frame": "必须展示宝宝/宠物/家长在真实家庭场景中的省心使用结果。",
        "physical": "产品与宝宝/宠物/家长手部/地面/家具真实接触；圆角、柔软、收纳或清洁动作符合真实照护逻辑；不做危险动作。",
        "anchors": "地面、沙发、婴儿床、宠物活动区、手部比例和产品位置保持连续。",
        "role": "anonymous adult caregiver or hand model interacting safely with the product; child/pet framing remains gentle and safe",
    },
    "sports": {
        "presenter_mode": "真人运动/户外演示 + 画外音",
        "result_showcase_type": "操作演示型 + 场景完成型",
        "result_frame": "必须展示穿戴、跑跳、拉伸、收纳、搭建、携带或户外使用后的真实结果。",
        "physical": "产品与身体、地面、器械、背包、帐篷或户外环境真实接触；支撑、扣具、防滑、拉伸动作符合物理逻辑；不做危险极限动作。",
        "anchors": "身体比例、地面接触点、器械/帐篷/背包位置、户外地平线保持连续。",
        "role": "anonymous adult sports or outdoor model using the product safely in a real action scene",
    },
    "general": {
        "presenter_mode": "按产品功能选择手模/真人演示 + 画外音",
        "result_showcase_type": "操作演示型",
        "result_frame": "必须展示真人手部或身体参与的真实使用过程和一个明确使用结果，不允许纯静物旋转。",
        "physical": "产品必须与手、桌面、身体、容器、工具或使用空间真实接触；动作简单可执行；不能漂浮、不能穿模、不能凭空变形。",
        "anchors": "手部比例、桌面/地面/墙面/容器边缘、产品位置和光源方向保持连续。",
        "role": "anonymous adult hand model or lifestyle model demonstrating the product in a real use scene",
    },
}

PRODUCT_IDENTITY_LOCKS = [
    "same color and color blocks",
    "same silhouette and shape",
    "same size ratio relative to hands/body/furniture",
    "same packaging structure",
    "same logo or label position when visible",
    "same printed pattern and texture direction when visible",
    "same material finish and surface texture",
    "same accessories, parts, openings, buttons, zippers, bottle cap, interface, or connectors",
    "no new colors, no new decorations, no extra parts, no missing parts",
]

RESULT_TYPE_HINTS = {
    "穿戴效果型": "Show the item worn or carried on a real person, including full effect and motion.",
    "使用前后型": "Show the problem state, the use process, and the visible after result with stable anchors.",
    "场景完成型": "Show the product placed into a real space and the completed scene result.",
    "操作演示型": "Show a real person or hand model operating the product with one clear action per shot.",
    "感官体验型": "Show visible sensory details such as texture, steam, cutaway, foam, shine, softness, or taste moment.",
    "信任证明型": "Show detail proof and safe everyday use without unsupported claims.",
}


def result_showcase_hint(result_type: str) -> str:
    hints = [hint for key, hint in RESULT_TYPE_HINTS.items() if key in result_type]
    return " ".join(dict.fromkeys(hints)) if hints else RESULT_TYPE_HINTS["操作演示型"]

UNSUPPORTED_TERMS = [
    "100%", "永久", "治愈", "治疗", "医用", "抗菌", "抑菌", "第一", "最强", "全网最低",
    "认证", "专利", "保证", "guaranteed", "cure", "medical", "antibacterial", "certified", "best", "number one",
]


def round_half_up(value: float) -> int:
    return int(math.floor(value + 0.5))


def normalize_duration(value: Any) -> int:
    duration = round_half_up(float(value))
    if duration < 4 or duration > 15:
        raise ValueError(f"duration must be 4-15 seconds after rounding; got {value!r}")
    return duration


def clean_points(points: list[str]) -> tuple[list[str], list[str]]:
    safe: list[str] = []
    warnings: list[str] = []
    for point in points:
        text = point.strip()
        if not text:
            continue
        found = [term for term in UNSUPPORTED_TERMS if term.lower() in text.lower()]
        if found:
            warnings.append(f"Removed unsupported or proof-sensitive selling point: {text} ({', '.join(found)})")
            continue
        safe.append(text)
    return safe, warnings


def scaled_marks(duration: int) -> list[tuple[float, float]]:
    base = [(0, 2), (2, 5), (5, 8), (8, 11.5), (11.5, 15)]
    factor = duration / 15
    marks = [(round(start * factor, 2), round(end * factor, 2)) for start, end in base]
    marks[-1] = (marks[-1][0], float(duration))
    return marks


def text_for_point(points: list[str], index: int) -> str:
    return points[index] if index < len(points) else ""


def spoken_benefit(points: list[str], index: int, fallback: str) -> str:
    point = text_for_point(points, index)
    return point if point else fallback


def sticker_intent(points: list[str], index: int, fallback: str) -> str:
    point = text_for_point(points, index)
    if point:
        return f"Readable sticker text from user-provided selling point: {point}"
    return fallback


def build_brief(args: argparse.Namespace) -> dict[str, Any]:
    platform_key = args.platform.lower()
    platform = PLATFORMS.get(platform_key, PLATFORMS["douyin"])
    category_key = args.category.lower()
    category = CATEGORY_HINTS.get(category_key, CATEGORY_HINTS["general"])
    rules = CATEGORY_RULES.get(category_key, CATEGORY_RULES["general"])
    duration = normalize_duration(args.duration)
    ratio = args.ratio or platform["ratio"]
    safe_points, warnings = clean_points(args.selling_point or [])
    if not safe_points:
        warnings.append("No safe user selling points were provided; do not invent selling-point copy. Use visible product facts only.")
    constraints = (
        "Product photos are the only product identity source. Keep the exact same product identity in every shot: "
        + "; ".join(PRODUCT_IDENTITY_LOCKS)
        + ". The storyboard sheet controls camera, scene, action, and result only; it must not redesign the product."
    )
    physical_constraints = (
        f"Presenter mode: {rules['presenter_mode']}. Result type: {rules['result_showcase_type']}. "
        f"Must-show result frame: {rules['result_frame']} Physical contact rule: {rules['physical']} "
        f"Space anchor rule: {rules['anchors']} Each shot has only one main action."
    )
    marks = scaled_marks(duration)
    voice_lines = [
        f"这个{args.product_name}，先看真实使用场景里的效果。",
        f"{spoken_benefit(safe_points, 0, '使用方式会直接在画面里演示')}。",
        f"{spoken_benefit(safe_points, 1, '放到真实使用场景里看效果')}。",
        f"镜头会拍清外观、结构和关键细节。",
        f"{args.target_audience or '日常需要提升体验的人'}可以重点看看，{platform['cta']}。",
    ]
    if args.voiceover_language.startswith("en") or platform_key in {"tiktok_shop", "amazon", "shopify"}:
        voice_lines = [
            f"Meet {args.product_name}, shown clearly with real product details.",
            f"{spoken_benefit(safe_points, 0, 'Watch the product in a direct use demo')}.",
            f"{spoken_benefit(safe_points, 1, 'See how it works in a real everyday scene')}.",
            "Show the visible details, structure, and product finish.",
            f"For {args.target_audience or 'everyday shoppers'}, {platform['cta']}.",
        ]
    shot_purposes = [
        f"首秒钩子：展示{category['hook']}",
        "核心卖点 1：动作演示解决痛点",
        "核心卖点 2：场景化使用或前后对比",
        f"证明镜头：{category['proof']}",
        "适用人群与 CTA 转化",
    ]
    visuals = [
        f"真人或手模在真实场景中立刻展示{category['hook']}，不要纯静物旋转。",
        f"真人/手模执行一个清楚动作：{category['demo']}，产品与身体或空间真实接触。",
        f"展示购买者关心的结果画面：{rules['result_frame']}",
        f"近景证明镜头：{category['proof']}，保持真实比例和接触关系。",
        "真人/手模完成最后一个使用动作，产品停留在真实结果场景中，配合 CTA 收尾。",
    ]
    stickers = [
        "",
        sticker_intent(safe_points, 0, ""),
        sticker_intent(safe_points, 1, ""),
        "",
        f"CTA lockup: {platform['cta']}",
    ]
    sounds = ["quick opening hit", "product handling tap/pop", "soft transition whoosh", "detail accent tap", "CTA accent"]
    shot_plan: list[dict[str, Any]] = []
    voiceover: list[dict[str, Any]] = []
    text_layer: list[dict[str, Any]] = []
    for i, (start, end) in enumerate(marks):
        shot_plan.append({
            "start": start,
            "end": end,
            "purpose": shot_purposes[i],
            "visual": visuals[i],
            "framing": "stable ecommerce framing; product remains readable and not cropped",
            "camera": "simple stable push-in or cut; avoid complex camera moves",
            "action": visuals[i],
            "model_or_host_role": rules["role"],
            "sticker_overlay": stickers[i],
            "sound_effect": sounds[i],
            "product_fidelity": constraints,
            "physical_scene": physical_constraints,
            "space_anchor": rules["anchors"],
            "result_frame_requirement": rules["result_frame"],
            "single_action_rule": "Only one main action in this shot; avoid combining multiple actions that can cause physics errors.",
        })
        voiceover.append({"start": start, "end": end, "text": voice_lines[i]})
        if stickers[i]:
            text_layer.append({"start": start, "end": end, "text": stickers[i]})
    return {
        "mode": "product_selling_video",
        "product_name": args.product_name,
        "platform": platform_key if platform_key in PLATFORMS else "douyin",
        "platform_name": platform["name"],
        "category": category_key if category_key in CATEGORY_HINTS else "general",
        "target_audience": args.target_audience or "",
        "style": args.style or "",
        "selling_points": safe_points,
        "duration": duration,
        "ratio": ratio,
        "resolution": args.resolution,
        "voiceover_language": args.voiceover_language,
        "voiceover_policy": {"enabled": not args.no_voiceover, "style": platform["voice"]},
        "caption_layer_policy": {"mode": args.caption_mode},
        "presenter_mode": rules["presenter_mode"],
        "result_showcase_type": rules["result_showcase_type"],
        "product_identity_locks": PRODUCT_IDENTITY_LOCKS,
        "physical_scene_constraints": physical_constraints,
        "must_show_result_frame": rules["result_frame"],
        "result_showcase_hint": result_showcase_hint(rules["result_showcase_type"]),
        "shot_plan": shot_plan,
        "adapted_voiceover": [] if args.no_voiceover else voiceover,
        "adapted_on_screen_text": text_layer,
        "product_identity_constraints": constraints,
        "negative_constraints": [
            "No reference-video remake, no video downloading, no ASR/OCR, no blueprint, no shot-by-shot recreation.",
            "No unsupported medical, safety, antibacterial, certification, ranking, price, discount, patent, warranty, or absolute claims.",
            "No platform UI, watermark, copied logo, copied captions, duplicate subtitle layer, or random unreadable text.",
            "No product-only still-life rotation. At least three shots must show a real person, hand model, real use action, or completed result scene.",
            "No floating products, no body/object intersection, no impossible scale, no changing logo/label/pattern/material across shots.",
        ],
        "warnings": warnings,
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Build a product-selling video brief")
    p.add_argument("--product-name", required=True)
    p.add_argument("--platform", default="douyin", choices=sorted(PLATFORMS))
    p.add_argument("--category", default="general", choices=sorted(CATEGORY_HINTS))
    p.add_argument("--selling-point", action="append")
    p.add_argument("--target-audience", default="")
    p.add_argument("--style", default="")
    p.add_argument("--duration", default=15)
    p.add_argument("--ratio", choices=["21:9", "16:9", "4:3", "1:1", "3:4", "9:16", "adaptive"])
    p.add_argument("--resolution", default="480p", choices=["480p", "720p", "1080p", "2K"])
    p.add_argument("--voiceover-language", default="zh-CN")
    p.add_argument("--caption-mode", default="sparse_stickers", choices=["voiceover_only", "sparse_stickers", "caption_driven", "no_readable_text"])
    p.add_argument("--no-voiceover", action="store_true")
    p.add_argument("--output-dir", required=True)
    return p


def main() -> None:
    args = parser().parse_args()
    try:
        brief = build_brief(args)
        out = Path(args.output_dir).expanduser().resolve()
        out.mkdir(parents=True, exist_ok=True)
        path = out / "selling_brief.json"
        path.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"ok": True, "brief_json": str(path), "warnings": brief.get("warnings", [])}, ensure_ascii=True, indent=2))
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "stage": "selling_brief", "error": str(exc)}, ensure_ascii=True, indent=2))
        raise SystemExit(2)


if __name__ == "__main__":
    main()
