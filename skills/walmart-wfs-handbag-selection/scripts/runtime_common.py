#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


SKILL_ROOT = Path(__file__).resolve().parents[1]


class SkillRuntimeError(RuntimeError):
    pass


def expanded_path(value: Any, base: Optional[Path] = None) -> Path:
    raw = os.path.expandvars(str(value or "").strip())
    if not raw:
        raise SkillRuntimeError("配置包含空路径。")
    if "$" in raw:
        raise SkillRuntimeError(f"路径仍含未设置的环境变量：{raw}")
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = (base or Path.cwd()) / path
    return path.resolve()


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise SkillRuntimeError(f"JSON 配置不存在：{path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SkillRuntimeError(f"JSON 配置格式错误：{path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SkillRuntimeError(f"JSON 顶层必须是对象：{path}")
    return value


def runner_path(value: Any, runner_root: Path) -> Path:
    raw = str(value or "").strip()
    path = Path(os.path.expandvars(raw)).expanduser()
    return path.resolve() if path.is_absolute() else (runner_root / path).resolve()


def build_context(*, config_path: Optional[Path] = None, runner_root: Optional[Path] = None) -> Dict[str, Any]:
    if bool(config_path) == bool(runner_root):
        raise SkillRuntimeError("必须且只能提供 --config 或 --runner-root。")

    wrapper: Dict[str, Any] = {}
    if config_path:
        config_path = config_path.expanduser().resolve()
        wrapper = read_json(config_path)
        base = config_path.parent
        root = expanded_path(wrapper.get("runner_root"), base)
        incremental_config = expanded_path(wrapper.get("incremental_config"), base)
        selection_config = expanded_path(wrapper.get("selection_config"), base)
        keyword_master = expanded_path(wrapper.get("keyword_master"), base)
        database = expanded_path(wrapper.get("ledger_database"), base)
        output_root = expanded_path(wrapper.get("output_root"), base)
        feishu_config = expanded_path(wrapper.get("feishu_integrations_file"), base)
        crawl_skill = expanded_path(wrapper.get("lc_amazon_data_crawl_skill"), base)
    else:
        root = runner_root.expanduser().resolve()
        incremental_config = root / "config" / "wfs_handbag_incremental.json"
        incremental = read_json(incremental_config)
        selection_config = runner_path(incremental.get("selection_config_file"), root)
        selection = read_json(selection_config)
        keyword_master = runner_path(selection.get("keyword_master_file"), root)
        database = runner_path(incremental.get("database_file"), root)
        output_root = runner_path(incremental.get("output_root"), root)
        feishu_config = runner_path(incremental.get("feishu_integrations_file"), root)
        crawl_skill = Path.home() / ".codex" / "skills" / "lc-amazon-data-crawl"

    return {
        "wrapper": wrapper,
        "config_path": config_path,
        "runner_root": root,
        "incremental_config": incremental_config,
        "selection_config": selection_config,
        "keyword_master": keyword_master,
        "ledger_database": database,
        "output_root": output_root,
        "feishu_integrations_file": feishu_config,
        "lc_amazon_data_crawl_skill": crawl_skill,
        "skill_root": SKILL_ROOT,
    }


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False
