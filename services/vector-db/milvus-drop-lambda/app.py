# ---------------------------------------------------------------------------
# app.py
# ---------------------------------------------------------------------------
"""Drop a Milvus collection."""

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
    """Drop the collection."""

    client.drop_collection()
    return {"dropped": True}
