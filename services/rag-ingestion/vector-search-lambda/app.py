import os

from common_utils import MilvusClient

TOP_K = int(os.environ.get("TOP_K", "5"))

client = MilvusClient()


def lambda_handler(event, context):
    embedding = event.get("embedding")
    if embedding is None:
        return {"matches": []}

    results = client.search(embedding, top_k=TOP_K)
    matches = [
        {"id": r.id, "score": r.score, "metadata": r.metadata}
        for r in results
    ]
    return {"matches": matches}
