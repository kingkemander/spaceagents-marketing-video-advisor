#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查并（在用户明确确认后）准备营销视频工具链。

仅调用操作系统已有的包管理器；不下载未知二进制，不保存任何密钥。
"""
from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys


def run(command: list[str], check: bool = False) -> tuple[bool, str]:
    try:
        p = subprocess.run(command, capture_output=True, text=True, check=False)
        output = (p.stdout or p.stderr or "").strip()
        return p.returncode == 0, output
    except OSError as exc:
        return False, str(exc)


def version(command: str) -> str:
    ok, out = run([command, "--version"])
    return out.splitlines()[0] if ok and out else "未检测到"


def inspect_tools() -> dict[str, str]:
    result = {}
    for name, command in (("node", "node"), ("npm", "npm"), ("ffmpeg", "ffmpeg"), ("yxer", "yxer")):
        result[name] = version(command) if shutil.which(command) else "未安装"
    return result


def install(confirm: bool) -> int:
    if not confirm:
        print("未执行安装。请在确认安装 Node.js、npm、FFmpeg 和 yxer 后追加 --confirm-install。")
        return 2
    system = platform.system()
    if system == "Darwin":
        if not shutil.which("brew"):
            print("未发现 Homebrew。请先从 https://brew.sh 安装，或手动安装 Node.js 与 FFmpeg。", file=sys.stderr)
            return 2
        missing = [x for x in ("node", "ffmpeg") if not shutil.which(x)]
        if missing and run(["brew", "install", *missing])[0] is False:
            print("Homebrew 安装 Node.js/FFmpeg 失败。", file=sys.stderr)
            return 1
    elif system == "Windows":
        if not shutil.which("winget"):
            print("未发现 winget。请安装 App Installer，或手动安装 Node.js LTS 与 FFmpeg。", file=sys.stderr)
            return 2
        if not shutil.which("node") and not run(["winget", "install", "--id", "OpenJS.NodeJS.LTS", "--exact", "--accept-source-agreements", "--accept-package-agreements"])[0]:
            return 1
        if not shutil.which("ffmpeg") and not run(["winget", "install", "--id", "Gyan.FFmpeg", "--exact", "--accept-source-agreements", "--accept-package-agreements"])[0]:
            return 1
    else:
        print(f"暂不自动安装 {system}；请手动准备 Node.js、npm、FFmpeg。", file=sys.stderr)
        return 2

    if not shutil.which("npm"):
        print("Node.js 已安装但 npm 尚未进入当前 PATH，请重启终端后重试。", file=sys.stderr)
        return 1
    if not shutil.which("yxer"):
        ok, out = run(["npm", "install", "-g", "@yixiaoermail/cli@latest"])
        if not ok:
            print(f"yxer CLI 安装失败：{out}", file=sys.stderr)
            return 1
    print("工具链已准备完成。")
    for name, value in inspect_tools().items():
        print(f"{name}: {value}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="营销视频军师工具链检查/安装")
    ap.add_argument("--install", action="store_true", help="检查缺失项并显示安装计划")
    ap.add_argument("--confirm-install", action="store_true", help="用户明确确认后执行安装")
    args = ap.parse_args()
    if args.install:
        print("当前工具链：")
        for name, value in inspect_tools().items():
            print(f"{name}: {value}")
        return install(args.confirm_install)
    for name, value in inspect_tools().items():
        print(f"{name}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
