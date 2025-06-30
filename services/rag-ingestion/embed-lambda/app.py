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
if not logger.handlers:
    logger.addHandler(_handler)

EMBED_MODEL = get_config("EMBED_MODEL") or os.environ.get("EMBED_MODEL", "sbert")
_MAP_RAW = get_config("EMBED_MODEL_MAP") or os.environ.get("EMBED_MODEL_MAP", "{}")
try:
    EMBED_MODEL_MAP = json.loads(_MAP_RAW) if _MAP_RAW else {}
except json.JSONDecodeError:
    EMBED_MODEL_MAP = {}


_SBERT_MODEL = None


def _sbert_embed(text: str) -> List[float]:
    """Embed ``text`` using a SentenceTransformer model."""

    global _SBERT_MODEL
    if _SBERT_MODEL is None:
        model_path = (
            get_config("SBERT_MODEL")
            or os.environ.get("SBERT_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        )
        if model_path.startswith("s3://"):
            import boto3
            from common_utils import parse_s3_uri

            bucket, key = parse_s3_uri(model_path)
            dest = os.path.join("/tmp", os.path.basename(key))
            boto3.client("s3").download_file(bucket, key, dest)
            model_path = dest

        from sentence_transformers import SentenceTransformer  # type: ignore

        _SBERT_MODEL = SentenceTransformer(model_path)

    return _SBERT_MODEL.encode([text])[0].tolist()


def _openai_embed(text: str) -> List[float]:
    """Embed ``text`` using the OpenAI API."""

    import openai  # type: ignore

    model = get_config("OPENAI_EMBED_MODEL") or os.environ.get(
        "OPENAI_EMBED_MODEL", "text-embedding-ada-002"
    )
    resp = openai.Embedding.create(input=[text], model=model)
    return resp["data"][0]["embedding"]


def _cohere_embed(text: str) -> List[float]:
    """Embed ``text`` using the Cohere API."""

    import cohere  # type: ignore

    api_key = get_config("COHERE_API_KEY", decrypt=True) or os.environ.get("COHERE_API_KEY")
    client = cohere.Client(api_key)
    resp = client.embed([text])
    return resp.embeddings[0]


_MODEL_MAP = {
    "sbert": _sbert_embed,
    "sentence": _sbert_embed,
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
        embed_fn = _MODEL_MAP.get(model_name, _sbert_embed)
        embeddings.append(embed_fn(text))

    return {"embeddings": embeddings}

