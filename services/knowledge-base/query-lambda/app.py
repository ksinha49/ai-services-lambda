"""Query the knowledge base using the summarization Lambda."""

from __future__ import annotations

import json
import os
import logging
import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s", "%Y-%m-%dT%H:%M:%S%z"))
if not logger.handlers:
    logger.addHandler(_handler)

SUMMARY_FUNCTION_ARN = os.environ.get("SUMMARY_FUNCTION_ARN")

lambda_client = boto3.client("lambda")


def lambda_handler(event: dict, context: object) -> dict:
    """Forward ``event`` to the summarization Lambda."""

    resp = lambda_client.invoke(
        FunctionName=SUMMARY_FUNCTION_ARN,
        Payload=json.dumps(event).encode("utf-8"),
    )
    return json.loads(resp["Payload"].read())
