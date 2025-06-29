import os
from typing import List, Any

from common_utils import MilvusClient, VectorItem

UPSERT = os.environ.get("MILVUS_UPSERT", "true").lower() == "true"

client = MilvusClient()


def lambda_handler(event, context):
    embeddings: List[List[float]] = event.get("embeddings", [])
    metadatas: List[Any] = event.get("metadatas", [])
    ids = event.get("ids") or []

    items = []
    for idx, embedding in enumerate(embeddings):
        metadata = metadatas[idx] if idx < len(metadatas) else None
        item_id = ids[idx] if idx < len(ids) else None
        items.append(VectorItem(embedding=embedding, metadata=metadata, id=item_id))

    inserted = client.insert(items, upsert=UPSERT)
    return {"inserted": inserted}
