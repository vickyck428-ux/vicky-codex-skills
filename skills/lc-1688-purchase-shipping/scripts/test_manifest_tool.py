#!/usr/bin/env python3
"""Offline unit tests for manifest_tool.py."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import manifest_tool


class ManifestToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.source_a = self.root / "order-a.png"
        self.source_b = self.root / "order-b.png"
        self.product = self.root / "product.png"
        self.source_a.write_bytes(b"order-a")
        self.source_b.write_bytes(b"order-b")
        self.product.write_bytes(b"product")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def manifest(self) -> dict:
        return {
            "schema_version": 1,
            "batch": {
                "batch_id": "test-batch",
                "source_files": [str(self.source_a), str(self.source_b)],
            },
            "items": [
                {
                    "source_index": "001",
                    "payment_status": "已下单",
                    "purchase_status": "待收货",
                    "product_name": "测试包",
                    "spec": "黑色",
                    "ordered_qty": 2,
                    "supplier": "测试供应商",
                    "source_screenshot": str(self.source_a),
                    "product_image": str(self.product),
                    "issues": [],
                },
                {
                    "source_index": "002",
                    "payment_status": "待付款",
                    "purchase_status": "待付款",
                    "product_name": "待付款包",
                    "spec": "蓝色",
                    "ordered_qty": 5,
                    "supplier": "测试供应商",
                    "source_screenshot": str(self.source_b),
                    "product_image": str(self.product),
                    "issues": [],
                },
            ],
            "excluded": [{"reason": "shopping_cart", "product_name": "购物车商品"}],
        }

    def test_fingerprint_is_input_order_independent(self) -> None:
        first = manifest_tool.batch_fingerprint([self.source_a, self.source_b])
        second = manifest_tool.batch_fingerprint([self.source_b, self.source_a])
        self.assertEqual(first, second)
        self.assertEqual(64, len(first))

    def test_prepare_assigns_stable_ids_and_preserves_existing_id(self) -> None:
        data = self.manifest()
        first = manifest_tool.prepare_manifest(data, self.root)
        second = manifest_tool.prepare_manifest(data, self.root)
        self.assertEqual(
            [item["detail_id"] for item in first["items"]],
            [item["detail_id"] for item in second["items"]],
        )
        data["items"][0]["detail_id"] = "legacy-001"
        preserved = manifest_tool.prepare_manifest(data, self.root)
        self.assertEqual("legacy-001", preserved["items"][0]["detail_id"])

    def test_quantity_change_does_not_change_new_detail_id(self) -> None:
        data = self.manifest()
        original = manifest_tool.prepare_manifest(data, self.root)
        changed = self.manifest()
        changed["items"][0]["ordered_qty"] = 9
        corrected = manifest_tool.prepare_manifest(changed, self.root)
        self.assertEqual(
            original["items"][0]["detail_id"], corrected["items"][0]["detail_id"]
        )

    def test_validate_summary_and_payload(self) -> None:
        prepared = manifest_tool.prepare_manifest(self.manifest(), self.root)
        self.assertEqual(
            [], manifest_tool.validate_manifest(prepared, self.root, require_images=True)
        )
        summary = manifest_tool.summarize(prepared)
        self.assertEqual(2, summary["row_count"])
        self.assertEqual(7, summary["total_quantity"])
        self.assertEqual(1, summary["pending_row_count"])
        self.assertEqual(5, summary["pending_quantity"])
        self.assertEqual(1, summary["excluded_count"])
        payload = manifest_tool.build_payload(prepared, self.root)
        self.assertEqual("dry-run", payload["mode"])
        self.assertEqual("明细ID", payload["match_field"])
        self.assertEqual(2, payload["record_count"])
        self.assertNotIn("Amazon计划数", payload["records"][0]["fields"])

    def test_blocking_issue_and_status_mismatch_fail_validation(self) -> None:
        data = self.manifest()
        data["items"][0]["issues"] = [
            {"code": "uncertain_qty", "message": "数量被遮挡", "blocking": True}
        ]
        data["items"][1]["purchase_status"] = "待收货"
        prepared = manifest_tool.prepare_manifest(data, self.root)
        errors = manifest_tool.validate_manifest(prepared, self.root, False)
        self.assertTrue(any("阻塞疑点" in error for error in errors))
        self.assertTrue(any("付款状态与采购状态不一致" in error for error in errors))

    def test_duplicate_signature_requires_review(self) -> None:
        data = self.manifest()
        duplicate = json.loads(json.dumps(data["items"][0], ensure_ascii=False))
        duplicate["source_index"] = "003"
        data["items"].append(duplicate)
        prepared = manifest_tool.prepare_manifest(data, self.root)
        self.assertEqual(2, prepared["items"][2]["occurrence_index"])
        errors = manifest_tool.validate_manifest(prepared, self.root, False)
        self.assertTrue(any("possible_duplicate" in error for error in errors))

    def test_from_tsv_can_keep_extra_evidence_and_exclusion(self) -> None:
        tsv = self.root / "manifest.tsv"
        tsv.write_text(
            "编号\t付款状态\t订单状态\t商品名称\t规格/SKU\t订购数\t供应商"
            "\t源订单截图\t商品图文件\n"
            "001\t已下单\t待收货\t测试包\t黑色\t2\t测试供应商"
            "\torder-a.png\tproduct.png\n",
            encoding="utf-8",
        )
        args = SimpleNamespace(
            input=str(tsv),
            source_root=str(self.root),
            image_root=str(self.root),
            batch_id="legacy",
            extra_source=[str(self.source_b)],
            excluded=[("波点包", "shopping_cart", str(self.source_b))],
        )
        converted = manifest_tool.manifest_from_tsv(args)
        self.assertEqual("legacy-001", converted["items"][0]["detail_id"])
        self.assertEqual(2, len(converted["batch"]["source_files"]))
        self.assertEqual("shopping_cart", converted["excluded"][0]["reason"])


if __name__ == "__main__":
    unittest.main()
