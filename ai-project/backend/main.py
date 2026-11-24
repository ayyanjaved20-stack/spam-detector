"""Local FastAPI backend + UI for the spam detector."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from model import METRICS_PATH, MODEL_PATH, predict

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"

app = FastAPI(title="SpamShield", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


class PredictIn(BaseModel):
    text: str
    source: str = "sms"  # "sms" or "email"


@app.get("/", include_in_schema=False)
def root():
    return FileResponse(STATIC / "index.html")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_ready": MODEL_PATH.exists(),
        "model_path": str(MODEL_PATH),
        "hint": None if MODEL_PATH.exists() else "Run: python train.py",
    }


@app.post("/predict")
def predict_endpoint(payload: PredictIn):
    if payload.source not in {"sms", "email"}:
        raise HTTPException(status_code=422, detail="source must be 'sms' or 'email'")
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Text must not be empty.")
    try:
        return predict(payload.text, payload.source)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/model-info")
def model_info():
    if not METRICS_PATH.exists():
        return {"trained": False, "hint": "Run: python train.py"}
    return json.loads(METRICS_PATH.read_text(encoding="utf-8"))
