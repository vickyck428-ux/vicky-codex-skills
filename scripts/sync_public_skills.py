#!/usr/bin/env python3
from __future__ import annotations

import argparse
import filecmp
import json
import os
import re
import shutil
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "skill-sources.json"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
EXCLUDED_NAMES = {
    ".env", "config.json", "credentials.json", "cookies.json", "Cookies",
    "History", "Login Data", "Local State",
}
EXCLUDED_SUFFIXES = {
    ".log", ".sqlite", ".sqlite3", ".db", ".pyc", ".pyo", ".key", ".pem",
}
EXCLUDED_PARTS = {
    "node_modules", "__pycache__", ".cache", "cache", "logs", "runs", "outputs",
    ".git", ".backups", "backups", "tmp", "temp", "reports",
}
PRIVATE_KEY_RE = re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----")
HIGH_RISK_TOKEN_RE = re.compile(r"(?:sk-[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{20,})")
ENV_SECRET_RE = re.compile(r"(?m)^\s*[A-Z0-9_]*(?:API_KEY|TOKEN|SECRET|PASSWORD)[A-Z0-9_]*\s*=\s*['\"]?([A-Za-z0-9_.\-]{8,})")
PLACEHOLDER_VALUES = {"your-api-key", "your_api_key", "example", "placeholder", "changeme", "replace_me", "replace-me"}
ABSOLUTE_USER_RE = re.compile(r"/(?:Users|home)/[^/\s]+/")


def load_manifest() -> tuple[list[str], set[str]]:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    primary = data["primary_skills"]
    compatibility = set(data["compatibility_skills"])
    names = primary + data["compatibility_skills"]
    if len(primary) != 47 or len(compatibility) != 2 or len(set(names)) != 49:
        raise RuntimeError("manifest must contain 47 unique primary and 2 unique compatibility skills")
    if any(not NAME_RE.fullmatch(name) for name in names):
        raise RuntimeError("manifest contains an invalid skill name")
    return names, compatibility


def should_copy(relative: Path, compatibility: bool) -> bool:
    if compatibility and relative.parts[0] not in {"SKILL.md", "agents"}:
        return False
    if any(part in EXCLUDED_PARTS or part.startswith(".tmp-") or ".backup-" in part or ".previous-" in part for part in relative.parts):
        return False
    if relative.name in EXCLUDED_NAMES or relative.name.startswith("config.local."):
        return False
    if relative.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    return True


def copy_skill(source: Path, destination: Path, compatibility: bool) -> None:
    for item in source.rglob("*"):
        relative = item.relative_to(source)
        if not should_copy(relative, compatibility) or item.is_symlink():
            continue
        target = destination / relative
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        if item.stat().st_size > 10 * 1024 * 1024:
            raise RuntimeError(f"large file blocked: {source.name}/{relative}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)


def audit_tree(root: Path) -> None:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if not should_copy(relative, False):
            raise RuntimeError(f"excluded file leaked into staging: {relative}")
        if path.stat().st_size > 10 * 1024 * 1024:
            raise RuntimeError(f"large file blocked: {relative}")
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if ABSOLUTE_USER_RE.search(text):
            raise RuntimeError(f"personal absolute path blocked: {relative}")
        config_like = path.name.startswith(".env") or path.suffix.lower() in {".json", ".yaml", ".yml", ".toml"}
        secret_values = [match.group(1).lower() for match in ENV_SECRET_RE.finditer(text)] if config_like else []
        if PRIVATE_KEY_RE.search(text) or HIGH_RISK_TOKEN_RE.search(text) or any(value not in PLACEHOLDER_VALUES for value in secret_values):
            raise RuntimeError(f"possible secret blocked: {relative}")


def same_tree(left: Path, right: Path) -> bool:
    comparison = filecmp.dircmp(left, right)
    if comparison.left_only or comparison.right_only or comparison.funny_files:
        return False
    if any(not filecmp.cmp(left / name, right / name, shallow=False) for name in comparison.common_files):
        return False
    return all(same_tree(left / name, right / name) for name in comparison.common_dirs)


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--source-root", type=Path)
    args = parser.parse_args()

    source_root = (args.source_root or Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "skills").expanduser().resolve()
    names, compatibility = load_manifest()
    with tempfile.TemporaryDirectory(prefix="vicky-skills-public-") as temp_dir:
        staged = Path(temp_dir) / "skills"
        staged.mkdir()
        for name in names:
            source = source_root / name
            if not (source / "SKILL.md").exists():
                raise RuntimeError(f"missing source skill: {name}")
            copy_skill(source, staged / name, name in compatibility)
        audit_tree(staged)
        destination = REPO_ROOT / "skills"
        changed = not destination.exists() or not same_tree(staged, destination)
        print(json.dumps({
            "status": "READY",
            "mode": "apply" if args.apply else "dry-run",
            "source_root": str(source_root),
            "skills": len(names),
            "primary": 47,
            "compatibility": 2,
            "changed": changed,
        }, ensure_ascii=False, indent=2))
        if args.apply and changed:
            replacement = REPO_ROOT / ".skills-next"
            if replacement.exists():
                shutil.rmtree(replacement)
            shutil.copytree(staged, replacement)
            if destination.exists():
                shutil.rmtree(destination)
            replacement.rename(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
