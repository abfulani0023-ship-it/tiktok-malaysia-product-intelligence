#!/usr/bin/env python3
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML_PATH = ROOT / "outputs" / "visual_product_report.html"
PDF_PATH = ROOT / "outputs" / "visual_product_report.pdf"
CHROME_PATH = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


def main():
    if PDF_PATH.exists() and PDF_PATH.stat().st_size == 0:
        PDF_PATH.unlink()
    if not HTML_PATH.exists():
        raise FileNotFoundError(f"Missing HTML report: {HTML_PATH}")
    if not CHROME_PATH.exists():
        raise SystemExit(f"Google Chrome not found: {CHROME_PATH}")

    with tempfile.TemporaryDirectory(prefix="chrome-pdf-") as user_data_dir:
        command = [
            str(CHROME_PATH),
            "--headless=new",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--no-first-run",
            "--no-default-browser-check",
            f"--user-data-dir={user_data_dir}",
            "--print-to-pdf-no-header",
            f"--print-to-pdf={PDF_PATH}",
            HTML_PATH.as_uri(),
        ]
        result = subprocess.run(
            command,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            raise SystemExit("Chrome headless PDF export failed. Use the HTML report's print view to save as PDF.")
    print(PDF_PATH)


if __name__ == "__main__":
    main()
