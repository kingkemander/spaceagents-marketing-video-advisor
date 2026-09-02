#!/usr/bin/env python3
"""营销视频军师对蚁小二 yxer CLI 的受控桥接。"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def run(command: list[str]) -> int:
    print("$ " + " ".join(command))
    return subprocess.run(command, check=False).returncode


def ensure_yxer(install: bool) -> None:
    if shutil.which("yxer"):
        return
    if not install:
        raise RuntimeError("未发现 yxer。请在用户明确授权后运行：npm install -g @yixiaoermail/cli@latest")
    if not shutil.which("npm"):
        raise RuntimeError("未发现 npm，无法安装 yxer CLI")
    if run(["npm", "install", "-g", "@yixiaoermail/cli@latest"]) != 0:
        raise RuntimeError("yxer CLI 安装失败")


def main() -> int:
    ap = argparse.ArgumentParser(description="蚁小二 CLI 受控桥接")
    ap.add_argument("--install", action="store_true", help="用户明确授权时才安装 yxer CLI")
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="检查 yxer、账号授权和发布通道")
    accounts = sub.add_parser("accounts", help="列出某平台可用账号")
    accounts.add_argument("platform")
    dry = sub.add_parser("dry-run", help="校验并预览发布，不会正式发布")
    dry.add_argument("platform")
    dry.add_argument("content_type", choices=("video", "imageText", "article"))
    dry.add_argument("payload", type=Path)
    publish = sub.add_parser("publish", help="正式发布：仅在用户明确确认后调用")
    publish.add_argument("platform")
    publish.add_argument("content_type", choices=("video", "imageText", "article"))
    publish.add_argument("payload", type=Path)
    publish.add_argument("--confirmed", action="store_true", help="用户已确认账号、内容和发布范围")
    args = ap.parse_args()
    try:
        ensure_yxer(args.install)
        if args.command == "doctor":
            return run(["yxer", "doctor"])
        if args.command == "accounts":
            return run(["yxer", "accounts", "list", args.platform, "--status", "1"])
        if not args.payload.is_file():
            raise RuntimeError(f"找不到 payload 文件：{args.payload}")
        validate = ["yxer", "validate", args.platform, args.content_type, str(args.payload)]
        if run(validate) != 0:
            return 1
        preview = ["yxer", "publish", args.content_type, args.platform, str(args.payload), "--dry-run"]
        if run(preview) != 0 or args.command == "dry-run":
            return 1
        if not args.confirmed:
            raise RuntimeError("预览已完成；正式发布必须在用户明确确认后追加 --confirmed")
        return run(["yxer", "publish", args.content_type, args.platform, str(args.payload)])
    except RuntimeError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
