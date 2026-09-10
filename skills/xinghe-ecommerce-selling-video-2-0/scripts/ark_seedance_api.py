#!/usr/bin/env python3
"""Minimal Volcengine Ark Seedance video helper."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib import error, request
from urllib.parse import urlparse


BASE_URL = os.environ.get("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3").rstrip("/")
DEFAULT_MODEL = os.environ.get("ARK_SEEDANCE_MODEL", "doubao-seedance-2-0-fast-260128")
TASKS_PATH = "/contents/generations/tasks"


def api_key() -> str:
    key = os.environ.get("ARK_API_KEY")
    if not key and os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as env_key:
                key, _ = winreg.QueryValueEx(env_key, "ARK_API_KEY")
        except OSError:
            key = None
    if not key:
        raise SystemExit(
            "ARK_API_KEY is not set. Configure it in PowerShell:\n"
            "[Environment]::SetEnvironmentVariable(\"ARK_API_KEY\", \"your_key\", \"User\")"
        )
    return key


def headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key()}",
        "Content-Type": "application/json",
    }


def request_json(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(BASE_URL + path, data=body, headers=headers(), method=method)
    try:
        with request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code}: {detail}") from exc


def read_prompt(args: argparse.Namespace) -> str:
    if getattr(args, "prompt_file", None):
        return Path(args.prompt_file).read_text(encoding="utf-8")
    return args.prompt


def image_path_to_data_url(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"Image path not found: {path}")
    mime = mimetypes.guess_type(p.name)[0] or "image/png"
    encoded = base64.b64encode(p.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def build_content(prompt: str, image_urls: list[str], image_paths: list[str]) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for url in image_urls:
        content.append({"type": "image_url", "image_url": {"url": url}, "role": "reference_image"})
    for path in image_paths:
        content.append({"type": "image_url", "image_url": {"url": image_path_to_data_url(path)}, "role": "reference_image"})
    return content


def extract_nested(data: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str):
            return value
    nested = data.get("data")
    if isinstance(nested, dict):
        return extract_nested(nested, keys)
    return None


def extract_video_url(data: Any) -> str | None:
    if isinstance(data, dict):
        for key in ("video_url", "url", "output_url"):
            value = data.get(key)
            if isinstance(value, str) and value.startswith(("http://", "https://")):
                return value
        for value in data.values():
            found = extract_video_url(value)
            if found:
                return found
    elif isinstance(data, list):
        for value in data:
            found = extract_video_url(value)
            if found:
                return found
    return None


def output_path_from_args(output: str | None, output_dir: str | None, output_name: str | None, url: str) -> Path:
    if output:
        return Path(output)
    directory = Path(output_dir or ".")
    if output_name:
        name = output_name
    else:
        parsed_name = Path(urlparse(url).path).name or "seedance_video.mp4"
        name = parsed_name if parsed_name.lower().endswith(".mp4") else f"{parsed_name}.mp4"
    return directory / name


def download_url(url: str, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    req = request.Request(url, method="GET")
    try:
        with request.urlopen(req, timeout=300) as resp:
            output.write_bytes(resp.read())
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Download HTTP {exc.code}: {detail}") from exc
    return output


def submit(args: argparse.Namespace) -> None:
    payload: dict[str, Any] = {
        "model": args.model,
        "content": build_content(read_prompt(args), args.image_url or [], args.image_path or []),
        "ratio": args.ratio,
        "resolution": args.resolution,
        "duration": args.duration,
    }
    if args.generate_audio is not None:
        payload["generate_audio"] = args.generate_audio
    if args.seed is not None:
        payload["seed"] = args.seed

    data = request_json("POST", TASKS_PATH, payload)
    task_id = extract_nested(data, ("id", "task_id", "taskId"))
    if task_id:
        data["_task_id"] = task_id
    print(json.dumps(data, ensure_ascii=False, indent=2))


def query(args: argparse.Namespace) -> dict[str, Any]:
    data = request_json("GET", f"{TASKS_PATH}/{args.task_id}")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return data


def poll(args: argparse.Namespace) -> None:
    deadline = time.time() + args.timeout
    while True:
        data = request_json("GET", f"{TASKS_PATH}/{args.task_id}")
        status = (extract_nested(data, ("status", "state")) or "unknown").lower()
        print(json.dumps(data, ensure_ascii=False, indent=2))
        if status in {"succeeded", "success", "completed", "failed", "cancelled", "canceled"}:
            return
        if time.time() >= deadline:
            raise SystemExit(f"Timed out while polling task {args.task_id}. Last status: {status}")
        print(f"Waiting {args.interval}s; current status: {status}", file=sys.stderr)
        time.sleep(args.interval)


def download(args: argparse.Namespace) -> None:
    output = output_path_from_args(args.output, args.output_dir, args.output_name, args.url)
    saved = download_url(args.url, output)
    print(json.dumps({"saved": str(saved), "bytes": saved.stat().st_size}, ensure_ascii=False, indent=2))


def generate(args: argparse.Namespace) -> None:
    submit_payload = argparse.Namespace(**vars(args))
    submit_payload.prompt = read_prompt(args)
    payload: dict[str, Any] = {
        "model": args.model,
        "content": build_content(submit_payload.prompt, args.image_url or [], args.image_path or []),
        "ratio": args.ratio,
        "resolution": args.resolution,
        "duration": args.duration,
    }
    if args.generate_audio is not None:
        payload["generate_audio"] = args.generate_audio
    if args.seed is not None:
        payload["seed"] = args.seed

    submitted = request_json("POST", TASKS_PATH, payload)
    task_id = extract_nested(submitted, ("id", "task_id", "taskId"))
    if not task_id:
        raise SystemExit(f"Task id not found in response: {json.dumps(submitted, ensure_ascii=False)}")

    print(json.dumps({"task_id": task_id, "status": "submitted"}, ensure_ascii=False), file=sys.stderr)
    deadline = time.time() + args.timeout
    final: dict[str, Any] | None = None
    while True:
        data = request_json("GET", f"{TASKS_PATH}/{task_id}")
        status = (extract_nested(data, ("status", "state")) or "unknown").lower()
        print(json.dumps({"task_id": task_id, "status": status}, ensure_ascii=False), file=sys.stderr)
        if status in {"succeeded", "success", "completed", "failed", "cancelled", "canceled"}:
            final = data
            break
        if time.time() >= deadline:
            raise SystemExit(f"Timed out while polling task {task_id}. Last status: {status}")
        time.sleep(args.interval)

    video_url = extract_video_url(final)
    result: dict[str, Any] = {"task_id": task_id, "result": final}
    if video_url:
        result["video_url"] = video_url
        if args.output or args.output_dir or args.output_name:
            output = output_path_from_args(args.output, args.output_dir, args.output_name, video_url)
            saved = download_url(video_url, output)
            result["saved"] = str(saved)
            result["bytes"] = saved.stat().st_size
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Volcengine Ark Seedance video helper")
    sub = parser.add_subparsers(dest="command", required=True)

    submit_p = sub.add_parser("submit")
    submit_p.add_argument("--prompt")
    submit_p.add_argument("--prompt-file")
    submit_p.add_argument("--image-url", action="append")
    submit_p.add_argument("--image-path", action="append")
    submit_p.add_argument("--ratio", default="9:16", choices=["21:9", "16:9", "4:3", "1:1", "3:4", "9:16", "adaptive"])
    submit_p.add_argument("--resolution", default="480p", choices=["480p", "720p", "1080p", "2K"])
    submit_p.add_argument("--duration", type=int, default=15)
    submit_p.add_argument("--model", default=DEFAULT_MODEL)
    submit_p.add_argument("--seed", type=int)
    submit_p.add_argument("--generate-audio", dest="generate_audio", action="store_true")
    submit_p.add_argument("--no-generate-audio", dest="generate_audio", action="store_false")
    submit_p.set_defaults(generate_audio=None, func=submit)

    generate_p = sub.add_parser("generate")
    generate_p.add_argument("--prompt")
    generate_p.add_argument("--prompt-file")
    generate_p.add_argument("--image-url", action="append")
    generate_p.add_argument("--image-path", action="append")
    generate_p.add_argument("--ratio", default="9:16", choices=["21:9", "16:9", "4:3", "1:1", "3:4", "9:16", "adaptive"])
    generate_p.add_argument("--resolution", default="480p", choices=["480p", "720p", "1080p", "2K"])
    generate_p.add_argument("--duration", type=int, default=15)
    generate_p.add_argument("--model", default=DEFAULT_MODEL)
    generate_p.add_argument("--seed", type=int)
    generate_p.add_argument("--generate-audio", dest="generate_audio", action="store_true")
    generate_p.add_argument("--no-generate-audio", dest="generate_audio", action="store_false")
    generate_p.add_argument("--interval", type=int, default=30)
    generate_p.add_argument("--timeout", type=int, default=900)
    generate_p.add_argument("--output")
    generate_p.add_argument("--output-dir")
    generate_p.add_argument("--output-name")
    generate_p.set_defaults(generate_audio=True, func=generate)

    query_p = sub.add_parser("query")
    query_p.add_argument("--task-id", required=True)
    query_p.set_defaults(func=query)

    poll_p = sub.add_parser("poll")
    poll_p.add_argument("--task-id", required=True)
    poll_p.add_argument("--interval", type=int, default=30)
    poll_p.add_argument("--timeout", type=int, default=900)
    poll_p.set_defaults(func=poll)

    download_p = sub.add_parser("download")
    download_p.add_argument("--url", required=True)
    download_p.add_argument("--output")
    download_p.add_argument("--output-dir")
    download_p.add_argument("--output-name")
    download_p.set_defaults(func=download)

    args = parser.parse_args()
    if getattr(args, "command", None) in {"submit", "generate"} and not (getattr(args, "prompt", None) or getattr(args, "prompt_file", None)):
        parser.error(f"{args.command} requires --prompt or --prompt-file")
    args.func(args)


if __name__ == "__main__":
    main()
