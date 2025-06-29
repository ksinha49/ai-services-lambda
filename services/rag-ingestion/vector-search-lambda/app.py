import os
import logging

from common_utils import MilvusClient
from common_utils.get_ssm import get_config

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s", "%Y-%m-%dT%H:%M:%S%z")
)
logger.addHandler(_handler)

TOP_K = int(get_config("TOP_K") or os.environ.get("TOP_K", "5"))

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
