import logging
import os
import secrets
import socket
import threading
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Konfiguration (ausschliesslich über Umgebungsvariablen)
# ---------------------------------------------------------------------------
MODEL_NAME = os.getenv("MODEL_NAME", "distilbert-base-uncased-finetuned-sst-2-english")
STARTUP_DELAY_SECONDS = int(os.getenv("STARTUP_DELAY_SECONDS", "20"))
APP_VERSION = os.getenv("APP_VERSION", "dev")
API_KEY = os.getenv("API_KEY")  # Pflicht – siehe Startup-Check unten
HOSTNAME = socket.gethostname()

logging.basicConfig(
    level=logging.INFO,
    format=f"%(asctime)s [{HOSTNAME}] %(levelname)s %(message)s",
)
log = logging.getLogger("sentiment-backend")

# ---------------------------------------------------------------------------
# Modell-Status (wird von einem Hintergrund-Thread befüllt)
# ---------------------------------------------------------------------------
_state = {"status": "loading", "pipeline": None, "error": None}


def _load_model() -> None:
    """Lädt das Modell im Hintergrund, damit der Prozess sofort 'lebt'."""
    from transformers import pipeline  # spät importieren: Import selbst dauert

    log.info("Loading model '%s' (simulated delay: %ss) ...", MODEL_NAME, STARTUP_DELAY_SECONDS)
    # Simulation einer langen Ladezeit (z.B. grosses LLM)
    time.sleep(STARTUP_DELAY_SECONDS)
    try:
        _state["pipeline"] = pipeline("sentiment-analysis", model=MODEL_NAME)
        _state["status"] = "ready"
        log.info("Model loaded successfully. Ready to serve traffic.")
    except Exception as e:  # noqa: BLE001
        _state["status"] = "failed"
        _state["error"] = str(e)
        log.error("FATAL: Could not load model: %s", e)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if not API_KEY:
        raise RuntimeError("Environment variable API_KEY is not set. Refusing to start.")
    threading.Thread(target=_load_model, daemon=True).start()
    yield


app = FastAPI(title="Sentiment Analysis API", version=APP_VERSION, lifespan=lifespan)


# ---------------------------------------------------------------------------
# Health-Endpoints
# ---------------------------------------------------------------------------
@app.get("/health/live")
def liveness():
    """Lebt der Prozess? Liefert 500, wenn das Laden des Modells endgültig fehlgeschlagen ist."""
    if _state["status"] == "failed":
        return JSONResponse(status_code=500, content={"status": "failed", "error": _state["error"]})
    return {"status": "alive", "host": HOSTNAME}


@app.get("/health/ready")
def readiness():
    """Kann der Pod Traffic bedienen? 503, solange das Modell noch lädt."""
    if _state["status"] != "ready":
        return JSONResponse(status_code=503, content={"status": _state["status"], "host": HOSTNAME})
    return {"status": "ready", "model": MODEL_NAME, "host": HOSTNAME, "version": APP_VERSION}


@app.get("/info")
def info():
    return {"host": HOSTNAME, "model": MODEL_NAME, "version": APP_VERSION, "status": _state["status"]}


# ---------------------------------------------------------------------------
# Inferenz (geschützt per API-Key)
# ---------------------------------------------------------------------------
class TextRequest(BaseModel):
    text: str = Field(..., max_length=2000)


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if not x_api_key or not secrets.compare_digest(x_api_key, API_KEY or ""):
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key header")


@app.post("/predict", dependencies=[Depends(require_api_key)])
def predict(request: TextRequest):
    if _state["status"] != "ready":
        raise HTTPException(status_code=503, detail="Model not loaded yet")
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    result = _state["pipeline"](request.text)[0]  # z.B. {'label': 'POSITIVE', 'score': 0.99}
    log.info("predict -> %s (%.3f)", result["label"], result["score"])
    return {
        "label": result["label"],
        "score": result["score"],
        "model": MODEL_NAME,
        "served_by": HOSTNAME,
        "version": APP_VERSION,
    }
