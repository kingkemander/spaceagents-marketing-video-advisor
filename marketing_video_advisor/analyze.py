#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音账号检测分析脚本
========================
一键生成：账号体检 + 对标矩阵 + 爆款拆解 + 完整 HTML/PDF 报告

用法:
  python3 analyze.py <抖音账号链接> [--keyword 行业关键词] [--out 报告名] [--no-benchmark]
  python3 analyze.py "https://v.douyin.com/_KkU7Hg07YI/" --keyword 产业园

依赖: 仅 Python 3 标准库（urllib / json / html / datetime）
数据源: AutoApi 抖音数据接口（token.spaceagents.cn），按次计费
"""
import argparse
import html
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime

# ---------- 配置 ----------
def load_config():
    """密钥只能通过当前用户的环境/私密目录注入，绝不随插件分发。"""
    return {
        "api_base": os.environ.get("DOUYIN_API_BASE", "https://token.spaceagents.cn"),
        "api_key": os.environ.get("DOUYIN_API_KEY", ""),
    }

CFG = load_config()
BASE = CFG["api_base"]
KEY = CFG["api_key"]

def post(path, payload, retries=3, timeout=45):
    """调用接口，带重试"""
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
    )
    for i in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            if i == retries:
                return {"_err": f"{e}"}
            time.sleep(1.5)
    return {"_err": "unknown"}

def get(path):
    req = urllib.request.Request(BASE + path, headers={"Authorization": f"Bearer {KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"_err": f"{e}"}

# ---------- 数据层 ----------
def account_detail(home_page):
    """账号详情: 粉丝/获赞/作品/签名"""
    return post("/api/douyin_user_detail", {"home_page": home_page})

def account_videos(home_page, limit=30):
    """作品列表: 每条视频的互动数据"""
    d = post("/api/douyin_user_videos", {"home_page": home_page})
    return d if isinstance(d, list) else []

def search_users(keyword, count=10):
    """搜索用户（找对标）"""
    d = post("/api/douyin_user_search", {"keyword": keyword, "count": count})
    return d if isinstance(d, list) else []

def search_videos(keyword):
    """搜索视频（找行业爆款）"""
    d = post("/api/douyin_video_search", {
        "keyword": keyword, "sort_type": "0", "publish_time": "0",
        "filter_duration": "0", "content_type": "0", "max_pages": 1,
    })
    return d if isinstance(d, list) else []

def video_to_text(video_url):
    """视频转文字（爆款文案拆解）"""
    return post("/api/video_to_text", {"video_url": video_url}, timeout=60)

def hot_list():
    """抖音热榜"""
    return get("/api/douyin_hot_list")

# ---------- 分析层 ----------
def analyze_account(home_page):
    """账号体检"""
    detail = account_detail(home_page)
    if "_err" in detail:
        return {"error": detail["_err"]}
    videos = account_videos(home_page)
    ident, stats, profile = detail.get("identity", {}), detail.get("stats", {}), detail.get("profile", {})

    # 内容统计
    total, likes, avg_likes = len(videos), 0, 0
    top, flat = [], []
    month_pub = {}
    if videos:
        likes = sum(v.get("statistics", {}).get("digg_count", 0) for v in videos)
        avg_likes = round(likes / len(videos))
        for v in videos:
            s = v.get("statistics", {})
            item = {
                "time": v.get("create_time_formatted", "?"),
                "dur": v.get("duration", "?"),
                "digg": s.get("digg_count", 0), "comment": s.get("comment_count", 0),
                "collect": s.get("collect_count", 0), "share": s.get("share_count", 0),
                "desc": v.get("desc", "")[:60],
            }
            (top if item["digg"] >= avg_likes else flat).append(item)
            m = (v.get("create_time_formatted") or "?")[:7]
            month_pub[m] = month_pub.get(m, 0) + 1
        top.sort(key=lambda x: -x["digg"])

    return {
        "identity": ident, "stats": stats, "profile": profile,
        "videos": videos, "top5": top[:5], "flat_count": len(flat),
        "avg_likes": avg_likes, "month_pub": dict(sorted(month_pub.items())),
        "home_page": home_page,
    }

def analyze_benchmark(keyword, exclude_nick="", max_accounts=6):
    """对标矩阵：搜同行业账号 → 拉详情"""
    results, seen = [], set()
    kws = [keyword, keyword + " 出租", "厂房出租", keyword + " 招商"]
    for kw in kws:
        users = search_users(kw, count=15)
        if not isinstance(users, list):
            continue
        for u in users:
            nick = (u.get("nickname") or "").strip()
            sec = u.get("sec_uid", "")
            if not sec or not nick or nick in seen:
                continue
            if exclude_nick and exclude_nick in nick:
                continue
            seen.add(nick)
            results.append({"nick": nick, "sec": sec, "fans": u.get("follower_count", 0)})
        if len(results) >= max_accounts * 2:
            break
    # 按粉丝排序取 top
    results.sort(key=lambda x: -x["fans"])
    top = results[:max_accounts]

    matrix = []
    for a in top:
        d = account_detail(f"https://www.douyin.com/user/{a['sec']}")
        if "_err" in d:
            continue
        ident, st, pf = d.get("identity", {}), d.get("stats", {}), d.get("profile", {})
        matrix.append({
            "nick": ident.get("nickname", a["nick"]),
            "fans": st.get("follower_count", a["fans"]),
            "likes": st.get("total_favorited", 0),
            "works": st.get("aweme_count", 0),
            "sign": (pf.get("signature") or "")[:80],
        })
    return matrix[:max_accounts]

def analyze_bomb(keyword):
    """行业爆款拆解：多关键词 + 多条视频尝试转写"""
    tried = 0
    for kw in [keyword + " 干货", keyword, keyword + " 招商", keyword + " 出租"]:
        vids = search_videos(kw)
        if not isinstance(vids, list) or not vids:
            continue
        for v in vids[:2]:
            share = v.get("share_url") or f"https://www.iesdouyin.com/share/video/{v.get('aweme_id')}/"
            author = v.get("author", {})
            txt = video_to_text(share)
            text = txt.get("text", "") if isinstance(txt, dict) else ""
            tried += 1
            if len(text) > 30:  # 转写成功
                return {
                    "author": author.get("nickname", "?"),
                    "desc": v.get("desc", "")[:60],
                    "share_url": share,
                    "text": text[:1200],
                }
    return None

# ---------- 报告层 ----------
def build_html(acc, benchmark, bomb, hot, keyword, costs):
    def esc(x): return html.escape(str(x))

    # KPI
    st = acc["stats"]
    kpi = (
        f'<div class="kpi">'
        f'<div class="item"><div class="num">{esc(st.get("follower_count", 0))}</div><div class="lab">粉丝</div></div>'
        f'<div class="item"><div class="num">{esc(st.get("total_favorited", 0))}</div><div class="lab">获赞</div></div>'
        f'<div class="item"><div class="num">{esc(acc["avg_likes"])}</div><div class="lab">均赞</div></div>'
        f'<div class="item"><div class="num">{esc(st.get("aweme_count", 0))}</div><div class="lab">作品</div></div>'
        f'<div class="item"><div class="num">{len(acc["month_pub"])}</div><div class="lab">活跃月份</div></div></div>'
    )

    # 月度更新表
    rows = "".join(
        f'<tr><td>{esc(m)}</td><td>{n}</td></tr>' for m, n in acc["month_pub"].items()
    ) or "<tr><td>-</td><td>无作品</td></tr>"

    # 爆款表
    top_rows = ""
    for v in acc["top5"]:
        top_rows += (
            f'<tr><td>{esc(v["desc"])}</td><td>{v["digg"]}</td>'
            f'<td>{v["share"]}</td><td>{v["time"]}</td></tr>'
        )
    if not top_rows:
        top_rows = "<tr><td colspan=4>暂无数据</td></tr>"

    # 对标表
    bm_rows = ""
    for i, b in enumerate(benchmark, 1):
        bm_rows += (
            f'<tr><td>{i}</td><td>{esc(b["nick"])}</td><td>{b["fans"]}</td>'
            f'<td>{b["likes"]}</td><td>{b["works"]}</td><td>{esc(b["sign"])}</td></tr>'
        )
    if not bm_rows:
        bm_rows = "<tr><td colspan=6>未获取到对标数据</td></tr>"

    # 爆款拆解
    bomb_html = ""
    if bomb:
        bomb_html = (
            f'<blockquote><b>爆款账号：{esc(bomb["author"])}</b> · {esc(bomb["desc"])}<br><br>'
            f'{esc(bomb["text"]).replace(chr(10), "<br>")}</blockquote>'
        )
    else:
        bomb_html = "<div class='card'>爆款转写失败（视频可能无语音或接口繁忙），可稍后重试。</div>"

    # 热榜
    hot_rows = ""
    if isinstance(hot, list):
        hot_rows = "".join(
            f'<tr><td>{h.get("rank", i)}</td><td>{esc(h.get("title", ""))}</td>'
            f'<td>{esc(h.get("hot", ""))}</td></tr>'
            for i, h in enumerate(hot[:10], 1)
        )
    if not hot_rows:
        hot_rows = "<tr><td colspan=3>热榜获取失败</td></tr>"

    name = acc["identity"].get("nickname", "该账号")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><title>账号分析报告 - {esc(name)}</title>
<style>
  @page {{ size: A4; margin: 14mm 13mm; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: "PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif; color:#1f2937; font-size:12px; line-height:1.65; }}
  h1 {{ font-size: 24px; color:#0f2f57; }}
  h2 {{ font-size:16px; color:#fff; background:#0f2f57; padding:7px 14px; border-radius:6px; margin:26px 0 12px; }}
  h3 {{ font-size:13.5px; color:#0f2f57; margin:16px 0 6px; border-left:4px solid #e8731c; padding-left:8px; }}
  table {{ width:100%; border-collapse:collapse; margin:8px 0 14px; font-size:11.5px; }}
  th {{ background:#eef2f7; color:#0f2f57; text-align:left; padding:6px 9px; border:1px solid #d5dce6; }}
  td {{ padding:6px 9px; border:1px solid #d5dce6; vertical-align:top; }}
  tr:nth-child(even) td {{ background:#fafbfd; }}
  .card {{ border:1px solid #e2e8f0; border-radius:8px; padding:12px 14px; margin:10px 0; background:#f8fafc; }}
  .kpi {{ display:flex; flex-wrap:wrap; gap:8px; margin:10px 0; }}
  .kpi .item {{ flex:1 1 18%; min-width:110px; background:#0f2f57; color:#fff; border-radius:8px; padding:10px; text-align:center; }}
  .kpi .num {{ font-size:20px; font-weight:700; color:#ffb347; }}
  .kpi .lab {{ font-size:10.5px; opacity:.9; }}
  blockquote {{ border-left:4px solid #e8731c; background:#fff7ed; padding:10px 14px; margin:10px 0; border-radius:0 6px 6px 0; color:#7c2d12; }}
  .cover {{ text-align:center; padding:60px 20px 30px; }}
  .cover h1 {{ font-size:30px; margin-bottom:10px; }}
  .tag {{ display:inline-block; background:#e8731c; color:#fff; border-radius:20px; padding:4px 16px; font-size:12px; margin:6px 3px; }}
  .meta {{ color:#6b7280; font-size:11px; margin-top:26px; }}
  .pagebreak {{ page-break-before: always; }}
</style></head><body>

<div class="cover">
  <h1>账号分析报告</h1>
  <div style="font-size:14px;color:#0f2f57;margin:6px 0 14px;">{esc(name)}</div>
  <div><span class="tag">账号体检</span><span class="tag">对标矩阵</span><span class="tag">爆款拆解</span><span class="tag">热点选题</span></div>
  <div class="meta">生成时间：{now} ｜ 行业关键词：{esc(keyword)} ｜ 数据源：AutoApi 抖音接口<br>接口调用成本合计：¥{costs:.2f}</div>
</div>

<h2>一、账号概览</h2>
{kpi}
<div class="card"><b>签名：</b>{esc(acc['profile'].get('signature', '无'))}</div>

<h2>二、更新节奏</h2>
<table><tr><th>月份</th><th>发布数</th></tr>{rows}</table>

<h2>三、爆款 Top5</h2>
<table><tr><th>视频</th><th>点赞</th><th>转发</th><th>时间</th></tr>{top_rows}</table>
<div class="card">共 {len(acc['videos'])} 条作品，均赞 {acc['avg_likes']}；低于均赞 {acc['flat_count']} 条 —— 断层说明选题质量不稳定。</div>

<div class="pagebreak"></div>
<h2>四、对标账号矩阵（{len(benchmark)} 个）</h2>
<table><tr><th>#</th><th>账号</th><th>粉丝</th><th>获赞</th><th>作品</th><th>简介</th></tr>{bm_rows}</table>

<h2>五、行业爆款拆解（{esc(bomb['author']) if bomb else '—'}）</h2>
{bomb_html}

<h2>六、抖音实时热榜 Top10</h2>
<table><tr><th>排名</th><th>话题</th><th>热度</th></tr>{hot_rows}</table>
<div class="card">建议：每周从热榜挑 1-2 条与行业相关的热点做内容，蹭流量。</div>

</body></html>"""

# ---------- 主流程 ----------
def main():
    ap = argparse.ArgumentParser(description="抖音账号检测分析")
    ap.add_argument("url", help="抖音账号链接（主页/分享短链均可）")
    ap.add_argument("--keyword", default="产业园", help="行业关键词（对标/爆款搜索用）")
    ap.add_argument("--out", default=None, help="报告文件名（不含扩展名）")
    ap.add_argument("--no-benchmark", action="store_true", help="跳过对标与爆款拆解，只做账号体检")
    ap.add_argument("--confirm-paid", action="store_true", help="确认本次完整检索会使用付费第三方数据服务")
    args = ap.parse_args()
    if not KEY:
        ap.error("未配置 DOUYIN_API_KEY；请在对话中授权后写入当前工作区私密目录")
    if not args.no_benchmark and not args.confirm_paid:
        ap.error("完整对标/爆款检索会产生第三方数据服务费用；确认后增加 --confirm-paid，或使用 --no-benchmark 做基础体检")

    print(f"① 账号体检：{args.url}")
    acc = analyze_account(args.url)
    for _ in range(2):
        if "error" not in acc:
            break
        print(f"  接口波动重试中（{acc['error']}）...")
        time.sleep(2)
        acc = analyze_account(args.url)
    if "error" in acc:
        print(f"✗ 账号解析失败：{acc['error']}")
        sys.exit(1)
    name = acc["identity"].get("nickname", "账号")
    print(f"  ✓ {name} | 粉丝{acc['stats'].get('follower_count', 0)} | 作品{len(acc['videos'])}条")

    hot = hot_list()
    if isinstance(hot, list):
        print(f"  ✓ 热榜 Top1：{hot[0].get('title', '?')}")
    else:
        print("  - 热榜获取失败，跳过")

    bomb, benchmark = None, []
    if not args.no_benchmark:
        print(f"② 对标搜索（关键词：{args.keyword}）")
        benchmark = analyze_benchmark(args.keyword, exclude_nick=name)
        print(f"  ✓ 获取 {len(benchmark)} 个对标账号")

        print("③ 行业爆款拆解")
        bomb = analyze_bomb(args.keyword)
        if bomb:
            print(f"  ✓ 拆解 {bomb['author']}：{bomb['desc']}")
        else:
            print("  - 爆款转写失败，跳过")

    # 成本估算
    calls = 1 + len(acc["videos"]) // 20 + 1 + len(benchmark) + 1 + 2 + 1
    costs = round(calls * 0.05, 2)  # 粗略估算，详见 config.json 单价

    print("④ 生成报告")
    html_str = build_html(acc, benchmark, bomb, hot, args.keyword, costs)
    out_name = args.out or f"抖音账号分析-{name}"
    out_html = os.path.join(os.getcwd(), out_name + ".html")
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html_str)

    # 尝试转 PDF（本机有 Chrome 时）
    pdf_path = None
    chrome_candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    ]
    chrome = next((c for c in chrome_candidates if os.path.exists(c)), None)
    if chrome:
        pdf_path = os.path.join(os.getcwd(), out_name + ".pdf")
        subprocess.run(
            [chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
             f"--print-to-pdf={pdf_path}", out_html],
            capture_output=True, timeout=120,
        )
        print(f"  ✓ PDF：{os.path.basename(pdf_path)}")

    print(f"  ✓ HTML：{os.path.basename(out_html)}")
    print(f"\n完成！报告已生成（成本约 ¥{costs}）。")

if __name__ == "__main__":
    main()
