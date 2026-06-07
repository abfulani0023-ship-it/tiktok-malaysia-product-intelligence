#!/usr/bin/env python3
import csv
import html
import mimetypes
import os
import smtplib
from collections import defaultdict
from datetime import date
from email.message import EmailMessage
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs"
RANKED_PATH = OUTPUT_DIR / "ranked_products.csv"
SCRIPT_PATH = OUTPUT_DIR / "tiktok_scripts.csv"


POSITIVE_TAGS = {
    "plug and play": "即插即用",
    "compact": "小巧",
    "portable": "便携",
    "cheap": "低价",
    "value": "性价比",
    "stable": "稳定",
    "protect": "保护",
    "clean": "清洁效果",
    "foldable": "可折叠",
    "rechargeable": "可充电",
}

NEGATIVE_TAGS = {
    "break": "容易坏",
    "slow": "速度慢",
    "hot": "发热",
    "sticky": "粘性/残留",
    "fall": "容易掉",
    "unstable": "不稳定",
    "incompatible": "兼容性差",
    "hard": "使用门槛",
    "dust": "进灰",
    "messy": "杂乱",
    "noisy": "噪音",
}


def env(name, default=None):
    value = os.environ.get(name, default)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def read_csv(path, limit=None):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return rows[:limit] if limit else rows


def fnum(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def fmt_int(value):
    return f"{int(fnum(value)):,}"


def money(value):
    try:
        return f"RM{float(value):.0f}"
    except (TypeError, ValueError):
        return "RM?"


def esc(value):
    return html.escape(str(value or ""))


def short_title(title, limit=78):
    title = str(title or "")
    return title if len(title) <= limit else title[:limit - 1] + "..."


def tag_list(text, mapping, fallback):
    blob = (text or "").lower()
    tags = [label for key, label in mapping.items() if key in blob]
    return list(dict.fromkeys(tags))[:4] or fallback


def positive_tags(row):
    return tag_list(
        " ".join([row.get("bullet_points", ""), row.get("title", "")]),
        POSITIVE_TAGS,
        ["低价", "轻小件", "场景清晰"],
    )


def negative_tags(row):
    return tag_list(
        " ".join([row.get("top_review_pain_points", ""), row.get("title", "")]),
        NEGATIVE_TAGS,
        ["同质化", "质量需验证"],
    )


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


def image_block(row):
    image_url = (row.get("image_url") or "").strip()
    if image_url:
        return (
            f'<img src="{esc(image_url)}" alt="{esc(row.get("title"))}" '
            'style="width:86px;height:86px;object-fit:contain;border:1px solid #e2e8f0;border-radius:10px;background:#fff;">'
        )
    return (
        '<div style="width:86px;height:86px;border:1px solid #e2e8f0;border-radius:10px;'
        'background:#f8fafc;color:#64748b;display:flex;align-items:center;justify-content:center;'
        'font-size:12px;text-align:center;">商品图<br>待采集</div>'
    )


def tags_html(tags, bg, color):
    return "".join(
        f'<span style="display:inline-block;margin:3px 4px 0 0;padding:3px 7px;'
        f'border-radius:999px;background:{bg};color:{color};font-size:12px;">{esc(tag)}</span>'
        for tag in tags
    )


def scripts_by_product():
    scripts = defaultdict(list)
    for row in read_csv(SCRIPT_PATH):
        scripts[row.get("product_id")].append(row)
    return scripts


def product_card(row, index, scripts):
    product_scripts = scripts.get(row.get("product_id"), [])
    hook = product_scripts[0].get("hook") if product_scripts else "用差评痛点开场，展示产品解决前后对比。"
    return f"""
    <div style="border:1px solid #dbe3ef;border-radius:14px;background:#ffffff;margin:12px 0;padding:14px;">
      <div style="display:flex;gap:12px;align-items:flex-start;">
        <div>{image_block(row)}</div>
        <div style="flex:1;min-width:0;">
          <div style="font-size:12px;color:#2563eb;font-weight:700;">#{index} 今日Top10 / Today Top10 · {esc(row.get("decision"))}</div>
          <div style="font-size:16px;font-weight:800;color:#0f172a;line-height:1.3;margin-top:4px;">{esc(short_title(row.get("title")))}</div>
          <div style="font-size:13px;color:#475569;margin-top:5px;">中文解释：{esc(zh_explain(row))}</div>
        </div>
        <div style="text-align:right;color:#0f766e;font-weight:900;font-size:26px;line-height:1;">{fnum(row.get("total_score")):.1f}<br><span style="font-size:11px;color:#64748b;font-weight:400;">机会分</span></div>
      </div>

      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:12px;">
        <div style="background:#f8fafc;border-radius:10px;padding:8px;"><b>{money(row.get("price_myr_est"))}</b><br><span style="font-size:11px;color:#64748b;">价格</span></div>
        <div style="background:#f8fafc;border-radius:10px;padding:8px;"><b>{fnum(row.get("rating")):.1f}</b><br><span style="font-size:11px;color:#64748b;">评分</span></div>
        <div style="background:#f8fafc;border-radius:10px;padding:8px;"><b>{fmt_int(row.get("review_count"))}</b><br><span style="font-size:11px;color:#64748b;">评论</span></div>
        <div style="background:#f8fafc;border-radius:10px;padding:8px;"><b>{fnum(row.get("review_growth_30d")):.0f}%</b><br><span style="font-size:11px;color:#64748b;">增长</span></div>
      </div>

      <div style="margin-top:10px;font-size:13px;color:#334155;"><b>上涨原因：</b>{esc(rise_reason(row))}</div>
      <div style="margin-top:8px;"><b style="font-size:13px;">正向标签：</b>{tags_html(positive_tags(row), "#ecfdf5", "#0f766e")}</div>
      <div style="margin-top:5px;"><b style="font-size:13px;">负向标签：</b>{tags_html(negative_tags(row), "#fff1f2", "#be123c")}</div>
      <div style="margin-top:8px;font-size:13px;color:#334155;"><b>差评机会点：</b>{esc(row.get("top_review_pain_points"))}</div>
      <div style="margin-top:8px;font-size:13px;color:#334155;"><b>风险预警：</b>{esc(risk_warning(row))}</div>
      <div style="margin-top:8px;font-size:13px;color:#334155;"><b>TikTok脚本角度：</b>{esc(hook)}</div>
    </div>
    """


def compact_rank(rows, title):
    items = []
    for index, row in enumerate(rows[:10], start=1):
        items.append(f"""
        <tr>
          <td style="padding:8px;border-bottom:1px solid #e5e7eb;color:#64748b;">{index}</td>
          <td style="padding:8px;border-bottom:1px solid #e5e7eb;"><b>{esc(short_title(row.get("title"), 46))}</b><br><span style="color:#64748b;">{money(row.get("price_myr_est"))} · {fnum(row.get("review_growth_30d")):.0f}%增长 · {fmt_int(row.get("review_count"))}评论</span></td>
          <td style="padding:8px;border-bottom:1px solid #e5e7eb;text-align:right;"><b>{fnum(row.get("total_score")):.1f}</b></td>
        </tr>
        """)
    return f"""
    <h3 style="margin:18px 0 8px;color:#0f172a;">{esc(title)}</h3>
    <table style="border-collapse:collapse;width:100%;font-size:13px;background:#fff;border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;">
      <tbody>{''.join(items)}</tbody>
    </table>
    """


def body_html(rows):
    today = date.today().isoformat()
    scripts = scripts_by_product()
    top = rows[0] if rows else {}
    cards = "".join(product_card(row, index, scripts) for index, row in enumerate(rows[:10], start=1))
    avg_score = sum(fnum(row.get("total_score")) for row in rows[:10]) / max(len(rows[:10]), 1)
    best_video = max(rows[:10], key=lambda row: fnum(row.get("score_tiktok_visual_potential")), default={})

    return f"""
    <html>
      <body style="margin:0;background:#f3f6fb;font-family:Arial,'Microsoft YaHei',sans-serif;color:#172033;line-height:1.5;">
        <div style="max-width:760px;margin:0 auto;padding:16px;">
          <div style="background:#0f172a;color:#fff;border-radius:16px;padding:18px;">
            <div style="font-size:12px;color:#93c5fd;font-weight:700;">Amazon US/SG/UK → TikTok Malaysia</div>
            <h2 style="margin:6px 0 4px;font-size:23px;line-height:1.25;">3C数码选品商业情报日报</h2>
            <div style="font-size:13px;color:#cbd5e1;">{today} · 手机优先阅读版 · Core ranking in email, full HTML in attachments</div>
          </div>

          <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:12px 0;">
            <div style="background:#fff;border-radius:12px;padding:11px;border:1px solid #e2e8f0;"><span style="font-size:11px;color:#64748b;">今日Top1</span><br><b>{esc(short_title(top.get("title"), 26))}</b></div>
            <div style="background:#fff;border-radius:12px;padding:11px;border:1px solid #e2e8f0;"><span style="font-size:11px;color:#64748b;">Top10均分</span><br><b>{avg_score:.1f}/100</b></div>
            <div style="background:#fff;border-radius:12px;padding:11px;border:1px solid #e2e8f0;"><span style="font-size:11px;color:#64748b;">最值得拍</span><br><b>{esc(short_title(best_video.get("title"), 24))}</b></div>
          </div>

          <div style="background:#fff7ed;border:1px solid #fed7aa;border-radius:12px;padding:12px;font-size:14px;color:#7c2d12;">
            <b>今日判断：</b>优先测试综合分高、视频表现强、差评痛点清楚的 3C 小件。高竞争品不要直接铺货，先用 3-5 条 TikTok 视频验证点击和转化。
          </div>

          {compact_rank(rows, "今日3C数码Top10 / Today Top10")}
          {compact_rank(rows, "本周3C数码Top10 / Weekly Watchlist")}

          <h3 style="margin:20px 0 8px;color:#0f172a;">商品卡片 / Product Cards</h3>
          {cards}

          <p style="font-size:12px;color:#64748b;margin:18px 0;">
            附件包含完整 HTML 看板、评分明细 CSV、TikTok 脚本 CSV。当前商品图依赖 image_url 字段；后续接入真实 Amazon 图片后会自动展示。
          </p>
        </div>
      </body>
    </html>
    """


def add_attachment(message, path):
    if not path.exists():
        return
    ctype, encoding = mimetypes.guess_type(path)
    if ctype is None or encoding is not None:
        ctype = "application/octet-stream"
    maintype, subtype = ctype.split("/", 1)
    message.add_attachment(
        path.read_bytes(),
        maintype=maintype,
        subtype=subtype,
        filename=path.name,
    )


def main():
    sender = env("GMAIL_USER")
    password = env("GMAIL_APP_PASSWORD")
    recipient = env("REPORT_RECIPIENT", "richardlee19831228@gmail.com")

    rows = read_csv(RANKED_PATH, limit=20)
    subject = f"【3C数码选品情报】{date.today().isoformat()}｜今日Top10 + 本周Top10｜TikTok MY"

    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content("Your email client does not support HTML. Please see the attached daily report.")
    message.add_alternative(body_html(rows), subtype="html")

    add_attachment(message, OUTPUT_DIR / "daily_crossborder_dashboard.html")
    add_attachment(message, OUTPUT_DIR / "visual_product_report.html")
    add_attachment(message, OUTPUT_DIR / "visual_product_report.pdf")
    add_attachment(message, OUTPUT_DIR / "ranked_products.csv")
    add_attachment(message, OUTPUT_DIR / "tiktok_scripts.csv")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender, password)
        smtp.send_message(message)

    print(f"Daily report sent to {recipient}")


if __name__ == "__main__":
    main()
