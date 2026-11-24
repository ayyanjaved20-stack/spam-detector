# Module docstring: this file loads and uses the model that train.py creates.
"""Inference helpers. Loads the pipeline that YOU create with train.py."""
# Enable postponed annotation evaluation for cleaner type hints.
from __future__ import annotations
# (blank line separates logical blocks)

# Import regular expressions for text processing.
import re
# Import a specific name needed by this module.
from functools import lru_cache
# Import Path for portable filesystem paths.
from pathlib import Path
# (blank line separates logical blocks)

# Import JSON support for reading or writing report data.
import json
# Import joblib to save or load the trained model.
import joblib
# (blank line separates logical blocks)

# Resolve this file's own folder so every path stays correct from any working directory.
ROOT = Path(__file__).resolve().parent
# Build the path to the trained model artifact produced by train.py.
MODEL_PATH = ROOT / "models" / "spam_model.joblib"
# Build the path to the metrics file that feeds the interface.
METRICS_PATH = ROOT / "models" / "metrics.json"
# (blank line separates logical blocks)

# Start a tuple of phrases typical of legitimate automated notifications.
HAM_HINTS = (
    # Ham cues: automated sender and receipt/tracking language used by legitimate services.
    "noreply", "no-reply", "statement", "receipt", "invoice", "delivered", "tracking",
    # Ham cues: appointment, subscription and portal wording common in genuine notices.
    "appointment", "confirmed", "renew", "subscription", "due date", "portal", "lms",
    # Ham cues: university and meeting vocabulary that should not be treated as spam.
    "meeting", "attendance", "conference", "auditorium", "university", "student",
    # Ham cues: banking and payroll words used by real transaction alerts.
    "salary", "credited", "balance", "transaction", "refund", "support",
# Close the tuple, list or call that was opened above.
)
# Start a tuple of phrases typical of scam and phishing messages.
SPAM_HINTS = (
    # Spam cues: requests to disclose OTP or pay an upfront fee.
    "otp share", "share otp", "send otp", "processing fee", "pay fee", "send money",
    # Spam cues: prize and urgency language used in lottery scams.
    "click here", "claim now", "won", "winner", "prize", "lottery", "inaam",
    # Spam cues: investment, crypto and shortened-link wording used in fraud.
    "invest", "usdt", "binance", "whatsapp", "bit.ly", "tinyurl",
# Close the tuple, list or call that was opened above.
)
# (blank line separates logical blocks)

# (blank line separates logical blocks)

# Define a function that keeps this step reusable and testable.
def get_threshold() -> float:
    # Check a condition before running the guarded code.
    if METRICS_PATH.exists():
        # Guard this block against expected runtime errors.
        try:
            # Return the computed value to the caller.
            return float(json.loads(METRICS_PATH.read_text(encoding="utf-8")).get("threshold", 0.5))
        # Catch an expected error and handle it gracefully.
        except Exception:
            # Return the computed value to the caller.
            return 0.5
    # Return the computed value to the caller.
    return 0.5
# (blank line separates logical blocks)

# Compile a pattern that recognises raw email header lines such as From: or To:.
_HEADER_RE = re.compile(r"^[A-Za-z][A-Za-z-]{0,30}:\s")
# Start compiling a pattern that recognises pasted email date lines.
_DATE_LINE_RE = re.compile(
    # Match the weekday part of an email date line.
    r"^(mon|tue|wed|thu|fri|sat|sun)\w*,?\s+"
    # Match the month and day part of an email date line.
    r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d",
    # Make the date pattern case-insensitive.
    re.I,
# Close the tuple, list or call that was opened above.
)
# (blank line separates logical blocks)

# (blank line separates logical blocks)

# Cache the result so expensive work happens only once.
@lru_cache(maxsize=1)
# Define a function that keeps this step reusable and testable.
def load_pipeline():
    # Function docstring: explain that the model is cached and that training must happen first.
    """Load once per process. Raises a helpful error if train.py was not run."""
    # Check a condition before running the guarded code.
    if not MODEL_PATH.exists():
        # Raise an error so failures are explicit and traceable.
        raise FileNotFoundError(
            # Build a helpful error message telling the user to train the model first.
            f"Model not found at {MODEL_PATH}. Run `python train.py` first."
        # Close the tuple, list or call that was opened above.
        )
    # Return the computed value to the caller.
    return joblib.load(MODEL_PATH)
# (blank line separates logical blocks)

# (blank line separates logical blocks)

# Define a function that keeps this step reusable and testable.
def clean_text(raw: str, source: str = "sms") -> str:
    # Function docstring: state that this helper standardises both SMS and email text.
    """Normalise SMS or email text (including international/English emails)."""
    # Begin with the untouched message so normalisation starts from the original input.
    text = raw
# (blank line separates logical blocks)

    # Check a condition before running the guarded code.
    if source == "email":
        # Split pasted email text into individual lines for header inspection.
        lines = raw.splitlines()
        # Initialise an empty subject in case the email has no Subject line.
        subject = ""
        # Create a list that will collect the actual message body lines.
        body_lines: list[str] = []
        # Start in header mode so leading header lines can be filtered out.
        header_mode = True
        # Loop over a collection to process each item.
        for line in lines:
            # Remove surrounding whitespace so comparisons are reliable.
            stripped = line.strip()
            # Check a condition before running the guarded code.
            if header_mode:
                # Check a condition before running the guarded code.
                if stripped == "":
                    # Leave header mode because the first blank line marks the start of the body.
                    header_mode = False
                    # Skip the rest of this loop iteration and move to the next line or term.
                    continue
                # Check a condition before running the guarded code.
                if stripped.lower().startswith("subject:"):
                    # Extract everything after 'Subject:' as the email subject.
                    subject = stripped.split(":", 1)[1].strip()
                    # Skip the rest of this loop iteration and move to the next line or term.
                    continue
                # Inline note explaining the intent of the code that follows.
                # Skip common raw header/date/recipient lines pasted from emails.
                # Check a condition before running the guarded code.
                if _HEADER_RE.match(stripped) or _DATE_LINE_RE.match(stripped):
                    # Skip the rest of this loop iteration and move to the next line or term.
                    continue
                # Check a condition before running the guarded code.
                if stripped.lower() in {"to", "cc", "bcc"}:
                    # Skip the rest of this loop iteration and move to the next line or term.
                    continue
                # Leave header mode because the first blank line marks the start of the body.
                header_mode = False
            # Keep this line as part of the message body.
            body_lines.append(line)
        # Rebuild the text from the subject plus the retained body lines.
        text = subject + "\n" + "\n".join(body_lines)
# (blank line separates logical blocks)

    # Replace HTML tags with spaces so markup does not become features.
    text = re.sub(r"<[^>]+>", " ", text)                 # HTML tags
    # Replace every URL with the single token URL to avoid thousands of unique links.
    text = re.sub(r"http\S+|www\.\S+", " URL ", text)    # links
    # Replace email addresses with the token EMAIL to standardise contact details.
    text = re.sub(r"\S+@\S+", " EMAIL ", text)           # email addresses
    # Replace Pakistani mobile numbers with the token PHONE.
    text = re.sub(r"\b03\d{2}[- ]?\d{7}\b", " PHONE ", text)  # PK mobile numbers
    # Replace remaining digits with the token NUM to keep money context but drop exact amounts.
    text = re.sub(r"\d+", " NUM ", text)                 # other numbers
    # Collapse whitespace, trim ends and lowercase so equivalent text maps to the same features.
    text = re.sub(r"\s+", " ", text).strip().lower()
    # Return the computed value to the caller.
    return text
# (blank line separates logical blocks)

# (blank line separates logical blocks)

# Define a function that keeps this step reusable and testable.
def top_terms(cleaned: str, k: int = 5) -> list[str]:
    # Function docstring: describe the legacy helper that returns spam-side terms.
    """Words in this message that push the model most towards 'spam'."""
    # Fetch the cached fitted pipeline instead of reloading it from disk.
    pipe = load_pipeline()
    # Guard this block against expected runtime errors.
    try:
        # Pull the fitted vectoriser out of the pipeline so its vocabulary can be inspected.
        vec = pipe.named_steps["tfidf"]
        # Pull the fitted classifier out of the pipeline so its coefficients can be inspected.
        clf = pipe.named_steps["clf"]
        # List class labels in the order used by the classifier's internal arrays.
        classes = list(clf.classes_)
        # Check a condition before running the guarded code.
        if "spam" not in classes or "ham" not in classes:
            # Return the computed value to the caller.
            return []
# (blank line separates logical blocks)

        # Inline note explaining the intent of the code that follows.
        # Works for both Naive Bayes (feature_log_prob_) and Logistic Regression (coef_).
        # Check a condition before running the guarded code.
        if hasattr(clf, "feature_log_prob_"):
            # For Naive Bayes, take the log probability of each feature under the spam class.
            spam_score = clf.feature_log_prob_[classes.index("spam")]
            # For Naive Bayes, take the log probability of each feature under the ham class.
            ham_score = clf.feature_log_prob_[classes.index("ham")]
            # Compute how much each feature favours spam over ham.
            log_ratio = spam_score - ham_score
        # Handle the next alternative condition.
        elif hasattr(clf, "coef_"):
            # For Logistic Regression, take the single coefficient array from the binary classifier.
            coef = clf.coef_[0]
            # Check a condition before running the guarded code.
            if classes.index("spam") == 0:
                # Flip the sign when spam is stored as class 0 so positive still means spam evidence.
                log_ratio = -coef
            # Handle the remaining branch of this decision.
            else:
                # Use the coefficient array directly when spam is stored as the second class.
                log_ratio = coef
        # Handle the remaining branch of this decision.
        else:
            # Return the computed value to the caller.
            return []
# (blank line separates logical blocks)

        # Transform this one message into TF-IDF weights and take its single row.
        weights = vec.transform([cleaned]).toarray()[0]
        # Multiply evidence direction by this message's weight to get per-term contributions.
        scores = log_ratio * weights
        # Build a reverse map from feature index back to the original term name.
        inverse = {index: word for word, index in vec.vocabulary_.items()}
        # Get the indices of the k largest scores in descending order.
        ranked = scores.argsort()[-k:][::-1]
        # Create the output list that will hold the selected spam-side terms.
        terms = []
        # Loop over a collection to process each item.
        for i in ranked:
            # Convert the numpy index to a plain Python integer.
            idx = int(i)
            # Check a condition before running the guarded code.
            if weights[idx] <= 0:
                # Skip the rest of this loop iteration and move to the next line or term.
                continue
            # Translate the feature index back into its readable word or phrase.
            term = inverse[idx]
            # Check a condition before running the guarded code.
            if term.isdigit() or term in {"num", "url", "email", "phone"}:
                # Skip the rest of this loop iteration and move to the next line or term.
                continue
            # Add the term to the result list.
            terms.append(term)
            # Check a condition before running the guarded code.
            if len(terms) == k:
                # Stop the loop because the requested number of terms has been collected.
                break
        # Return the computed value to the caller.
        return terms
    # Catch an expected error and handle it gracefully.
    except (KeyError, AttributeError, ValueError):
        # Return the computed value to the caller.
        return []
# (blank line separates logical blocks)

# (blank line separates logical blocks)

# Define a function that keeps this step reusable and testable.
def term_contributions(cleaned: str, k: int = 6) -> list[dict]:
    #     # Docstring describes the purpose of this block.
    """Terms in this message with their signed model contribution.

    #     @DOCSTR
    Positive score pushes toward spam, negative toward ham. Unlike top_terms(),
    #     @DOCSTR
    this surfaces both directions so the UI can show real model evidence.
    #     @DOCSTR
    """
    # Fetch the cached fitted pipeline instead of reloading it from disk.
    pipe = load_pipeline()
    # Guard this block against expected runtime errors.
    try:
        # Pull the fitted vectoriser out of the pipeline so its vocabulary can be inspected.
        vec = pipe.named_steps["tfidf"]
        # Pull the fitted classifier out of the pipeline so its coefficients can be inspected.
        clf = pipe.named_steps["clf"]
        # List class labels in the order used by the classifier's internal arrays.
        classes = list(clf.classes_)
        # Check a condition before running the guarded code.
        if "spam" not in classes or "ham" not in classes:
            # Return the computed value to the caller.
            return []
# (blank line separates logical blocks)

        # Check a condition before running the guarded code.
        if hasattr(clf, "feature_log_prob_"):
            # For Naive Bayes, compute the spam-versus-ham log-ratio for every feature.
            log_ratio = clf.feature_log_prob_[classes.index("spam")] - clf.feature_log_prob_[classes.index("ham")]
        # Handle the next alternative condition.
        elif hasattr(clf, "coef_"):
            # Carry out this statement as part of the surrounding logic.
            log_ratio = clf.coef_[0]
            # Check a condition before running the guarded code.
            if classes.index("spam") == 0:
                # Carry out this statement as part of the surrounding logic.
                log_ratio = -log_ratio
        # Handle the remaining branch of this decision.
        else:
            # Return the computed value to the caller.
            return []
# (blank line separates logical blocks)

        # Transform this one message into TF-IDF weights and take its single row.
        weights = vec.transform([cleaned]).toarray()[0]
        # Multiply evidence direction by this message's weight to get per-term contributions.
        scores = log_ratio * weights
        # Build a reverse map from feature index back to the original term name.
        inverse = {index: word for word, index in vec.vocabulary_.items()}
        # Keep only features that actually occur in this message.
        active = [i for i in range(len(scores)) if weights[i] > 0]
        # Order active terms by the strength of their evidence, ignoring direction.
        active.sort(key=lambda i: abs(scores[i]), reverse=True)
# (blank line separates logical blocks)

        # Create the output list that will hold term/score dictionaries.
        result: list[dict] = []
        # Loop over a collection to process each item.
        for index in active:
            # Look up the term name and use an empty string if the index is missing.
            term = inverse.get(int(index), "")
            # Check a condition before running the guarded code.
            if not term or term.isdigit() or term in {"num", "url", "email", "phone"}:
                # Skip the rest of this loop iteration and move to the next line or term.
                continue
            # Store the term together with its rounded signed contribution score.
            result.append({"term": term, "score": round(float(scores[index]), 4)})
            # Check a condition before running the guarded code.
            if len(result) == k:
                # Stop the loop because the requested number of terms has been collected.
                break
        # Return the computed value to the caller.
        return result
    # Catch an expected error and handle it gracefully.
    except (KeyError, AttributeError, ValueError):
        # Return the computed value to the caller.
        return []
# (blank line separates logical blocks)

# (blank line separates logical blocks)

# Define a function that keeps this step reusable and testable.
def predict(text: str, source: str = "sms") -> dict:
    # Function docstring: state that this is the main inference entry point.
    """Return the verdict, probability, confidence and model-derived terms."""
    # Fetch the cached fitted pipeline instead of reloading it from disk.
    pipe = load_pipeline()
    # Normalise the incoming message using the appropriate SMS or email branch.
    cleaned = clean_text(text, source)
    # Ask the classifier for probabilities and take the row for this single message.
    probabilities = pipe.predict_proba([cleaned])[0]
    # Carry out this statement as part of the surrounding logic.
    classes = list(pipe.classes_)
    # Find which probability column belongs to the spam class.
    spam_index = classes.index("spam") if "spam" in classes else len(classes) - 1
    # Extract the spam probability as a plain Python float.
    spam_probability = float(probabilities[spam_index])
# (blank line separates logical blocks)

    # Inline note explaining the intent of the code that follows.
    # Light, explainable guardrail for common automated/transactional false positives.
    # Lowercase the original text so ham/spam cue matching is case-insensitive.
    raw_low = text.lower()
    # Count how many legitimate-message cue phrases appear in the raw text.
    ham_hits = sum(1 for h in HAM_HINTS if h in raw_low)
    # Count how many scam cue phrases appear in the raw text.
    spam_hits = sum(1 for s in SPAM_HINTS if s in raw_low)
    # Check a condition before running the guarded code.
    if ham_hits >= 2 and spam_hits == 0:
        # Cap a strong ham-cue message at 0.35 so it cannot cross the 0.60 spam threshold.
        spam_probability = min(spam_probability, 0.35)
    # Handle the next alternative condition.
    elif ham_hits >= 1 and spam_hits == 0 and spam_probability < 0.85:
        # Apply a milder 0.45 cap when there is one ham cue and no spam cues.
        spam_probability = min(spam_probability, 0.45)
# (blank line separates logical blocks)

    # Read the decision threshold that was saved during training.
    threshold = get_threshold()
    # Return the computed value to the caller.
    return {
        # Apply the threshold to convert probability into a final verdict.
        "label": "spam" if spam_probability >= threshold else "ham",
        # Return the probability rounded for display and stable history caching.
        "spam_probability": round(spam_probability, 4),
        # Return distance from a coin flip as the confidence value.
        "confidence": round(max(spam_probability, 1 - spam_probability), 4),
        # Return the threshold so the UI can place the meter marker correctly.
        "threshold": round(threshold, 2),
        # Include legacy spam-side terms for compatibility with older history entries.
        "top_terms": top_terms(cleaned),
        # Include signed term contributions that power the MODEL SIGNALS chips.
        "term_scores": term_contributions(cleaned),
    # Close the dictionary or code block that was opened earlier.
    }
