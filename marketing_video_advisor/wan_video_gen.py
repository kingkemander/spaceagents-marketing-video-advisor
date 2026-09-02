#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wan 3.0 多参考招商视频生成脚本（阿里云百炼 DashScope）
=========================================================
一条龙：素材上传 → 创建视频任务 → 轮询 → 下载 → 字幕烧录 → BGM 混音 → 终版

用法示例：
  # 横屏 16:9 招商片（人物+场景+音色，10 秒）
  python3 wan-video-gen.py \
    --prompt-file prompt.txt \
    --images 人物.png 场景-外立面.jpg 场景-露台.jpg \
    --audios 音色.mp3 \
    --duration 10 --ratio 16:9 --resolution 720P \
    --subtitle "0.3-3|850万，买一栋1400平米的独栋。" \
    --bgm bgm.mp3 --output 招商片-横屏.mp4

  # 竖屏 9:16（抖音/视频号）
  python3 wan-video-gen.py \
    --prompt-file prompt.txt \
    --images 人物.png 场景-外立面.jpg \
    --audios 音色.mp3 \
    --duration 10 --ratio 9:16 --resolution 720P \
    --subtitle "0.3-3|850万，买一栋1400平米的独栋。" --subtitle "3.2-7|独立入口、独立动线..." \
    --bgm bgm.mp3 --output 招商片-竖屏.mp4

Key：环境变量 DASHSCOPE_API_KEY 或 ~/.config/spaceagents-seedance/dashscope.key
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import urllib.error

# ---------- 配置 ----------
API_BASE = "https://llm-coge565i4eehwuk9.cn-beijing.maas.aliyuncs.com/api/v1"
SECRET_FILE = os.path.expanduser("~/.config/spaceagents-seedance/dashscope.key")
DEFAULT_OUT = "artifacts/videos"

# ---------- Key ----------
def get_key():
    k = os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("ALIYUN_DASHSCOPE_API_KEY")
    if k:
        return k.strip()
    try:
        with open(SECRET_FILE) as f:
            k = f.read().strip()
        if k:
            return k
    except Exception:
        pass
    return None

# ---------- 素材处理 ----------
def to_data_uri(path):
    ext = os.path.splitext(path)[1].lower()
    mime = {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".webp": "image/webp", ".bmp": "image/bmp", ".mp3": "audio/mpeg",
        ".wav": "audio/wav", ".mp4": "video/mp4", ".mov": "video/quicktime",
    }.get(ext, "application/octet-stream")
    import base64
    with open(path, "rb") as f:
        return f"data:{mime};base64,{base64.b64encode(f.read()).decode()}"

def upload_to_uguu(path, allow_public_upload=False):
    """仅在用户明确授权后，才把本地音频上传到第三方公网中转站。"""
    if not allow_public_upload:
        raise RuntimeError("本地音频不能默认上传到公网。请改用受信任 URL，或在确认隐私风险后显式传入 --allow-public-upload。")
    import mimetypes
    boundary = "----wanvideoskill" + str(int(time.time()))
    with open(path, "rb") as f:
        data = f.read()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="files[]"; filename="{os.path.basename(path)}"\r\n'
        f"Content-Type: {mimetypes.guess_type(path)[0] or 'application/octet-stream'}\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        "https://uguu.se/upload.php?output=text", data=body, method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=90) as r:
        text = r.read().decode()
    m = re.search(r"https?://[^\s\"']+", text)
    if not m:
        raise RuntimeError("图床上传失败，未返回 URL")
    return m.group(0)

def to_media_url(v, allow_public_upload=False):
    if re.match(r"^https?://", v) or v.startswith("data:"):
        return v
    ext = os.path.splitext(v)[1].lower()
    if ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
        return to_data_uri(v)  # 图片官方支持 base64
    return upload_to_uguu(v, allow_public_upload)   # 仅经明确授权的公网中转

# ---------- 任务 ----------
def create_task(key, prompt, images, audios, duration, resolution, ratio, model, allow_public_upload=False):
    media = []
    for i in images:
        media.append({"type": "reference_image", "url": to_media_url(i, allow_public_upload)})
    for a in audios:
        media.append({"type": "reference_audio", "url": to_media_url(a, allow_public_upload)})
    payload = {
        "model": model,
        "input": {"prompt": prompt, "media": media},
        "parameters": {"resolution": resolution, "ratio": ratio, "duration": duration},
    }
    req = urllib.request.Request(
        API_BASE + "/services/aigc/video-generation/video-synthesis",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}",
                 "X-DashScope-Async": "enable"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            d = json.loads(r.read())
        return d.get("output", {}).get("task_id")
    except urllib.error.HTTPError as e:
        print("❌ 创建任务失败:", e.read().decode(errors="replace")[:400])
        return None

def poll_task(key, task_id, timeout=1800):
    deadline = time.time() + timeout
    last = ""
    while time.time() < deadline:
        req = urllib.request.Request(f"{API_BASE}/tasks/{task_id}",
                                     headers={"Authorization": f"Bearer {key}"}, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read())
        except Exception as e:
            print("  查询异常:", str(e)[:60])
            time.sleep(10)
            continue
        st = d.get("output", {}).get("task_status")
        if st != last:
            print(f"⏳ 状态: {st}")
            last = st
        if st == "SUCCEEDED":
            return d.get("output", {}).get("video_url")
        if st in ("FAILED", "CANCELED", "UNKNOWN"):
            print("❌ 任务失败:", json.dumps(d, ensure_ascii=False)[:300])
            return None
        time.sleep(10)
    print("⏰ 轮询超时")
    return None

def download(url, path):
    with urllib.request.urlopen(url, timeout=300) as r:
        data = r.read()
    with open(path, "wb") as f:
        f.write(data)
    return path

# ---------- 后期：字幕 + BGM ----------
def build_ass(subtitles, width, height):
    lines = []
    for s in subtitles:
        m = re.match(r"([\d.]+)-([\d.]+)\|(.+)", s)
        if not m:
            continue
        start, end, text = float(m.group(1)), float(m.group(2)), m.group(3)
        def ts(t):
            ms = int((t - int(t)) * 1000)
            mm, ss = divmod(int(t), 60)
            return f"0:{mm:02d}:{ss:02d}.{ms:02d}"
        lines.append(f"Dialogue: 0,{ts(start)},{ts(end)},Default,,0,0,0,,{text}")
    font_size = 44 if height > width else 50
    margin_v = 60 if height > width else 40
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Hiragino Sans GB,{font_size},&H00FFFFFF,&H000000FF,&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,40,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(lines)

def postprocess(video, subtitles, bgm, output, duration):
    # 获取视频尺寸
    info = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", video],
                          capture_output=True, text=True)
    d = json.loads(info.stdout)
    vstream = next(s for s in d["streams"] if s["codec_type"] == "video")
    width, height = vstream["width"], vstream["height"]

    filters = []
    maps = []
    idx = 0
    if subtitles:
        ass_file = os.path.join(os.path.dirname(output), "_sub.ass")
        with open(ass_file, "w", encoding="utf-8") as f:
            f.write(build_ass(subtitles, width, height))
        filters.append(f"[0:v]ass={ass_file}[vout]")
        maps += ["-map", "[vout]"]
    else:
        maps += ["-map", "0:v"]

    inputs = ["-i", video]
    if bgm:
        inputs += ["-i", bgm]
        fade_start = max(float(duration) - 1.5, 0)
        has_source_audio = any(s.get("codec_type") == "audio" for s in d["streams"])
        if has_source_audio:
            filters.append(f"[1:a]atrim=0:{duration},volume=2.5,afade=t=out:st={fade_start}:d=1.5[bgm];"
                           "[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[aout]")
        else:
            filters.append(f"[1:a]atrim=0:{duration},volume=2.5,afade=t=out:st={fade_start}:d=1.5[aout]")
        maps += ["-map", "[aout]"]
    else:
        if any(s.get("codec_type") == "audio" for s in d["streams"]):
            maps += ["-map", "0:a"]

    cmd = ["ffmpeg", "-y", "-v", "error"] + inputs + ["-filter_complex", ";".join(filters)] + maps + \
          ["-c:v", "libx264", "-crf", "20", "-c:a", "aac", output]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("❌ 后期处理失败:", r.stderr[-500:])
        return None
    return output

# ---------- 主流程 ----------
def main():
    ap = argparse.ArgumentParser(description="Wan 3.0 多参考招商视频生成")
    ap.add_argument("--prompt", help="提示词/脚本（直接传）")
    ap.add_argument("--prompt-file", help="提示词文件路径")
    ap.add_argument("--images", nargs="*", default=[], help="参考图（本地路径或URL，顺序=图1/图2...）")
    ap.add_argument("--audios", nargs="*", default=[], help="参考音频（本地或URL，顺序=音频1/音频2...）")
    ap.add_argument("--duration", type=int, default=10, help="时长秒数 2-30")
    ap.add_argument("--resolution", default="720P", choices=["480P", "720P", "1080P"])
    ap.add_argument("--ratio", default="16:9", choices=["16:9", "9:16", "1:1", "4:3", "3:4", "adaptive"])
    ap.add_argument("--model", default="wan3.0-video", choices=["wan3.0-video", "wan3.0-video-prime"])
    ap.add_argument("--subtitle", action="append", default=[], help="字幕，格式：开始秒-结束秒|文本（可多次）")
    ap.add_argument("--bgm", help="BGM 音频文件路径")
    ap.add_argument("--output", help="输出文件名（含路径或相对路径）")
    ap.add_argument("--workdir", default=".", help="工作目录（默认当前目录）")
    ap.add_argument("--allow-public-upload", action="store_true", help="确认将本地音频上传到第三方公网中转站；默认禁止")
    args = ap.parse_args()

    key = get_key()
    if not key:
        print("❌ 未找到 Key：设置 DASHSCOPE_API_KEY 或写入 ~/.config/spaceagents-seedance/dashscope.key")
        sys.exit(1)

    prompt = args.prompt
    if args.prompt_file:
        with open(args.prompt_file, encoding="utf-8") as f:
            prompt = f.read()
    if not prompt:
        print("❌ 需要 --prompt 或 --prompt-file")
        sys.exit(1)

    out_dir = os.path.join(args.workdir, DEFAULT_OUT)
    os.makedirs(out_dir, exist_ok=True)
    base = args.output or f"wan3-{int(time.time())}"
    if not base.endswith(".mp4"):
        base += ".mp4"
    raw_path = os.path.join(out_dir, "_raw-" + base)
    final_path = os.path.join(out_dir, base)

    # 1. 创建任务
    print("🚀 提交任务...")
    tid = create_task(key, prompt, args.images, args.audios, args.duration, args.resolution, args.ratio, args.model, args.allow_public_upload)
    if not tid:
        sys.exit(1)

    # 2. 轮询 + 下载
    print("⏳ 等待生成（通常 1-5 分钟）...")
    url = poll_task(key, tid)
    if not url:
        sys.exit(1)
    download(url, raw_path)
    print(f"✅ 原片已下载: {raw_path}")

    # 3. 后期（字幕+BGM）
    if args.subtitle or args.bgm:
        print("🎬 后期处理（字幕+BGM）...")
        done = postprocess(raw_path, args.subtitle, args.bgm, final_path, args.duration)
        if done:
            print(f"🎉 终版完成: {final_path}")
            if sys.platform == "darwin":
                subprocess.run(["open", final_path])
        else:
            print(f"⚠️ 后期失败，原片在: {raw_path}")
    else:
        import shutil
        shutil.move(raw_path, final_path)
        print(f"🎉 完成（无后期）: {final_path}")
        if sys.platform == "darwin":
            subprocess.run(["open", final_path])

if __name__ == "__main__":
    main()
