#!/usr/bin/env python3
"""Create a textured static prop with Meshy's Multi-Image to 3D API."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = "https://api.meshy.ai/openapi/v1"
SUCCESS = "SUCCEEDED"
TERMINAL_FAILURES = {"FAILED", "CANCELED", "CANCELLED", "EXPIRED"}


class MeshyError(RuntimeError):
    pass


def data_uri(path: Path) -> str:
    if not path.is_file():
        raise MeshyError(f"Input image not found: {path}")
    mime, _ = mimetypes.guess_type(path.name)
    if mime not in {"image/png", "image/jpeg"}:
        raise MeshyError(f"Input must be a PNG or JPEG: {path}")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def api_json(method: str, path: str, key: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        f"{BASE_URL}{path}",
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=90) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(detail).get("message", detail)
        except json.JSONDecodeError:
            pass
        raise MeshyError(f"Meshy {method} {path} failed ({exc.code}): {detail}") from exc
    except URLError as exc:
        raise MeshyError(f"Could not reach Meshy: {exc.reason}") from exc


def wait_for_task(task_id: str, key: str, timeout_seconds: int) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        task = api_json("GET", f"/multi-image-to-3d/{task_id}", key)
        status = task.get("status", "UNKNOWN")
        progress = task.get("progress", 0)
        print(f"Meshy prop {task_id}: {status} ({progress}%)", flush=True)
        if status == SUCCESS:
            return task
        if status in TERMINAL_FAILURES:
            message = task.get("task_error", {}).get("message") or "No error message returned."
            raise MeshyError(f"Meshy task {task_id} ended as {status}: {message}")
        time.sleep(5)
    raise MeshyError(f"Timed out after {timeout_seconds}s waiting for Meshy task {task_id}.")


def download(url: str, destination: Path) -> None:
    if destination.exists():
        raise MeshyError(f"Refusing to overwrite: {destination}")
    try:
        with urlopen(url, timeout=180) as response:
            destination.write_bytes(response.read())
    except (HTTPError, URLError) as exc:
        raise MeshyError(f"Failed to download {destination.name}: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--front", required=True, type=Path, help="Front image; always first for Meshy 7.")
    parser.add_argument("--side", required=True, type=Path)
    parser.add_argument("--back", required=True, type=Path)
    parser.add_argument("--height-meters", required=True, type=float)
    parser.add_argument("--target-polycount", type=int, default=12_000)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--timeout-seconds", type=int, default=1200)
    args = parser.parse_args()

    key = os.environ.get("MESHY_API_KEY")
    if not key:
        raise SystemExit("MESHY_API_KEY is required in the environment; it is never read from files or arguments.")
    if args.height_meters <= 0:
        raise SystemExit("--height-meters must be positive.")
    if not 100 <= args.target_polycount <= 300_000:
        raise SystemExit("--target-polycount must be between 100 and 300000.")
    if args.output.exists() and any(args.output.iterdir()):
        raise SystemExit(f"Output directory must be new or empty: {args.output}")
    args.output.mkdir(parents=True, exist_ok=True)

    image_paths = [args.front, args.side, args.back]
    payload = {
        "image_urls": [data_uri(path) for path in image_paths],
        "ai_model": "latest",
        "should_texture": True,
        "enable_pbr": True,
        "texture_resolution": "2k",
        "should_remesh": True,
        "topology": "quad",
        "target_polycount": args.target_polycount,
        "target_formats": ["glb", "fbx"],
        "auto_size": True,
        "origin_at": "bottom",
        "multi_view_thumbnails": True,
    }
    created = api_json("POST", "/multi-image-to-3d", key, payload)
    task_id = created.get("result")
    if not isinstance(task_id, str):
        raise MeshyError("Meshy did not return a model task ID.")
    print(f"Submitted Meshy prop task: {task_id}", flush=True)
    task = wait_for_task(task_id, key, args.timeout_seconds)

    model_urls = task.get("model_urls") or {}
    assets = {
        "mission-terminal.glb": model_urls.get("glb"),
        "mission-terminal.fbx": model_urls.get("fbx"),
    }
    if not assets["mission-terminal.glb"]:
        raise MeshyError("Meshy succeeded but did not return a GLB URL.")
    downloaded = []
    for filename, url in assets.items():
        if isinstance(url, str) and url:
            download(url, args.output / filename)
            downloaded.append(filename)
            print(f"Downloaded {filename}", flush=True)

    thumbnail = task.get("thumbnail_url")
    if isinstance(thumbnail, str) and thumbnail:
        download(thumbnail, args.output / "meshy-thumbnail.png")
        downloaded.append("meshy-thumbnail.png")

    manifest = {
        "asset": "Athen Hill mission terminal",
        "source_views": [str(path.resolve()) for path in image_paths],
        "model_task_id": task_id,
        "height_meters": args.height_meters,
        "target_polycount": args.target_polycount,
        "files": downloaded,
        "api_options": {key: value for key, value in payload.items() if key != "image_urls"},
        "unity_import": "Import mission-terminal.glb with glTFast, normalize its bounds to 1.95 m, add a box collider, and instance it at the three mission slab slots.",
    }
    (args.output / "meshy-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Completed: {args.output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except MeshyError as exc:
        print(f"ERROR: {exc}", file=os.sys.stderr)
        raise SystemExit(1)
