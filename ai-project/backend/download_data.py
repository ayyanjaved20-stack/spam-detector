"""Download the three public datasets used to train the spam detector.

Run once:  python download_data.py
Force re-download:  python download_data.py --force
"""
from __future__ import annotations

import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DATA.mkdir(parents=True, exist_ok=True)

SOURCES = {
    # Pakistan-focused SMS/scam messages (English + Roman Urdu + Urdu, mixed)
    "pakistan_sms.xlsx": (
        "https://raw.githubusercontent.com/saifkhandev/Muhafiz-AI/main/"
        "scam_detection/data/scam_messages_dataset.xlsx"
    ),
    # Roman Urdu phishing SMS, UMT Lahore (CC BY 4.0, DOI 10.5281/zenodo.21810885)
    "roman_urdu_phishing.xlsx": (
        "https://zenodo.org/records/21810885/files/"
        "phishing_dataset_1000.xlsx?download=1"
    ),
    # Enron-Spam emails, preprocessed into one CSV (international email coverage)
    "enron_spam_data.zip": (
        "https://github.com/MWiechmann/enron_spam_data/raw/master/enron_spam_data.zip"
    ),
}


def download(url: str, dest: Path) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        print(f"skip   {dest.name} (already exists)")
        return
    print(f"fetch  {dest.name} ...")
    request = urllib.request.Request(
        url, headers={"User-Agent": "spam-detector-semester-project/1.0"}
    )
    with urllib.request.urlopen(request, timeout=180) as response, open(dest, "wb") as out:
        out.write(response.read())
    print(f"done   {dest.name} ({dest.stat().st_size:,} bytes)")


def main() -> None:
    force = "--force" in sys.argv

    for name, url in SOURCES.items():
        dest = DATA / name
        if force and dest.exists():
            dest.unlink()
        download(url, dest)

    zip_path = DATA / "enron_spam_data.zip"
    out_dir = DATA / "enron_spam_data"
    out_dir.mkdir(exist_ok=True)
    if not list(out_dir.rglob("*.csv")):
        print(f"unzip  {zip_path.name} ...")
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(out_dir)

    csv_files = sorted(out_dir.rglob("*.csv"))
    if not csv_files:
        raise RuntimeError(f"No CSV found inside {zip_path.name}")

    print("\nReady. Training inputs:")
    for path in [DATA / "pakistan_sms.xlsx", DATA / "roman_urdu_phishing.xlsx", csv_files[0]]:
        print(f"  {path}")
    print(f"  {DATA / 'local_pakistani_emails.csv'}")


if __name__ == "__main__":
    main()
