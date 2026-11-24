# PROJECT.md — Rajput Spam Detector (SpamShield, AI Spam/Email Detector)

> **Purpose of this file**: handoff/context document for any future AI chatbot or developer. Read this first before changing code.

## 1. Project snapshot

- **Name**: Rajput Spam Detector (SpamShield, semester AI project)
- **Goal**: local, supervised-learning spam/scam detector for **SMS and email**, including **Pakistani/Roman-Urdu** and **international** messages, with a clean web UI.
- **Status**: backend + frontend working locally; model trained; no cloud deployment.
- **Owner constraint**: must run **100% locally** on Windows; user trains the model themselves. No API keys, no external runtime calls.

## 2. What it does

1. User pastes SMS/email in the browser UI (`http://127.0.0.1:8000` or `:8001`).
2. UI sends `POST /predict` with `{text, source}` where `source` is `sms` or `email`.
3. Backend cleans text, loads the locally trained sklearn pipeline, returns label/probability/confidence/top terms.
4. UI shows SPAM/HAM verdict, confidence bar, signal chips, and keeps last 5 checks in browser `localStorage`.

## 3. Tech stack

| Layer | Tech | Notes |
|---|---|---|
| ML | scikit-learn `TfidfVectorizer` + `LogisticRegression` | Supervised; saved as `joblib` pipeline |
| Data | pandas, openpyxl | Reads CSV/XLSX |
| API | FastAPI + Uvicorn + Pydantic | Serves API + static UI |
| UI | Plain HTML/CSS/JS in `backend/static/` | **No CDN/npm/build** — fully offline |
| Env | Python 3.10+ (tested on Anaconda Python 3.14.6) | Windows, `.venv` |

## 4. Repository structure

```text
ai-project/
├── PROJECT.md                          # THIS FILE — read first
├── Spam_Detector_Documentation.pdf     # Full architecture/model/evaluation/code-map PDF
└── backend/
    ├── download_data.py                # Fetches 3 public datasets, unzips Enron
    ├── train.py                        # Builds training set, trains model, writes metrics
    ├── model.py                        # clean_text(), load_pipeline(), top_terms(), predict()
    ├── main.py                         # FastAPI app: /, /health, /predict, /model-info, /static
    ├── requirements.txt
    ├── setup.bat                       # Creates .venv, installs deps (Windows)
    ├── run_backend.bat                 # Activates venv, runs python -m uvicorn main:app --reload
    ├── README_backend.md               # User-facing backend runbook + verified results
    ├── data/
    │   ├── local_pakistani_emails.csv  # Hand-written/local hard negatives & positives (editable)
    │   ├── pakistan_sms.xlsx           # Downloaded by download_data.py
    │   ├── roman_urdu_phishing.xlsx    # Downloaded by download_data.py
    │   ├── enron_spam_data.zip         # Downloaded by download_data.py
    │   └── enron_spam_data/
    │       └── enron_spam_data.csv     # Extracted Enron corpus
    ├── models/                         # Generated — gitignore in real repo
    │   ├── spam_model.joblib           # Trained sklearn Pipeline
    │   └── metrics.json                # Accuracy/F1/confusion/threshold/per-source
    ├── static/
        ├── index.html                  # Three-column dashboard UI
        ├── style.css                   # Light-only reference palette + bundled fonts, offline
        ├── app.js                      # Fetch /predict, render result, localStorage history
        ├── fonts/                      # Bundled Space Grotesk + JetBrains Mono
        └── logo.svg                    # One-file logo swap point
    └── commented code/                 # Line-by-line annotated copies; read with the PDF
```

> **New documentation pack**: `Spam_Detector_Documentation.pdf` is a 15-page machine-learning guide covering TF-IDF, logistic regression, preprocessing, training, evaluation, limitations and a viva Q&A. `backend/commented code/` contains line-by-line commented copies of every code file. Edit the originals, not the commented copies.

**Do not commit**: `.venv/`, `__pycache__/`, large downloaded datasets/models if publishing publicly (check licenses). `models/` is reproducible via `train.py`.

## 5. Data sources (all local files after download)

| File | Rows used | Role | License/citation |
|---|---:|---|---|
| `data/pakistan_sms.xlsx` | 868 total in file | Pakistan SMS/scam (English/Roman Urdu/Urdu/mixed) | Muhafiz-AI repo, MIT — https://github.com/saifkhandev/Muhafiz-AI |
| `data/roman_urdu_phishing.xlsx` | 1,000 | Roman Urdu phishing/legit SMS | Ghufran Siddiq, UMT Lahore, CC BY 4.0, DOI `10.5281/zenodo.21810885` |
| `data/enron_spam_data.csv` | sampled 2,000 (1k spam+1k ham) | International email structure/vocab | Enron-Spam preprocessed by MWiechmann, GPL-3.0 |
| `data/local_pakistani_emails.csv` | 161 rows currently | **Hand-curated** Pakistani + international legitimate notifications and scams; includes wire-transfer/crypto/OTP contrast pairs | Project-authored |

**Column handling is defensive** in `train.py`:
- Muhafiz XLSX: uses `Message Content` + `Label` (not `Scam Category`).
- Roman Urdu XLSX: picks raw text + label columns.
- Enron: combines `Subject` + `Message`, maps `Spam/Ham`.

## 6. Training pipeline (`train.py`)

1. Load all sources into `text,label,source` (`label` in `{spam, ham}`).
2. Exact dedup by normalized text.
3. `train_test_split(test_size=0.2, stratify=label, random_state=42)`.
4. **Oversample after split** (no leakage): SMS train rows x3, local-pattern email rows x5. Local pattern regex targets Pakistani/transactional terms (`nayapay,easypaisa,hbl,otp,tracking,statement,...`).
5. Train sklearn `Pipeline`:
   - `TfidfVectorizer(ngram_range=(1,2), min_df=1, max_df=0.95, max_features=80_000, strip_accents='unicode', sublinear_tf=True)`
   - `LogisticRegression(max_iter=3000, class_weight={'ham':1.35,'spam':1.0}, solver='liblinear')`
6. Evaluate on held-out test at fixed `threshold=0.60` (conservative, fewer false positives). Save metrics + model.

## 7. Inference (`model.py`)

- `clean_text(text, source)`: strips HTML/URLs/emails, normalizes PK phone/nums, collapses whitespace; for `email` it keeps Subject and drops common header/date/recipient noise.
- `predict(text, source)`: returns
  ```json
  {"label":"spam|ham","spam_probability":0.0,"confidence":0.0,"threshold":0.6,"top_terms":["..."]}
  ```
- **Top terms**: model-derived. Uses NB `feature_log_prob_` or LR `coef_` (compatible with both). Filters tokens like `num/url/email/phone`.
- **Guardrail** (explainable, not hidden): if strong ham cues present and no spam cues, cap probability (`<=0.35` or `<=0.45` depending on hits). This reduces false positives on legitimate NayaPay/bank/university notifications. **Document this in report/viva.**
- Threshold read from `models/metrics.json`; default 0.5.

## 8. API (`main.py`)

| Endpoint | Method | Purpose |
|---|---|---|
| `/` | GET | Serves `static/index.html` |
| `/health` | GET | `model_ready`, path, hint |
| `/predict` | POST | `{text, source}` -> prediction. 400 empty, 422 bad source, 503 no model |
| `/model-info` | GET | Raw `metrics.json` or `{trained:false}` |
| `/static/*` | GET | CSS/JS assets |

Request: `{"text":"...","source":"sms"|"email"}`.

## 9. Frontend (`backend/static/`)

- **Layout**: split dashboard (input left, result right).
- **Theme**: reference-inspired typography and palette on the original three-column dashboard — light-only `#f4f3ef` paper, `#111` ink, `#777` secondary, `#d6d4ce` rules, `#ff3b30` accent for spam. Locally bundled Space Grotesk + JetBrains Mono (`static/fonts/`), large light-weight typography, hairline rules and paper grain. No CDN, dark mode, or runtime network calls. Layout is a vertical model-status rail / input / analysis, with a vertical recent-scans footer beneath it. Logo is a standalone `/static/logo.svg` (swap that file to change the mark).
- **Features**: SMS/Email tabs, char count, clear, drag-and-drop `.txt`/`.eml`, `Ctrl+Enter` to scan, staged scan animation, oversized verdict, spam-probability meter with visible `T 0.60` threshold, model-derived signed signal chips (`term_scores`, falls back to `top_terms`), tip, vertical model-status rail (`/model-info`: status, accuracy, spam F1, rows, sources, mode), model-info drawer (pipeline, confusion matrix heatmap, per-source accuracy, dataset citations), bordered recent-5 scans list in the footer with slim custom scrollbar in `localStorage` key `spamshield_history_v1`; clicking an entry restores the message, source, and cached analysis without re-scanning or adding a duplicate.
- **Accessibility/UX**: aria labels, `aria-live` result, focus-visible rings, dialog focus/escape handling, `prefers-reduced-motion`, responsive 3→2→1 column grid.

## 10. Current verified metrics (latest retrain)

From `backend/models/metrics.json` after adding 68 curated email examples (local notification/scam pairs, then international notification/phishing pairs):

- **Model**: TF-IDF + Logistic Regression, threshold **0.60**
- **Data**: 4,029 rows (email 2,158, sms 1,871); train 6,715 after oversampling; test 806
- **Accuracy 0.8350**
- **Spam precision 0.9805 / recall 0.6623 / F1 0.7906**
- **Ham precision 0.7673**
- **Confusion** `[[422,5],[128,251]]` (labels `[ham,spam]`) — 5 ham false positives, 128 missed spam
- **Per-source accuracy**: email 0.7171 (n=449), sms 0.9832 (n=357)

**Interpretation**: conservative by design — better to avoid flagging legit bank/university notifications than to catch every spam. Good viva talking point; can be retuned.

## 11. Known issues / gotchas

1. **PowerShell**: use `.\run_backend.bat` and `.\.venv\Scripts\python.exe`. Plain `run_backend.bat` not found by PS.
2. **Broken `py` launcher** on this machine points to missing `C:\Python314\python.exe`; working interpreter is `C:\anaconda\python.exe`. `setup.bat` falls back to it and creates venv with `--system-site-packages`.
3. **Port 8000 ghost listener** was observed earlier; workaround `--port 8001`. If UI looks old, the old process is still running — kill it or change port.
4. **Stale model in memory**: after retraining, restart uvicorn; `model.load_pipeline` is `@lru_cache(maxsize=1)`.
5. **Template leakage risk**: Roman Urdu Zenodo set is template-based; exact dedup helps but not semantic dedup. Mention in report.
6. **Class imbalance/domain shift**: Enron is old English email; modern Pakistani transactional notifications were underrepresented — fixed by adding `local_pakistani_emails.csv` hard negatives and threshold/guardrail. More local examples = better.
7. **No auth/rate limit/DB**: intentional for semester local demo.

## 12. How to run (Windows)

```bat
cd backend
setup.bat                       :: or ensure .venv exists
.\.venv\Scripts\python.exe download_data.py
.\.venv\Scripts\python.exe train.py
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8001
```

Open `http://127.0.0.1:8001`. API docs: `/docs`. Health: `/health`.

## 13. How to retrain after adding data

1. Add rows to `data/local_pakistani_emails.csv` as `text,label,source` (`label` `spam|ham`, `source` usually `email` or `sms`).
2. Run `.\.venv\Scripts\python.exe train.py`.
3. Restart the backend process.
4. Smoke test with the previously misclassified examples.

## 14. Safe extension ideas (if asked)

- **More local data**: best ROI for Pakistani false positives.
- **Threshold slider / calibrate**: expose `threshold` in UI; current default 0.60.
- **Per-source models**: separate SMS/email models (more work, may help email).
- **Explainability**: show which tokens pushed spam vs ham (LR coefficients already available).
- **Batch CSV upload**: simple FastAPI endpoint + table UI.
- **Tests**: pytest for `clean_text`, `predict` smoke cases, API 400/503.
- **Do not** add cloud calls or heavy frameworks unless user asks; keep it local and simple.

## 15. File change log (important decisions)

- Initial backend: FastAPI + TF-IDF + MultinomialNB.
- Fixed `train.py` label detection bug: Muhafiz has `Label` and `Scam Category`; exact `label` must win.
- Fixed pandas `str` dtype detection in `pick_text_column`.
- Added UI: `static/index.html/css/js`, mounted by `main.py`. No CDN.
- Fixed false positives: added 54+ hard negatives, switched to Logistic Regression, added threshold 0.60, added explainable ham-cue guardrail, improved email cleaning. **Restart backend after retrain.**

## 16. Quick smoke tests

```powershell
# health
Invoke-RestMethod http://127.0.0.1:8001/health

# should be SPAM
Invoke-RestMethod -Uri http://127.0.0.1:8001/predict -Method Post -ContentType application/json -Body '{"text":"Aap ko Rs. 50,000 ka inaam mila hai. OTP share karein.","source":"sms"}'

# should be HAM (legit NayaPay-style)
Invoke-RestMethod -Uri http://127.0.0.1:8001/predict -Method Post -ContentType application/json -Body '{"text":"You have used 2 of 5 failed international transactions. Navigate to Cards tab to reset. Best, NayaPay Team","source":"email"}'
```

---

*Last updated: 2026-11-22 by coding agent during local build/debug session.*