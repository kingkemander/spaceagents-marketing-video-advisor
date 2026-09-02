#!/usr/bin/env python3
"""本地工作区初始化与私密配置入口。"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


WORKSPACE_DIR = "营销视频工作区"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def init(workspace: Path) -> Path:
    root = workspace / WORKSPACE_DIR
    for name in ("config", "materials", "plans", "reports", "artifacts/videos", "artifacts/covers"):
        (root / name).mkdir(parents=True, exist_ok=True)
    profile = root / "config" / "账号资料.md"
    if not profile.exists():
        write_text(profile, "# 账号资料\n\n- 品牌/项目：\n- 核心受众：\n- 主推产品或服务：\n- 所在城市/区域：\n- 当前账号链接：\n- 可确认的价格、面积、交付等事实：\n")
    return root


def configure_douyin_key(workspace: Path, key: str) -> Path:
    if not key.strip():
        raise ValueError("API Key 不能为空")
    secret = workspace / ".spaceagents" / "secrets" / "marketing-video-advisor" / "douyin-api-key"
    write_text(secret, key.strip() + "\n")
    try:
        os.chmod(secret, 0o600)
    except OSError:
        pass
    return secret


def main() -> int:
    ap = argparse.ArgumentParser(prog="marketing-video-advisor")
    sub = ap.add_subparsers(dest="command", required=True)
    p_init = sub.add_parser("init", help="初始化营销视频工作区")
    p_init.add_argument("--workspace", required=True)
    p_key = sub.add_parser("configure-douyin-key", help="保存抖音数据服务的 API Key 到本机")
    p_key.add_argument("--workspace", required=True)
    p_key.add_argument("--api-key", required=True)
    args = ap.parse_args()
    workspace = Path(args.workspace).expanduser().resolve()
    if args.command == "init":
        print(init(workspace))
    else:
        configure_douyin_key(workspace, args.api_key)
        print("已保存到当前工作区的本机私密目录。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
