# # Module docstring names the three dataset families combined for training.
"""Train the spam classifier on Pakistan SMS + Roman Urdu + international email.

You run this yourself. It writes:
    #     @DOCSTR
    models/spam_model.joblib   (the supervised model)
    #     @DOCSTR
    models/metrics.json        (numbers for your report)

Usage:  python train.py
"""
# Enable postponed annotation evaluation so forward references in type hints are safe.
from __future__ import annotations
# (blank line separates logical blocks)

# Import JSON support for writing the metrics report file.
import json
# Import regular expressions for whitespace cleanup in the deduplication key.
import re
# Import Path for dataset and output paths anchored to this file.
from pathlib import Path
# (blank line separates logical blocks)

# Import joblib to serialise the fitted pipeline for the inference server.
import joblib
# Import pandas to load and reshape the Excel and CSV datasets.
import pandas as pd
# Import TF-IDF vectorisation to turn text into numeric features.
from sklearn.feature_extraction.text import TfidfVectorizer
# Import the report and matrix functions used to evaluate the held-out set.
from sklearn.metrics import classification_report, confusion_matrix
# Import the splitter that creates reproducible stratified train and test sets.
from sklearn.model_selection import train_test_split
# Import logistic regression as the supervised classifier.
from sklearn.linear_model import LogisticRegression
# Import the pipeline that chains vectorisation and classification into one object.
from sklearn.pipeline import Pipeline
# (blank line separates logical blocks)

# Anchoring every path to this file makes training work from any working directory.
# Resolve this file's own folder as the base for data and model paths.
ROOT = Path(__file__).resolve().parent
# Point to the folder containing all raw datasets.
DATA = ROOT / "data"
# Point to the folder where the model and metrics will be saved.
MODELS = ROOT / "models"
# Name the serialised pipeline file consumed by model.py.
MODEL_PATH = MODELS / "spam_model.joblib"
# Name the JSON metrics file consumed by the UI and model.py.
METRICS_PATH = MODELS / "metrics.json"
# (blank line separates logical blocks)

# Different public datasets spell spam and ham labels differently.
# A single map normalises all of them to exactly two classes before training.
# Open the dictionary that maps raw label spellings to canonical classes.
LABEL_MAP = {
    # Treat spam, scam, phishing, fraud and positive flags as spam.
    "spam": "spam", "scam": "spam", "phishing": "spam", "fraud": "spam",
    # Treat ham, safe, legitimate, clean and negative flags as ham.
    "1": "spam", "true": "spam", "yes": "spam",
    # Close the label map.
    "ham": "ham", "safe": "ham", "legitimate": "ham", "legit": "ham",
    # Map additional ham synonyms to the canonical ham label.
    "clean": "ham", "not spam": "ham", "non spam": "ham", "nonspam": "ham",
    # Map numeric and boolean-style ham labels to the canonical ham label.
    "0": "ham", "false": "ham", "no": "ham",
# Define a helper that converts one raw dataset label into a canonical class.
}
# (blank line separates logical blocks)

# (blank line separates logical blocks)

# Define a function that keeps this step reusable and testable.
def normalise_label(value) -> str | None:
    # Define a helper that finds which column in a dataset carries the label.
    return LABEL_MAP.get(str(value).strip().lower())
# (blank line separates logical blocks)

# (blank line separates logical blocks)

# Exact header matches are trusted first so category columns cannot win accidentally.
# Try the most common exact label header names.
def pick_label_column(frame: pd.DataFrame) -> str:
    # Inspect every column in the dataset.
    columns = list(frame.columns)
# (blank line separates logical blocks)

    # Return the first exact match found.
    # 1) Exact names win (e.g. Muhafiz has both "Label" and "Scam Category").
    # Loop over a collection to process each item.
    for key in ("label", "labels", "spam/ham", "target", "class"):
        # Substring matching handles headers like Spam or Ham when exact matching failed.
        # Try looser names but exclude category and type columns.
        for column in columns:
            # Inspect every column again with the looser names.
            if str(column).strip().lower() == key:
                # Lowercase the column name once for all substring tests.
                return column
# (blank line separates logical blocks)

    # Return the first suitable substring match.
    # 2) Substring match, but never a category/type column.
    # Loop over a collection to process each item.
    for key in ("label", "spam/ham", "class", "target"):
        # Last resort: a small set of values that all map to spam or ham is likely a label.
        # Inspect every column a third time.
        for column in columns:
            # Collect the distinct non-null string values in the column.
            lowered = str(column).lower()
            # Accept only small cardinality columns whose values all normalise to a class.
            if key in lowered and "categor" not in lowered and "type" not in lowered:
                # Return the inferred label column.
                return column
# (blank line separates logical blocks)

    # Inline note explaining the intent of the code that follows.
    # 3) Fallback: small-cardinality column whose values all map to spam/ham.
    # Loop over a collection to process each item.
    for column in columns:
        # Define a helper that finds the text column, honouring a preferred keyword when given.
        values = frame[column].dropna().astype(str).unique()
        # Candidate columns must hold text rather than numbers or labels.
        # Collect object and string dtype columns as possible text sources.
        if 0 < len(values) <= 8 and all(normalise_label(v) for v in values):
            # Stop immediately when there is no text-like column at all.
            return column
# (blank line separates logical blocks)

    # Inspect each candidate for the preferred keyword.
    raise ValueError(f"No label column found. Columns: {columns}")
# (blank line separates logical blocks)

# (blank line separates logical blocks)

# Return a column whose name mentions text, message, sms, content or body.
def pick_text_column(frame: pd.DataFrame, prefer: tuple[str, ...] = ()) -> str:
    # Fall back to the column whose average string length is largest.
    candidates = [
        # Iterate over every column name in the dataframe.
        c for c in frame.columns
        # Check a condition before running the guarded code.
        if frame[c].dtype == object or pd.api.types.is_string_dtype(frame[c])
    # Define a loader that reshapes one Excel dataset into the common three-column format.
    ]
    # Read the workbook into a pandas DataFrame.
    if not candidates:
        # Show the discovered headers so the student can verify column detection.
        raise ValueError(f"No text column found. Columns: {list(frame.columns)}")
    # Detect the text column with the caller's preference.
    for keyword in prefer:
        # Detect the label column with the general heuristics.
        for column in candidates:
            # Log which columns were chosen for transparency.
            if keyword in str(column).lower():
                # Every dataset is projected into text, label and source so they can be concatenated safely.
                # Start building the normalised frame.
                return column
    # Copy the text column as strings.
    for column in candidates:
        # Map raw labels through the normaliser, leaving unknown values as missing.
        lowered = str(column).lower()
        # Record which dataset family this row came from.
        if any(key in lowered for key in ("text", "message", "sms", "content", "body")):
            # Finish and return the normalised frame.
            return column
    # Return the computed value to the caller.
    return max(candidates, key=lambda c: frame[c].dropna().astype(str).str.len().mean())
# (blank line separates logical blocks)

# (blank line separates logical blocks)

# Find every CSV produced by unzipping the Enron archive.
def load_xlsx(path: Path, source: str, prefer: tuple[str, ...] = ()) -> pd.DataFrame:
    # Fail with a clear instruction when download_data.py has not been run.
    frame = pd.read_excel(path)
    # Read the first discovered CSV file.
    print(f"  {path.name} columns: {list(frame.columns)}")
    # Strip whitespace from every header to make later matching reliable.
    text_col = pick_text_column(frame, prefer)
    # Find a subject-like column, defaulting to empty string.
    label_col = pick_label_column(frame)
    # The message lookup spans multiple physical lines but stays one expression.
    # Start searching for a message or body column.
    print(f"    text='{text_col}'  label='{label_col}'")
    # Supply the generator expression that checks both names.
    return pd.DataFrame({
        # Close the search and use an empty string when nothing matches.
        "text": frame[text_col].astype(str),
        # Start with no known label column.
        "label": frame[label_col].map(normalise_label),
        # Inspect each normalised header name.
        "source": source,
    # Remove spaces so variants like Spam Ham are recognised.
    })
# (blank line separates logical blocks)

# (blank line separates logical blocks)

# Stop searching once a label column is found.
def load_enron() -> pd.DataFrame:
    # Fall back to the generic label detector when no obvious header exists.
    csv_files = sorted((DATA / "enron_spam_data").rglob("*.csv"))
    # Check a condition before running the guarded code.
    if not csv_files:
        # Combine subject and message text with a newline so both are learned.
        raise FileNotFoundError("Enron CSV missing. Run `python download_data.py` first.")
    # Normalise the detected label column values.
    frame = pd.read_csv(csv_files[0])
    # Mark every Enron row as email for later per-source reporting.
    frame = frame.rename(columns={c: c.strip() for c in frame.columns})
# Capping each class at 1000 keeps training fast and roughly balanced.
# (blank line separates logical blocks)

    # Iterate over the ham and spam groups.
    subject = next((c for c in frame.columns if "subject" in c.lower()), "")
    # Sample at most 1000 rows with a fixed seed for reproducibility.
    message = next(
        # Join the balanced groups into one frame with fresh indexes.
        (c for c in frame.columns if "message" in c.lower() or "body" in c.lower()), ""
    # Report the original columns and the resulting sampled size.
    )
    # Return only the three common columns.
    label_col = None
    # Loop over a collection to process each item.
    for column in frame.columns:
        # Normalise a column name for comparing against known label names.
        lowered = column.lower().replace(" ", "")
        # Define the training entry point that builds, evaluates and saves the model.
        if "spam/ham" in lowered or lowered in ("label", "class", "spam"):
            # Announce the start of dataset loading.
            label_col = column
            # Collect normalised datasets in this list.
            break
    # Check a condition before running the guarded code.
    if label_col is None:
        # Load the two Pakistan focused Excel files one by one.
        label_col = pick_label_column(frame)
# (blank line separates logical blocks)

    # Load it when the file exists, preferring the raw text column.
    subject_text = frame[subject].fillna("").astype(str) if subject else ""
    # Warn and continue when the file is absent so other data can still train.
    message_text = frame[message].fillna("").astype(str) if message else ""
    # Combine subject and body into one text field so the subject influences the model.
    frame["text"] = subject_text + "\n" + message_text
    # Add the international Enron emails when the extracted folder exists.
    frame["label"] = frame[label_col].map(normalise_label)
    # Warn that the folder is missing when download_data.py was not run.
    frame["source"] = "email"
# (blank line separates logical blocks)

    # Point to the locally authored hard negative email file.
    # 1,000 spam + 1,000 ham keeps training fast and roughly balanced.
    # Add those hand-curated emails when present.
    pieces = []
    # Warn when the local file is absent.
    for _, group in frame.groupby("label"):
        # Sample at most 1,000 emails per class with a fixed seed for balance and repeatability.
        pieces.append(group.sample(min(len(group), 1000), random_state=42))
    # Stop when not a single dataset was available to train on.
    frame = pd.concat(pieces, ignore_index=True)
    # Print progress or results so a student can follow execution.
    print(f"  Enron columns: {list(frame.columns)} -> sampled {len(frame)} emails")
    # Concatenate all available datasets into one training frame.
    return frame[["text", "label", "source"]]
# (blank line separates logical blocks)

# (blank line separates logical blocks)

# Remove very short messages that cannot carry useful signal.
def main() -> None:
    # Build a lowercase whitespace-normalised key for exact duplicate detection.
    print("Loading datasets...")
    # Remember the row count before deduplication.
    parts: list[pd.DataFrame] = []
# (blank line separates logical blocks)

    # Print how many duplicates were removed.
    for name in ("pakistan_sms.xlsx", "roman_urdu_phishing.xlsx"):
        # Print the distribution of rows across sources.
        path = DATA / name
        # Print the distribution of rows across classes.
        if path.exists():
            # Load an SMS workbook into the combined training list.
            parts.append(load_xlsx(path, "sms", prefer=("raw",)))
        # Splitting before oversampling prevents duplicated rows from leaking into the test set.
        # Stratifying keeps the spam and ham ratio the same in both partitions.
        # Create a reproducible stratified 80/20 train and test split.
        else:
            # Print progress or results so a student can follow execution.
            print(f"  WARN {name} missing (run download_data.py)")
# International email coverage is kept, but local Pakistani patterns are emphasised.
# Oversampling SMS and local-looking emails biases the model toward this project's domain.
# (blank line separates logical blocks)

    # Build a boolean mask for emails containing Pakistan specific keywords.
    if (DATA / "enron_spam_data").exists():
        # List payment app and organisation keywords in the first string chunk.
        parts.append(load_enron())
    # List university, document and OTP keywords in the second chunk.
    else:
        # List currency and city keywords in the final chunk.
        print("  WARN Enron folder missing (run download_data.py)")
# (blank line separates logical blocks)

    # Select the local-looking email rows using that mask.
    local = DATA / "local_pakistani_emails.csv"
    # Appending the SMS frame three extra times gives SMS rows four total weights.
    # Appending the local email frame four extra times gives those rows six total weights.
    # Combine the original training rows with the oversampled subsets.
    if local.exists():
        # Close the concatenation call.
        parts.append(pd.read_csv(local))
    # Report the resulting training and test row counts with the multipliers.
    else:
        # Print progress or results so a student can follow execution.
        print("  WARN local_pakistani_emails.csv missing")
# (blank line separates logical blocks)

    # Chaining the vectoriser and classifier in one Pipeline prevents train and serve skew.
    # The saved object will accept raw text directly during inference.
    # Start the pipeline definition.
    if not parts:
        # Begin configuring the TF-IDF vectoriser step.
        raise RuntimeError("No training data found. Run `python download_data.py` first.")
# (blank line separates logical blocks)

    # Include terms seen at least once because some datasets are small.
    frame = pd.concat(parts, ignore_index=True)
    # Ignore terms appearing in more than 95 percent of documents as uninformative.
    frame = frame.dropna(subset=["text", "label"])
    # Cap the vocabulary at 80,000 features to keep the model file manageable.
    frame["text"] = frame["text"].astype(str).str.strip()
    # Strip accents so Roman Urdu spellings collapse to consistent forms.
    frame = frame[frame["text"].str.len() > 3]
    # Use sublinear term frequency so repeated words do not dominate.
    frame["key"] = frame["text"].str.lower().str.replace(r"\s+", " ", regex=True)
    # Close the vectoriser configuration.
    before = len(frame)
    # Begin configuring the logistic regression classifier.
    frame = frame.drop_duplicates(subset="key").drop(columns="key")
    # Allow up to 3000 iterations so optimisation can converge on sparse text data.
    print(f"\nCombined rows: {before} -> {len(frame)} after exact deduplication")
    # Weighting ham slightly higher reduces false positives on legitimate notifications.
    # Give ham a 1.35 class weight and spam a neutral 1.0 weight.
    print("By source:", frame["source"].value_counts().to_dict())
    # Use liblinear, a solver that works well for small sparse binary problems.
    print("By label :", frame["label"].value_counts().to_dict())
# (blank line separates logical blocks)

    # Close the pipeline definition.
    # Split BEFORE oversampling so duplicate copies never cross into the test set.
    # Fit the whole pipeline on the oversampled training text and labels.
    train_df, test_df = train_test_split(
        # Hold out 20 percent for testing while preserving the label ratio with a fixed seed.
        frame, test_size=0.2, stratify=frame["label"], random_state=42
    # A 0.60 threshold is deliberately conservative to avoid flagging real notifications.
    # The same number is stored in metrics.json and reused by model.py at prediction time.
    # Set the decision threshold and document the reason in an inline comment.
    )
# (blank line separates logical blocks)

    # List class names to locate the spam probability column.
    # Keep international coverage, but strongly emphasize Pakistani/local patterns.
    # Find the index of the spam class.
    sms_train = train_df[train_df["source"] == "sms"]
    # Extract just the spam probability column for thresholding.
    is_local_email = (train_df["source"] == "email") & train_df["text"].str.contains(
        # Carry out this statement as part of the surrounding logic.
        "easypaisa|nayapay|jazzcash|sadapay|hbl|ubl|meezan|bahria|nadra|fbr|pta|kelectric|nayatel|"
        # Apply the threshold to turn probabilities into hard labels.
        "bahria|university|student|portal|invoice|receipt|statement|tracking|delivery|order|otp|"
        # Build a dictionary-style classification report on the held-out predictions.
        "rs\\.|pkr|lahore|karachi|islamabad|pakistan",
        # Build a confusion matrix with an explicit ham then spam label order.
        case=False, na=False, regex=True
    # Close the tuple, list or call that was opened above.
    )
    # Start a dictionary that will hold accuracy for each data source.
    local_train = train_df[is_local_email]
    # Evaluate each source group separately to reveal domain shift.
    train_df = pd.concat(
        # Get spam probabilities for just this source's test rows.
        [train_df, sms_train, sms_train, local_train, local_train, local_train, local_train],
        # Apply the same threshold to this source's rows.
        ignore_index=True,
    # Resetting the index keeps the boolean comparison aligned before averaging.
    # Start storing the per-source result object.
    )
    # Record how many test rows this source contributed.
    print(
        # Compute and round the accuracy for this source.
        f"Train rows: {len(train_df)} (SMS x4, Pakistani/local email x6), Test rows: {len(test_df)}"
    # Close the per-source result object.
    )
# (blank line separates logical blocks)

    # These metrics become the student's report numbers and the website's footer values.
    # Start the metrics dictionary.
    print("\nTraining TF-IDF + Logistic Regression...")
    # Record that training completed successfully.
    pipeline = Pipeline([
        # Name the modelling approach for the report.
        ("tfidf", TfidfVectorizer(
            # Store the threshold used for every decision.
            ngram_range=(1, 2),
            # Record how many unique rows survived cleaning.
            min_df=1,
            # Record the oversampled training row count.
            max_df=0.95,
            # Record the held-out test row count.
            max_features=80_000,
            # Record how many rows came from each dataset source.
            strip_accents="unicode",
            # Store overall held-out accuracy.
            sublinear_tf=True,
        # Store spam precision, recall and F1 for the report.
        )),
        # Store spam recall on its own line for clarity in the JSON.
        ("clf", LogisticRegression(
            # Store spam F1, which the UI footer displays.
            max_iter=3000,
            # Store ham precision to show the other class's quality.
            class_weight={ "ham": 1.35, "spam": 1.0 },
            # Store the labelled confusion matrix values.
            solver="liblinear",
        # Attach the per-source breakdown computed earlier.
        )),
    # Close the metrics dictionary.
    ])
    # Fit the whole vectoriser-plus-classifier pipeline on the training texts and labels.
    pipeline.fit(train_df["text"], train_df["label"])
# (blank line separates logical blocks)

    # Serialise the fitted pipeline to the path inference code expects.
    threshold = 0.60  # conservative: reduce false positives on legit notifications
    # Write the metrics as indented UTF-8 JSON so students can read it.
    proba = pipeline.predict_proba(test_df["text"])
    # List the class labels in the order used by predict_proba.
    classes = list(pipeline.classes_)
    # Print the full human-readable classification report.
    spam_i = classes.index("spam")
    # Print the confusion matrix with its label order.
    spam_p = proba[:, spam_i]
# (blank line separates logical blocks)

    # Show where the model file was saved.
    predictions = ["spam" if p >= threshold else "ham" for p in spam_p]
    # Show where the metrics file was saved.
    report = classification_report(test_df["label"], predictions, output_dict=True, zero_division=0)
    # Build the confusion matrix and convert it to a plain nested list for JSON output.
    matrix = confusion_matrix(test_df["label"], predictions, labels=["ham", "spam"]).tolist()
# (blank line separates logical blocks)

    # Run main only when the file is executed directly, not when imported.
    per_source: dict[str, dict] = {}
    # Call the training entry point.
    for source, group in test_df.groupby("source"):
        # 
        gp = pipeline.predict_proba(group["text"])[:, spam_i]
        # Apply the same threshold to one source group to compute its accuracy.
        source_predictions = ["spam" if p >= threshold else "ham" for p in gp]
        # Start recording evaluation results for this source.
        per_source[str(source)] = {
            # Store how many test rows this source contributed.
            "n": int(len(group)),
            # Compute and round the fraction of correct predictions within this source group.
            "accuracy": round(float((pd.Series(source_predictions) == group["label"].reset_index(drop=True)).mean()), 4),
        # Close the dictionary or code block that was opened earlier.
        }
# (blank line separates logical blocks)

    # Start assembling the metrics dictionary that will be written to metrics.json.
    metrics = {
        # Record that a model has been successfully trained and saved.
        "trained": True,
        # Record the model name for display in the interface.
        "model": "TF-IDF + Logistic Regression",
        # Store the decision threshold so inference and reporting stay in sync.
        "threshold": threshold,
        # Store the number of unique rows after deduplication.
        "rows_total": int(len(frame)),
        # Store the training row count after oversampling.
        "rows_train": int(len(train_df)),
        # Store the untouched test row count.
        "rows_test": int(len(test_df)),
        # Carry out this statement as part of the surrounding logic.
        "sources": {str(k): int(v) for k, v in frame["source"].value_counts().items()},
        # Store overall accuracy from the classification report.
        "accuracy": round(report["accuracy"], 4),
        # Store spam precision so the UI can report false-alarm quality.
        "spam_precision": round(report["spam"]["precision"], 4),
        # Store spam recall so missed spam is visible.
        "spam_recall": round(report["spam"]["recall"], 4),
        # Store the spam F1 score as the balanced headline metric.
        "spam_f1": round(report["spam"]["f1-score"], 4),
        # Store ham precision to show how often legitimate mail is correctly accepted.
        "ham_precision": round(report["ham"]["precision"], 4),
        # Store the labelled confusion matrix for the drawer visualisation.
        "confusion_matrix": {"labels": ["ham", "spam"], "values": matrix},
        # Store per-source accuracy so SMS and email can be compared.
        "per_source": per_source,
    # Close the dictionary or code block that was opened earlier.
    }
# (blank line separates logical blocks)

    # Ensure the models directory exists before saving artifacts.
    MODELS.mkdir(parents=True, exist_ok=True)
    # Serialise the fitted pipeline so the API can load it without retraining.
    joblib.dump(pipeline, MODEL_PATH)
    # Write the metrics dictionary to a readable JSON file for the interface.
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
# (blank line separates logical blocks)

    # Print progress or results so a student can follow execution.
    print("\n" + classification_report(test_df["label"], predictions))
    # Print progress or results so a student can follow execution.
    print("Confusion matrix [ham, spam]:", matrix)
    # Print progress or results so a student can follow execution.
    print("Per-source accuracy:", per_source)
    # Print progress or results so a student can follow execution.
    print(f"\nSaved {MODEL_PATH}")
    # Print progress or results so a student can follow execution.
    print(f"Saved {METRICS_PATH}")
# (blank line separates logical blocks)

# (blank line separates logical blocks)

# Run this code only when the file is executed directly.
if __name__ == "__main__":
    # Run this script's main() function when the file is executed directly.
    main()
