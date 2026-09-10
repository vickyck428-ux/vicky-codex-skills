#!/usr/bin/env python3
"""Minimal Sorftime MCP client used by the Xinghe selection skill."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


SERVER_NAME = "sorftime"
DEFAULT_GLOBAL_CONFIG = Path.home() / ".codex" / "mcp.json"
LEGACY_GLOBAL_CONFIG = Path.home() / ".mcp.json"
ENV_KEY = "SORFTIME_API_KEY"
BASE_URL = "https://mcp.sorftime.com?key={key}"
EXPECTED_TOOL_PREFIXES = (
    "category_",
    "keyword_",
    "product_",
    "tiktok_",
    "shopee_",
    "walmart_",
    "temu_",
    "ali1688_",
)


def global_config_path(target: str | None = None) -> Path:
    if target:
        return Path(target).expanduser()
    return DEFAULT_GLOBAL_CONFIG


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def key_from_config(path: Path) -> str | None:
    payload = load_json(path)
    server = payload.get("mcpServers", {}).get(SERVER_NAME, {})
    url = server.get("url", "")
    match = re.search(r"[?&]key=([^&]+)", url)
    if match:
        return urllib.parse.unquote(match.group(1))
    return None


def sorftime_url(key: str) -> str:
    return BASE_URL.format(key=urllib.parse.quote(key, safe=""))


def resolve_key(config_path: str | None = None) -> tuple[str | None, Path | None]:
    env_key = os.environ.get(ENV_KEY)
    if env_key:
        return env_key, None

    candidates = [global_config_path(config_path)]
    if config_path is None and LEGACY_GLOBAL_CONFIG not in candidates:
        candidates.append(LEGACY_GLOBAL_CONFIG)

    for path in candidates:
        key = key_from_config(path)
        if key:
            return key, path
    return None, candidates[0]


def write_sorftime_config(key: str, target: str | None = None) -> Path:
    path = global_config_path(target)
    payload = load_json(path)
    servers = payload.setdefault("mcpServers", {})
    servers[SERVER_NAME] = {
        "type": "streamableHttp",
        "url": sorftime_url(key),
        "name": "Sorftime MCP",
        "description": "Sorftime cross-border ecommerce data service for Amazon, TikTok Shop, Shopee, Walmart, Temu, and 1688 product selection.",
    }
    save_json(path, payload)
    return path


def parse_sse_response(raw: str) -> dict[str, Any]:
    data_lines = []
    for line in raw.splitlines():
        if line.startswith("data:"):
            data_lines.append(line[5:].strip())
    if not data_lines:
        return json.loads(raw)
    return json.loads("\n".join(data_lines))


def extract_text_content(response: dict[str, Any]) -> Any:
    result = response.get("result", response)
    content = result.get("content") if isinstance(result, dict) else None
    if isinstance(content, list) and content:
        first = content[0]
        if isinstance(first, dict) and first.get("type") == "text":
            text = first.get("text", "")
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text
    return result


def call_tool(name: str, arguments: dict[str, Any], *, key: str | None = None, config_path: str | None = None, timeout: int = 90) -> Any:
    if key is None:
        key, _ = resolve_key(config_path)
    if not key:
        raise RuntimeError("Sorftime MCP key is not configured.")

    url = sorftime_url(key)
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"Sorftime MCP HTTP {exc.code}: {detail}") from exc
    return extract_text_content(parse_sse_response(raw))


def list_tools(*, key: str | None = None, config_path: str | None = None, timeout: int = 30) -> dict[str, Any]:
    if key is None:
        key, _ = resolve_key(config_path)
    if not key:
        raise RuntimeError("Sorftime MCP key is not configured.")

    request = urllib.request.Request(
        sorftime_url(key),
        data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"Sorftime MCP HTTP {exc.code}: {detail}") from exc
    return parse_sse_response(raw)


def tool_names(response: dict[str, Any]) -> list[str]:
    tools = response.get("result", {}).get("tools", [])
    return [tool.get("name", "") for tool in tools if isinstance(tool, dict)]


def validate_tool_response(response: dict[str, Any]) -> tuple[bool, str, list[str]]:
    names = tool_names(response)
    if not names:
        return False, "no_tools_returned", names
    if any(name in {"NotAuthorization", "Authentication required"} for name in names):
        return False, "not_authorized", names
    if not any(name.startswith(EXPECTED_TOOL_PREFIXES) for name in names):
        return False, "sorftime_tools_missing", names
    return True, "ok", names


def main() -> int:
    parser = argparse.ArgumentParser(description="Call Sorftime MCP tools.")
    parser.add_argument("tool", help="Tool name, or tools/list")
    parser.add_argument("--args", default="{}", help="JSON arguments for tools/call")
    parser.add_argument("--config", help="Override global MCP config path")
    args = parser.parse_args()

    try:
        if args.tool == "tools/list":
            result = list_tools(config_path=args.config)
        else:
            result = call_tool(args.tool, json.loads(args.args), config_path=args.config)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
