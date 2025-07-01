# ---------------------------------------------------------------------------
# app.py
# ---------------------------------------------------------------------------
"""Split large text into overlapping chunks."""

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

DEFAULT_CHUNK_SIZE = int(
    get_config("CHUNK_SIZE") or os.environ.get("CHUNK_SIZE", "1000")
)
DEFAULT_CHUNK_OVERLAP = int(
    get_config("CHUNK_OVERLAP") or os.environ.get("CHUNK_OVERLAP", "100")
)


def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Split ``text`` using ``chunk_size`` and ``overlap``."""

    step = chunk_size - overlap
    if step <= 0:
        step = chunk_size
    return [text[i : i + chunk_size] for i in range(0, len(text), step)]


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Return chunked text for ingestion."""

    text = event.get("text", "")
    doc_type = event.get("docType") or event.get("type")
    metadata = event.get("metadata", {})
    chunk_size = int(event.get("chunk_size", DEFAULT_CHUNK_SIZE))
    overlap = int(event.get("chunk_overlap", DEFAULT_CHUNK_OVERLAP))
    chunks = chunk_text(text, chunk_size, overlap)
    chunk_list = [
        {"text": c, "metadata": {**metadata, "docType": doc_type} if doc_type else {**metadata}}
        for c in chunks
    ]
    payload: Dict[str, Any] = {"chunks": chunk_list}
    if doc_type:
        payload["docType"] = doc_type
    if metadata:
        payload["metadata"] = metadata
    return payload

