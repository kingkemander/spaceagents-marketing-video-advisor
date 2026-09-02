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
import shutil
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
        "api_key": os.environ.get("SPACEAGENTS_AUTO_API_KEY") or os.environ.get("DOUYIN_API_KEY", ""),
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


def _number(value):
    """接口字段可能是空字符串，统一转成非负整数。"""
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _latest_video_date(videos):
    """尽量从接口格式化日期取得最近发布日；字段异常时宁可不判断。"""
    candidates = []
    for video in videos:
        raw = str(video.get("create_time_formatted") or "")
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y/%m/%d"):
            try:
                candidates.append(datetime.strptime(raw[:16], fmt))
                break
            except ValueError:
                continue
    return max(candidates) if candidates else None


def diagnose_account(acc, keyword):
    """将公开账号数据转成可解释、可执行的经营诊断。

    不把封面、出镜表现或视频画面当作已验证事实：本函数仅使用接口返回的
    主页签名、作品标题、发布时间和互动字段，所有结论均给出相应证据。
    """
    videos = acc.get("videos", [])
    stats = acc.get("stats", {})
    profile = acc.get("profile", {})
    signature = str(profile.get("signature") or "").strip()
    descriptions = [str(v.get("desc") or "") for v in videos]
    text = " ".join([signature] + descriptions).lower()
    fans = _number(stats.get("follower_count"))
    works = _number(stats.get("aweme_count")) or len(videos)
    avg_likes = _number(acc.get("avg_likes"))
    likes = [_number(v.get("statistics", {}).get("digg_count")) for v in videos]
    comments = [_number(v.get("statistics", {}).get("comment_count")) for v in videos]
    shares = [_number(v.get("statistics", {}).get("share_count")) for v in videos]
    collects = [_number(v.get("statistics", {}).get("collect_count")) for v in videos]
    latest = _latest_video_date(videos)
    days_since = (datetime.now() - latest).days if latest else None
    top_like = max(likes) if likes else 0
    top_ratio = round(top_like / avg_likes, 1) if avg_likes else None
    interaction_avg = round((sum(likes) + sum(comments) + sum(shares) + sum(collects)) / len(videos)) if videos else 0

    # 当前定位：依据签名和作品标题中可观察到的线索，不假装读过视频画面。
    business_terms = [x for x in ("产业园", "厂房", "独栋", "写字楼", "企业选址", "招商", keyword.lower()) if x and x.lower() in text]
    location_terms = [x for x in ("太原", "坞城", "山西", "园区") if x.lower() in text]
    has_contact = any(ch.isdigit() for ch in signature) or any(x in signature for x in ("联系", "私信", "咨询", "电话"))
    has_customer = any(x in text for x in ("老板", "企业", "创业", "工厂", "公司", "客户"))
    has_offer = any(x in text for x in ("平米", "㎡", "户型", "出租", "出售", "租", "买", "独栋"))

    positioning_parts = []
    if location_terms:
        positioning_parts.append("本地产业载体")
    if business_terms:
        positioning_parts.append("企业选址/园区招商")
    if has_offer:
        positioning_parts.append("厂房与独栋空间供给")
    positioning = " · ".join(positioning_parts) if positioning_parts else "定位信号不足，暂无法从公开字段确认主营方向"
    audience = "企业老板、选址决策者及产业服务合作方" if has_customer else "目标客户在公开文案中未被稳定点明"

    # 健康度用于排优先级，不以“算法评分”冒充真实平台权重。
    positioning_score = 0
    positioning_score += 35 if business_terms else 0
    positioning_score += 25 if location_terms else 0
    positioning_score += 20 if has_customer else 0
    positioning_score += 20 if has_contact else 0
    cadence_score = 70 if days_since is not None and days_since <= 14 else 45 if days_since is not None and days_since <= 30 else 20 if days_since is not None else 0
    cadence_score = min(100, cadence_score + min(len(acc.get("month_pub", {})) * 5, 25))
    efficiency_score = 65 if avg_likes >= 100 else 45 if avg_likes >= 30 else 25
    if top_ratio and top_ratio >= 4:
        efficiency_score -= 15  # 头部断层意味着可复制性不足
    conversion_score = 50 + (25 if has_contact else 0) + (15 if has_customer else 0) + (10 if has_offer else 0)

    risks = []
    actions = []
    if days_since is None:
        risks.append(("更新节奏无法判定", "作品发布时间字段缺失，先补齐近 30 天发布记录后再判断频次。"))
    elif days_since > 30:
        risks.append(("更新已中断", f"最近一条公开作品距今约 {days_since} 天，账号难以累积稳定推荐信号。"))
        actions.append(("P0｜恢复稳定发布", "先连续 4 周每周 3 条：周一选址问题、周三园区实景/节点、周五客户决策案例；先稳定频率，再追爆款。", "以每周发布≥3条、连续4周完成率为验收。"))
    elif days_since > 14:
        risks.append(("更新间隔偏长", f"最近一条公开作品距今约 {days_since} 天，建议将发布间隔压缩到 3 天以内。"))
        actions.append(("P0｜建立内容周节奏", "固定每周 3 条，提前一次性写完标题、口播和拍摄清单，避免临时断更。", "以连续28天发布≥8条为验收。"))
    if len(acc.get("month_pub", {})) <= 2:
        risks.append(("有效样本不足", f"接口返回 {len(videos)} 条作品，但仅覆盖 {len(acc.get('month_pub', {}))} 个活跃月份，无法形成稳定内容模型。"))
    if top_ratio and top_ratio >= 4:
        risks.append(("爆款依赖明显", f"最高赞 {top_like}，约为均赞的 {top_ratio} 倍；头部内容带动强，但中位内容承接不足。"))
        actions.append(("P1｜复用有效选题结构", "把 Top3 作品分别拆成“开头问题—目标客户—空间/区位证据—行动引导”，每个结构至少衍生 3 条，不直接复制原文案。", "新发9条中，至少6条使用已验证结构；均赞较当前提升30%。"))
    if not has_customer or not has_offer or not has_contact:
        missing = "、".join(x for x, ok in (("目标客户", has_customer), ("核心产品/面积", has_offer), ("明确咨询动作", has_contact)) if not ok)
        risks.append(("主页转化信息不完整", f"签名中未稳定呈现：{missing}。访问者需要自行猜测“适不适合我、下一步怎么问”。"))
        actions.append(("P0｜重写主页三件套", "头像表达“人/品牌”，昵称保留区域+业务，签名按“服务谁｜有什么空间/价值｜在哪｜如何咨询”四句式重写；置顶三条分别讲园区总览、主力户型、到访流程。", "新用户在10秒内能回答：你服务谁、卖什么、在哪、怎样咨询。"))
    if interaction_avg and fans and interaction_avg / max(fans, 1) < 0.01:
        risks.append(("互动与粉丝体量不匹配", f"近 {len(videos)} 条样本平均总互动约 {interaction_avg}，需优先测试更强的问题型开头与本地决策场景。"))
    if not actions:
        actions.append(("P1｜建立可复制内容栏目", "保留现有表现较好的话题，新增“企业选址避坑、真实空间答疑、园区进度与配套、客户决策故事”四类固定栏目。", "30天内每类至少发布2条，并按完播、咨询、到访线索复盘。"))
    if not any(title.startswith("P0") for title, _, _ in actions):
        actions.insert(0, ("P0｜明确账号一句话定位", "将主页、置顶视频和前3秒口播统一为同一承诺：为哪类企业解决什么选址/空间问题。", "随机抽查3个入口，定位表述一致。"))

    return {
        "positioning": positioning,
        "audience": audience,
        "evidence": f"公开签名与 {len(videos)} 条作品标题中识别到：{('、'.join(business_terms[:5]) or '有效业务关键词不足')}。",
        "latest": latest.strftime("%Y-%m-%d") if latest else "未取得",
        "days_since": days_since,
        "scores": [("定位清晰度", positioning_score), ("更新稳定度", cadence_score), ("内容效率", max(0, efficiency_score)), ("转化准备度", min(100, conversion_score))],
        "risks": risks,
        "actions": actions[:4],
        "content_note": "本报告的定位与问题判断仅依据接口返回的公开字段、作品标题、发布时间及互动数据；封面、画面品质、出镜表现和评论语义需在取得视频素材或逐条转写后再补充判断。",
    }

# ---------- 报告层 ----------
def build_html(acc, benchmark, bomb, hot, keyword, costs):
    def esc(x): return html.escape(str(x))
    diagnosis = diagnose_account(acc, keyword)

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

    score_cards = "".join(
        f'<div class="score"><b>{esc(label)}</b><span>{score}<small>/100</small></span></div>'
        for label, score in diagnosis["scores"]
    )
    risk_html = "".join(
        f'<div class="risk"><b>{esc(title)}</b><p>{esc(detail)}</p></div>'
        for title, detail in diagnosis["risks"]
    ) or "<div class='card'>当前样本未发现需优先处理的结构性风险；仍建议持续跟踪发布节奏与咨询线索。</div>"
    action_rows = "".join(
        f'<tr><td><b>{esc(priority)}</b></td><td>{esc(action)}</td><td>{esc(metric)}</td></tr>'
        for priority, action, metric in diagnosis["actions"]
    )

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
  .scoregrid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin:10px 0 14px; }}
  .score {{ border:1px solid #d7e1ef; border-radius:8px; padding:10px; background:#f8fbff; color:#274766; }}
  .score b {{ display:block; font-size:11px; font-weight:600; }}
  .score span {{ display:block; margin-top:3px; color:#e8731c; font-size:23px; font-weight:700; }}
  .score small {{ font-size:10px; color:#718096; margin-left:2px; }}
  .risk {{ border-left:4px solid #e8731c; background:#fff8ef; padding:9px 12px; margin:7px 0; border-radius:0 6px 6px 0; }}
  .risk p {{ margin-top:2px; color:#5e503d; }}
  .label {{ display:inline-block; padding:2px 7px; margin-right:5px; border-radius:99px; background:#e8f0fb; color:#0f4c81; font-size:10.5px; }}
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

<h2>二、账号定位与经营结论</h2>
<div class="card"><span class="label">当前定位</span><b>{esc(diagnosis['positioning'])}</b><br>
<span class="label">目标人群</span>{esc(diagnosis['audience'])}<br>
<span class="label">判断依据</span>{esc(diagnosis['evidence'])}</div>
<div class="scoregrid">{score_cards}</div>
<div class="card"><b>一句话结论：</b>账号已有产业空间/企业选址的业务信号，但下一阶段不应只追求播放量，应优先把“定位一致、稳定更新、咨询转化”做成闭环；以下问题和动作按公开数据优先级排序。</div>

<h3>优先问题</h3>
{risk_html}

<h3>30 天优化动作</h3>
<table><tr><th>优先级</th><th>要做什么</th><th>如何验收</th></tr>{action_rows}</table>
<div class="card"><b>数据边界：</b>{esc(diagnosis['content_note'])}</div>

<h2>三、更新节奏</h2>
<table><tr><th>月份</th><th>发布数</th></tr>{rows}</table>
<div class="card">最近公开作品：{esc(diagnosis['latest'])}{f'（距今约 {diagnosis["days_since"]} 天）' if diagnosis['days_since'] is not None else '（接口未返回可识别发布时间）'}。</div>

<h2>四、作品表现与可复制线索</h2>
<table><tr><th>视频</th><th>点赞</th><th>转发</th><th>时间</th></tr>{top_rows}</table>
<div class="card">共 {len(acc['videos'])} 条作品，均赞 {acc['avg_likes']}；低于均赞 {acc['flat_count']} 条。Top 内容只代表当前有效的标题/主题信号，需结合逐条转写后再判断完整话术与镜头结构。</div>

<div class="pagebreak"></div>
<h2>五、对标账号矩阵（{len(benchmark)} 个）</h2>
<table><tr><th>#</th><th>账号</th><th>粉丝</th><th>获赞</th><th>作品</th><th>简介</th></tr>{bm_rows}</table>

<h2>六、行业爆款拆解（{esc(bomb['author']) if bomb else '—'}）</h2>
{bomb_html}

<h2>七、抖音实时热榜 Top10</h2>
<table><tr><th>排名</th><th>话题</th><th>热度</th></tr>{hot_rows}</table>
<div class="card">建议：每周从热榜挑 1-2 条与行业相关的热点做内容，蹭流量。</div>

</body></html>"""

# ---------- 主流程 ----------
def main():
    ap = argparse.ArgumentParser(description="抖音账号检测分析")
    ap.add_argument("url", help="抖音账号链接（主页/分享短链均可）")
    ap.add_argument("--keyword", default="产业园", help="行业关键词（对标/爆款搜索用）")
    ap.add_argument("--out", default=None, help="报告文件名（不含扩展名）")
    ap.add_argument("--out-dir", default=".", help="HTML/PDF 报告输出目录")
    ap.add_argument("--no-benchmark", action="store_true", help="跳过对标与爆款拆解，只做账号体检")
    ap.add_argument("--confirm-paid", action="store_true", help="确认本次完整检索会使用付费第三方数据服务")
    args = ap.parse_args()
    if not KEY:
        ap.error("未配置 SPACEAGENTS_AUTO_API_KEY（或 DOUYIN_API_KEY）；请在算力中心环境中运行或由用户授权配置")
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
    os.makedirs(args.out_dir, exist_ok=True)
    out_html = os.path.join(args.out_dir, out_name + ".html")
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html_str)

    # 尝试转 PDF（本机有 Chrome 时）
    pdf_path = None
    chrome_candidates = [
        os.environ.get("CHROME_PATH", ""),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        os.path.join(os.environ.get("PROGRAMFILES", ""), "Google/Chrome/Application/chrome.exe"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Microsoft/Edge/Application/msedge.exe"),
        shutil.which("google-chrome") or "",
        shutil.which("chromium") or "",
        shutil.which("msedge") or "",
    ]
    chrome = next((c for c in chrome_candidates if c and os.path.exists(c)), None)
    if chrome:
        pdf_path = os.path.join(args.out_dir, out_name + ".pdf")
        subprocess.run(
            [chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
             f"--print-to-pdf={pdf_path}", out_html],
            capture_output=True, timeout=120,
        )
        if os.path.isfile(pdf_path):
            print(f"  ✓ PDF：{os.path.basename(pdf_path)}")
        else:
            print("  - PDF 生成失败，已保留 HTML 报告")

    print(f"  ✓ HTML：{os.path.basename(out_html)}")
    print(f"\n完成！报告已生成（成本约 ¥{costs}）。")

if __name__ == "__main__":
    main()
