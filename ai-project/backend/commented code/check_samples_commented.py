# # Module docstring describes the batch check and shows the command to run it.
"""Batch-check data/test_samples.csv against the current trained model.

Run from the backend folder:
    #     @DOCSTR
    .\\.venv\\Scripts\\python.exe check_samples.py
"""
# Enable postponed annotation evaluation for cleaner type hints.
from __future__ import annotations
# (blank line separates logical blocks)

# Import csv to read the labelled sample file.
import csv
# Import Path to locate the sample file next to this script.
from pathlib import Path
# (blank line separates logical blocks)

# Reuse the exact predict function used by the web backend.
from model import predict
# (blank line separates logical blocks)

# Anchoring the path to this file makes the check work from any directory.
# Locate data/test_samples.csv relative to this script.
CSV_PATH = Path(__file__).resolve().parent / "data" / "test_samples.csv"
# (blank line separates logical blocks)

# (blank line separates logical blocks)

# Define the batch checking routine.
def main() -> None:
    # Open the sample file as UTF-8 text with newline handling suited to CSV.
    with CSV_PATH.open(encoding="utf-8", newline="") as handle:
        # Read all rows into dictionaries keyed by the CSV header names.
        rows = list(csv.DictReader(handle))
# (blank line separates logical blocks)

    # Exit early with a message when the file has no data rows.
    if not rows:
        # Report that nothing was found.
        print(f"No rows found in {CSV_PATH}")
        # Stop because there is nothing to check.
        return
# (blank line separates logical blocks)

    # Keep a count of correct predictions for the final summary.
    matched = 0
    # Number each row from one so the printed report is easy to read.
    for index, row in enumerate(rows, start=1):
        # Read and normalise the expected label from the CSV.
        expected = row["label"].strip().lower()
        # Call the real prediction function with both text and source.
        result = predict(row["text"], row["source"].strip().lower())
        # Extract the predicted label from the returned dictionary.
        got = result["label"]
        # Compare prediction with expectation.
        ok = got == expected
        # Increment the success counter when the prediction matched.
        matched += int(ok)
# (blank line separates logical blocks)

        # The multi-line print is bundled into one formatted report row per sample.
        # Start a formatted status line for this sample.
        print(
            # Show the row number and padded source label.
            f"{index:02d} [{row['source']:5}] "
            # Show the padded expected and predicted labels side by side.
            f"expected={expected:4} got={got:4} "
            # Show the spam probability to three decimals.
            f"p(spam)={result['spam_probability']:.3f} "
            # Append OK or MISS depending on the comparison result.
            f"{'OK' if ok else 'MISS'}"
        # Close the print call.
        )
        # Flatten embedded newlines so the snippet stays on one line.
        snippet = row["text"].replace("\n", " ")
        # Print a short preview of the tested message text.
        print(f"    {snippet[:110]}")
# (blank line separates logical blocks)

    # Print how many samples matched, both as a count and a percentage.
    print(f"\n{matched}/{len(rows)} matched ({matched / len(rows):.0%})")
# (blank line separates logical blocks)

# (blank line separates logical blocks)

# Run main only when this file is executed as a script.
if __name__ == "__main__":
    # Call the batch checking routine.
    main()
