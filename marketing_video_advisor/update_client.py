#!/usr/bin/env python3
"""营销视频军师运行时更新器：仅下载已校验的 GitHub Release。"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

REPO = "kingkemander/spaceagents-marketing-video-advisor"
MANIFEST_URL = f"https://github.com/{REPO}/releases/latest/download/update-manifest.json"
PLUGIN_ID = "spaceagents-marketing-video-advisor"
INTERVAL_SECONDS = 24 * 60 * 60


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(url: str, timeout: int = 90) -> bytes:
    error = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SpaceAgents-MarketingVideoAdvisor/1"})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read()
        except Exception as exc:
            error = exc
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"下载失败（已重试 3 次）：{error}")


def version_tuple(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in value.lstrip("v").split(".") if part.isdigit())


def safe_extract(archive: Path, target: Path) -> None:
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            candidate = (target / info.filename).resolve()
            if not str(candidate).startswith(str(target.resolve()) + os.sep):
                raise ValueError("运行时压缩包包含不安全路径")
        zf.extractall(target)


def runtime_valid(path: Path) -> bool:
    return all((path / name).is_file() for name in ("cli.py", "update_client.py", "agent-template.md"))


def runtime_root(workspace: Path) -> Path:
    return workspace / ".spaceagents" / "plugins" / PLUGIN_ID


def read_current(root: Path) -> dict:
    try:
        return json.loads((root / "current.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_current(root: Path, value: dict) -> None:
    root.mkdir(parents=True, exist_ok=True)
    tmp = root / "current.json.tmp"
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(root / "current.json")


def sync_agent(workspace: Path, runtime: Path) -> Path | None:
    """将受本插件管理的主智能体模板同步到最新版运行时。"""
    template = runtime / "agent-template.md"
    if not template.is_file():
        return None
    agents = workspace / ".opencode" / "agents"
    agents.mkdir(parents=True, exist_ok=True)
    target = agents / "营销视频军师.md"
    marker = "managed-by-spaceagents-marketing-video-advisor"
    if target.exists() and marker not in target.read_text(encoding="utf-8", errors="ignore"):
        target = agents / "营销视频军师（SpaceAgents）.md"
    target.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
    return target


def check(workspace: Path, force: bool = False) -> dict:
    root = runtime_root(workspace)
    current = read_current(root)
    now = time.time()
    if not force and now - float(current.get("last_update_check", 0)) < INTERVAL_SECONDS:
        return {"status": "skipped", "reason": "checked_recently"}
    try:
        manifest = json.loads(fetch(MANIFEST_URL).decode("utf-8"))
        version, url, digest = manifest["version"], manifest["runtime_url"], manifest["runtime_sha256"]
        if not url.startswith(f"https://github.com/{REPO}/") or len(digest) != 64:
            raise ValueError("更新清单不可信")
        if current.get("version") and version_tuple(version) <= version_tuple(current["version"]):
            current["last_update_check"] = now
            write_current(root, current)
            existing_runtime = Path(current.get("runtime", ""))
            if runtime_valid(existing_runtime):
                sync_agent(workspace, existing_runtime)
            return {"status": "current", "version": current["version"]}
        payload = fetch(url, timeout=300)
        if sha256(payload) != digest:
            raise ValueError("运行时校验失败")
        with tempfile.TemporaryDirectory(prefix="mva-update-") as temporary:
            archive = Path(temporary) / "runtime.zip"
            stage = Path(temporary) / "runtime"
            archive.write_bytes(payload)
            stage.mkdir()
            safe_extract(archive, stage)
            if not runtime_valid(stage):
                raise ValueError("下载的运行时不完整")
            destination = root / f"runtime-v{version}"
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(stage, destination)
        write_current(root, {"version": version, "runtime": str(destination), "last_update_check": now})
        sync_agent(workspace, destination)
        return {"status": "updated", "version": version}
    except Exception as exc:
        current["last_update_check"] = now
        write_current(root, current)
        return {"status": "deferred", "reason": str(exc)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    print(json.dumps(check(Path(args.workspace).expanduser().resolve(), args.force), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
