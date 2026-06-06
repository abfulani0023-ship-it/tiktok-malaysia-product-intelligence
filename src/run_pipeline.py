#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(script):
    subprocess.run([sys.executable, str(ROOT / "src" / script)], cwd=ROOT, check=True)


def main():
    run("score_products.py")
    run("build_visual_report.py")
    run("build_daily_dashboard.py")
    try:
        run("export_pdf.py")
    except subprocess.CalledProcessError:
        print("PDF export skipped: use the HTML report's print view to save as PDF.")
    print("")
    print("Pipeline complete.")
    print(f"Visual report: {ROOT / 'outputs' / 'visual_product_report.html'}")
    print(f"Daily dashboard: {ROOT / 'outputs' / 'daily_crossborder_dashboard.html'}")
    pdf_path = ROOT / "outputs" / "visual_product_report.pdf"
    if pdf_path.exists() and pdf_path.stat().st_size > 0:
        print(f"PDF report: {pdf_path}")
    print(f"Ranked products: {ROOT / 'outputs' / 'ranked_products.csv'}")
    print(f"TikTok scripts: {ROOT / 'outputs' / 'tiktok_scripts.csv'}")


if __name__ == "__main__":
    main()
