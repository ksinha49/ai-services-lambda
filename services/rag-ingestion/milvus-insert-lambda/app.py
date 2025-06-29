import os
from typing import List, Any
from pymilvus import Collection, connections

HOST = os.environ.get("MILVUS_HOST", "localhost")
PORT = int(os.environ.get("MILVUS_PORT", "19530"))
COLLECTION_NAME = os.environ.get("MILVUS_COLLECTION", "docs")
UPSERT = os.environ.get("MILVUS_UPSERT", "true").lower() == "true"

connections.connect(alias="default", host=HOST, port=PORT)
collection = Collection(COLLECTION_NAME)


def lambda_handler(event, context):
    embeddings: List[List[float]] = event.get("embeddings", [])
    metadatas: List[Any] = event.get("metadatas", [])
    ids = event.get("ids")
    if UPSERT and ids:
        collection.delete(f"id in {ids}")
    if ids:
        entities = [ids, embeddings, metadatas]
    else:
        entities = [embeddings, metadatas]
    collection.insert(entities)
    return {"inserted": len(embeddings)}
