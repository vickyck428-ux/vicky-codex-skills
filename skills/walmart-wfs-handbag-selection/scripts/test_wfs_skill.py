#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import sqlite3
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch
from datetime import datetime

from audit_state import audit
from portable_batch import FIELDNAMES, initialize, inspect_batch, pack
from runtime_common import SKILL_ROOT, build_context
from validate_config import is_strict_womens_handbag_keyword, validate
from wfs_skillctl import BEIJING, main as skillctl_main, readonly_validation


class WfsSkillTests(unittest.TestCase):
    def fixture(self, temp: Path, *, schedule_enabled: bool = False, operations_paused: bool = False) -> Path:
        runner = temp / "runner"
        runtime = temp / "runtime"
        crawl_skill = temp / "crawl-skill"
        (runner / "config").mkdir(parents=True)
        (runner / "scripts").mkdir()
        (runtime / "config").mkdir(parents=True)
        (runtime / "inputs").mkdir()
        (runtime / "state").mkdir()
        (runtime / "outputs").mkdir()
        crawl_skill.mkdir()
        (runner / "scripts" / "run_wfs_handbag_incremental.py").write_text("# fixture\n", encoding="utf-8")
        (runner / "lc-amazon-data-crawl.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        (crawl_skill / "SKILL.md").write_text("---\nname: crawl\ndescription: fixture\n---\n", encoding="utf-8")

        keyword_master = runtime / "inputs" / "wfs_handbag_keywords_master.csv"
        shutil.copyfile(SKILL_ROOT / "assets" / "inputs" / "keywords-master.csv", keyword_master)
        selection_config = runtime / "config" / "wfs_handbag_selection.json"
        selection_config.write_text(json.dumps({
            "keyword_master_file": str(keyword_master),
            "formal_keyword_min": 60,
            "formal_keyword_min_per_pool": 30,
            "pilot_keyword_count": 10,
            "core_thresholds": {
                "amazon_price_min": 25,
                "amazon_sales_30d_min": 150,
                "amazon_sales_30d_max": 600,
            },
            "benchmark_candidate_share_max": 0.2,
            "walmart_markets": ["US", "CA"],
            "no_marketplace_mutations": True,
        }), encoding="utf-8")
        incremental_config = runtime / "config" / "wfs_handbag_incremental.json"
        incremental_config.write_text(json.dumps({
            "selection_config_file": str(selection_config),
            "database_file": str(runtime / "state" / "wfs_incremental.sqlite3"),
            "output_root": str(runtime / "outputs"),
            "smoke_keywords": ["leather shoulder bag for women", "y2k shoulder bag"],
            "smoke_pages_per_keyword": 3,
            "daily_keywords_per_pool": 2,
            "keyword_cooldown_days": 28,
            "required_field_coverage": 0.8,
            "amazon_delivery_postal_code": "10001",
            "operations_paused": operations_paused,
            "no_marketplace_mutations": True,
        }), encoding="utf-8")
        config = temp / "wfs-local.json"
        config.write_text(json.dumps({
            "schema_version": 1,
            "runner_root": str(runner),
            "incremental_config": str(incremental_config),
            "selection_config": str(selection_config),
            "keyword_master": str(keyword_master),
            "ledger_database": str(runtime / "state" / "wfs_incremental.sqlite3"),
            "output_root": str(runtime / "outputs"),
            "feishu_integrations_file": str(runtime / "config" / "feishu.json"),
            "lc_amazon_data_crawl_skill": str(crawl_skill),
            "markets": {"US": {"postal_code": "10001"}, "CA": {"postal_code": "M5V 2T6"}},
            "schedule_enabled": schedule_enabled,
            "operations_paused": operations_paused,
            "no_marketplace_mutations": True,
        }), encoding="utf-8")
        return config

    def test_valid_external_config_and_keyword_template_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            context = build_context(config_path=self.fixture(Path(temp_dir)))
            result = validate(context)
            self.assertEqual("PASS", result["status"], result["errors"])
            self.assertEqual({"MAINSTREAM": 40, "STYLE": 40}, result["checks"]["keywords"]["pools"])

    def test_schedule_cannot_be_enabled_during_migration(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            context = build_context(config_path=self.fixture(Path(temp_dir), schedule_enabled=True))
            result = validate(context)
            self.assertEqual("FAIL", result["status"])
            self.assertTrue(any("schedule_enabled" in item for item in result["errors"]))

    def test_audit_reports_blocked_smoke_without_mutating_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            context = build_context(config_path=self.fixture(Path(temp_dir)))
            database = context["ledger_database"]
            connection = sqlite3.connect(database)
            connection.executescript("""
                CREATE TABLE runs (
                  run_id TEXT, run_date TEXT, mode TEXT, status TEXT, requested_pages INTEGER,
                  completed_pages INTEGER, raw_records INTEGER, unique_asins INTEGER,
                  report_hash TEXT, error TEXT, updated_at TEXT, run_dir TEXT
                );
                CREATE TABLE run_keywords (keyword TEXT);
                CREATE TABLE products (asin TEXT);
                CREATE TABLE observations (asin TEXT);
                CREATE TABLE deliveries (idempotency_key TEXT);
            """)
            connection.execute(
                "INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                ("smoke", "2026-08-05", "TECHNICAL_SMOKE_TEST", "BLOCKED", 6, 0, 0, 0,
                 "hash", "verification_timeout", "2026-08-05T10:00:00+08:00", str(context["output_root"] / "runs" / "smoke")),
            )
            connection.commit()
            connection.close()
            result = audit(context)
            self.assertEqual("BLOCKED", result["technical_smoke"]["status"])
            self.assertEqual(0, result["technical_smoke"]["completed_pages"])
            self.assertFalse(result["formal_daily_ready"])

    def test_doctor_cli_passes_with_external_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self.fixture(Path(temp_dir))
            output = StringIO()
            with patch.object(sys, "argv", ["wfs_skillctl.py", "doctor", "--config", str(config)]), redirect_stdout(output):
                code = skillctl_main()
            self.assertEqual(0, code)
            self.assertEqual("PASS", json.loads(output.getvalue())["status"])

    def test_live_daily_fails_closed_before_smoke_and_keyword_gates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self.fixture(Path(temp_dir))
            output = StringIO()
            with patch.object(sys, "argv", ["wfs_skillctl.py", "daily", "--config", str(config)]), redirect_stdout(output):
                code = skillctl_main()
            self.assertEqual(2, code)
            self.assertEqual(
                ["SMOKE_TEST_NOT_PASSED", "KEYWORD_GATE_NOT_PASSED"],
                json.loads(output.getvalue())["reasons"],
            )

    def test_pause_blocks_daily_before_operational_gates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self.fixture(Path(temp_dir), operations_paused=True)
            output = StringIO()
            with patch.object(sys, "argv", ["wfs_skillctl.py", "daily", "--config", str(config)]), redirect_stdout(output):
                code = skillctl_main()
            self.assertEqual(2, code)
            self.assertEqual("OPERATIONS_PAUSED", json.loads(output.getvalue())["reason"])

    def test_paused_readonly_validation_enforces_window_and_idempotence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self.fixture(Path(temp_dir), operations_paused=True)
            context = build_context(config_path=config)
            outside = datetime(2026, 8, 10, 9, 30, tzinfo=BEIJING)
            output = StringIO()
            with redirect_stdout(output):
                code = readonly_validation(context, "2026-08-10", outside)
            self.assertEqual(2, code)
            self.assertEqual("OUTSIDE_READONLY_VALIDATION_WINDOW", json.loads(output.getvalue())["reason"])

            inside = datetime(2026, 8, 10, 10, 0, tzinfo=BEIJING)
            with patch("wfs_skillctl.run_controller", return_value=0):
                first = StringIO()
                with redirect_stdout(first):
                    self.assertEqual(0, readonly_validation(context, "2026-08-10", inside))
                second = StringIO()
                with redirect_stdout(second):
                    self.assertEqual(0, readonly_validation(context, "2026-08-10", inside))
            self.assertEqual("SUCCESS", json.loads(first.getvalue())["status"])
            self.assertEqual("ALREADY_VALIDATED", json.loads(second.getvalue())["status"])

    def fill_portable_rows(self, batch_dir: Path, *, wfs_count: int = 4) -> None:
        import csv

        rows = []
        for index in range(30):
            row = {field: "" for field in FIELDNAMES}
            row.update({
                "product_group_key": f"group-{index:02d}",
                "pool": "MAINSTREAM" if index < 15 else "STYLE",
                "candidate_id": f"candidate-{index:02d}",
                "supplier_detail_id": str(100000 + index),
                "supplier_url": f"https://detail.1688.com/offer/{100000 + index}.html",
                "title": f"Handbag {index}",
                "image_ref": f"images/group-{index:02d}.jpg",
                "asin": f"B0TEST{index:04d}",
                "parent_asin": f"B0PARENT{index:02d}",
                "price": "35",
                "parent_sales_30d": "300",
                "child_sales_30d": "12",
                "amazon_signal_status": "PASS",
                "walmart_us_status": "STRONG_GAP",
                "us_demand_evidence": "TRUE",
                "walmart_ca_status": "NEEDS_REVIEW",
                "fbm_gate_status": "PASS",
                "manual_wfs_choice": "WFS" if index in {0, 1, 15, 16} and wfs_count == 4 else "SYSTEM",
                "listing_quality_score": "90",
                "unit_profit_rmb": "90",
                "profit_complete": "TRUE",
                "infringement_pass": "TRUE",
                "patent_pass": "TRUE",
                "supply_pass": "TRUE",
                "packaging_pass": "TRUE",
                "barcode_pass": "TRUE",
                "country_origin_pass": "TRUE",
                "walmart_sku": f"SKU-{index:02d}",
                "gtin": f"000000000{index:03d}",
                "observed_at": "2026-08-10T12:00:00+08:00",
            })
            rows.append(row)
        with (batch_dir / "daily_results.csv").open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)
        metadata = json.loads((batch_dir / "submission.json").read_text(encoding="utf-8"))
        metadata["status"] = "SUCCESS"
        (batch_dir / "submission.json").write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")

    def test_portable_batch_initializes_without_node_or_feishu(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            batch_dir = Path(temp_dir) / "batch"
            result = initialize(batch_dir, "2026-08-10")
            self.assertEqual("CREATED", result["status"])
            self.assertTrue((batch_dir / "submission.json").exists())
            self.assertTrue((batch_dir / "daily_results.csv").exists())
            self.assertEqual("PENDING", json.loads((batch_dir / "submission.json").read_text(encoding="utf-8"))["status"])

    def test_portable_batch_accepts_30_fbm_and_4_wfs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            batch_dir = Path(temp_dir) / "batch"
            initialize(batch_dir, "2026-08-10")
            self.fill_portable_rows(batch_dir)
            result = inspect_batch(batch_dir, require_success=True)
            self.assertEqual("PASS", result["status"], result["errors"])
            self.assertEqual(30, result["fbm"]["pass"])
            self.assertEqual(4, result["wfs"]["selected"])
            self.assertEqual({"美国站1": 2, "美国站2": 2}, result["wfs"]["by_store"])
            packed = pack(batch_dir, Path(temp_dir) / "result.zip")
            self.assertTrue(Path(packed["archive"]).exists())

    def test_portable_batch_blocks_wfs_without_hard_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            batch_dir = Path(temp_dir) / "batch"
            initialize(batch_dir, "2026-08-10")
            self.fill_portable_rows(batch_dir)
            import csv
            with (batch_dir / "daily_results.csv").open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            rows[0]["unit_profit_rmb"] = "60"
            with (batch_dir / "daily_results.csv").open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
                writer.writeheader()
                writer.writerows(rows)
            result = inspect_batch(batch_dir, require_success=True)
            self.assertEqual("BLOCKED", result["status"])
            self.assertTrue(any("预计贡献利润低于70元" in error for error in result["errors"]))

    def test_keyword_template_contains_only_explicit_womens_handbags(self) -> None:
        import csv

        with (SKILL_ROOT / "assets" / "inputs" / "keywords-master.csv").open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(80, len(rows))
        self.assertTrue(all(is_strict_womens_handbag_keyword(row["keyword"]) for row in rows))
        keywords = {row["keyword"] for row in rows}
        self.assertIn("women's concert bag", keywords)
        self.assertIn("ita bag", keywords)
        self.assertIn("pins display bag", keywords)
        self.assertIn("work tote bag for women", keywords)
        self.assertIn("y2k shoulder bag", keywords)
        self.assertFalse(is_strict_womens_handbag_keyword("laptop handbag for women"))


if __name__ == "__main__":
    unittest.main()
