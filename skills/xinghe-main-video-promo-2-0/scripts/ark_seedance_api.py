#!/usr/bin/env python3
"""Small, structured Volcengine Ark Seedance client."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import socket
import sys
import time
from pathlib import Path
from typing import Any
from urllib import error, request
from urllib.parse import urlparse

BASE_URL = os.environ.get("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3").rstrip("/")
DEFAULT_MODEL = os.environ.get("ARK_SEEDANCE_MODEL", "doubao-seedance-2-0-fast-260128")
TASKS_PATH = "/contents/generations/tasks"
TERMINAL = {"succeeded", "success", "completed", "failed", "cancelled", "canceled"}
SUCCESS = {"succeeded", "success", "completed"}


class ArkError(RuntimeError):
    def __init__(self, stage: str, message: str, *, status: int | None = None, detail: str | None = None):
        super().__init__(message)
        self.stage, self.status, self.detail = stage, status, detail

    def as_dict(self) -> dict[str, Any]:
        return {"ok": False, "stage": self.stage, "error": str(self), "http_status": self.status, "detail": self.detail}


def api_key() -> str:
    key = os.environ.get("ARK_API_KEY")
    if not key and os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as env_key:
                key, _ = winreg.QueryValueEx(env_key, "ARK_API_KEY")
        except OSError:
            pass
    if not key:
        raise ArkError("preflight", "ARK_API_KEY is missing; configure it locally and do not paste it into chat")
    return key


def request_json(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(BASE_URL + path, data=body, method=method,
                          headers={"Authorization": f"Bearer {api_key()}", "Content-Type": "application/json"})
    try:
        with request.urlopen(req, timeout=120) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ArkError("api", f"Ark returned HTTP {exc.code}", status=exc.code, detail=detail) from exc
    except (error.URLError, socket.timeout, TimeoutError) as exc:
        raise ArkError("network", "Could not reach Ark or the request timed out", detail=str(exc)) from exc
    except json.JSONDecodeError as exc:
        raise ArkError("api", "Ark returned invalid JSON", detail=str(exc)) from exc


def nested_string(data: Any, keys: tuple[str, ...]) -> str | None:
    if isinstance(data, dict):
        for key in keys:
            if isinstance(data.get(key), str):
                return data[key]
        for value in data.values():
            found = nested_string(value, keys)
            if found:
                return found
    elif isinstance(data, list):
        for value in data:
            found = nested_string(value, keys)
            if found:
                return found
    return None


def data_url(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def build_content(prompt: str, image_paths: list[Path]) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for index, path in enumerate(image_paths):
        content.append({"type": "image_url", "image_url": {"url": data_url(path)},
                        "role": "reference_image"})
    return content


def safe_download(url: str, output: Path) -> int:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ArkError("download", "Refused a non-HTTPS or invalid video URL")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".part")
    try:
        with request.urlopen(request.Request(url, method="GET"), timeout=300) as response, temporary.open("wb") as handle:
            total = 0
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > 2 * 1024 * 1024 * 1024:
                    raise ArkError("download", "Video exceeded the 2 GiB safety limit")
                handle.write(chunk)
        temporary.replace(output)
        return total
    except ArkError:
        temporary.unlink(missing_ok=True)
        raise
    except (error.HTTPError, error.URLError, socket.timeout, TimeoutError, OSError) as exc:
        temporary.unlink(missing_ok=True)
        raise ArkError("download", "Video download failed", detail=str(exc)) from exc


def generate_video(*, prompt: str, image_paths: list[Path], output: Path, model: str, ratio: str,
                   resolution: str, duration: int, generate_audio: bool, interval: int = 30,
                   timeout: int = 900) -> dict[str, Any]:
    if not model.strip():
        raise ArkError("preflight", "Model name cannot be empty")
    payload = {"model": model, "content": build_content(prompt, image_paths), "ratio": ratio,
               "resolution": resolution, "duration": duration, "generate_audio": generate_audio}
    submitted = request_json("POST", TASKS_PATH, payload)
    task_id = nested_string(submitted, ("id", "task_id", "taskId"))
    if not task_id:
        raise ArkError("submit", "Ark response did not contain a task id", detail=json.dumps(submitted, ensure_ascii=False))
    deadline, final, status = time.time() + timeout, None, "submitted"
    while time.time() < deadline:
        final = request_json("GET", f"{TASKS_PATH}/{task_id}")
        status = (nested_string(final, ("status", "state")) or "unknown").lower()
        print(json.dumps({"task_id": task_id, "status": status}, ensure_ascii=False), file=sys.stderr)
        if status in TERMINAL:
            break
        time.sleep(interval)
    else:
        raise ArkError("poll", f"Task {task_id} timed out after {timeout} seconds", detail=f"last_status={status}")
    if status not in SUCCESS:
        raise ArkError("generation", f"Task {task_id} ended with status {status}", detail=json.dumps(final, ensure_ascii=False))
    video_url = nested_string(final, ("video_url", "output_url", "url"))
    if not video_url:
        raise ArkError("result", f"Task {task_id} succeeded but no video URL was found", detail=json.dumps(final, ensure_ascii=False))
    size = safe_download(video_url, output)
    return {"ok": True, "task_id": task_id, "status": status, "model": model, "ratio": ratio,
            "resolution": resolution, "duration": duration, "generate_audio": generate_audio,
            "video_url": video_url, "saved": str(output), "bytes": size}


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit one prebuilt Seedance video request")
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--image-path", action="append", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--ratio", choices=["1:1", "9:16", "16:9", "3:4", "4:3", "21:9", "adaptive"], required=True)
    parser.add_argument("--resolution", choices=["480p", "720p", "1080p", "2K"], default="480p")
    parser.add_argument("--duration", type=int, default=15)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--no-generate-audio", dest="generate_audio", action="store_false")
    parser.add_argument("--interval", type=int, default=30)
    parser.add_argument("--timeout", type=int, default=900)
    parser.set_defaults(generate_audio=True)
    args = parser.parse_args()
    try:
        result = generate_video(prompt=Path(args.prompt_file).read_text(encoding="utf-8"),
                                image_paths=[Path(p).resolve() for p in args.image_path], output=Path(args.output).resolve(),
                                model=args.model, ratio=args.ratio, resolution=args.resolution, duration=args.duration,
                                generate_audio=args.generate_audio, interval=args.interval, timeout=args.timeout)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except ArkError as exc:
        print(json.dumps(exc.as_dict(), ensure_ascii=False, indent=2))
        raise SystemExit(2)


if __name__ == "__main__":
    main()
