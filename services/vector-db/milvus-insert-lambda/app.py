# ---------------------------------------------------------------------------
# app.py
# ---------------------------------------------------------------------------
"""Insert embeddings into a Milvus collection."""

from __future__ import annotations

import os
import logging
from typing import Any, List

from common_utils import MilvusClient, VectorItem
from common_utils.get_ssm import get_config

# Module Metadata
__author__ = "Koushik Sinha"
__version__ = "1.0.0"
__modified_by__ = "Koushik Sinha"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s", "%Y-%m-%dT%H:%M:%S%z")
)
if not logger.handlers:
    logger.addHandler(_handler)

UPSERT = (get_config("MILVUS_UPSERT") or os.environ.get("MILVUS_UPSERT", "true")).lower() == "true"

client = MilvusClient()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Insert provided embeddings into Milvus."""

    embeddings: List[List[float]] = event.get("embeddings", [])
    metadatas: List[Any] = event.get("metadatas", [])
    ids = event.get("ids") or []

    items: List[VectorItem] = []
    for idx, embedding in enumerate(embeddings):
        metadata = metadatas[idx] if idx < len(metadatas) else None
        item_id = ids[idx] if idx < len(ids) else None
        items.append(VectorItem(embedding=embedding, metadata=metadata, id=item_id))

    inserted = client.insert(items, upsert=UPSERT)
    return {"inserted": inserted}

