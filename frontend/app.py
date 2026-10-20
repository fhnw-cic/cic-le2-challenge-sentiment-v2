import os
import sqlite3
from datetime import datetime

import pandas as pd
import requests
import streamlit as st

SENTIMENT_API_URL = os.getenv("SENTIMENT_API_URL", "http://localhost:8080").rstrip("/")
API_KEY = os.getenv("API_KEY", "")
HISTORY_DIR = os.getenv("HISTORY_DIR", "/var/lib/sentiment")
STUDENT_ID = os.getenv("STUDENT_ID", "not-set")
HISTORY_DB = os.path.join(HISTORY_DIR, "history.db")

st.set_page_config(page_title="Sentiment Analyzer", page_icon="🤖")

st.title("Sentiment Analyzer")
st.markdown(f"Microservice example for LE2 from the module cic · Deployment by **{STUDENT_ID}**")


# --- Persistenz (SQLite) ---
def get_db() -> sqlite3.Connection:
    os.makedirs(HISTORY_DIR, exist_ok=True)
    conn = sqlite3.connect(HISTORY_DB, timeout=5)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS history (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               time TEXT NOT NULL,
               text TEXT NOT NULL,
               label TEXT NOT NULL,
               score REAL NOT NULL,
               served_by TEXT NOT NULL
           )"""
    )
    return conn


# --- Sidebar: Status Check ---
st.sidebar.header("System Status")
try:
    r = requests.get(f"{SENTIMENT_API_URL}/health/ready", timeout=2)
    if r.status_code == 200:
        health = r.json()
        st.sidebar.success(f"Backend ready ✅  \nModel: {health.get('model')}  \nVersion: {health.get('version')}")
    else:
        st.sidebar.warning(f"Backend not ready ⏳ (HTTP {r.status_code})")
except Exception:
    st.sidebar.error(f"Backend offline ❌  \nURL: {SENTIMENT_API_URL}")
    st.sidebar.info("Tip: Check if the service is started and reachable.")

if not API_KEY:
    st.sidebar.error("API_KEY is not configured – requests will be rejected.")

# --- Main Area: Inferenz ---
st.subheader("Analyze new text")
text_input = st.text_area("Insert English text:", height=100)

if st.button("Analyze"):
    if text_input.strip():
        try:
            with st.spinner("Request API..."):
                response = requests.post(
                    f"{SENTIMENT_API_URL}/predict",
                    json={"text": text_input},
                    headers={"X-API-Key": API_KEY},
                    timeout=30,
                )

            if response.status_code == 200:
                result = response.json()
                label = result["label"]
                score = round(result["score"] * 100, 2)
                served_by = result.get("served_by", "?")

                if label == "POSITIVE":
                    st.success(f"Result: POSITIVE ({score}%) – served by `{served_by}`")
                else:
                    st.error(f"Result: NEGATIVE ({score}%) – served by `{served_by}`")

                try:
                    with get_db() as conn:
                        conn.execute(
                            "INSERT INTO history (time, text, label, score, served_by) VALUES (?, ?, ?, ?, ?)",
                            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), text_input, label, score, served_by),
                        )
                except Exception as e:
                    st.error(f"Could not write history to {HISTORY_DB}: {e}")
            elif response.status_code == 401:
                st.error("Backend rejected the request: invalid API key (HTTP 401).")
            elif response.status_code == 503:
                st.warning("Backend is still loading the model (HTTP 503). Try again in a few seconds.")
            else:
                st.error(f"Backend error: {response.status_code}")

        except Exception as e:
            st.error(f"Connection error: {e}")

# --- History Area ---
st.divider()
st.subheader("History")
st.caption(f"Loading data from: `{HISTORY_DB}`")

if os.path.exists(HISTORY_DB):
    try:
        with get_db() as conn:
            df = pd.read_sql_query("SELECT time, text, label, score, served_by FROM history ORDER BY id DESC", conn)
        st.dataframe(df, width="stretch")
        if not df.empty:
            st.caption("Requests per backend instance:")
            st.bar_chart(df["served_by"].value_counts())
    except Exception as e:
        st.error(f"Error loading history data: {e}")
else:
    st.warning("No history found.")
