# ---------------------------------------------------------------------------
# app.py
# ---------------------------------------------------------------------------
"""Perform hybrid keyword and vector search against Milvus."""

from __future__ import annotations

import os
import logging
from typing import Any, Dict, List

from pymilvus import Collection, connections

from common_utils.get_ssm import get_config

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s", "%Y-%m-%dT%H:%M:%S%z")
)
logger.addHandler(_handler)

HOST = get_config("MILVUS_HOST") or os.environ.get("MILVUS_HOST", "localhost")
PORT = int(get_config("MILVUS_PORT") or os.environ.get("MILVUS_PORT", "19530"))
COLLECTION_NAME = get_config("MILVUS_COLLECTION") or os.environ.get("MILVUS_COLLECTION", "docs")
TOP_K = int(get_config("TOP_K") or os.environ.get("TOP_K", "5"))

connections.connect(alias="default", host=HOST, port=PORT)
collection = Collection(COLLECTION_NAME)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Search Milvus using a vector embedding and optional keywords."""

    embedding = event.get("embedding")
    keywords: List[str] = event.get("keywords", [])
    res = collection.search(
        [embedding],
        "embedding",
        {"metric_type": "L2"},
        limit=TOP_K,
        output_fields=["metadata"],
    )
    matches = [
        {"id": r.id, "score": r.distance, "metadata": r.entity.get("metadata")}
        for r in res[0]
    ]
    if keywords:
        filtered = []
        for m in matches:
            text = str(m.get("metadata", {}).get("text", "")).lower()
            if any(k.lower() in text for k in keywords):
                filtered.append(m)
        matches = filtered

    return {"matches": matches[:TOP_K]}

