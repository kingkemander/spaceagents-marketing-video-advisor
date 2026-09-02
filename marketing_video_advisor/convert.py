#!/usr/bin/env python3
"""把已确认的视频执行卡转换为提示词、准确字幕时间轴及可复现命令。"""
from __future__ import annotations

import argparse
import json
import shlex
from pathlib import Path


def scene_map(scenes: dict) -> str:
    return "；".join(f"{key}={value}" for key, value in scenes.items()) + "。"


def timeline(lines: list[dict], total_duration: int) -> list[dict]:
    if not lines:
        raise ValueError("执行卡缺少 script_lines")
    cursor = 0.0
    result = []
    for index, item in enumerate(lines, 1):
        seconds = float(item.get("duration", 0))
        text = str(item.get("text", "")).strip()
        if seconds <= 0 or not text:
            raise ValueError(f"第 {index} 段必须有正时长和台词")
        result.append({"start": cursor, "end": cursor + seconds, "text": text,
                       "shot": item.get("shot") or item.get("scene") or "按参考图稳定呈现"})
        cursor += seconds
    if abs(cursor - total_duration) > 0.01:
        raise ValueError(f"执行卡台词时长合计为 {cursor:g} 秒，与请求的 {total_duration} 秒不一致；请先调整执行卡。")
    return result


def prompt(cfg: dict, segments: list[dict]) -> str:
    rows = []
    for item in segments:
        rows.append(f"{item['start']:g}-{item['end']:g} 秒：{item['shot']}。数字人台词：\"{item['text']}\"")
    return "\n".join([
        f"【参考素材】{scene_map(cfg.get('scenes', {}))}",
        f"【整体风格】{cfg.get('style', '真实、克制、专业的商业视频质感。')}",
        "【镜头与台词时间轴】", *rows,
        "【一致性】人物身份、脸部、服装与参考图一致；建筑外立面、露台和园区布局以参考图为准；镜头运动克制，避免无意义动作。",
        "【声音】台词清晰、语速与时间轴匹配；环境声轻铺。",
        f"【负面约束】{cfg.get('negative', '人物不变脸、不换装、不出现多人；无水印、无畸形建筑、无无关文字。')}",
    ])


def subtitle_lines(segments: list[dict]) -> list[str]:
    return [f"{item['start']:.1f}-{max(item['end'] - 0.1, item['start'] + 0.1):.1f}|{item['text']}" for item in segments]


def cli(cfg: dict, args: argparse.Namespace, subtitles: list[str]) -> str:
    asset_dir = cfg.get("assets_dir", "视频素材/客户名")
    images = [f"{asset_dir}/{name}" for name in ("人物.png", "场景-外立面.jpg", "场景-露台室内.jpg", "场景-区域配套.jpg")]
    runtime = "<运行时目录>/wan_video_gen.py"
    command = ["python3", runtime, "--prompt-file", "prompt.txt", "--images", *images,
               "--audios", f"{asset_dir}/音色.mp3", "--duration", str(args.duration),
               "--ratio", args.ratio, "--resolution", args.resolution]
    for item in subtitles:
        command.extend(["--subtitle", item])
    command.extend(["--output", f"{cfg.get('id', 'video')}.mp4"])
    return " \\\n+  ".join(shlex.quote(part) for part in command)


def main() -> int:
    ap = argparse.ArgumentParser(description="执行卡转视频脚本")
    ap.add_argument("card")
    ap.add_argument("--duration", type=int, required=True, help="必须与执行卡各段 duration 合计一致")
    ap.add_argument("--ratio", default="9:16")
    ap.add_argument("--resolution", default="720P")
    ap.add_argument("--out")
    args = ap.parse_args()
    if not 2 <= args.duration <= 30:
        ap.error("时长必须在 2-30 秒之间")
    cfg = json.loads(Path(args.card).read_text(encoding="utf-8"))
    segments = timeline(cfg.get("script_lines", []), args.duration)
    subtitles = subtitle_lines(segments)
    out_dir = Path(args.out or Path(args.card).parent / "out")
    out_dir.mkdir(parents=True, exist_ok=True)
    identity = cfg.get("id", "video")
    (out_dir / f"{identity}-prompt.txt").write_text(prompt(cfg, segments), encoding="utf-8")
    (out_dir / f"{identity}-subtitles.txt").write_text("\n".join(subtitles) + "\n", encoding="utf-8")
    (out_dir / f"{identity}-cli.sh").write_text(cli(cfg, args, subtitles) + "\n", encoding="utf-8")
    print(f"已生成：{out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
