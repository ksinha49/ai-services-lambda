import os
import json

CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", "100"))


def chunk_text(text: str):
    step = CHUNK_SIZE - CHUNK_OVERLAP
    if step <= 0:
        step = CHUNK_SIZE
    return [text[i:i + CHUNK_SIZE] for i in range(0, len(text), step)]


def lambda_handler(event, context):
    text = event.get("text", "")
    chunks = chunk_text(text)
    return {"chunks": chunks}
