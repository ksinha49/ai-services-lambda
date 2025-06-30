# ---------------------------------------------------------------------------
# app.py
# ---------------------------------------------------------------------------
"""Delete records from a Milvus collection by ID."""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable

from common_utils import MilvusClient

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s", "%Y-%m-%dT%H:%M:%S%z")
)
if not logger.handlers:
    logger.addHandler(_handler)

client = MilvusClient()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Delete the provided IDs from Milvus."""

    ids: Iterable[int] = event.get("ids", [])
    deleted = client.delete(ids)
    return {"deleted": deleted}
