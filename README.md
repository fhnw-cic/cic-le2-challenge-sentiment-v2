# cic-le2-challenge-sentiment

Sentiment-Analyzer bestehend aus zwei Microservices:

| Service  | Technologie | Port | Start-Befehl |
|----------|-------------|------|--------------|
| backend  | FastAPI + Hugging Face Transformers | `8080` | `uvicorn main:app --host 0.0.0.0 --port 8080` |
| frontend | Streamlit | `8501` | `streamlit run app.py --server.port=8501 --server.address=0.0.0.0` |

## Backend

### Umgebungsvariablen

| Variable | Pflicht | Default | Beschreibung |
|----------|---------|---------|--------------|
| `API_KEY` | **ja** | – | Gemeinsames Geheimnis. Ohne diese Variable startet das Backend nicht. Requests auf `/predict` brauchen den Header `X-API-Key`. |
| `MODEL_NAME` | nein | `distilbert-base-uncased-finetuned-sst-2-english` | Hugging-Face-Modell |
| `STARTUP_DELAY_SECONDS` | nein | `20` | Simulierte zusätzliche Ladezeit des Modells |
| `APP_VERSION` | nein | `dev` | Wird in `/health/ready`, `/info` und `/predict` zurückgegeben |
| `HF_HOME` | nein | `~/.cache/huggingface` | Cache-Verzeichnis für Modelle (Standardvariable von Hugging Face) |
| `HF_HUB_OFFLINE` | nein | – | `1` = kein Download zur Laufzeit, Modell muss bereits im Cache liegen |

### Endpoints

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/health/live` | `200`, solange der Prozess lebt; `500`, wenn das Laden des Modells endgültig fehlgeschlagen ist |
| GET | `/health/ready` | `503`, solange das Modell lädt; `200`, sobald Anfragen bedient werden können |
| GET | `/info` | Hostname, Modell, Version, Status |
| POST | `/predict` | Body `{"text": "..."}`, Header `X-API-Key`. Antwort enthält u.a. `served_by` (Hostname der Instanz) |

Hinweise:

- Das Modell wird **nach** dem Start des Webservers in einem Hintergrund-Thread geladen. Der Server antwortet also sofort, ist aber erst nach ca. 20–40 Sekunden bereit.
- `prefetch_model.py` lädt das Modell in den Cache (`HF_HOME`), z.B. während eines Image-Builds:
  ```bash
  MODEL_NAME=distilbert-base-uncased-finetuned-sst-2-english python prefetch_model.py
  ```

## Frontend

### Umgebungsvariablen

| Variable | Pflicht | Default | Beschreibung |
|----------|---------|---------|--------------|
| `SENTIMENT_API_URL` | ja | `http://localhost:8080` | Basis-URL des Backends |
| `API_KEY` | ja | – | Wird als `X-API-Key` an das Backend gesendet |
| `HISTORY_DIR` | nein | `/var/lib/sentiment` | Verzeichnis, in dem die SQLite-Datenbank `history.db` abgelegt wird (muss beschreibbar sein) |
| `STUDENT_ID` | ja (für die Challenge) | `not-set` | Wird im UI angezeigt |

Die Historie liegt in der SQLite-Datei `${HISTORY_DIR}/history.db` (Tabelle `history`).
Inhalt prüfen:

```bash
sqlite3 history.db "SELECT * FROM history ORDER BY id DESC LIMIT 10;"
```

## Lokal ohne Container starten

```bash
# Terminal 1
cd backend && pip install -r requirements.txt
API_KEY=dev-secret uvicorn main:app --host 0.0.0.0 --port 8080

# Terminal 2
cd frontend && pip install -r requirements.txt
SENTIMENT_API_URL=http://localhost:8080 API_KEY=dev-secret HISTORY_DIR=./data STUDENT_ID=me \
  streamlit run app.py --server.port=8501 --server.address=0.0.0.0
```
