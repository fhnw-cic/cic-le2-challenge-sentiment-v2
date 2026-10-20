"""Lädt Modell und Tokenizer in den Hugging-Face-Cache (HF_HOME).

Gedacht für den Build-Schritt eines Images, damit der Container später
ohne Internetzugang (HF_HUB_OFFLINE=1) starten kann.

    MODEL_NAME=... HF_HOME=/some/path python prefetch_model.py
"""

import os

from transformers import AutoModelForSequenceClassification, AutoTokenizer

model_name = os.getenv("MODEL_NAME", "distilbert-base-uncased-finetuned-sst-2-english")
print(f"Prefetching '{model_name}' into HF_HOME={os.getenv('HF_HOME', '~/.cache/huggingface')} ...")
AutoTokenizer.from_pretrained(model_name)
AutoModelForSequenceClassification.from_pretrained(model_name)
print("Done.")
