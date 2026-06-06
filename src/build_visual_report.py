#!/usr/bin/env python3
import csv
import html
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RANKED_PATH = ROOT / "outputs" / "ranked_products.csv"
SCRIPT_PATH = ROOT / "outputs" / "tiktok_scripts.csv"
OUTPUT_PATH = ROOT / "outputs" / "visual_product_report.html"
WATCHLIST_PATH = ROOT / "config" / "daily_watchlist.json"

DIMENSIONS = [
    ("score_amazon_trend", "Amazon趋势", 20, "热度、销量估算、评论增长、BSR、降价信号"),
    ("score_pain_point_clarity", "痛点清晰", 15, "评论痛点是否明确，能不能直接转成视频开头"),
    ("score_tiktok_visual_potential", "视频表现", 15, "能否做before/after、对比、演示、爽感镜头"),
    ("score_malaysia_market_fit", "马来适配", 15, "是否适合马来西亚天气、通勤、租房、办公和日常消费"),
    ("score_impulse_price_fit", "价格带", 10, "是否落在RM15-RM50/RM80附近的冲动消费区间"),
    ("score_logistics_risk", "物流售后", 10, "越高代表越轻小、低破损、低售后"),
    ("score_competition_risk", "竞争余量", 10, "越高代表竞争压力相对更小"),
    ("score_compliance_risk", "合规安全", 5, "越高代表越低侵权、低夸大功效、低平台风险"),
]

PALETTE = {
    "scale-test": "#0f766e",
    "test": "#2563eb",
    "watch": "#b45309",
    "skip": "#64748b",
}


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_watchlist():
    if WATCHLIST_PATH.exists():
        return json.loads(WATCHLIST_PATH.read_text(encoding="utf-8"))
    return {
        "target_market": "TikTok Malaysia",
        "amazon_marketplaces": [{"code": "US"}, {"code": "SG"}, {"code": "UK"}],
        "selection_hypothesis": "Amazon trending products deserve fast TikTok Malaysia validation.",
    }


def esc(value):
    return html.escape(str(value or ""))


def fnum(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def pct(value, max_value):
    return max(0, min(100, fnum(value) / max_value * 100))


def short_title(title):
    title = title or ""
    replacements = {
        "Keyboard Cleaning Gel and Electronics Dust Cleaner Kit": "电子清洁凝胶",
        "4-Port USB 3.0 Hub for Laptop Desk Setup": "4口USB Hub",
        "Magnetic Phone Ring Holder Stand": "磁吸手机环支架",
        "Silicone Cable Clips Desk Organizer 6-Pack": "桌面理线夹",
        "USB TV LED Backlight Strip Kit": "电视LED氛围灯",
        "Cable Protector Spiral Saver 20-Pack": "充电线保护套",
        "Wired USB-C Lavalier Microphone for Phone": "USB-C领夹麦",
        "Anti-Dust Charging Port Plug Set for USB-C Phone": "USB-C防尘塞",
        "Adjustable Foldable Phone Stand for Desk": "折叠手机支架",
        "USB-C to USB-A Adapter 3-Pack": "USB-C转接头",
    }
    return replacements.get(title, title[:28])


def category_icon(category):
    category = (category or "").lower()
    if "car" in category:
        return "CAR"
    if "audio" in category:
        return "MIC"
    if "lighting" in category:
        return "LED"
    if "phone" in category:
        return "PHN"
    if "smart" in category:
        return "IOT"
    return "USB"


def why_selected(row):
    reasons = []
    if fnum(row.get("score_tiktok_visual_potential")) >= 13:
        reasons.append("视频表现强，适合做对比、演示或before/after")
    if fnum(row.get("score_malaysia_market_fit")) >= 13:
        reasons.append("马来西亚日常场景贴合度高")
    if fnum(row.get("score_impulse_price_fit")) >= 9:
        reasons.append("价格处在低决策门槛区间")
    if fnum(row.get("score_amazon_trend")) >= 14:
        reasons.append("Amazon热度和上升信号较强")
    if not reasons:
        reasons.append("综合分进入观察区，可小量验证")
    return reasons[:4]


def risk_notes(row):
    title = (row.get("title") or "").lower()
    category = (row.get("category") or "").lower()
    notes = []
    if fnum(row.get("score_competition_risk")) <= 2:
        notes.append("竞争较强，需要靠场景和脚本差异化")
    if fnum(row.get("score_logistics_risk")) <= 6:
        notes.append("要先验证质量、发热、胶粘性或兼容性")
    if "charger" in title or "wireless" in title or "smart plug" in title:
        notes.append("涉及用电体验，供应链和安全认证要先确认")
    if "screen protector" in title:
        notes.append("型号碎片化明显，库存管理难度高")
    if "audio" in category or "microphone" in title:
        notes.append("不同手机兼容性要实测，避免夸大降噪")
    if not notes:
        notes.append("主要风险是同质化，需要用本地场景提高转化")
    return notes[:3]


def top_hooks(scripts, product_id):
    hooks = [row.get("hook", "") for row in scripts if row.get("product_id") == product_id]
    return hooks[:3]


def dimension_bar(row):
    parts = []
    for key, label, max_score, _ in DIMENSIONS:
        value = fnum(row.get(key))
        width = pct(value, max_score)
        parts.append(
            f"""
            <div class="metric">
              <div class="metric-head"><span>{esc(label)}</span><b>{value:.1f}/{max_score}</b></div>
              <div class="bar"><span style="width:{width:.1f}%"></span></div>
            </div>
            """
        )
    return "\n".join(parts)


def leaderboard(rows):
    top = rows[:10]
    max_score = max(fnum(row.get("total_score")) for row in top) if top else 100
    items = []
    for index, row in enumerate(top, start=1):
        score = fnum(row.get("total_score"))
        width = score / max_score * 100
        color = PALETTE.get(row.get("decision"), "#334155")
        items.append(
            f"""
            <div class="rank-row">
              <div class="rank-num">{index}</div>
              <div class="rank-main">
                <div class="rank-label"><b>{esc(short_title(row.get("title")))}</b><span>RM{fnum(row.get("price_myr_est")):.0f}</span></div>
                <div class="rank-bar"><span style="width:{width:.1f}%; background:{color}"></span></div>
              </div>
              <div class="rank-score">{score:.1f}</div>
            </div>
            """
        )
    return "\n".join(items)


def cards(rows, scripts):
    rendered = []
    for index, row in enumerate(rows[:12], start=1):
        decision = row.get("decision") or "watch"
        decision_color = PALETTE.get(decision, "#334155")
        reasons = "".join(f"<li>{esc(item)}</li>" for item in why_selected(row))
        risks = "".join(f"<li>{esc(item)}</li>" for item in risk_notes(row))
        hooks = "".join(f"<li>{esc(item)}</li>" for item in top_hooks(scripts, row.get("product_id")))
        product_url = row.get("product_url") or "#"
        rendered.append(
            f"""
            <article class="product-card">
              <div class="product-top">
                <div class="thumb">
                  <span>{esc(category_icon(row.get("category")))}</span>
                </div>
                <div>
                  <div class="eyebrow">#{index} · {esc(row.get("product_id"))} · {esc(row.get("category"))}</div>
                  <h2>{esc(row.get("title"))}</h2>
                  <div class="chips">
                    <span style="border-color:{decision_color}; color:{decision_color}">{esc(decision)}</span>
                    <span>RM{fnum(row.get("price_myr_est")):.0f}</span>
                    <span>{fnum(row.get("review_growth_30d")):.0f}% review growth</span>
                    <span>{fnum(row.get("monthly_sales_est")):.0f} est. monthly sales</span>
                  </div>
                </div>
                <div class="score" style="color:{decision_color}">
                  <b>{fnum(row.get("total_score")):.1f}</b>
                  <span>/100</span>
                </div>
              </div>
              <div class="card-grid">
                <section>
                  <h3>为什么选中</h3>
                  <ul>{reasons}</ul>
                </section>
                <section>
                  <h3>主要风险</h3>
                  <ul>{risks}</ul>
                </section>
              </div>
              <div class="pain">
                <b>评论痛点</b>
                <p>{esc(row.get("top_review_pain_points"))}</p>
              </div>
              <div class="score-grid">
                {dimension_bar(row)}
              </div>
              <div class="hooks">
                <h3>可直接测试的Hook</h3>
                <ol>{hooks}</ol>
              </div>
              <a class="link" href="{esc(product_url)}">打开 Amazon 搜索参考</a>
            </article>
            """
        )
    return "\n".join(rendered)


def dimension_table():
    rows = []
    for _, label, max_score, desc in DIMENSIONS:
        rows.append(
            f"""
            <tr>
              <td>{esc(label)}</td>
              <td>{max_score}</td>
              <td>{esc(desc)}</td>
            </tr>
            """
        )
    return "\n".join(rows)


def main():
    rows = read_csv(RANKED_PATH)
    scripts = read_csv(SCRIPT_PATH)
    watchlist = read_watchlist()
    total = len(rows)
    scale = sum(1 for row in rows if row.get("decision") == "scale-test")
    test = sum(1 for row in rows if row.get("decision") == "test")
    avg = sum(fnum(row.get("total_score")) for row in rows) / max(total, 1)
    marketplace_codes = " / ".join(item.get("code", "") for item in watchlist.get("amazon_marketplaces", []))
    hypothesis = watchlist.get("selection_hypothesis", "")

    html_doc = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>RM15-RM50 3C数码选品图文看板</title>
  <style>
    :root {{
      --ink: #172033;
      --muted: #64748b;
      --line: #d9e1ea;
      --soft: #f5f7fa;
      --blue: #2563eb;
      --teal: #0f766e;
      --gold: #b45309;
      --card: #ffffff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Arial, "PingFang SC", "Microsoft YaHei", sans-serif;
      color: var(--ink);
      background: #dfe5ec;
      line-height: 1.5;
    }}
    .page {{
      width: min(210mm, calc(100% - 28px));
      min-height: 297mm;
      margin: 18px auto;
      padding: 16mm;
      background: #ffffff;
      border: 1px solid #cbd5e1;
      box-shadow: 0 18px 42px rgba(15, 23, 42, 0.14);
    }}
    header {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 28px;
      margin-bottom: 18px;
    }}
    h1 {{ margin: 0 0 8px; font-size: 30px; letter-spacing: 0; }}
    h2 {{ margin: 4px 0 10px; font-size: 20px; letter-spacing: 0; }}
    h3 {{ margin: 0 0 8px; font-size: 14px; letter-spacing: 0; }}
    p {{ margin: 0; }}
    .report-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 18px;
    }}
    .report-meta span {{
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 5px 10px;
      color: #334155;
      background: #fbfdff;
      font-size: 12px;
    }}
    .subtitle {{ color: var(--muted); max-width: 860px; }}
    .kpis {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin: 14px 0; }}
    .kpi {{ background: var(--card); border: 1px solid var(--line); border-radius: 8px; padding: 16px; }}
    .kpi span {{ color: var(--muted); font-size: 13px; }}
    .kpi b {{ display: block; font-size: 28px; margin-top: 4px; }}
    .panel {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 22px;
      margin-bottom: 18px;
    }}
    .two-col {{ display: grid; grid-template-columns: 1fr; gap: 12px; align-items: start; }}
    .rank-row {{ display: grid; grid-template-columns: 32px 1fr 58px; gap: 10px; align-items: center; margin: 12px 0; }}
    .rank-num {{ color: var(--muted); font-weight: 700; text-align: right; }}
    .rank-label {{ display: flex; justify-content: space-between; gap: 12px; font-size: 14px; }}
    .rank-label span {{ color: var(--muted); white-space: nowrap; }}
    .rank-bar, .bar {{ height: 9px; background: #e8edf3; border-radius: 99px; overflow: hidden; margin-top: 5px; }}
    .rank-bar span, .bar span {{ display: block; height: 100%; background: var(--blue); border-radius: inherit; }}
    .rank-score {{ font-weight: 700; text-align: right; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ padding: 10px 8px; border-bottom: 1px solid var(--line); vertical-align: top; }}
    th {{ text-align: left; color: var(--muted); font-size: 12px; }}
    .product-card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 22px;
      margin-bottom: 18px;
    }}
    .product-top {{ display: grid; grid-template-columns: 76px 1fr auto; gap: 16px; align-items: start; }}
    .thumb {{
      width: 76px;
      height: 76px;
      border-radius: 8px;
      background: linear-gradient(135deg, #dce8f5, #ffffff);
      border: 1px solid var(--line);
      display: grid;
      place-items: center;
      color: #1d4ed8;
      font-weight: 800;
      letter-spacing: 0;
    }}
    .eyebrow {{ color: var(--muted); font-size: 12px; }}
    .chips {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }}
    .chips span {{
      display: inline-flex;
      align-items: center;
      min-height: 28px;
      padding: 4px 9px;
      border: 1px solid var(--line);
      border-radius: 999px;
      font-size: 12px;
      color: #334155;
      background: #fbfdff;
    }}
    .score {{ text-align: right; min-width: 86px; }}
    .score b {{ display: block; font-size: 34px; line-height: 1; }}
    .score span {{ color: var(--muted); }}
    .card-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-top: 18px; }}
    ul, ol {{ margin: 0; padding-left: 20px; }}
    li {{ margin: 5px 0; }}
    .pain {{ background: var(--soft); border: 1px solid var(--line); border-radius: 8px; padding: 12px; margin: 16px 0; }}
    .pain b {{ display: block; margin-bottom: 4px; }}
    .score-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }}
    .metric {{ min-width: 0; }}
    .metric-head {{ display: flex; justify-content: space-between; gap: 8px; font-size: 12px; color: var(--muted); }}
    .metric-head b {{ color: var(--ink); white-space: nowrap; }}
    .hooks {{ margin-top: 16px; }}
    .link {{ display: inline-block; margin-top: 12px; color: var(--blue); text-decoration: none; font-weight: 700; }}
    .note {{ color: var(--muted); font-size: 13px; margin-top: 8px; }}
    .print-footer {{ display: none; }}
    @media (max-width: 860px) {{
      .page {{ width: calc(100% - 20px); padding: 14px; margin: 10px auto; }}
      .kpis, .two-col, .card-grid, .score-grid {{ grid-template-columns: 1fr; }}
      .product-top {{ grid-template-columns: 60px 1fr; }}
      .thumb {{ width: 60px; height: 60px; }}
      .score {{ grid-column: 1 / -1; text-align: left; }}
      h1 {{ font-size: 24px; }}
    }}
    @page {{
      size: A4;
      margin: 14mm 12mm;
    }}
    @media print {{
      * {{
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
      }}
      body {{
        background: #ffffff;
        font-size: 11px;
      }}
      .page {{
        max-width: none;
        width: 100%;
        min-height: auto;
        padding: 0;
        margin: 0;
        border: 0;
        box-shadow: none;
      }}
      header {{
        padding: 18px;
        margin-bottom: 10px;
      }}
      h1 {{ font-size: 24px; }}
      h2 {{ font-size: 16px; }}
      h3 {{ font-size: 12px; }}
      .kpis {{
        grid-template-columns: repeat(4, 1fr);
        gap: 8px;
        margin: 10px 0;
      }}
      .kpi {{
        padding: 10px;
      }}
      .kpi b {{
        font-size: 22px;
      }}
      .two-col {{
        grid-template-columns: 1fr 1fr;
        gap: 10px;
      }}
      .panel, .product-card {{
        border-radius: 6px;
        padding: 14px;
        margin-bottom: 10px;
        break-inside: avoid;
        page-break-inside: avoid;
      }}
      .product-card {{
        break-inside: avoid-page;
      }}
      .product-top {{
        grid-template-columns: 56px 1fr 68px;
        gap: 10px;
      }}
      .thumb {{
        width: 56px;
        height: 56px;
      }}
      .score b {{
        font-size: 24px;
      }}
      .chips {{
        gap: 5px;
      }}
      .chips span {{
        min-height: 22px;
        padding: 2px 7px;
        font-size: 10px;
      }}
      .score-grid {{
        grid-template-columns: repeat(4, 1fr);
        gap: 8px;
      }}
      .card-grid {{
        grid-template-columns: 1fr 1fr;
        gap: 10px;
      }}
      .rank-row {{
        margin: 8px 0;
      }}
      th, td {{
        padding: 6px 5px;
      }}
      .link {{
        color: #334155;
        font-weight: 400;
      }}
      .print-footer {{
        display: block;
        color: var(--muted);
        font-size: 10px;
        margin-top: 12px;
      }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <header>
      <h1>RM15-RM50 3C数码选品图文看板</h1>
      <p class="subtitle">面向 TikTok 马来西亚出单，基于 Amazon {esc(marketplace_codes)} 热门/上升趋势信号、评论痛点、视频表现力、价格带、物流售后和合规风险做综合评分。数据为公开趋势研究与手工候选品整理，后续可替换为实时抓取数据。</p>
      <div class="report-meta">
        <span>目标市场：TikTok Malaysia</span>
        <span>监控站点：Amazon {esc(marketplace_codes)}</span>
        <span>价格带：RM15-RM50</span>
        <span>类目：3C数码轻小件</span>
        <span>输出：选品评分 + 脚本Hook</span>
      </div>
    </header>

    <section class="kpis">
      <div class="kpi"><span>候选商品</span><b>{total}</b></div>
      <div class="kpi"><span>建议放量测试</span><b>{scale}</b></div>
      <div class="kpi"><span>建议小批量测试</span><b>{test}</b></div>
      <div class="kpi"><span>平均综合分</span><b>{avg:.1f}</b></div>
    </section>

    <section class="two-col">
      <div class="panel">
        <h2>Top 10 综合排行</h2>
        {leaderboard(rows)}
        <p class="note">分数越高，代表越适合先用 TikTok 马来西亚短视频测试。不是越高越一定爆，而是更值得优先花素材和账号流量。</p>
      </div>
      <div class="panel">
        <h2>评分维度</h2>
        <table>
          <thead><tr><th>维度</th><th>权重</th><th>判断依据</th></tr></thead>
          <tbody>{dimension_table()}</tbody>
        </table>
      </div>
    </section>

    <section class="panel">
      <h2>为什么最后选这些品</h2>
      <p>本轮选品按这个假设执行：{esc(hypothesis)} 但进入测试池前还要看价格、轻小件属性、视频表现力、评论痛点、马来西亚场景和风险。比如清洁凝胶、USB Hub、理线夹、电视氛围灯、领夹麦，都能在 3 秒内让用户看到问题和结果，这比单纯讲参数更适合 TikTok Shop 转化。</p>
    </section>

    {cards(rows, scripts)}
    <p class="print-footer">Generated from local product intelligence pipeline. Use this report for first-round testing decisions, not as a guarantee of sales performance.</p>
  </main>
</body>
</html>
"""
    OUTPUT_PATH.write_text(html_doc, encoding="utf-8")
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
