# ---------------------------------------------------------------------------
# app.py
# ---------------------------------------------------------------------------
"""Generate a summary using context from vector search results."""

from __future__ import annotations

import os
import json
import logging
import boto3
import httpx

from typing import Any, Dict

from common_utils.get_ssm import get_config

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s", "%Y-%m-%dT%H:%M:%S%z")
)
if not logger.handlers:
    logger.addHandler(_handler)

LAMBDA_FUNCTION = get_config("VECTOR_SEARCH_FUNCTION") or os.environ.get("VECTOR_SEARCH_FUNCTION")
SUMMARY_ENDPOINT = get_config("SUMMARY_ENDPOINT") or os.environ.get("SUMMARY_ENDPOINT")

lambda_client = boto3.client("lambda")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Return a summary for ``query`` using retrieved context."""

    query = event.get("query")
    emb = event.get("embedding")
    search_payload = {"embedding": emb} if emb is not None else {"query": query}
    resp = lambda_client.invoke(
        FunctionName=LAMBDA_FUNCTION,
        Payload=json.dumps(search_payload).encode("utf-8"),
    )
    result = json.loads(resp["Payload"].read())
    context_text = " ".join(
        m.get("metadata", {}).get("text", "") for m in result.get("matches", [])
    )
    r = httpx.post(SUMMARY_ENDPOINT, json={"query": query, "context": context_text})
    r.raise_for_status()
    return {"summary": r.json()}

