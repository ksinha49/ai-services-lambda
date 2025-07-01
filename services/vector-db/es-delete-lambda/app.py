# ---------------------------------------------------------------------------
# app.py
# ---------------------------------------------------------------------------
"""Delete documents from an Elasticsearch index."""

from __future__ import annotations

import logging
from common_utils import configure_logger
from typing import Any, Dict, Iterable

from common_utils import ElasticsearchClient

# Module Metadata
__author__ = "Koushik Sinha"
__version__ = "1.0.0"
__modified_by__ = "Koushik Sinha"

logger = configure_logger(__name__)

client = ElasticsearchClient()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Delete the provided IDs from Elasticsearch."""

    ids: Iterable[str] = event.get("ids", [])
    deleted = client.delete(ids)
    return {"deleted": deleted}
