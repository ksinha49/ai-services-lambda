# ---------------------------------------------------------------------------
# app.py
# ---------------------------------------------------------------------------
"""Embed text chunks using a configurable embedding provider."""

from __future__ import annotations

import os
import json
import logging

from typing import Any, Dict, List

from common_utils.get_ssm import get_config

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s", "%Y-%m-%dT%H:%M:%S%z")
)
logger.addHandler(_handler)

EMBED_MODEL = get_config("EMBED_MODEL") or os.environ.get("EMBED_MODEL", "dummy")
_MAP_RAW = get_config("EMBED_MODEL_MAP") or os.environ.get("EMBED_MODEL_MAP", "{}")
try:
    EMBED_MODEL_MAP = json.loads(_MAP_RAW) if _MAP_RAW else {}
except json.JSONDecodeError:
    EMBED_MODEL_MAP = {}


def _dummy_embed(text: str) -> List[float]:
    """Return a deterministic embedding for testing."""

    return [float(ord(c) % 5) for c in text]


def _openai_embed(text: str) -> List[float]:
    """Embed ``text`` using the OpenAI API."""

    import openai  # type: ignore

    model = os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-ada-002")
    resp = openai.Embedding.create(input=[text], model=model)
    return resp["data"][0]["embedding"]


def _cohere_embed(text: str) -> List[float]:
    """Embed ``text`` using the Cohere API."""

    import cohere  # type: ignore

    api_key = os.environ.get("COHERE_API_KEY")
    client = cohere.Client(api_key)
    resp = client.embed([text])
    return resp.embeddings[0]


_MODEL_MAP = {
    "dummy": _dummy_embed,
    "openai": _openai_embed,
    "cohere": _cohere_embed,
}


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Return vector embeddings for the provided chunks."""

    chunks = event.get("chunks", [])
    doc_type = event.get("docType") or event.get("type")
    embeddings: List[List[float]] = []
    for chunk in chunks:
        text = chunk
        c_type = doc_type
        if isinstance(chunk, dict):
            text = chunk.get("text", "")
            meta = chunk.get("metadata", {})
            c_type = meta.get("docType") or meta.get("type") or c_type
        model_name = EMBED_MODEL_MAP.get(c_type, EMBED_MODEL)
        embed_fn = _MODEL_MAP.get(model_name, _dummy_embed)
        embeddings.append(embed_fn(text))

    return {"embeddings": embeddings}

