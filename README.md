# cic-le2-challenge-sentiment

Sentiment analyzer consisting of two microservices:

| Service  | Technology | Port | Start command |
|----------|-------------|------|--------------|
| backend  | FastAPI + Hugging Face Transformers | `8080` | `uvicorn main:app --host 0.0.0.0 --port 8080` |
| frontend | Streamlit | `8501` | `streamlit run app.py --server.port=8501 --server.address=0.0.0.0` |

## Backend

### Environment variables

| Variable | Required | Default | Description |
|----------|---------|---------|--------------|
| `API_KEY` | **yes** | – | Shared secret. The backend does not start without this variable. Requests to `/predict` require the `X-API-Key` header. |
| `MODEL_NAME` | no | `distilbert-base-uncased-finetuned-sst-2-english` | Hugging Face model |
| `STARTUP_DELAY_SECONDS` | no | `20` | Simulated additional model loading time |
| `APP_VERSION` | no | `dev` | Returned by `/health/ready`, `/info` and `/predict` |
| `HF_HOME` | no | `~/.cache/huggingface` | Cache directory for models (standard Hugging Face variable) |
| `HF_HUB_OFFLINE` | no | – | `1` = no download at runtime; the model must already be in the cache |

### Endpoints

| Method | Path | Description |
|---------|------|--------------|
| GET | `/health/live` | `200` as long as the process is alive; `500` if loading the model has failed permanently |
| GET | `/health/ready` | `503` while the model is loading; `200` once requests can be served |
| GET | `/info` | Hostname, model, version, status |
| POST | `/predict` | Body `{"text": "..."}`, header `X-API-Key`. The response includes, among other things, `served_by` (hostname of the instance) |

Notes:

- The model is loaded in a background thread **after** the web server starts. The server therefore responds immediately, but is only ready after about 20–40 seconds.
- `prefetch_model.py` downloads the model into the cache (`HF_HOME`), e.g. during an image build:
  ```bash
  MODEL_NAME=distilbert-base-uncased-finetuned-sst-2-english python prefetch_model.py
  ```

## Frontend

### Environment variables

| Variable | Required | Default | Description |
|----------|---------|---------|--------------|
| `SENTIMENT_API_URL` | yes | `http://localhost:8080` | Base URL of the backend |
| `API_KEY` | yes | – | Sent to the backend as `X-API-Key` |
| `HISTORY_DIR` | no | `/var/lib/sentiment` | Directory where the SQLite database `history.db` is stored (must be writable) |
| `STUDENT_ID` | yes (for the challenge) | `not-set` | Displayed in the UI |

The history is stored in the SQLite file `${HISTORY_DIR}/history.db` (table `history`).
To inspect its contents:

```bash
sqlite3 history.db "SELECT * FROM history ORDER BY id DESC LIMIT 10;"
```

## Running locally without containers

```bash
# Terminal 1
cd backend && pip install -r requirements.txt
API_KEY=dev-secret uvicorn main:app --host 0.0.0.0 --port 8080

# Terminal 2
cd frontend && pip install -r requirements.txt
SENTIMENT_API_URL=http://localhost:8080 API_KEY=dev-secret HISTORY_DIR=./data STUDENT_ID=me \
  streamlit run app.py --server.port=8501 --server.address=0.0.0.0
```
