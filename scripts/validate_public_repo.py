#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK_RE = re.compile(r"\[[^\]]+\]\((?!https?://|#)([^)]+)\)")
ABSOLUTE_USER_RE = re.compile(r"/(?:Users|home)/[^/\s]+/")
PRIVATE_KEY_RE = re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----")
HIGH_RISK_TOKEN_RE = re.compile(r"(?:sk-[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{20,})")
ENV_SECRET_RE = re.compile(r"(?m)^\s*[A-Z0-9_]*(?:API_KEY|TOKEN|SECRET|PASSWORD)[A-Z0-9_]*\s*=\s*['\"]?([A-Za-z0-9_.\-]{8,})")
PLACEHOLDER_VALUES = {"your-api-key", "your_api_key", "example", "placeholder", "changeme", "replace_me", "replace-me"}
BAD_PARTS = {"node_modules", "__pycache__", ".cache", "cache", "logs", "runs", "outputs", "reports", ".backups", "backups", "tmp", "temp"}
BAD_NAMES = {".env", "config.json", "credentials.json", "cookies.json", "Cookies", "History", "Login Data", "Local State"}


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise ValueError("missing YAML frontmatter")
    raw = text.split("\n---\n", 1)[0].splitlines()[1:]
    result = {}
    for line in raw:
        if ":" in line:
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip().strip('"\'')
    return result


def main() -> int:
    manifest = json.loads((ROOT / "skill-sources.json").read_text(encoding="utf-8"))
    primary = manifest["primary_skills"]
    compatibility = manifest["compatibility_skills"]
    expected = primary + compatibility
    actual = sorted(path.name for path in (ROOT / "skills").iterdir() if path.is_dir())
    errors: list[str] = []
    if len(primary) != 44 or len(compatibility) != 2 or len(set(expected)) != 46:
        errors.append("manifest count must be 44 primary + 2 compatibility")
    if sorted(expected) != actual:
        errors.append("skills directory does not match manifest")
    if (ROOT / "LICENSE").exists() or (ROOT / "LICENSE.md").exists():
        errors.append("repository must not contain an open-source LICENSE file")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    if "All rights reserved" not in readme:
        errors.append("README copyright notice missing")

    for name in expected:
        skill_dir = ROOT / "skills" / name
        if not NAME_RE.fullmatch(name):
            errors.append(f"invalid folder name: {name}")
        try:
            meta = frontmatter(skill_dir / "SKILL.md")
            if meta.get("name") != name:
                errors.append(f"frontmatter name mismatch: {name}")
            if not meta.get("description") or "TODO" in meta.get("description", ""):
                errors.append(f"missing description: {name}")
            if "license" in meta:
                errors.append(f"per-skill license conflicts with repository policy: {name}")
        except (OSError, ValueError) as exc:
            errors.append(f"{name}: {exc}")
        agent_file = skill_dir / "agents" / "openai.yaml"
        if not agent_file.exists():
            errors.append(f"missing agents/openai.yaml: {name}")
        elif name in compatibility and "allow_implicit_invocation: false" not in agent_file.read_text(encoding="utf-8"):
            errors.append(f"compatibility skill is not explicit-only: {name}")

        for path in skill_dir.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(ROOT)
            if any(part in BAD_PARTS or part.startswith(".tmp-") or ".backup-" in part or ".previous-" in part for part in relative.parts):
                errors.append(f"excluded path present: {relative}")
            if path.name in BAD_NAMES or path.name.startswith("config.local."):
                errors.append(f"private config present: {relative}")
            if path.stat().st_size > 10 * 1024 * 1024:
                errors.append(f"large file present: {relative}")
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if ABSOLUTE_USER_RE.search(text):
                errors.append(f"personal absolute path: {relative}")
            config_like = path.name.startswith(".env") or path.suffix.lower() in {".json", ".yaml", ".yml", ".toml"}
            secret_values = [match.group(1).lower() for match in ENV_SECRET_RE.finditer(text)] if config_like else []
            if PRIVATE_KEY_RE.search(text) or HIGH_RISK_TOKEN_RE.search(text) or any(value not in PLACEHOLDER_VALUES for value in secret_values):
                errors.append(f"possible secret: {relative}")
            if path.suffix.lower() in {".md", ".yaml", ".yml"} and ("TODO" in text or "[TODO" in text):
                errors.append(f"unfinished placeholder: {relative}")
            if path.suffix.lower() == ".md":
                for target in LINK_RE.findall(text):
                    clean = target.split("#", 1)[0]
                    if clean and not (path.parent / clean).resolve().exists():
                        errors.append(f"broken relative link: {relative} -> {target}")

    report = {"status": "PASS" if not errors else "FAIL", "primary": len(primary), "compatibility": len(compatibility), "errors": sorted(set(errors))}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
