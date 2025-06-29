import os
import json

EMBED_MODEL = os.environ.get("EMBED_MODEL", "dummy")


def _dummy_embed(text: str):
    return [float(ord(c) % 5) for c in text]


_MODEL_MAP = {
    "dummy": _dummy_embed,
}


def lambda_handler(event, context):
    chunks = event.get("chunks", [])
    embed_fn = _MODEL_MAP.get(EMBED_MODEL, _dummy_embed)
    embeddings = [embed_fn(c) for c in chunks]
    return {"embeddings": embeddings}
