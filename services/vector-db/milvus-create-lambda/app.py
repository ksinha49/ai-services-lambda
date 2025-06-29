# ---------------------------------------------------------------------------
# app.py
# ---------------------------------------------------------------------------
"""Create a Milvus collection if it does not exist."""

from __future__ import annotations

import logging
from typing import Any, Dict

from common_utils import MilvusClient

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s", "%Y-%m-%dT%H:%M:%S%z")
)
logger.addHandler(_handler)

client = MilvusClient()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Create the collection."""

    dimension = int(event.get("dimension", 768))
    client.create_collection(dimension=dimension)
    return {"created": True}
