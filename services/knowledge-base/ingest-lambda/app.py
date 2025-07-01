"""Start the ingestion workflow for a knowledge base document."""

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

STATE_MACHINE_ARN = os.environ.get("STATE_MACHINE_ARN")

sfn = boto3.client("stepfunctions")


def lambda_handler(event: dict, context: object) -> dict:
    """Trigger the RAG ingestion state machine."""

    text = event.get("text")
    if not text:
        return {"started": False}

    payload = {"text": text}
    doc_type = event.get("docType") or event.get("type")
    if doc_type:
        payload["docType"] = doc_type
    sfn.start_execution(stateMachineArn=STATE_MACHINE_ARN, input=json.dumps(payload))
    return {"started": True}
