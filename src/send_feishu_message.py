#!/usr/bin/env python3
import base64
import csv
import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs"
RANKED_PATH = OUTPUT_DIR / "ranked_products.csv"


def read_ranked(limit=10):
    if not RANKED_PATH.exists():
        return []
    with RANKED_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))[:limit]


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


def short_title(title, limit=48):
    title = str(title or "")
    return title if len(title) <= limit else title[:limit - 1] + "..."


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
    return "、".join(warnings) if warnings else "风险较低"


def make_sign(timestamp, secret):
    string_to_sign = f"{timestamp}\n{secret}".encode("utf-8")
    digest = hmac.new(string_to_sign, b"", digestmod=hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def paragraph(*nodes):
    return [node for node in nodes if node]


def text(value, un_escape=True):
    return {"tag": "text", "text": str(value), "un_escape": un_escape}


def link(label, href):
    if not href:
        return text(label)
    return {"tag": "a", "text": label, "href": href}


def build_post(rows):
    today = date.today().isoformat()
    top = rows[0] if rows else {}
    avg_score = sum(fnum(row.get("total_score")) for row in rows) / max(len(rows), 1)

    content = [
        paragraph(text(f"今日Top1：{short_title(top.get('title'), 64)}\n")),
        paragraph(text(f"Top10均分：{avg_score:.1f}/100｜目标市场：TikTok Malaysia｜类目：3C数码轻小件\n")),
        paragraph(text("判断：优先测综合分高、视频表现强、差评痛点清楚的产品；高竞争品先用 3-5 条视频验证。\n")),
    ]

    for index, row in enumerate(rows[:10], start=1):
        product_url = row.get("product_url") or ""
        line = (
            f"{index}. {short_title(row.get('title'))}\n"
            f"机会分 {fnum(row.get('total_score')):.1f}｜{money(row.get('price_myr_est'))}｜"
            f"评分 {fnum(row.get('rating')):.1f}｜评论 {fmt_int(row.get('review_count'))}｜"
            f"增长 {fnum(row.get('review_growth_30d')):.0f}%\n"
            f"风险：{risk_warning(row)}｜"
        )
        content.append(paragraph(text(line), link("打开Amazon", product_url), text("\n")))

    content.append(paragraph(text("\n完整日报已同步发送到 Gmail，HTML/CSV 附件里有商品卡片、标签、差评机会点和脚本角度。")))

    return {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": f"3C数码选品情报日报｜{today}",
                    "content": content,
                }
            }
        },
    }


def post_json(url, payload, headers=None):
    headers = {"Content-Type": "application/json; charset=utf-8", **(headers or {})}
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Feishu API failed: HTTP {error.code} {body}") from error


def send_webhook(payload, webhook_url, secret=None):
    if secret:
        timestamp = str(int(time.time()))
        payload["timestamp"] = timestamp
        payload["sign"] = make_sign(timestamp, secret)

    body = post_json(webhook_url, payload)
    result = json.loads(body)
    if result.get("code") not in (0, None):
        raise RuntimeError(f"Feishu webhook failed: {body}")
    return body


def tenant_access_token(app_id, app_secret):
    body = post_json(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        {
            "app_id": app_id,
            "app_secret": app_secret,
        },
    )
    result = json.loads(body)
    if result.get("code") != 0:
        raise RuntimeError(f"Failed to get tenant_access_token: {body}")
    return result["tenant_access_token"]


def send_app_message(payload, app_id, app_secret, chat_id):
    token = tenant_access_token(app_id, app_secret)
    message_payload = {
        "receive_id": chat_id,
        "msg_type": payload["msg_type"],
        "content": json.dumps(payload["content"], ensure_ascii=False),
    }
    url = "https://open.feishu.cn/open-apis/im/v1/messages?" + urllib.parse.urlencode(
        {"receive_id_type": "chat_id"}
    )
    body = post_json(url, message_payload, {"Authorization": f"Bearer {token}"})
    result = json.loads(body)
    if result.get("code") != 0:
        raise RuntimeError(f"Failed to send Feishu app message: {body}")
    return body


def main():
    rows = read_ranked()
    if not rows:
        raise RuntimeError("No ranked products found for Feishu message.")

    payload = build_post(rows)

    webhook_url = os.environ.get("FEISHU_WEBHOOK_URL", "").strip()
    if webhook_url:
        body = send_webhook(payload, webhook_url, os.environ.get("FEISHU_SECRET", "").strip() or None)
        print(f"Feishu webhook report sent: {body}")
        return

    app_id = os.environ.get("FEISHU_APP_ID", "").strip()
    app_secret = os.environ.get("FEISHU_APP_SECRET", "").strip()
    chat_id = os.environ.get("FEISHU_CHAT_ID", "").strip()
    if app_id and app_secret and chat_id:
        body = send_app_message(payload, app_id, app_secret, chat_id)
        print(f"Feishu app report sent: {body}")
        return

    print("Feishu is not configured. Skipping Feishu push.")


if __name__ == "__main__":
    main()
