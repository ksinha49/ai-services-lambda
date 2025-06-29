import os
import logging
from typing import List, Any

from common_utils import MilvusClient, VectorItem
from common_utils.get_ssm import get_config

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s", "%Y-%m-%dT%H:%M:%S%z")
)
logger.addHandler(_handler)

UPSERT = (get_config("MILVUS_UPSERT") or os.environ.get("MILVUS_UPSERT", "true")).lower() == "true"

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
