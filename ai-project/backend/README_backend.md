# SpamShield — backend (local only)

Runs entirely on your laptop. No cloud, no API keys, no external calls at runtime.
You train the model yourself — no pretrained model is shipped.

## 1. Install Python (one time)

Install **Python 3.10+** from https://www.python.org/downloads/ and tick
**“Add Python to PATH”** during installation.

> On this machine the `py` launcher currently points to a missing
> `C:\Python314\python.exe`. Reinstalling Python with “Add to PATH” fixes it.

## 2. Setup

Double-click **`setup.bat`**. It creates `.venv` and installs `requirements.txt`.

## 3. Download datasets

```bat
python download_data.py
```

This fetches and prepares:

| File | What it is | Citation / licence |
|---|---|---|
| `data/pakistan_sms.xlsx` | 868 Pakistan scam/safe messages (English + Roman Urdu + Urdu) | Muhafiz-AI, MIT |
| `data/roman_urdu_phishing.xlsx` | 1,000 Roman Urdu phishing/legit SMS | Ghufran Siddiq, UMT — DOI `10.5281/zenodo.21810885`, CC BY 4.0 |
| `data/enron_spam_data.zip` → `data/enron_spam_data/` | 33,716 international emails (we sample 2,000) | Enron-Spam, GPL-3.0 |
| `data/local_pakistani_emails.csv` | 40 locally written Pakistani emails (generated for you) | Your own |

## 4. Train the model

```bat
python train.py
```

Writes:
- `models/spam_model.joblib` — the trained TF-IDF + Naive Bayes pipeline
- `models/metrics.json` — accuracy, precision, recall, F1, confusion matrix, per-source accuracy

The console prints a classification report. Copy those numbers into your report.

## 5. Run the API

```bat
run_backend.bat
```

- Backend: http://127.0.0.1:8000
- Interactive docs: http://127.0.0.1:8000/docs
- `GET /health` — is the model loaded?
- `GET /model-info` — training metrics
- `POST /predict` — `{"text": "...", "source": "sms" | "email"}`

Example response:

```json
{
  "label": "spam",
  "spam_probability": 0.9631,
  "confidence": 0.9631,
  "top_terms": ["otp", "bisp", "fee", "url", "cnic"]
}
```

Example request with PowerShell:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/predict -Method Post `
  -ContentType "application/json" `
  -Body '{"text":"BISP payment approved. OTP share karein.","source":"email"}'
```

## Notes for the report

- **Supervised learning:** labeled data → `TfidfVectorizer` → `MultinomialNB`.
- **Pakistan coverage:** local SMS + Roman Urdu + 40 local email examples, oversampled 3×.
- **International coverage:** 2,000 Enron emails (1,000 spam + 1,000 ham).
- **Leakage control:** exact duplicates removed, and oversampling happens *after* the train/test split.
- **Limitation:** the Zenodo dataset contains repeated templates; exact dedup helps but does not fully remove template similarity. Mention this honestly.

## Verified results on this machine

After running the full pipeline with all three datasets:

```text
Combined rows: 3908  (email 2040, sms 1868)
By label: ham 2041, spam 1867
Train rows: 6176 (Pakistan SMS oversampled x3), Test rows: 782

              precision  recall  f1-score
ham               0.88    0.91     0.90
spam              0.90    0.86     0.88
accuracy                           0.89

Confusion matrix [ham, spam]: [[373, 35], [52, 322]]
Per-source accuracy: email 0.8178 | sms 0.9796
```

Live smoke tests through `POST /predict`:

| Input | source | Result |
|---|---|---|
| `Aap ko Rs. 50,000 ka inaam mila hai. OTP share karein.` | sms | spam, 0.9976 |
| `Subject: You have won a lottery ... send a processing fee` | email | spam, 0.9982 |
| `Easypaisa: Rs. 2,500 ka transaction Ali ko ho gaya. Txn # 12345.` | email | ham, 0.4649 |
| `Bhai kal 3 baje office mein milte hain.` | sms | ham, 0.0378 |

`get /health` returned `"model_ready": true`.

### PowerShell tip

In PowerShell, run local scripts with `.\`, e.g. `.\run_backend.bat` (plain `run_backend.bat` is not found by default).

The launcher uses `python -m uvicorn` rather than a bare `uvicorn` command, because the venv inherits uvicorn from Anaconda as a module without creating a `.exe` on PATH.

### Environment note

This machine's `py` launcher points to a missing `C:\Python314\python.exe`. The working interpreter is `C:\anaconda\python.exe`. `setup.bat` detects this and builds `.venv` with `--system-site-packages`, so scikit-learn/pandas are inherited instead of being recompiled.

## Next

The UI is intentionally not built yet. We will decide its look after this backend is confirmed working.
