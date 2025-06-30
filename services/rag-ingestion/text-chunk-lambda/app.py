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

CHUNK_SIZE = int(get_config("CHUNK_SIZE") or os.environ.get("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(get_config("CHUNK_OVERLAP") or os.environ.get("CHUNK_OVERLAP", "100"))


def chunk_text(text: str) -> List[str]:
    """Split ``text`` into chunks respecting ``CHUNK_SIZE`` and ``CHUNK_OVERLAP``."""

    step = CHUNK_SIZE - CHUNK_OVERLAP
    if step <= 0:
        step = CHUNK_SIZE
    return [text[i : i + CHUNK_SIZE] for i in range(0, len(text), step)]


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Return chunked text for ingestion."""

    text = event.get("text", "")
    doc_type = event.get("docType") or event.get("type")
    chunks = chunk_text(text)
    payload: Dict[str, Any] = {"chunks": chunks}
    if doc_type:
        payload["docType"] = doc_type
    return payload

