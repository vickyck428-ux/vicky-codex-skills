#!/usr/bin/env python3
"""Test Sorftime MCP connectivity."""

from __future__ import annotations

import argparse
import json
import sys

from sorftime_client import list_tools, resolve_key, validate_tool_response


def main() -> int:
    parser = argparse.ArgumentParser(description="Test Sorftime MCP connection.")
    parser.add_argument("--scope", choices=["global"], default="global")
    parser.add_argument("--target", help="Override global MCP config path.")
    args = parser.parse_args()

    key, source = resolve_key(args.target)
    if not key:
        print(json.dumps({"ok": False, "reason": "missing_key", "config": str(source)}, ensure_ascii=False))
        return 2

    try:
        response = list_tools(key=key)
        valid, reason, names = validate_tool_response(response)
        if not valid:
            print(json.dumps({"ok": False, "reason": reason, "source": str(source) if source else "env", "sample_tools": names[:20]}, ensure_ascii=False, indent=2), file=sys.stderr)
            return 1
        print(json.dumps({"ok": True, "source": str(source) if source else "env", "tool_count": len(names), "sample_tools": names[:20]}, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "reason": "connection_failed", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
