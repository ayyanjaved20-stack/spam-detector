# # Module docstring explains the one-time download and the force option.
"""Download the three public datasets used to train the spam detector.

Run once:  python download_data.py
Force re-download:  python download_data.py --force
"""
# Enable postponed annotation evaluation for cleaner type hints.
from __future__ import annotations
# (blank line separates logical blocks)

# Import sys to inspect command-line arguments.
import sys
# Import urllib.request for plain HTTP downloads without extra dependencies.
import urllib.request
# Import zipfile to unpack the Enron archive.
import zipfile
# Import Path to place downloads next to this script.
from pathlib import Path
# (blank line separates logical blocks)

# Paths are anchored to the script so downloads land in backend/data regardless of cwd.
# Resolve this file's own folder as the path base.
ROOT = Path(__file__).resolve().parent
# Point to the data directory inside the backend folder.
DATA = ROOT / "data"
# Create the data directory if a fresh checkout does not contain it yet.
DATA.mkdir(parents=True, exist_ok=True)
# (blank line separates logical blocks)

# Each key is the local filename and each value is its public source URL.
# Open the source catalogue dictionary.
SOURCES = {
    # Note that the Pakistan dataset mixes English, Roman Urdu and Urdu messages.
    # Pakistan-focused SMS/scam messages (English + Roman Urdu + Urdu, mixed)
    # Name the local file for the Pakistan SMS dataset.
    "pakistan_sms.xlsx": (
        # Start the first half of its raw GitHub URL.
        "https://raw.githubusercontent.com/saifkhandev/Muhafiz-AI/main/"
        # Finish the path to the workbook in that repository.
        "scam_detection/data/scam_messages_dataset.xlsx"
    # Close the Pakistan URL tuple.
    ),
    # Note the licence and DOI of the Roman Urdu phishing dataset.
    # Roman Urdu phishing SMS, UMT Lahore (CC BY 4.0, DOI 10.5281/zenodo.21810885)
    # Name the local file for that dataset.
    "roman_urdu_phishing.xlsx": (
        # Start the Zenodo record URL.
        "https://zenodo.org/records/21810885/files/"
        # Finish the URL with the download query flag.
        "phishing_dataset_1000.xlsx?download=1"
    # Close the Roman Urdu URL tuple.
    ),
    # Note that Enron provides international email coverage.
    # Enron-Spam emails, preprocessed into one CSV (international email coverage)
    # Name the local zip file for Enron email data.
    "enron_spam_data.zip": (
        # Give the raw GitHub URL of the preprocessed zip.
        "https://github.com/MWiechmann/enron_spam_data/raw/master/enron_spam_data.zip"
    # Close the source catalogue.
    ),
# Close the dictionary or code block that was opened earlier.
}
# (blank line separates logical blocks)

# (blank line separates logical blocks)

# Skip when the destination exists and is non-empty to avoid re-downloading.
def download(url: str, dest: Path) -> None:
    # Tell the user the download was skipped.
    if dest.exists() and dest.stat().st_size > 0:
        # Leave the function early because no network call is needed.
        print(f"skip   {dest.name} (already exists)")
        # Announce which file is being fetched.
        return
    # A custom user agent identifies the project politely to the dataset host.
    # Start building a request instead of calling urlopen with a bare URL.
    print(f"fetch  {dest.name} ...")
    # Attach the user agent header to the request.
    request = urllib.request.Request(
        # Close the request constructor.
        url, headers={"User-Agent": "spam-detector-semester-project/1.0"}
    # A long timeout tolerates slow academic hosts while still failing eventually.
    # Open the URL with a 180-second timeout and a binary output file together.
    )
    # Write the entire response body to the destination file.
    with urllib.request.urlopen(request, timeout=180) as response, open(dest, "wb") as out:
        # Report the final byte count so the student can confirm a complete download.
        out.write(response.read())
    # Print progress or results so a student can follow execution.
    print(f"done   {dest.name} ({dest.stat().st_size:,} bytes)")
# (blank line separates logical blocks)

# (blank line separates logical blocks)

# Detect whether the user passed the force flag.
def main() -> None:
    # Detect whether the user passed --force to re-download existing files.
    force = "--force" in sys.argv
# (blank line separates logical blocks)

    # Build the full destination path inside the data folder.
    for name, url in SOURCES.items():
        # Delete an existing file only when force was requested.
        dest = DATA / name
        # Download this source into its destination.
        if force and dest.exists():
            # Delete the existing file so the forced download starts from a clean state.
            dest.unlink()
        # Point to the downloaded Enron zip file.
        download(url, dest)
# (blank line separates logical blocks)

    # Create the extraction folder if needed.
    zip_path = DATA / "enron_spam_data.zip"
    # Unzip only when no CSV is present yet.
    out_dir = DATA / "enron_spam_data"
    # Announce the extraction step.
    out_dir.mkdir(exist_ok=True)
    # Open the zip archive as a context manager so it closes reliably.
    if not list(out_dir.rglob("*.csv")):
        # Extract every member into the dedicated folder.
        print(f"unzip  {zip_path.name} ...")
        # Open a resource safely and close it automatically.
        with zipfile.ZipFile(zip_path) as archive:
            # List the extracted CSV files in sorted order for predictable output.
            archive.extractall(out_dir)
# (blank line separates logical blocks)

    # Collect extracted CSV files in sorted order so the chosen input is predictable.
    csv_files = sorted(out_dir.rglob("*.csv"))
    # Announce the training inputs that are now ready.
    if not csv_files:
        # Print each downloaded workbook and the first extracted CSV.
        raise RuntimeError(f"No CSV found inside {zip_path.name}")
# (blank line separates logical blocks)

    # Print progress or results so a student can follow execution.
    print("\nReady. Training inputs:")
    # Loop over a collection to process each item.
    for path in [DATA / "pakistan_sms.xlsx", DATA / "roman_urdu_phishing.xlsx", csv_files[0]]:
        # Run main only when this file is executed as a script.
        print(f"  {path}")
    # Call the download orchestration function.
    print(f"  {DATA / 'local_pakistani_emails.csv'}")
# (blank line separates logical blocks)

# (blank line separates logical blocks)

# Run this code only when the file is executed directly.
if __name__ == "__main__":
    # Run this script's main() function when the file is executed directly.
    main()
