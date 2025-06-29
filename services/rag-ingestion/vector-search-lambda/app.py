import os
from pymilvus import Collection, connections

HOST = os.environ.get("MILVUS_HOST", "localhost")
PORT = int(os.environ.get("MILVUS_PORT", "19530"))
COLLECTION_NAME = os.environ.get("MILVUS_COLLECTION", "docs")
TOP_K = int(os.environ.get("TOP_K", "5"))

connections.connect(alias="default", host=HOST, port=PORT)
collection = Collection(COLLECTION_NAME)


def lambda_handler(event, context):
    embedding = event.get("embedding")
    if embedding is None:
        return {"matches": []}
    res = collection.search([
        embedding
    ], "embedding", {"metric_type": "L2"}, limit=TOP_K, output_fields=["metadata"])
    matches = [
        {"id": r.id, "score": r.distance, "metadata": r.entity.get("metadata")}
        for r in res[0]
    ]
    return {"matches": matches}
