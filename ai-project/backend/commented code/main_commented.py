# Module docstring stating that this file serves both the API and the browser UI.
"""Local FastAPI backend + UI for the spam detector."""
# Enable postponed annotation evaluation so type hints stay flexible and cheap.
from __future__ import annotations
# (blank line separates logical blocks)

# Import JSON support for reading the saved metrics file.
import json
# Import Path for portable filesystem paths that behave the same on Windows and Linux.
from pathlib import Path
# (blank line separates logical blocks)

# Import the app class and the error type used to return clean HTTP failures.
from fastapi import FastAPI, HTTPException
# Import the response class that streams a file such as index.html back to the browser.
from fastapi.responses import FileResponse
# Import the helper that serves CSS, JavaScript and image assets.
from fastapi.staticfiles import StaticFiles
# Import the base class used to declare the request body schema.
from pydantic import BaseModel
# (blank line separates logical blocks)

# Reuse the inference function and model paths defined in model.py.
from model import METRICS_PATH, MODEL_PATH, predict
# (blank line separates logical blocks)

# Resolve this file's own folder so paths work from any working directory.
# Store the absolute backend directory as the base for every other path.
ROOT = Path(__file__).resolve().parent
# Build the absolute path to the folder that holds the browser assets.
STATIC = ROOT / "static"
# (blank line separates logical blocks)

# Create the ASGI application whose title and version appear in the generated docs.
app = FastAPI(title="SpamShield", version="1.0.0")
# Mounting makes every file under static reachable through a /static URL prefix.
# The browser needs this to load style.css, app.js and logo.svg successfully.
# Serve the static folder at /static so the HTML page can fetch its assets.
app.mount("/static", StaticFiles(directory=STATIC), name="static")
# (blank line separates logical blocks)

# (blank line separates logical blocks)

# Declare the Pydantic schema that validates the JSON body of prediction requests.
class PredictIn(BaseModel):
    # Require the message text to be supplied as a string.
    text: str
    # Default the source to SMS; the trailing inline note documents the two allowed values.
    source: str = "sms"  # "sms" or "email"
# (blank line separates logical blocks)

# (blank line separates logical blocks)

# The root page is a browser view, not an API operation, so hide it from /docs.
# Register the root URL as a GET endpoint excluded from the API schema.
@app.get("/", include_in_schema=False)
# Define the handler that returns the single-page UI.
def root():
    # Stream index.html from the static folder as the response body.
    return FileResponse(STATIC / "index.html")
# (blank line separates logical blocks)

# (blank line separates logical blocks)

# Register a GET endpoint for checking whether the service and model are ready.
@app.get("/health")
# Define the health check handler used by the UI or by a developer.
def health():
    # Start building a JSON object with diagnostic information.
    return {
        # Report that the backend process itself is running.
        "status": "ok",
        # Report whether the trained model file is present on disk.
        "model_ready": MODEL_PATH.exists(),
        # Expose the expected model location to help debugging.
        "model_path": str(MODEL_PATH),
        # Give a helpful next step only when the model is missing.
        "hint": None if MODEL_PATH.exists() else "Run: python train.py",
    # Close the diagnostics object and return it as JSON.
    }
# (blank line separates logical blocks)

# (blank line separates logical blocks)

# This is the main API operation the browser calls when the user runs a scan.
# POST is used because the message text travels in the request body, not the URL.
# Register the prediction endpoint as an HTTP POST route.
@app.post("/predict")
# Receive the already validated request body through the PredictIn model.
def predict_endpoint(payload: PredictIn):
    # Guard against unknown source values before any inference code runs.
    if payload.source not in {"sms", "email"}:
        # Return an unprocessable-entity error with a clear message for a bad source.
        raise HTTPException(status_code=422, detail="source must be 'sms' or 'email'")
    # Reject whitespace-only input that would produce a meaningless prediction.
    if not payload.text.strip():
        # Return a bad-request error explaining that text is required.
        raise HTTPException(status_code=400, detail="Text must not be empty.")
    # Wrap inference so a missing model can be translated into an HTTP error.
    try:
        # Delegate cleaning and classification to model.py and send back its JSON result.
        return predict(payload.text, payload.source)
    # Catch the specific error raised when train.py has not produced a model yet.
    except FileNotFoundError as exc:
        # Convert that error into a service-unavailable response while preserving its cause.
        raise HTTPException(status_code=503, detail=str(exc)) from exc
# (blank line separates logical blocks)

# (blank line separates logical blocks)

# Register a GET endpoint that exposes training metrics to the UI.
@app.get("/model-info")
# Define the handler used by the model information drawer and footer.
def model_info():
    # Check whether train.py has written the metrics file yet.
    if not METRICS_PATH.exists():
        # Tell the UI that no model is trained and suggest the training command.
        return {"trained": False, "hint": "Run: python train.py"}
    # Read and parse the saved JSON metrics so the page can display real numbers.
    return json.loads(METRICS_PATH.read_text(encoding="utf-8"))
