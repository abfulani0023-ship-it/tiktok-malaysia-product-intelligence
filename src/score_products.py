#!/usr/bin/env python3
import csv
import json
import math
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "amazon_products.csv"
WEIGHTS_PATH = ROOT / "config" / "scoring_weights.json"
OUTPUT_DIR = ROOT / "outputs"

USD_TO_MYR = 4.70

VISUAL_KEYWORDS = {
    "organizer", "storage", "cleaner", "cleaning", "mop", "brush", "kitchen",
    "beauty", "makeup", "mist", "led", "lamp", "car", "pet", "before",
    "after", "portable", "foldable", "mini", "automatic", "tool", "basket",
    "drawer", "rack", "holder", "vacuum", "bottle", "sprayer"
}

MALAYSIA_FIT_KEYWORDS = {
    "hot", "humid", "rain", "portable", "small apartment", "office", "aircon",
    "kitchen", "bathroom", "car", "storage", "travel", "compact", "easy",
    "clean", "mosquito", "shoe", "laundry", "raya", "home"
}

RISK_KEYWORDS = {
    "medical", "cure", "treat", "weight loss", "skin whitening", "branded",
    "apple", "dyson", "nike", "lego", "medicine", "supplement", "battery",
    "laser", "knife", "fragile", "glass", "ceramic"
}

BULKY_KEYWORDS = {
    "furniture", "chair", "table", "mattress", "large", "heavy", "glass",
    "ceramic", "mirror", "fragile", "machine"
}


def read_weights():
    if WEIGHTS_PATH.exists():
        return json.loads(WEIGHTS_PATH.read_text(encoding="utf-8"))
    return {
        "amazon_trend": 20,
        "pain_point_clarity": 15,
        "tiktok_visual_potential": 15,
        "malaysia_market_fit": 15,
        "impulse_price_fit": 10,
        "logistics_risk": 10,
        "competition_risk": 10,
        "compliance_risk": 5,
    }


def as_float(row, key, default=0.0):
    raw = row.get(key)
    if isinstance(raw, (int, float)):
        return float(raw)
    value = (raw or "").strip()
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def text_blob(row):
    fields = [
        "category",
        "title",
        "bullet_points",
        "top_review_pain_points",
        "bsr_category",
        "compliance_risk_notes",
    ]
    return " ".join((row.get(field) or "") for field in fields).lower()


def clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


def manual_score(row, key):
    raw = as_float(row, key, 0)
    if raw <= 0:
        return None
    return clamp(raw / 5.0)


def keyword_score(blob, keywords):
    hits = sum(1 for word in keywords if word in blob)
    return clamp(hits / 6.0)


def score_amazon_trend(row):
    monthly_sales = as_float(row, "monthly_sales_est")
    review_growth = as_float(row, "review_growth_30d")
    price_drop = as_float(row, "price_drop_pct")
    bsr_rank = as_float(row, "bsr_rank", 999999)
    review_count = as_float(row, "review_count")

    sales_component = clamp(math.log10(max(monthly_sales, 1)) / 4.0)
    growth_component = clamp(review_growth / 25.0)
    bsr_component = clamp(1.0 - (math.log10(max(bsr_rank, 1)) / 6.0))
    review_component = clamp(math.log10(max(review_count, 1)) / 5.0)
    price_component = clamp(price_drop / 30.0)

    return (
        sales_component * 0.35
        + growth_component * 0.25
        + bsr_component * 0.20
        + review_component * 0.10
        + price_component * 0.10
    )


def score_pain_points(row):
    pain = (row.get("top_review_pain_points") or "").strip()
    if not pain:
        return 0.2
    separators = pain.count(";") + pain.count(",")
    length_component = clamp(len(pain) / 160.0)
    structure_component = clamp((separators + 1) / 5.0)
    return length_component * 0.55 + structure_component * 0.45


def score_visual(row):
    manual = manual_score(row, "manual_visual_score")
    if manual is not None:
        return manual
    return keyword_score(text_blob(row), VISUAL_KEYWORDS)


def score_malaysia_fit(row):
    manual = manual_score(row, "manual_malaysia_fit_score")
    if manual is not None:
        return manual
    blob = text_blob(row)
    keyword_component = keyword_score(blob, MALAYSIA_FIT_KEYWORDS)
    price_component = score_price(row)
    return keyword_component * 0.65 + price_component * 0.35


def score_price(row):
    price_myr = as_float(row, "price_usd") * USD_TO_MYR
    if price_myr <= 0:
        return 0.3
    if 15 <= price_myr <= 80:
        return 1.0
    if 80 < price_myr <= 120:
        return 0.7
    if 120 < price_myr <= 180:
        return 0.45
    if price_myr < 15:
        return 0.65
    return 0.2


def inverse_risk_score(row, manual_key, keywords):
    manual = manual_score(row, manual_key)
    if manual is not None:
        return 1.0 - manual
    blob = text_blob(row)
    hits = sum(1 for word in keywords if word in blob)
    return 1.0 - clamp(hits / 4.0)


def score_competition(row):
    manual = manual_score(row, "manual_competition_risk")
    if manual is not None:
        return 1.0 - manual
    review_count = as_float(row, "review_count")
    bsr_rank = as_float(row, "bsr_rank", 999999)
    crowded = clamp(math.log10(max(review_count, 1)) / 5.0)
    hot_rank = clamp(1.0 - (math.log10(max(bsr_rank, 1)) / 6.0))
    return 1.0 - clamp(crowded * 0.65 + hot_rank * 0.35)


def compute_scores(row, weights):
    dimensions = {
        "amazon_trend": score_amazon_trend(row),
        "pain_point_clarity": score_pain_points(row),
        "tiktok_visual_potential": score_visual(row),
        "malaysia_market_fit": score_malaysia_fit(row),
        "impulse_price_fit": score_price(row),
        "logistics_risk": inverse_risk_score(row, "manual_logistics_risk", BULKY_KEYWORDS),
        "competition_risk": score_competition(row),
        "compliance_risk": inverse_risk_score(row, "manual_compliance_risk", RISK_KEYWORDS),
    }
    weighted = {
        key: round(dimensions[key] * weights[key], 2)
        for key in dimensions
    }
    total = round(sum(weighted.values()), 2)
    return dimensions, weighted, total


def decision_label(total):
    if total >= 75:
        return "scale-test"
    if total >= 65:
        return "test"
    if total >= 55:
        return "watch"
    return "skip"


def script_angles(row):
    title = row.get("title") or "this product"
    pain_points = [
        item.strip()
        for item in (row.get("top_review_pain_points") or "daily hassle").split(";")
        if item.strip()
    ]
    pain = pain_points[0] if pain_points else "daily hassle"
    price_myr = as_float(row, "price_usd") * USD_TO_MYR
    price_text = f"around RM{price_myr:.0f}" if price_myr else "promo price"
    product_id = row.get("product_id") or row.get("asin") or "UNKNOWN"
    category = (row.get("category") or "").lower()

    local_scene = "desk, office, bedroom, car, or small condo"
    malay_hook = "Benda kecil, tapi memang boleh settle masalah harian."
    proof_metric = "time saved, cleaner setup, easier use, or visible before/after"

    if "car" in category:
        local_scene = "Grab commute, daily drive, parking lot, or dashboard navigation scene"
        malay_hook = "Kalau selalu drive, masalah phone jatuh memang annoying."
        proof_metric = "phone stability, one-hand use, and cleaner dashboard"
    elif "audio" in category:
        local_scene = "TikTok recording, live selling, cafe, street, or home office scene"
        malay_hook = "Suara clear lagi senang orang percaya bila buat video jualan."
        proof_metric = "voice clarity before/after and noise reduction"
    elif "lighting" in category:
        local_scene = "night TV setup, gaming room, small bedroom, or rental room makeover"
        malay_hook = "Bilik nampak lagi mahal, tapi modal kecil saja."
        proof_metric = "room mood before/after and glare reduction"
    elif "phone" in category:
        local_scene = "commute, cafe table, bedroom, office desk, or content creator setup"
        malay_hook = "Phone hari-hari pakai, benda kecil macam ni memang terasa beza."
        proof_metric = "grip, charging speed, protection, or hands-free convenience"
    elif "computer" in category:
        local_scene = "student desk, work-from-home desk, office, or cyber cafe setup"
        malay_hook = "Meja kerja nampak simple, tapi masalah cable dan port selalu kacau."
        proof_metric = "cleaner desk, easier connection, and faster workflow"
    elif "smart home" in category:
        local_scene = "bedroom fan, desk lamp, rental room, or home appliance timer scene"
        malay_hook = "Lampu atau kipas boleh jadi smart tanpa tukar barang besar."
        proof_metric = "timer control, app control, and convenience"

    return [
        {
            "product_id": product_id,
            "angle": "problem_solution",
            "language": "en-ms",
            "hook": f"Still dealing with {pain}?",
            "scene_plan": f"Show the problem in a Malaysia-relevant scene: {local_scene}. Then introduce {title}.",
            "proof": "Use before/after shots and one close-up of the product solving the problem.",
            "cta": f"Check the yellow cart. If it is {price_text}, this is worth testing.",
        },
        {
            "product_id": product_id,
            "angle": "malay_local",
            "language": "ms-en",
            "hook": malay_hook,
            "scene_plan": f"Open with a local Malaysia scene: {local_scene}. Show {title} in use within 3 seconds.",
            "proof": f"Show {proof_metric}. Keep every shot clear enough to understand without sound.",
            "cta": "Tekan cart kuning kalau nak tengok harga promo hari ini.",
        },
        {
            "product_id": product_id,
            "angle": "comparison_test",
            "language": "en",
            "hook": "Cheap solution vs this one. Which works better?",
            "scene_plan": f"Split the screen into old method and product method using the same {local_scene} setup.",
            "proof": f"Compare {proof_metric} in 10 seconds.",
            "cta": "I would test this first because the result is easy to see.",
        },
        {
            "product_id": product_id,
            "angle": "review_pain_reply",
            "language": "en-ms",
            "hook": f"Someone said: '{pain}'. Let me show the fix.",
            "scene_plan": f"Use one buyer-pain comment style overlay, then demonstrate {title} in a realistic shot.",
            "proof": "Show the exact pain disappearing on screen. Avoid exaggerated claims.",
            "cta": "Save this if you have the same problem, or check the cart for today's price.",
        },
    ]


def read_products():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Missing input file: {DATA_PATH}")
    with DATA_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main():
    weights = read_weights()
    products = read_products()
    ranked = []
    scripts = []

    for row in products:
        _, weighted, total = compute_scores(row, weights)
        price_myr = as_float(row, "price_usd") * USD_TO_MYR
        result = dict(row)
        result.update({
            "price_myr_est": round(price_myr, 2),
            "total_score": total,
            "decision": decision_label(total),
        })
        for key, value in weighted.items():
            result[f"score_{key}"] = value
        ranked.append(result)
        if total >= 55:
            scripts.extend(script_angles(row))

    ranked.sort(key=lambda item: as_float(item, "total_score"), reverse=True)

    ranked_fields = list(ranked[0].keys()) if ranked else []
    write_csv(OUTPUT_DIR / "ranked_products.csv", ranked, ranked_fields)

    script_fields = ["product_id", "angle", "language", "hook", "scene_plan", "proof", "cta"]
    write_csv(OUTPUT_DIR / "tiktok_scripts.csv", scripts, script_fields)

    report_lines = [
        "# TikTok Malaysia Product Intelligence Report",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        "## Top Products",
        "",
    ]
    for index, item in enumerate(ranked[:10], start=1):
        report_lines.extend([
            f"{index}. {item.get('title', '')}",
            f"   - Product ID: {item.get('product_id', '')}",
            f"   - Score: {item.get('total_score')} / 100",
            f"   - Decision: {item.get('decision')}",
            f"   - Est. MYR price: RM{item.get('price_myr_est')}",
            f"   - Pain points: {item.get('top_review_pain_points', '')}",
            "",
        ])

    report_lines.extend([
        "## Operating Notes",
        "",
        "- Prioritize `scale-test` and `test` products first.",
        "- Create 10-20 TikTok script variants before judging a product.",
        "- Use real review pain points as hooks, not generic product descriptions.",
        "- For Malaysia, test English, Malay, and mixed subtitles separately.",
        "",
    ])

    (OUTPUT_DIR / "product_report.md").write_text("\n".join(report_lines), encoding="utf-8")

    print(f"Ranked products: {OUTPUT_DIR / 'ranked_products.csv'}")
    print(f"TikTok scripts: {OUTPUT_DIR / 'tiktok_scripts.csv'}")
    print(f"Report: {OUTPUT_DIR / 'product_report.md'}")


if __name__ == "__main__":
    main()
