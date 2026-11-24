"""Inference helpers. Loads the pipeline that YOU create with train.py."""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import json
import joblib

ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "models" / "spam_model.joblib"
METRICS_PATH = ROOT / "models" / "metrics.json"

HAM_HINTS = (
    "noreply", "no-reply", "statement", "receipt", "invoice", "delivered", "tracking",
    "appointment", "confirmed", "renew", "subscription", "due date", "portal", "lms",
    "meeting", "attendance", "conference", "auditorium", "university", "student",
    "salary", "credited", "balance", "transaction", "refund", "support",
)
SPAM_HINTS = (
    "otp share", "share otp", "send otp", "processing fee", "pay fee", "send money",
    "click here", "claim now", "won", "winner", "prize", "lottery", "inaam",
    "invest", "usdt", "binance", "whatsapp", "bit.ly", "tinyurl",
)


def get_threshold() -> float:
    if METRICS_PATH.exists():
        try:
            return float(json.loads(METRICS_PATH.read_text(encoding="utf-8")).get("threshold", 0.5))
        except Exception:
            return 0.5
    return 0.5

_HEADER_RE = re.compile(r"^[A-Za-z][A-Za-z-]{0,30}:\s")
_DATE_LINE_RE = re.compile(
    r"^(mon|tue|wed|thu|fri|sat|sun)\w*,?\s+"
    r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d",
    re.I,
)


@lru_cache(maxsize=1)
def load_pipeline():
    """Load once per process. Raises a helpful error if train.py was not run."""
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found at {MODEL_PATH}. Run `python train.py` first."
        )
    return joblib.load(MODEL_PATH)


def clean_text(raw: str, source: str = "sms") -> str:
    """Normalise SMS or email text (including international/English emails)."""
    text = raw

    if source == "email":
        lines = raw.splitlines()
        subject = ""
        body_lines: list[str] = []
        header_mode = True
        for line in lines:
            stripped = line.strip()
            if header_mode:
                if stripped == "":
                    header_mode = False
                    continue
                if stripped.lower().startswith("subject:"):
                    subject = stripped.split(":", 1)[1].strip()
                    continue
                # Skip common raw header/date/recipient lines pasted from emails.
                if _HEADER_RE.match(stripped) or _DATE_LINE_RE.match(stripped):
                    continue
                if stripped.lower() in {"to", "cc", "bcc"}:
                    continue
                header_mode = False
            body_lines.append(line)
        text = subject + "\n" + "\n".join(body_lines)

    text = re.sub(r"<[^>]+>", " ", text)                 # HTML tags
    text = re.sub(r"http\S+|www\.\S+", " URL ", text)    # links
    text = re.sub(r"\S+@\S+", " EMAIL ", text)           # email addresses
    text = re.sub(r"\b03\d{2}[- ]?\d{7}\b", " PHONE ", text)  # PK mobile numbers
    text = re.sub(r"\d+", " NUM ", text)                 # other numbers
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def top_terms(cleaned: str, k: int = 5) -> list[str]:
    """Words in this message that push the model most towards 'spam'."""
    pipe = load_pipeline()
    try:
        vec = pipe.named_steps["tfidf"]
        clf = pipe.named_steps["clf"]
        classes = list(clf.classes_)
        if "spam" not in classes or "ham" not in classes:
            return []

        # Works for both Naive Bayes (feature_log_prob_) and Logistic Regression (coef_).
        if hasattr(clf, "feature_log_prob_"):
            spam_score = clf.feature_log_prob_[classes.index("spam")]
            ham_score = clf.feature_log_prob_[classes.index("ham")]
            log_ratio = spam_score - ham_score
        elif hasattr(clf, "coef_"):
            coef = clf.coef_[0]
            if classes.index("spam") == 0:
                log_ratio = -coef
            else:
                log_ratio = coef
        else:
            return []

        weights = vec.transform([cleaned]).toarray()[0]
        scores = log_ratio * weights
        inverse = {index: word for word, index in vec.vocabulary_.items()}
        ranked = scores.argsort()[-k:][::-1]
        terms = []
        for i in ranked:
            idx = int(i)
            if weights[idx] <= 0:
                continue
            term = inverse[idx]
            if term.isdigit() or term in {"num", "url", "email", "phone"}:
                continue
            terms.append(term)
            if len(terms) == k:
                break
        return terms
    except (KeyError, AttributeError, ValueError):
        return []


def term_contributions(cleaned: str, k: int = 6) -> list[dict]:
    """Terms in this message with their signed model contribution.

    Positive score pushes toward spam, negative toward ham. Unlike top_terms(),
    this surfaces both directions so the UI can show real model evidence.
    """
    pipe = load_pipeline()
    try:
        vec = pipe.named_steps["tfidf"]
        clf = pipe.named_steps["clf"]
        classes = list(clf.classes_)
        if "spam" not in classes or "ham" not in classes:
            return []

        if hasattr(clf, "feature_log_prob_"):
            log_ratio = clf.feature_log_prob_[classes.index("spam")] - clf.feature_log_prob_[classes.index("ham")]
        elif hasattr(clf, "coef_"):
            log_ratio = clf.coef_[0]
            if classes.index("spam") == 0:
                log_ratio = -log_ratio
        else:
            return []

        weights = vec.transform([cleaned]).toarray()[0]
        scores = log_ratio * weights
        inverse = {index: word for word, index in vec.vocabulary_.items()}
        active = [i for i in range(len(scores)) if weights[i] > 0]
        active.sort(key=lambda i: abs(scores[i]), reverse=True)

        result: list[dict] = []
        for index in active:
            term = inverse.get(int(index), "")
            if not term or term.isdigit() or term in {"num", "url", "email", "phone"}:
                continue
            result.append({"term": term, "score": round(float(scores[index]), 4)})
            if len(result) == k:
                break
        return result
    except (KeyError, AttributeError, ValueError):
        return []


def predict(text: str, source: str = "sms") -> dict:
    """Return the verdict, probability, confidence and model-derived terms."""
    pipe = load_pipeline()
    cleaned = clean_text(text, source)
    probabilities = pipe.predict_proba([cleaned])[0]
    classes = list(pipe.classes_)
    spam_index = classes.index("spam") if "spam" in classes else len(classes) - 1
    spam_probability = float(probabilities[spam_index])

    # Light, explainable guardrail for common automated/transactional false positives.
    raw_low = text.lower()
    ham_hits = sum(1 for h in HAM_HINTS if h in raw_low)
    spam_hits = sum(1 for s in SPAM_HINTS if s in raw_low)
    if ham_hits >= 2 and spam_hits == 0:
        spam_probability = min(spam_probability, 0.35)
    elif ham_hits >= 1 and spam_hits == 0 and spam_probability < 0.85:
        spam_probability = min(spam_probability, 0.45)

    threshold = get_threshold()
    return {
        "label": "spam" if spam_probability >= threshold else "ham",
        "spam_probability": round(spam_probability, 4),
        "confidence": round(max(spam_probability, 1 - spam_probability), 4),
        "threshold": round(threshold, 2),
        "top_terms": top_terms(cleaned),
        "term_scores": term_contributions(cleaned),
    }
