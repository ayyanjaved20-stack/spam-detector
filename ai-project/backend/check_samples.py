"""Batch-check data/test_samples.csv against the current trained model.

Run from the backend folder:
    .\\.venv\\Scripts\\python.exe check_samples.py
"""
from __future__ import annotations

import csv
from pathlib import Path

from model import predict

CSV_PATH = Path(__file__).resolve().parent / "data" / "test_samples.csv"


def main() -> None:
    with CSV_PATH.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    if not rows:
        print(f"No rows found in {CSV_PATH}")
        return

    matched = 0
    for index, row in enumerate(rows, start=1):
        expected = row["label"].strip().lower()
        result = predict(row["text"], row["source"].strip().lower())
        got = result["label"]
        ok = got == expected
        matched += int(ok)

        print(
            f"{index:02d} [{row['source']:5}] "
            f"expected={expected:4} got={got:4} "
            f"p(spam)={result['spam_probability']:.3f} "
            f"{'OK' if ok else 'MISS'}"
        )
        snippet = row["text"].replace("\n", " ")
        print(f"    {snippet[:110]}")

    print(f"\n{matched}/{len(rows)} matched ({matched / len(rows):.0%})")


if __name__ == "__main__":
    main()
