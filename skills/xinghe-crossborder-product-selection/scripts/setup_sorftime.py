#!/usr/bin/env python3
"""Configure Sorftime MCP for the current user."""

from __future__ import annotations

import argparse
import getpass
import sys

from sorftime_client import list_tools, validate_tool_response, write_sorftime_config


def main() -> int:
    parser = argparse.ArgumentParser(description="Set up Sorftime MCP.")
    parser.add_argument("--scope", choices=["global"], default="global")
    parser.add_argument("--key", help="Sorftime MCP API key. If omitted, prompt securely.")
    parser.add_argument("--target", help="Override global MCP config path. Defaults to ~/.codex/mcp.json.")
    parser.add_argument("--skip-test", action="store_true", help="Write config without testing the key.")
    args = parser.parse_args()

    key = args.key or getpass.getpass("Sorftime MCP key: ").strip()
    if not key:
        print("Sorftime key is required.", file=sys.stderr)
        return 2

    if args.skip_test:
        path = write_sorftime_config(key, args.target)
        print(f"Sorftime MCP config written: {path}")
        return 0

    try:
        tools = list_tools(key=key)
        valid, reason, names = validate_tool_response(tools)
        if not valid:
            print(f"Sorftime MCP connection failed: {reason}. Tools returned: {', '.join(names[:5])}", file=sys.stderr)
            return 1
        path = write_sorftime_config(key, args.target)
        print(f"Sorftime MCP config written: {path}")
        print(f"Sorftime MCP connection OK. Tools available: {len(names)}")
        return 0
    except Exception as exc:
        print(f"Sorftime MCP connection failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
