# ---------------------------------------------------------------------------
# app.py
# ---------------------------------------------------------------------------
"""Update records in a Milvus collection."""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List

from common_utils import MilvusClient, VectorItem

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s", "%Y-%m-%dT%H:%M:%S%z")
)
logger.addHandler(_handler)

client = MilvusClient()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Update the provided embeddings in Milvus."""

    embeddings: List[List[float]] = event.get("embeddings", [])
    metadatas: List[Any] = event.get("metadatas", [])
    ids: Iterable[int] = event.get("ids", [])

    items: List[VectorItem] = []
    for idx, embedding in enumerate(embeddings):
        metadata = metadatas[idx] if idx < len(metadatas) else None
        item_id = ids[idx] if idx < len(ids) else None
        items.append(VectorItem(embedding=embedding, metadata=metadata, id=item_id))

    updated = client.update(items)
    return {"updated": updated}
