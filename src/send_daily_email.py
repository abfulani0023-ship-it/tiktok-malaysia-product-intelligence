#!/usr/bin/env python3
import csv
import mimetypes
import os
import smtplib
from datetime import date
from email.message import EmailMessage
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs"
RANKED_PATH = OUTPUT_DIR / "ranked_products.csv"


def env(name, default=None):
    value = os.environ.get(name, default)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def read_ranked(limit=7):
    if not RANKED_PATH.exists():
        return []
    with RANKED_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))[:limit]


def money(value):
    try:
        return f"RM{float(value):.0f}"
    except (TypeError, ValueError):
        return "RM?"


def body_html(rows):
    today = date.today().isoformat()
    cards = []
    for index, row in enumerate(rows, start=1):
        cards.append(f"""
        <tr>
          <td style="padding:10px;border-bottom:1px solid #e5e7eb;">{index}</td>
          <td style="padding:10px;border-bottom:1px solid #e5e7eb;">
            <b>{row.get("title", "")}</b><br>
            <span style="color:#64748b;">{row.get("marketplace", "")} · {row.get("bsr_category", "")}</span>
          </td>
          <td style="padding:10px;border-bottom:1px solid #e5e7eb;">{money(row.get("price_myr_est"))}</td>
          <td style="padding:10px;border-bottom:1px solid #e5e7eb;">{row.get("rating", "")}</td>
          <td style="padding:10px;border-bottom:1px solid #e5e7eb;">{row.get("review_count", "")}</td>
          <td style="padding:10px;border-bottom:1px solid #e5e7eb;">{row.get("review_growth_30d", "")}%</td>
          <td style="padding:10px;border-bottom:1px solid #e5e7eb;"><b>{row.get("total_score", "")}</b></td>
        </tr>
        """)

    return f"""
    <html>
      <body style="font-family:Arial,'Microsoft YaHei',sans-serif;color:#172033;line-height:1.55;">
        <h2>Amazon → TikTok MY 每日跨境选品日报 / Daily Product Intelligence</h2>
        <p>日期 Date：{today}</p>
        <p>
          监控站点 Source：Amazon US / SG / UK<br>
          目标市场 Target：TikTok Malaysia<br>
          核心逻辑 Logic：Amazon 能爆或即将爆的品，优先进入 TikTok Malaysia 测试池。
        </p>
        <h3>今日优先商品 / Top Recommended Products</h3>
        <table style="border-collapse:collapse;width:100%;font-size:14px;">
          <thead>
            <tr style="background:#f8fafc;color:#475569;">
              <th style="padding:10px;text-align:left;">#</th>
              <th style="padding:10px;text-align:left;">商品 Product</th>
              <th style="padding:10px;text-align:left;">价格 Price</th>
              <th style="padding:10px;text-align:left;">评分 Rating</th>
              <th style="padding:10px;text-align:left;">评论 Reviews</th>
              <th style="padding:10px;text-align:left;">增长 Growth</th>
              <th style="padding:10px;text-align:left;">综合分 Score</th>
            </tr>
          </thead>
          <tbody>
            {''.join(cards)}
          </tbody>
        </table>
        <h3>附件 / Attachments</h3>
        <p>
          已附上 HTML 可视化日报、商品评分明细、TikTok 脚本表。<br>
          If attachments fail in the mail client, the same files are generated in the workspace outputs folder.
        </p>
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

    rows = read_ranked()
    subject = f"【Amazon→TikTok MY 选品日报】{date.today().isoformat()}｜US/SG/UK Daily Product Intelligence"

    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content("Your email client does not support HTML. Please see the attached daily report.")
    message.add_alternative(body_html(rows), subtype="html")

    add_attachment(message, OUTPUT_DIR / "daily_crossborder_dashboard.html")
    add_attachment(message, OUTPUT_DIR / "ranked_products.csv")
    add_attachment(message, OUTPUT_DIR / "tiktok_scripts.csv")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender, password)
        smtp.send_message(message)

    print(f"Daily report sent to {recipient}")


if __name__ == "__main__":
    main()
