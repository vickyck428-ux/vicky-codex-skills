#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import struct
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest import mock

import ark_seedance_api as api
import build_product_promo_prompt as builder
import generate_product_video as video_entry


def png(path: Path, width: int = 640, height: int = 640) -> None:
    raw = b"".join(b"\x00" + b"\xff\xff\xff" * width for _ in range(height))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)

    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


class SkillTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.image = self.root / "product.png"
        png(self.image)

    def tearDown(self):
        self.temp.cleanup()

    def args(self, **updates):
        values = dict(product_name="Generic product", image_path=[str(self.image)], image_notes="square white package with blue label",
                      storyboard_image_path=[],
                      selling_points="", audience="", platform="generic", category="other", resolution="480p",
                      duration=15, output_dir=str(self.root / "out"), generate_audio=True, voiceover=True,
                      voiceover_language="zh-CN", voiceover_style="premium Mandarin Chinese advertising narration", voiceover_script="",
                      cinematic_level="premium", model_presence="auto", storyboard_file="",
                      benchmark_style_notes="")
        values.update(updates)
        return argparse.Namespace(**values)

    def test_all_category_prompts_are_concrete(self):
        banned = ["category-relevant", "appropriate to the product", "daily use scene", "[PRODUCT"]
        for category in builder.CATEGORIES:
            with self.subTest(category=category):
                result = builder.write_artifacts(self.args(category=category, output_dir=str(self.root / category)))
                prompt = Path(result["prompt_path"]).read_text(encoding="utf-8")
                self.assertEqual(prompt.count("Shot 1 - Context Entry"), 1)
                self.assertIn("Product Memory Hero", prompt)
                self.assertIn("no captions", prompt)
                self.assertTrue(all(term.lower() not in prompt.lower() for term in banned))

    def test_platform_ratios(self):
        for platform in ("taobao", "tmall", "jd", "pinduoduo"):
            self.assertEqual(builder.PLATFORMS[platform][0], "1:1")
        for platform in ("douyin", "xiaohongshu"):
            self.assertEqual(builder.PLATFORMS[platform][0], "9:16")
        self.assertEqual(builder.PLATFORMS["amazon"][0], "16:9")
        self.assertEqual(builder.PLATFORMS["tiktok-shop"][0], "9:16")
        for platform in ("shopify", "aliexpress", "temu"):
            self.assertEqual(builder.PLATFORMS[platform][0], "1:1")

    def test_platform_aliases_and_crossborder_defaults(self):
        self.assertEqual(builder.normalize_platform("亚马逊"), "amazon")
        self.assertEqual(builder.normalize_platform("tiktokshop"), "tiktok-shop")
        self.assertEqual(builder.normalize_platform("独立站"), "shopify")
        self.assertEqual(builder.normalize_platform("速卖通"), "aliexpress")
        self.assertEqual(builder.normalize_platform("淘宝"), "taobao")
        result = builder.write_artifacts(self.args(platform="amazon", voiceover_language=None, voiceover_style=None))
        self.assertEqual(result["market"], "crossborder")
        self.assertEqual(result["voiceover_language"], "en-US")
        domestic = builder.write_artifacts(self.args(platform="tmall", voiceover_language=None, voiceover_style=None, output_dir=str(self.root / "domestic")))
        self.assertEqual(domestic["market"], "domestic")
        self.assertEqual(domestic["voiceover_language"], "zh-CN")

    def test_video_entry_default_output_name_uses_2_0(self):
        parser = video_entry.build_parser()
        args = parser.parse_args([])
        self.assertEqual(args.output_name, "xinghe-main-video-promo-2-0.mp4")

    def test_multiple_image_roles(self):
        second = self.root / "detail.png"
        png(second)
        result = builder.write_artifacts(self.args(image_path=[str(self.image), str(second)]))
        self.assertEqual([item["role"] for item in result["images"]], ["primary_identity", "alternate_view"])

    def test_missing_and_bad_images(self):
        with self.assertRaisesRegex(ValueError, "Image not found"):
            builder.write_artifacts(self.args(image_path=[str(self.root / "missing.png")]))
        bad = self.root / "bad.gif"
        bad.write_bytes(b"GIF89a")
        with self.assertRaisesRegex(ValueError, "Unsupported image format"):
            builder.write_artifacts(self.args(image_path=[str(bad)]))

    def test_claim_warning(self):
        result = builder.write_artifacts(self.args(selling_points="100% cure"))
        self.assertGreaterEqual(len(result["warnings"]), 2)
        crossborder = builder.write_artifacts(self.args(output_dir=str(self.root / "claims"), selling_points="FDA approved clinically proven No.1"))
        self.assertTrue(any("fda approved" in item.lower() for item in crossborder["warnings"]))
        chinese = builder.write_artifacts(self.args(output_dir=str(self.root / "cn-claims"), selling_points="保证治愈 第一"))
        self.assertTrue(any("治愈" in item for item in chinese["warnings"]))

    def test_input_json_preserves_utf8_text(self):
        input_json = self.root / "input.json"
        input_json.write_text(json.dumps({
            "product_name": "White packaged serum",
            "image_paths": [str(self.image)],
            "image_notes": "white bottle, silver pump, blue front label",
            "selling_points": "lightweight texture",
            "output_dir": str(self.root / "json-out"),
        }, ensure_ascii=False), encoding="utf-8")
        ns = argparse.Namespace(input_json=str(input_json), product_name=None, image_path=None, image_notes=None,
                                storyboard_image_path=None, selling_points=None, audience=None, platform=None, category=None, resolution=None,
                                duration=None, output_dir=None, generate_audio=None, voiceover=None,
                                voiceover_language=None, voiceover_style=None, voiceover_script=None,
                                cinematic_level=None, model_presence=None, storyboard_file=None,
                                benchmark_style_notes=None)
        result = builder.write_artifacts(ns)
        prompt = Path(result["prompt_path"]).read_text(encoding="utf-8")
        self.assertIn("White packaged serum", prompt)
        self.assertIn("lightweight texture", prompt)
        self.assertEqual(result["voiceover_language"], "zh-CN")

    def test_input_json_accepts_utf8_bom(self):
        input_json = self.root / "bom-input.json"
        payload = json.dumps({
            "product_name": "White packaged product",
            "image_paths": [str(self.image)],
            "output_dir": str(self.root / "bom-out"),
        }, ensure_ascii=False)
        input_json.write_text(payload, encoding="utf-8-sig")
        ns = argparse.Namespace(input_json=str(input_json), product_name=None, image_path=None, image_notes=None,
                                storyboard_image_path=None, selling_points=None, audience=None, platform=None, category=None, resolution=None,
                                duration=None, output_dir=None, generate_audio=None, voiceover=None,
                                voiceover_language=None, voiceover_style=None, voiceover_script=None,
                                cinematic_level=None, model_presence=None, storyboard_file=None,
                                benchmark_style_notes=None)
        result = builder.write_artifacts(ns)
        self.assertEqual(result["product_name"], "White packaged product")

    def test_input_json_relative_paths_and_string_booleans(self):
        nested = self.root / "json"
        nested.mkdir()
        image = nested / "relative.png"
        png(image)
        input_json = nested / "input.json"
        input_json.write_text(json.dumps({
            "product_name": "Relative path product",
            "image_paths": ["relative.png"],
            "output_dir": "out",
            "voiceover": "false",
            "generate_audio": "true",
        }, ensure_ascii=False), encoding="utf-8")
        ns = argparse.Namespace(input_json=str(input_json), product_name=None, image_path=None, image_notes=None,
                                storyboard_image_path=None, selling_points=None, audience=None, platform=None, category=None, resolution=None,
                                duration=None, output_dir=None, generate_audio=None, voiceover=None,
                                voiceover_language=None, voiceover_style=None, voiceover_script=None,
                                cinematic_level=None, model_presence=None, storyboard_file=None,
                                benchmark_style_notes=None)
        result = builder.write_artifacts(ns)
        self.assertEqual(Path(result["images"][0]["path"]), image.resolve())
        self.assertEqual(Path(result["manifest_path"]).parent, (nested / "out").resolve())
        self.assertFalse(result["voiceover"])
        self.assertTrue(result["generate_audio"])

    def test_default_voiceover_and_no_voiceover(self):
        voiced = builder.write_artifacts(self.args(output_dir=str(self.root / "voiced")))
        voiced_prompt = Path(voiced["prompt_path"]).read_text(encoding="utf-8")
        self.assertIn("Generate advertising-film voiceover in Mandarin Chinese", voiced_prompt)
        self.assertTrue(voiced["voiceover"])

        music_only = builder.write_artifacts(self.args(output_dir=str(self.root / "music"), voiceover=False))
        music_prompt = Path(music_only["prompt_path"]).read_text(encoding="utf-8")
        self.assertIn("premium instrumental background music", music_prompt)
        self.assertIn("No speech, no voiceover", music_prompt)
        self.assertFalse(music_only["voiceover"])

    def test_no_audio_disables_voiceover_manifest_state(self):
        result = builder.write_artifacts(self.args(output_dir=str(self.root / "silent"), generate_audio=False, voiceover=True))
        prompt = Path(result["prompt_path"]).read_text(encoding="utf-8")
        self.assertIn("Generate silent video", prompt)
        self.assertFalse(result["voiceover"])
        self.assertFalse(result["generate_audio"])

    def test_voiceover_script_is_included(self):
        result = builder.write_artifacts(self.args(output_dir=str(self.root / "script"), voiceover_script="See the real texture, choose a calm daily experience."))
        prompt = Path(result["prompt_path"]).read_text(encoding="utf-8")
        self.assertIn("Use this user-provided voiceover script", prompt)
        self.assertIn("See the real texture", prompt)
        self.assertIn("voiceover_script", result)

    def test_voiceover_language_variants(self):
        english = builder.write_artifacts(self.args(output_dir=str(self.root / "en"), voiceover_language="en-US"))
        japanese = builder.write_artifacts(self.args(output_dir=str(self.root / "ja"), voiceover_language="ja-JP"))
        self.assertIn("American English", Path(english["prompt_path"]).read_text(encoding="utf-8"))
        self.assertIn("Japanese", Path(japanese["prompt_path"]).read_text(encoding="utf-8"))

    def test_auto_category_avoids_single_character_packaging_match(self):
        self.assertEqual(builder.infer_category("white packaged product", "square package box"), "other")
        self.assertEqual(builder.infer_category("minimal leather handbag", ""), "apparel-accessories")

    def test_explicit_category_overrides_auto(self):
        result = builder.write_artifacts(self.args(category="beauty-personal-care"))
        self.assertEqual(result["category"], "beauty-personal-care")

    def test_prompt_contains_premium_constraints(self):
        result = builder.write_artifacts(self.args())
        prompt = Path(result["prompt_path"]).read_text(encoding="utf-8")
        self.assertIn("PRODUCT IDENTITY IS NON-NEGOTIABLE", prompt)
        self.assertIn("premium advertising-film cinematography", prompt)
        self.assertIn("premium instrumental ambience", prompt)
        self.assertIn("Preserve the exact product silhouette", prompt)
        self.assertIn("one coherent physical location", prompt)
        self.assertIn("final frame suitable for inspection", prompt)

    def test_prompt_contains_experiential_model_rules(self):
        result = builder.write_artifacts(self.args(category="beauty-personal-care", model_presence="lifestyle-model"))
        prompt = Path(result["prompt_path"]).read_text(encoding="utf-8")
        self.assertIn("Storyboard-controlled commercial", prompt)
        self.assertIn("director-designed shot count", prompt)
        self.assertIn("Shot 1 - Context Entry", prompt)
        self.assertIn("Ritual Experience", prompt)
        self.assertIn("partial framing", prompt)
        self.assertIn("Do not: show before/after results, skin improvement", prompt)
        self.assertIn("Follow this storyboard exactly", prompt)
        self.assertIn("Each shot card has time, director intent, scene style", prompt)
        self.assertEqual(result["model_presence"], "lifestyle-model")

    def test_storyboard_artifact_and_custom_storyboard(self):
        custom = self.root / "storyboard.md"
        custom.write_text("# Custom storyboard\nShot 1 - custom controlled entry", encoding="utf-8")
        result = builder.write_artifacts(self.args(output_dir=str(self.root / "story"), storyboard_file=str(custom)))
        storyboard = Path(result["storyboard_path"]).read_text(encoding="utf-8")
        prompt = Path(result["prompt_path"]).read_text(encoding="utf-8")
        self.assertIn("Custom storyboard", storyboard)
        self.assertIn("Custom storyboard", prompt)
        self.assertIn("storyboard_path", result)

    def test_storyboard_images_are_uploaded_after_product_reference(self):
        board = self.root / "storyboard.png"
        png(board)
        result = builder.write_artifacts(self.args(output_dir=str(self.root / "storyboard-image"), storyboard_image_path=[str(board)]))
        roles = [item["role"] for item in result["images"]]
        self.assertEqual(roles, ["primary_identity", "storyboard_reference_1"])
        self.assertEqual(result["storyboard_image_status"], "provided")
        prompt = Path(result["prompt_path"]).read_text(encoding="utf-8")
        self.assertIn("Storyboard control images are provided", prompt)
        self.assertIn("never copy their product details", prompt)

    def test_storyboard_image_prompt_and_requested_status(self):
        result = builder.write_artifacts(self.args(output_dir=str(self.root / "storyboard-request"), generate_storyboard_image=True))
        self.assertEqual(result["storyboard_image_status"], "requested")
        prompt_path = Path(result["storyboard_image_prompt_path"])
        self.assertTrue(prompt_path.is_file())
        prompt = prompt_path.read_text(encoding="utf-8")
        self.assertIn("director storyboard control sheet", prompt)
        self.assertIn("Do not add marketing slogans", prompt)

    def test_xinghe_helper_missing_requests_imagegen_fallback(self):
        result = builder.write_artifacts(self.args(output_dir=str(self.root / "fallback"), generate_storyboard_image=True))
        with mock.patch.dict(os.environ, {"XINGHE_IMAGE_GENERATOR": str(self.root / "missing.ps1")}):
            ok, update = video_entry.try_generate_storyboard_image(result, Path(result["manifest_path"]).parent)
        self.assertFalse(ok)
        self.assertEqual(update["storyboard_image_status"], "needs_imagegen_fallback")
        self.assertIn("storyboard_image_target_path", update)

    def test_xinghe_helper_success_adds_generated_status(self):
        out = self.root / "helper-success"
        result = builder.write_artifacts(self.args(output_dir=str(out), generate_storyboard_image=True))
        helper = self.root / "helper.ps1"
        helper.write_text(
            "param($PromptFile, [string[]]$ReferenceImage, $OutputDir, $Size, $FileName)\n"
            "$bytes=[Convert]::FromBase64String('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAFgwJ/lJ7mWQAAAABJRU5ErkJggg==')\n"
            "[IO.File]::WriteAllBytes((Join-Path $OutputDir $FileName), $bytes)\n",
            encoding="utf-8",
        )
        with mock.patch.dict(os.environ, {"XINGHE_IMAGE_GENERATOR": str(helper)}):
            ok, update = video_entry.try_generate_storyboard_image(result, out)
        self.assertTrue(ok)
        self.assertEqual(update["storyboard_image_status"], "xinghe_generated")
        self.assertTrue(Path(update["storyboard_image_path"]).is_file())

    def test_benchmark_style_notes_are_in_storyboard_and_prompt(self):
        result = builder.write_artifacts(self.args(
            output_dir=str(self.root / "benchmark"),
            benchmark_style_notes="match a glossy pale-green skincare benchmark with water reflections"))
        storyboard = Path(result["storyboard_path"]).read_text(encoding="utf-8")
        prompt = Path(result["prompt_path"]).read_text(encoding="utf-8")
        self.assertIn("glossy pale-green skincare benchmark", storyboard)
        self.assertIn("glossy pale-green skincare benchmark", prompt)
        self.assertIn("benchmark_style_notes", result)

    def test_storyboard_shot_count_varies_by_category(self):
        beauty = builder.write_artifacts(self.args(category="beauty-personal-care", output_dir=str(self.root / "beauty")))
        other = builder.write_artifacts(self.args(category="other", output_dir=str(self.root / "other-story")))
        beauty_storyboard = Path(beauty["storyboard_path"]).read_text(encoding="utf-8")
        other_storyboard = Path(other["storyboard_path"]).read_text(encoding="utf-8")
        self.assertIn("Shot count decision: use 6 shots", beauty_storyboard)
        self.assertIn("Shot count decision: use 5 shots", other_storyboard)
        self.assertIn("Do not force a fixed five-shot template", beauty_storyboard)

    def test_storyboard_contains_director_shot_card_fields(self):
        result = builder.write_artifacts(self.args(
            category="beauty-personal-care",
            output_dir=str(self.root / "shot-cards"),
            benchmark_style_notes="pale green water-glass luxury skincare scene"))
        storyboard = Path(result["storyboard_path"]).read_text(encoding="utf-8")
        for required in [
            "Storyboard role: this is the director shot list",
            "Director shot-card schema:",
            "Time:",
            "Director intent:",
            "Scene style:",
            "Main subject:",
            "Action beat:",
            "Camera movement:",
            "Lighting / premium cue:",
            "Sound / voiceover timing:",
            "Transition:",
            "Product consistency lock:",
            "Storyboard control image requirements:",
            "shot number, time range, camera movement, main action beat, and scene/style cue",
        ]:
            self.assertIn(required, storyboard)
        self.assertIn("pale green water-glass luxury skincare scene", storyboard)
        self.assertIn("same silhouette, proportions, color, material", storyboard)

    def test_no_voiceover_storyboard_uses_no_voiceover_timing(self):
        result = builder.write_artifacts(self.args(
            output_dir=str(self.root / "shot-card-no-voice"),
            voiceover=False))
        storyboard = Path(result["storyboard_path"]).read_text(encoding="utf-8")
        self.assertIn("no voiceover", storyboard)
        prompt = Path(result["prompt_path"]).read_text(encoding="utf-8")
        self.assertNotIn("synchronized with the five shots", prompt)

    def test_http_error_is_structured(self):
        exc = __import__("urllib.error").error.HTTPError("https://example", 429, "rate", {}, None)
        exc.read = mock.Mock(return_value=b"rate limited")
        with mock.patch.dict(os.environ, {"ARK_API_KEY": "test"}), mock.patch("urllib.request.urlopen", side_effect=exc):
            with self.assertRaises(api.ArkError) as caught:
                api.request_json("GET", "/test")
        self.assertEqual(caught.exception.as_dict()["http_status"], 429)

    def test_timeout_is_structured(self):
        with mock.patch.dict(os.environ, {"ARK_API_KEY": "test"}), mock.patch("urllib.request.urlopen", side_effect=TimeoutError("late")):
            with self.assertRaises(api.ArkError) as caught:
                api.request_json("GET", "/test")
        self.assertEqual(caught.exception.as_dict()["stage"], "network")

    def test_task_poll_timeout_is_structured(self):
        with mock.patch.object(api, "request_json", return_value={"id": "task-1"}):
            with self.assertRaises(api.ArkError) as caught:
                api.generate_video(prompt="test", image_paths=[self.image], output=self.root / "video.mp4",
                                   model="model", ratio="1:1", resolution="480p", duration=15,
                                   generate_audio=True, interval=0, timeout=0)
        self.assertEqual(caught.exception.as_dict()["stage"], "poll")

    def test_missing_api_key_is_structured(self):
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(api.os, "name", "posix"):
            with self.assertRaises(api.ArkError) as caught:
                api.api_key()
        self.assertEqual(caught.exception.as_dict()["stage"], "preflight")

    def test_download_rejects_http(self):
        with self.assertRaises(api.ArkError):
            api.safe_download("http://example.com/video.mp4", self.root / "video.mp4")


if __name__ == "__main__":
    unittest.main(verbosity=2)
