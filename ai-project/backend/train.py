"""Train the spam classifier on Pakistan SMS + Roman Urdu + international email.

You run this yourself. It writes:
    models/spam_model.joblib   (the supervised model)
    models/metrics.json        (numbers for your report)

Usage:  python train.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
MODELS = ROOT / "models"
MODEL_PATH = MODELS / "spam_model.joblib"
METRICS_PATH = MODELS / "metrics.json"

LABEL_MAP = {
    "spam": "spam", "scam": "spam", "phishing": "spam", "fraud": "spam",
    "1": "spam", "true": "spam", "yes": "spam",
    "ham": "ham", "safe": "ham", "legitimate": "ham", "legit": "ham",
    "clean": "ham", "not spam": "ham", "non spam": "ham", "nonspam": "ham",
    "0": "ham", "false": "ham", "no": "ham",
}


def normalise_label(value) -> str | None:
    return LABEL_MAP.get(str(value).strip().lower())


def pick_label_column(frame: pd.DataFrame) -> str:
    columns = list(frame.columns)

    # 1) Exact names win (e.g. Muhafiz has both "Label" and "Scam Category").
    for key in ("label", "labels", "spam/ham", "target", "class"):
        for column in columns:
            if str(column).strip().lower() == key:
                return column

    # 2) Substring match, but never a category/type column.
    for key in ("label", "spam/ham", "class", "target"):
        for column in columns:
            lowered = str(column).lower()
            if key in lowered and "categor" not in lowered and "type" not in lowered:
                return column

    # 3) Fallback: small-cardinality column whose values all map to spam/ham.
    for column in columns:
        values = frame[column].dropna().astype(str).unique()
        if 0 < len(values) <= 8 and all(normalise_label(v) for v in values):
            return column

    raise ValueError(f"No label column found. Columns: {columns}")


def pick_text_column(frame: pd.DataFrame, prefer: tuple[str, ...] = ()) -> str:
    candidates = [
        c for c in frame.columns
        if frame[c].dtype == object or pd.api.types.is_string_dtype(frame[c])
    ]
    if not candidates:
        raise ValueError(f"No text column found. Columns: {list(frame.columns)}")
    for keyword in prefer:
        for column in candidates:
            if keyword in str(column).lower():
                return column
    for column in candidates:
        lowered = str(column).lower()
        if any(key in lowered for key in ("text", "message", "sms", "content", "body")):
            return column
    return max(candidates, key=lambda c: frame[c].dropna().astype(str).str.len().mean())


def load_xlsx(path: Path, source: str, prefer: tuple[str, ...] = ()) -> pd.DataFrame:
    frame = pd.read_excel(path)
    print(f"  {path.name} columns: {list(frame.columns)}")
    text_col = pick_text_column(frame, prefer)
    label_col = pick_label_column(frame)
    print(f"    text='{text_col}'  label='{label_col}'")
    return pd.DataFrame({
        "text": frame[text_col].astype(str),
        "label": frame[label_col].map(normalise_label),
        "source": source,
    })


def load_enron() -> pd.DataFrame:
    csv_files = sorted((DATA / "enron_spam_data").rglob("*.csv"))
    if not csv_files:
        raise FileNotFoundError("Enron CSV missing. Run `python download_data.py` first.")
    frame = pd.read_csv(csv_files[0])
    frame = frame.rename(columns={c: c.strip() for c in frame.columns})

    subject = next((c for c in frame.columns if "subject" in c.lower()), "")
    message = next(
        (c for c in frame.columns if "message" in c.lower() or "body" in c.lower()), ""
    )
    label_col = None
    for column in frame.columns:
        lowered = column.lower().replace(" ", "")
        if "spam/ham" in lowered or lowered in ("label", "class", "spam"):
            label_col = column
            break
    if label_col is None:
        label_col = pick_label_column(frame)

    subject_text = frame[subject].fillna("").astype(str) if subject else ""
    message_text = frame[message].fillna("").astype(str) if message else ""
    frame["text"] = subject_text + "\n" + message_text
    frame["label"] = frame[label_col].map(normalise_label)
    frame["source"] = "email"

    # 1,000 spam + 1,000 ham keeps training fast and roughly balanced.
    pieces = []
    for _, group in frame.groupby("label"):
        pieces.append(group.sample(min(len(group), 1000), random_state=42))
    frame = pd.concat(pieces, ignore_index=True)
    print(f"  Enron columns: {list(frame.columns)} -> sampled {len(frame)} emails")
    return frame[["text", "label", "source"]]


def main() -> None:
    print("Loading datasets...")
    parts: list[pd.DataFrame] = []

    for name in ("pakistan_sms.xlsx", "roman_urdu_phishing.xlsx"):
        path = DATA / name
        if path.exists():
            parts.append(load_xlsx(path, "sms", prefer=("raw",)))
        else:
            print(f"  WARN {name} missing (run download_data.py)")

    if (DATA / "enron_spam_data").exists():
        parts.append(load_enron())
    else:
        print("  WARN Enron folder missing (run download_data.py)")

    local = DATA / "local_pakistani_emails.csv"
    if local.exists():
        parts.append(pd.read_csv(local))
    else:
        print("  WARN local_pakistani_emails.csv missing")

    if not parts:
        raise RuntimeError("No training data found. Run `python download_data.py` first.")

    frame = pd.concat(parts, ignore_index=True)
    frame = frame.dropna(subset=["text", "label"])
    frame["text"] = frame["text"].astype(str).str.strip()
    frame = frame[frame["text"].str.len() > 3]
    frame["key"] = frame["text"].str.lower().str.replace(r"\s+", " ", regex=True)
    before = len(frame)
    frame = frame.drop_duplicates(subset="key").drop(columns="key")
    print(f"\nCombined rows: {before} -> {len(frame)} after exact deduplication")
    print("By source:", frame["source"].value_counts().to_dict())
    print("By label :", frame["label"].value_counts().to_dict())

    # Split BEFORE oversampling so duplicate copies never cross into the test set.
    train_df, test_df = train_test_split(
        frame, test_size=0.2, stratify=frame["label"], random_state=42
    )

    # Keep international coverage, but strongly emphasize Pakistani/local patterns.
    sms_train = train_df[train_df["source"] == "sms"]
    is_local_email = (train_df["source"] == "email") & train_df["text"].str.contains(
        "easypaisa|nayapay|jazzcash|sadapay|hbl|ubl|meezan|bahria|nadra|fbr|pta|kelectric|nayatel|"
        "bahria|university|student|portal|invoice|receipt|statement|tracking|delivery|order|otp|"
        "rs\\.|pkr|lahore|karachi|islamabad|pakistan",
        case=False, na=False, regex=True
    )
    local_train = train_df[is_local_email]
    train_df = pd.concat(
        [train_df, sms_train, sms_train, local_train, local_train, local_train, local_train],
        ignore_index=True,
    )
    print(
        f"Train rows: {len(train_df)} (SMS x4, Pakistani/local email x6), Test rows: {len(test_df)}"
    )

    print("\nTraining TF-IDF + Logistic Regression...")
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.95,
            max_features=80_000,
            strip_accents="unicode",
            sublinear_tf=True,
        )),
        ("clf", LogisticRegression(
            max_iter=3000,
            class_weight={ "ham": 1.35, "spam": 1.0 },
            solver="liblinear",
        )),
    ])
    pipeline.fit(train_df["text"], train_df["label"])

    threshold = 0.60  # conservative: reduce false positives on legit notifications
    proba = pipeline.predict_proba(test_df["text"])
    classes = list(pipeline.classes_)
    spam_i = classes.index("spam")
    spam_p = proba[:, spam_i]

    predictions = ["spam" if p >= threshold else "ham" for p in spam_p]
    report = classification_report(test_df["label"], predictions, output_dict=True, zero_division=0)
    matrix = confusion_matrix(test_df["label"], predictions, labels=["ham", "spam"]).tolist()

    per_source: dict[str, dict] = {}
    for source, group in test_df.groupby("source"):
        gp = pipeline.predict_proba(group["text"])[:, spam_i]
        source_predictions = ["spam" if p >= threshold else "ham" for p in gp]
        per_source[str(source)] = {
            "n": int(len(group)),
            "accuracy": round(float((pd.Series(source_predictions) == group["label"].reset_index(drop=True)).mean()), 4),
        }

    metrics = {
        "trained": True,
        "model": "TF-IDF + Logistic Regression",
        "threshold": threshold,
        "rows_total": int(len(frame)),
        "rows_train": int(len(train_df)),
        "rows_test": int(len(test_df)),
        "sources": {str(k): int(v) for k, v in frame["source"].value_counts().items()},
        "accuracy": round(report["accuracy"], 4),
        "spam_precision": round(report["spam"]["precision"], 4),
        "spam_recall": round(report["spam"]["recall"], 4),
        "spam_f1": round(report["spam"]["f1-score"], 4),
        "ham_precision": round(report["ham"]["precision"], 4),
        "confusion_matrix": {"labels": ["ham", "spam"], "values": matrix},
        "per_source": per_source,
    }

    MODELS.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print("\n" + classification_report(test_df["label"], predictions))
    print("Confusion matrix [ham, spam]:", matrix)
    print("Per-source accuracy:", per_source)
    print(f"\nSaved {MODEL_PATH}")
    print(f"Saved {METRICS_PATH}")


if __name__ == "__main__":
    main()
