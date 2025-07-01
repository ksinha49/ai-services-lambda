# ---------------------------------------------------------------------------
# app.py
# ---------------------------------------------------------------------------
"""Search an Elasticsearch index using a vector embedding."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from common_utils import ElasticsearchClient

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s", "%Y-%m-%dT%H:%M:%S%z")
)
if not logger.handlers:
    logger.addHandler(_handler)

client = ElasticsearchClient()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Search for the best matching documents."""

    embedding: List[float] | None = event.get("embedding")
    if embedding is None:
        return {"matches": []}

    top_k = int(event.get("top_k", 5))
    results = client.search(embedding, top_k=top_k)
    return {"matches": results}
