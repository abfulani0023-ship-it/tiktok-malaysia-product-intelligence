#!/usr/bin/env python3
import csv
import html
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RANKED_PATH = ROOT / "outputs" / "ranked_products.csv"
SCRIPT_PATH = ROOT / "outputs" / "tiktok_scripts.csv"
WATCHLIST_PATH = ROOT / "config" / "daily_watchlist.json"
OUTPUT_PATH = ROOT / "outputs" / "daily_crossborder_dashboard.html"

DIMENSIONS = [
    ("score_amazon_trend", "趋势 Trend", 20, "#2563eb"),
    ("score_pain_point_clarity", "痛点 Pain", 15, "#0f766e"),
    ("score_tiktok_visual_potential", "视频 Visual", 15, "#b45309"),
    ("score_malaysia_market_fit", "马来 Fit", 15, "#7c3aed"),
    ("score_impulse_price_fit", "价格 Price", 10, "#db2777"),
    ("score_logistics_risk", "物流 Logistics", 10, "#0891b2"),
    ("score_competition_risk", "竞争 Competition", 10, "#475569"),
    ("score_compliance_risk", "合规 Safety", 5, "#16a34a"),
]

POSITIVE_TAGS = {
    "easy": "易用",
    "fast": "快",
    "compact": "小巧",
    "portable": "便携",
    "cheap": "便宜",
    "value": "性价比",
    "clean": "清洁效果",
    "clear": "清晰",
    "stable": "稳定",
    "space": "省空间",
    "saving": "省空间",
    "protect": "保护",
    "rechargeable": "可充电",
    "foldable": "可折叠",
    "plug and play": "即插即用",
}

NEGATIVE_TAGS = {
    "break": "容易坏",
    "breaks": "容易坏",
    "slow": "速度慢",
    "hot": "发热",
    "heat": "发热",
    "sticky": "粘手/胶不牢",
    "fall": "容易掉",
    "falls": "容易掉",
    "unstable": "不稳定",
    "incompatible": "兼容性差",
    "hard": "使用门槛",
    "dust": "进灰",
    "messy": "杂乱",
    "noisy": "噪音",
    "expensive": "维修贵",
    "short": "寿命短",
}


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_watchlist():
    if WATCHLIST_PATH.exists():
        return json.loads(WATCHLIST_PATH.read_text(encoding="utf-8"))
    return {"amazon_marketplaces": [{"code": "US"}, {"code": "SG"}, {"code": "UK"}]}


def esc(value):
    return html.escape(str(value or ""))


def fnum(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def fmt_int(value):
    return f"{int(fnum(value)):,}"


def tags_from_text(text, mapping, fallback):
    text = (text or "").lower()
    tags = [label for key, label in mapping.items() if key in text]
    return list(dict.fromkeys(tags))[:5] or fallback


def positive_tags(row):
    text = " ".join([row.get("bullet_points", ""), row.get("title", "")])
    return tags_from_text(text, POSITIVE_TAGS, ["低价", "轻小件", "使用场景清晰"])


def negative_tags(row):
    text = " ".join([row.get("top_review_pain_points", ""), row.get("title", "")])
    return tags_from_text(text, NEGATIVE_TAGS, ["同质化", "供应链质量需验证"])


def opportunity(row):
    neg = negative_tags(row)
    title = (row.get("title") or "").lower()
    if "charger" in title or "wireless" in title:
        return "机会在于做低发热、稳定充电、认证清楚的版本；视频里要直接测温和充电速度。"
    if "hub" in title or "adapter" in title:
        return "机会在于强调稳定连接、不掉线、办公/学生真实场景，不要只讲接口数量。"
    if "cleaning" in title or "gel" in title:
        return "机会在于找不粘手、无残留、密封更好的版本，用差评担忧做信任视频。"
    if "ring" in title or "mount" in title or "stand" in title:
        return "机会在于做强磁、强支撑、兼容手机壳版本，用甩动/支撑测试建立信任。"
    if "cable" in title or "clips" in title:
        return "机会在于用低价多件装解决线材乱和断裂，用before/after做强视觉。"
    if "microphone" in title:
        return "机会在于声音before/after，对比手机原声，面向TikTok创作者和直播卖家。"
    return f"机会来自差评痛点：{'、'.join(neg)}。找能解决这些痛点的供应链版本。"


def zh_explain(row):
    title = (row.get("title") or "").lower()
    if "cleaning" in title or "dust" in title:
        return "键盘、车缝、电脑缝隙清洁工具，适合做强 before/after 演示。"
    if "hub" in title or "adapter" in title or "card reader" in title:
        return "电脑/手机接口扩展类小配件，解决办公、学生、直播设备连接问题。"
    if "ring" in title or "stand" in title or "mount" in title:
        return "手机支架/固定类配件，适合通勤、办公桌、车内导航场景。"
    if "cable" in title or "charger" in title or "wireless" in title:
        return "充电与线材类刚需小件，价格低、复购高，但要重点验证发热和耐用。"
    if "microphone" in title:
        return "短视频/直播收音配件，适合用声音对比证明价值。"
    return "3C数码轻小件，优先看能否用一个镜头讲清楚痛点和效果。"


def rise_reason(row):
    return (
        f"评论增长 {fnum(row.get('review_growth_30d')):.0f}%、"
        f"月销估算 {fmt_int(row.get('monthly_sales_est'))}、"
        f"BSR {fmt_int(row.get('bsr_rank'))}，说明 Amazon 侧已有需求信号。"
    )


def risk_warning(row):
    warnings = []
    if fnum(row.get("score_competition_risk")) <= 2:
        warnings.append("竞争偏高")
    if fnum(row.get("score_logistics_risk")) <= 6:
        warnings.append("物流/售后需验证")
    if fnum(row.get("score_compliance_risk")) <= 3:
        warnings.append("合规风险需检查")
    if "charger" in (row.get("title") or "").lower():
        warnings.append("充电器要看认证和发热")
    return "、".join(warnings) if warnings else "风险较低，重点验证供应链质量。"


def category_rows(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row.get("bsr_category") or row.get("category") or "Other"].append(row)
    out = []
    for category, items in grouped.items():
        out.append({
            "category": category,
            "count": len(items),
            "avg_score": sum(fnum(item.get("total_score")) for item in items) / len(items),
            "avg_growth": sum(fnum(item.get("review_growth_30d")) for item in items) / len(items),
            "reviews": sum(fnum(item.get("review_count")) for item in items),
            "top_product": max(items, key=lambda item: fnum(item.get("total_score"))).get("title"),
        })
    return sorted(out, key=lambda item: (item["avg_growth"], item["avg_score"]), reverse=True)


def horizontal_bar(label, value, max_value, color="#2563eb", suffix=""):
    width = 0 if max_value <= 0 else max(2, min(100, value / max_value * 100))
    return f"""
    <div class="hbar-row">
      <div class="hbar-label">{esc(label)}</div>
      <div class="hbar-track"><span style="width:{width:.1f}%; background:{color}"></span></div>
      <div class="hbar-value">{value:.1f}{suffix}</div>
    </div>
    """


def category_chart(rows):
    cats = category_rows(rows)[:8]
    max_growth = max([item["avg_growth"] for item in cats] or [1])
    return "\n".join(horizontal_bar(item["category"], item["avg_growth"], max_growth, "#0f766e", "%") for item in cats)


def product_rank_chart(rows):
    top = rows[:10]
    max_score = max([fnum(row.get("total_score")) for row in top] or [1])
    return "\n".join(
        horizontal_bar(row.get("title", "")[:34], fnum(row.get("total_score")), max_score, "#2563eb")
        for row in top
    )


def top10_board(rows, title, subtitle):
    cards = []
    for index, row in enumerate(rows[:10], start=1):
        risk = risk_warning(row)
        cards.append(f"""
        <div class="top10-item">
          <div class="top10-rank">{index}</div>
          <div class="top10-main">
            <b>{esc(row.get("title"))}</b>
            <span>{esc(zh_explain(row))}</span>
            <small>{esc(rise_reason(row))}</small>
          </div>
          <div class="top10-score">
            <strong>{fnum(row.get("total_score")):.1f}</strong>
            <span>{esc(risk)}</span>
          </div>
        </div>
        """)
    return f"""
    <section class="panel top10-panel">
      <div class="section-head">
        <div>
          <h2>{esc(title)}</h2>
          <p>{esc(subtitle)}</p>
        </div>
      </div>
      {''.join(cards)}
    </section>
    """


def marketplace_mix(rows):
    counts = Counter(row.get("marketplace") or "Unknown" for row in rows)
    total = sum(counts.values()) or 1
    chunks = []
    for market, count in counts.items():
        width = count / total * 100
        chunks.append(f'<span style="width:{width:.1f}%">{esc(market)}</span>')
    return "".join(chunks)


def evidence_table(rows):
    table_rows = []
    for row in rows[:12]:
        table_rows.append(f"""
        <tr>
          <td><b>{esc(row.get("title"))}</b><small>{esc(row.get("marketplace"))} · {esc(row.get("bsr_category"))}</small></td>
          <td>RM{fnum(row.get("price_myr_est")):.0f}</td>
          <td>{fnum(row.get("rating")):.1f}</td>
          <td>{fmt_int(row.get("review_count"))}</td>
          <td>{fnum(row.get("review_growth_30d")):.0f}%</td>
          <td>{fmt_int(row.get("monthly_sales_est"))}</td>
          <td>{fnum(row.get("total_score")):.1f}</td>
        </tr>
        """)
    return "\n".join(table_rows)


def score_stack(row):
    parts = []
    for key, label, max_score, color in DIMENSIONS:
        value = fnum(row.get(key))
        width = value
        parts.append(f'<span title="{esc(label)} {value:.1f}" style="width:{width:.2f}%; background:{color}"></span>')
    return "".join(parts)


def tag_spans(tags, cls):
    return "".join(f'<span class="{cls}">{esc(tag)}</span>' for tag in tags)


def product_image(row):
    image_url = (row.get("image_url") or "").strip()
    title = row.get("title") or "Product image"
    if image_url:
        return f'<img src="{esc(image_url)}" alt="{esc(title)}" loading="lazy">'
    return """
    <div class="image-placeholder">
      <b>IMAGE</b>
      <span>待采集商品图<br>Waiting for image_url</span>
    </div>
    """


def product_cards(rows, scripts):
    by_product = defaultdict(list)
    for script in scripts:
        by_product[script.get("product_id")].append(script)

    cards = []
    for index, row in enumerate(rows[:10], start=1):
        product_id = row.get("product_id")
        hooks = by_product.get(product_id, [])[:2]
        hook_items = "".join(f"<li>{esc(item.get('hook'))}</li>" for item in hooks)
        pos = positive_tags(row)
        neg = negative_tags(row)
        cards.append(f"""
        <article class="evidence-card">
          <div class="product-layout">
            <div class="product-image">
              {product_image(row)}
            </div>
            <div>
          <div class="card-head">
          <div>
              <div class="rank-pill">#{index} · {esc(row.get("decision"))}</div>
              <h3>{esc(row.get("title"))}</h3>
              <p>{esc(row.get("marketplace"))} · {esc(row.get("category"))} · {esc(row.get("bsr_category"))}</p>
              <p class="zh-explain">{esc(zh_explain(row))}</p>
            </div>
            <div class="big-score">{fnum(row.get("total_score")):.1f}<span>/100</span></div>
          </div>

          <div class="data-strip">
            <div><b>RM{fnum(row.get("price_myr_est")):.0f}</b><span>估算售价 Est. Price</span></div>
            <div><b>{fnum(row.get("rating")):.1f}</b><span>用户评分 Rating</span></div>
            <div><b>{fmt_int(row.get("review_count"))}</b><span>评论数 Reviews</span></div>
            <div><b>{fnum(row.get("review_growth_30d")):.0f}%</b><span>评论增长 Growth</span></div>
            <div><b>{fmt_int(row.get("monthly_sales_est"))}</b><span>月销估算 Sales Est.</span></div>
          </div>

          <div class="stack">{score_stack(row)}</div>
          <div class="legend-mini">
            <span>趋势</span><span>痛点</span><span>视频</span><span>马来</span><span>价格</span><span>物流</span><span>竞争</span><span>合规</span>
          </div>

          <div class="reason-row">
            <section><h4>上涨原因 Rise Reason</h4><p>{esc(rise_reason(row))}</p></section>
            <section><h4>风险预警 Risk Warning</h4><p>{esc(risk_warning(row))}</p></section>
          </div>

          <div class="insight-grid">
            <section>
              <h4>正向评论标签 Positive Tags</h4>
              <div class="tags">{tag_spans(pos, "tag-pos")}</div>
            </section>
            <section>
              <h4>负向评论标签 Negative Tags</h4>
              <div class="tags">{tag_spans(neg, "tag-neg")}</div>
            </section>
          </div>

          <div class="comment-box">
            <h4>差评/痛点摘要 Review Pain Points</h4>
            <p>{esc(row.get("top_review_pain_points"))}</p>
          </div>
          <div class="opportunity">
            <h4>市场机会判断 Market Opportunity</h4>
            <p>{esc(opportunity(row))}</p>
          </div>
          <div class="hooks">
            <h4>今日可测 Hook / Test Hooks</h4>
            <ol>{hook_items}</ol>
          </div>
          <a href="{esc(row.get("product_url"))}">Amazon 搜索参考 / Search Reference</a>
            </div>
          </div>
        </article>
        """)
    return "\n".join(cards)


def main():
    rows = read_csv(RANKED_PATH)
    scripts = read_csv(SCRIPT_PATH)
    watchlist = read_watchlist()
    markets = " / ".join(item.get("code", "") for item in watchlist.get("amazon_marketplaces", []))
    total = len(rows)
    scale = sum(1 for row in rows if row.get("decision") == "scale-test")
    avg_score = sum(fnum(row.get("total_score")) for row in rows) / max(total, 1)
    total_reviews = sum(fnum(row.get("review_count")) for row in rows)
    avg_growth = sum(fnum(row.get("review_growth_30d")) for row in rows) / max(total, 1)
    top = rows[0] if rows else {}
    best_video = max(rows[:10], key=lambda row: fnum(row.get("score_tiktok_visual_potential")), default={})
    highest_risk = min(rows[:10], key=lambda row: fnum(row.get("score_compliance_risk")) + fnum(row.get("score_logistics_risk")) + fnum(row.get("score_competition_risk")), default={})

    html_doc = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>每日跨境选品数据看板 Daily Product Intelligence</title>
  <style>
    :root {{
      --ink:#152033; --muted:#64748b; --line:#d8e0ea; --soft:#f4f7fb; --card:#fff;
      --blue:#2563eb; --teal:#0f766e; --gold:#b45309; --red:#be123c;
    }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:#e6ebf1; color:var(--ink); font-family:Arial,"PingFang SC","Microsoft YaHei",sans-serif; line-height:1.45; }}
    .page {{ width:min(1180px, calc(100% - 28px)); margin:18px auto; }}
    .hero {{ background:#fff; border:1px solid var(--line); border-radius:8px; padding:26px; margin-bottom:14px; }}
    .hero h1 {{ margin:0 0 8px; font-size:30px; letter-spacing:0; }}
    .hero p {{ margin:0; color:var(--muted); max-width:900px; }}
    .hero-callouts {{ display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin-top:16px; }}
    .hero-callout {{ border:1px solid var(--line); border-radius:8px; background:#f8fafc; padding:12px; }}
    .hero-callout span {{ display:block; color:var(--muted); font-size:12px; margin-bottom:4px; }}
    .hero-callout b {{ font-size:16px; line-height:1.25; }}
    .meta {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:16px; }}
    .meta span,.tag-pos,.tag-neg {{ border:1px solid var(--line); border-radius:999px; padding:5px 10px; font-size:12px; background:#fbfdff; }}
    .kpis {{ display:grid; grid-template-columns:repeat(5,1fr); gap:10px; margin-bottom:14px; }}
    .kpi {{ background:#fff; border:1px solid var(--line); border-radius:8px; padding:16px; }}
    .kpi span {{ color:var(--muted); font-size:12px; }}
    .kpi b {{ display:block; font-size:25px; margin-top:4px; }}
    .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-bottom:14px; }}
    .panel,.evidence-card {{ background:#fff; border:1px solid var(--line); border-radius:8px; padding:18px; }}
    .section-head {{ display:flex; justify-content:space-between; gap:12px; align-items:flex-start; margin-bottom:12px; }}
    .section-head p {{ margin:4px 0 0; color:var(--muted); }}
    h2 {{ margin:0 0 12px; font-size:20px; letter-spacing:0; }}
    h3 {{ margin:0 0 5px; font-size:19px; letter-spacing:0; }}
    h4 {{ margin:0 0 7px; font-size:13px; letter-spacing:0; }}
    .hbar-row {{ display:grid; grid-template-columns:170px 1fr 56px; gap:9px; align-items:center; margin:9px 0; font-size:13px; }}
    .hbar-label {{ overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
    .hbar-track {{ height:10px; background:#edf2f7; border-radius:999px; overflow:hidden; }}
    .hbar-track span {{ display:block; height:100%; border-radius:999px; }}
    .hbar-value {{ text-align:right; font-weight:700; }}
    .market-stack {{ display:flex; height:34px; overflow:hidden; border-radius:6px; border:1px solid var(--line); margin-top:10px; }}
    .market-stack span {{ display:grid; place-items:center; background:#dbeafe; color:#1d4ed8; font-size:12px; font-weight:700; border-right:1px solid #fff; }}
    table {{ width:100%; border-collapse:collapse; font-size:13px; background:#fff; }}
    th,td {{ padding:9px 8px; border-bottom:1px solid var(--line); vertical-align:top; }}
    th {{ color:var(--muted); font-size:12px; text-align:left; }}
    td small {{ display:block; color:var(--muted); margin-top:3px; }}
    .evidence-card {{ margin-bottom:14px; break-inside:avoid; }}
    .top10-panel {{ margin-bottom:14px; }}
    .top10-item {{ display:grid; grid-template-columns:34px 1fr 150px; gap:12px; align-items:start; border-top:1px solid var(--line); padding:12px 0; }}
    .top10-item:first-of-type {{ border-top:0; }}
    .top10-rank {{ width:28px; height:28px; display:grid; place-items:center; border-radius:999px; background:#eff6ff; color:#1d4ed8; font-weight:800; }}
    .top10-main b {{ display:block; font-size:15px; line-height:1.3; }}
    .top10-main span {{ display:block; color:#334155; font-size:13px; margin-top:4px; }}
    .top10-main small {{ display:block; color:var(--muted); font-size:12px; margin-top:4px; }}
    .top10-score {{ text-align:right; }}
    .top10-score strong {{ display:block; color:#0f766e; font-size:22px; }}
    .top10-score span {{ display:block; color:#be123c; font-size:12px; margin-top:4px; }}
    .card-head {{ display:grid; grid-template-columns:1fr auto; gap:12px; align-items:start; }}
    .card-head p {{ margin:0; color:var(--muted); font-size:13px; }}
    .card-head .zh-explain {{ color:#334155; margin-top:6px; }}
    .rank-pill {{ display:inline-block; background:#ecfdf5; color:#0f766e; border:1px solid #99f6e4; border-radius:999px; padding:3px 8px; font-size:12px; margin-bottom:8px; }}
    .big-score {{ text-align:right; font-size:36px; font-weight:800; color:#0f766e; }}
    .big-score span {{ display:block; color:var(--muted); font-size:12px; font-weight:400; }}
    .data-strip {{ display:grid; grid-template-columns:repeat(5,1fr); gap:8px; margin:15px 0; }}
    .data-strip div {{ background:var(--soft); border:1px solid var(--line); border-radius:6px; padding:9px; }}
    .data-strip b {{ display:block; font-size:18px; }}
    .data-strip span {{ color:var(--muted); font-size:11px; }}
    .stack {{ display:flex; height:14px; border-radius:999px; overflow:hidden; background:#edf2f7; }}
    .stack span {{ display:block; height:100%; }}
    .legend-mini {{ display:grid; grid-template-columns:repeat(8,1fr); gap:4px; color:var(--muted); font-size:10px; margin-top:5px; }}
    .reason-row {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:12px; }}
    .reason-row section {{ border:1px solid var(--line); border-radius:6px; background:#fbfdff; padding:12px; }}
    .reason-row p {{ margin:0; font-size:13px; }}
    .insight-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:14px; }}
    .tags {{ display:flex; flex-wrap:wrap; gap:6px; }}
    .tag-pos {{ border-color:#99f6e4; color:#0f766e; background:#f0fdfa; }}
    .tag-neg {{ border-color:#fecdd3; color:#be123c; background:#fff1f2; }}
    .comment-box,.opportunity,.hooks {{ margin-top:12px; padding:12px; border:1px solid var(--line); border-radius:6px; background:#fbfdff; }}
    .comment-box p,.opportunity p {{ margin:0; }}
    .hooks ol {{ margin:0; padding-left:19px; }}
    a {{ color:var(--blue); text-decoration:none; font-weight:700; display:inline-block; margin-top:10px; }}
    .product-layout {{ display:grid; grid-template-columns:180px 1fr; gap:18px; align-items:start; }}
    .product-image {{
      width:180px;
      aspect-ratio:1 / 1;
      border:1px solid var(--line);
      border-radius:8px;
      background:#f8fafc;
      overflow:hidden;
      display:grid;
      place-items:center;
      position:sticky;
      top:12px;
    }}
    .product-image img {{
      width:100%;
      height:100%;
      object-fit:contain;
      background:#fff;
    }}
    .image-placeholder {{
      width:100%;
      height:100%;
      display:grid;
      place-items:center;
      align-content:center;
      gap:8px;
      color:#64748b;
      text-align:center;
      padding:16px;
    }}
    .image-placeholder b {{
      color:#2563eb;
      font-size:22px;
      letter-spacing:0;
    }}
    .image-placeholder span {{
      font-size:12px;
      line-height:1.4;
    }}
    @media (max-width:900px) {{ .kpis,.grid,.data-strip,.insight-grid,.product-layout,.hero-callouts,.reason-row {{ grid-template-columns:1fr; }} .hbar-row {{ grid-template-columns:1fr; }} .product-image {{ width:100%; max-width:260px; position:static; }} .top10-item {{ grid-template-columns:30px 1fr; }} .top10-score {{ grid-column:2; text-align:left; }} }}
    @page {{ size:A4; margin:12mm; }}
    @media print {{
      body {{ background:#fff; font-size:11px; }}
      .page {{ width:100%; margin:0; }}
      .hero,.panel,.evidence-card,.kpi {{ break-inside:avoid; box-shadow:none; }}
      * {{ -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <section class="hero">
      <h1>3C数码选品商业情报日报 / Product Intelligence Brief</h1>
      <p>围绕 Amazon {esc(markets)} 的热门/上升 3C 小件，把“可能在 Amazon 爆或即将爆”的商品转成 TikTok Malaysia 测试池。页面按手机阅读优化，结论优先，证据跟随。</p>
      <div class="meta">
        <span>目标 Target：TikTok Malaysia</span><span>站点 Source：Amazon {esc(markets)}</span><span>价格 Price：RM15-RM80</span><span>重点 Focus：3C数码轻小件</span>
      </div>
      <div class="hero-callouts">
        <div class="hero-callout"><span>今日Top1</span><b>{esc(top.get("title"))}</b></div>
        <div class="hero-callout"><span>最值得拍视频</span><b>{esc(best_video.get("title"))}</b></div>
        <div class="hero-callout"><span>重点风险预警</span><b>{esc(risk_warning(highest_risk))}</b></div>
      </div>
    </section>

    <section class="kpis">
      <div class="kpi"><span>候选商品 Candidates</span><b>{total}</b></div>
      <div class="kpi"><span>放量测试 Scale-test</span><b>{scale}</b></div>
      <div class="kpi"><span>平均评分 Avg Score</span><b>{avg_score:.1f}</b></div>
      <div class="kpi"><span>总评论样本 Reviews</span><b>{total_reviews/1000:.0f}k</b></div>
      <div class="kpi"><span>平均评论增长 Growth</span><b>{avg_growth:.1f}%</b></div>
    </section>

    <section class="grid">
      <div class="panel"><h2>上升品类雷达 / Rising Categories</h2>{category_chart(rows)}</div>
      <div class="panel"><h2>商品综合分排行 / Product Ranking</h2>{product_rank_chart(rows)}</div>
    </section>

    {top10_board(rows, "今日3C数码Top10 / Today Top10", "按爆品机会评分排序，优先看综合分、上涨原因、风险预警和视频可拍性。")}
    {top10_board(rows, "本周3C数码Top10 / Weekly Watchlist", "当前版本用最近样本生成周榜视图；接入7日历史后将自动改为真实周榜。")}

    <section class="grid">
      <div class="panel">
        <h2>站点覆盖 / Marketplace Coverage</h2>
        <p>日报默认盯 US / SG / UK。当前样例数据以 US 为主，接入 SG/UK 后这里会显示三站占比。</p>
        <div class="market-stack">{marketplace_mix(rows)}</div>
      </div>
      <div class="panel">
        <h2>今日第一判断 / Top Call</h2>
        <p>最高优先级：<b>{esc(top.get("title"))}</b>，综合分 {fnum(top.get("total_score")):.1f}。关键证据：评分 {fnum(top.get("rating")):.1f}、评论 {fmt_int(top.get("review_count"))}、评论增长 {fnum(top.get("review_growth_30d")):.0f}%、估算月销量 {fmt_int(top.get("monthly_sales_est"))}。</p>
      </div>
    </section>

    <section class="panel">
      <h2>推荐商品证据表 / Evidence Table</h2>
      <table>
        <thead><tr><th>商品 Product</th><th>价格 Price</th><th>评分 Rating</th><th>评论数 Reviews</th><th>评论增长 Growth</th><th>月销量估算 Sales Est.</th><th>综合分 Score</th></tr></thead>
        <tbody>{evidence_table(rows)}</tbody>
      </table>
    </section>

    {product_cards(rows, scripts)}
  </main>
</body>
</html>
"""
    OUTPUT_PATH.write_text(html_doc, encoding="utf-8")
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
