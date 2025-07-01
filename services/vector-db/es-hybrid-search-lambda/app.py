# ---------------------------------------------------------------------------
# app.py
# ---------------------------------------------------------------------------
"""Perform hybrid keyword and vector search against Elasticsearch."""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List

from common_utils import ElasticsearchClient

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

client = ElasticsearchClient()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Run hybrid search with optional keywords."""

    embedding = event.get("embedding")
    if embedding is None:
        return {"matches": []}

    keywords: Iterable[str] = event.get("keywords", [])
    top_k = int(event.get("top_k", 5))
    results = client.hybrid_search(embedding, keywords=keywords, top_k=top_k)
    return {"matches": results}
