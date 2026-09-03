#!/usr/bin/env python3
"""从已校验的 Release 安装营销视频军师运行时，并创建可见智能体。"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

REPO = "kingkemander/spaceagents-marketing-video-advisor"
VERSION = "1.0.10"
RUNTIME_URL = f"https://github.com/{REPO}/releases/download/v{VERSION}/spaceagents-marketing-video-advisor-runtime-v{VERSION}.zip"
RUNTIME_SHA256 = "ce991e55877d2bd06c506ff2f58e4f93752e20a72c11846a35db2f801dbd0569"
PLUGIN_ID = "spaceagents-marketing-video-advisor"


def download(url: str) -> bytes:
    error = None
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "SpaceAgents-MarketingVideoAdvisor/1"})
            with urllib.request.urlopen(request, timeout=300) as response:
                return response.read()
        except Exception as exc:
            error = exc
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"运行时下载失败（已重试 3 次）：{error}")


def extract_safely(archive: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive) as zf:
        for item in zf.infolist():
            output = (destination / item.filename).resolve()
            if not str(output).startswith(str(destination.resolve()) + os.sep):
                raise RuntimeError("运行时压缩包包含不安全路径")
        zf.extractall(destination)


def install_runtime(workspace: Path) -> Path:
    root = workspace / ".spaceagents" / "plugins" / PLUGIN_ID
    destination = root / f"runtime-v{VERSION}"
    if destination.is_dir() and (destination / "cli.py").is_file():
        return destination
    content = download(RUNTIME_URL)
    actual = hashlib.sha256(content).hexdigest()
    if actual != RUNTIME_SHA256:
        raise RuntimeError("运行时下载校验失败，请重新从官方 GitHub 链接安装")
    with tempfile.TemporaryDirectory(prefix="mva-bootstrap-") as temporary:
        archive = Path(temporary) / "runtime.zip"
        stage = Path(temporary) / "runtime"
        archive.write_bytes(content)
        stage.mkdir()
        extract_safely(archive, stage)
        if not all((stage / n).is_file() for n in ("cli.py", "update_client.py", "agent-template.md")):
            raise RuntimeError("运行时内容不完整")
        if destination.exists():
            shutil.rmtree(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(stage, destination)
    (root / "current.json").write_text(json.dumps({"version": VERSION, "runtime": str(destination)}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destination


def write_agent(workspace: Path, runtime: Path) -> Path:
    agents = workspace / ".opencode" / "agents"
    agents.mkdir(parents=True, exist_ok=True)
    target = agents / "营销视频军师.md"
    content = (runtime / "agent-template.md").read_text(encoding="utf-8")
    if target.exists() and "managed-by-spaceagents-marketing-video-advisor" not in target.read_text(encoding="utf-8", errors="ignore"):
        target = agents / "营销视频军师（SpaceAgents）.md"
    target.write_text(content, encoding="utf-8")
    return target


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default=".", help="目标工作区根目录")
    args = ap.parse_args()
    workspace = Path(args.workspace).expanduser().resolve()
    runtime = install_runtime(workspace)
    subprocess.run(["python3", str(runtime / "cli.py"), "init", "--workspace", str(workspace)], check=True)
    agent = write_agent(workspace, runtime)
    subprocess.run(["python3", str(runtime / "update_client.py"), "--workspace", str(workspace)], check=False)
    print(f"已安装营销视频军师：{agent}")
    print("请新建会话后，在智能体下拉列表选择“营销视频军师”。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
