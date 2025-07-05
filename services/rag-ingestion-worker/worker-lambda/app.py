"""Worker Lambda invoking the RAG ingestion state machine."""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

import boto3
from botocore.exceptions import ClientError
from common_utils import configure_logger

logger = configure_logger(__name__)

STATE_MACHINE_ARN = os.environ.get("STATE_MACHINE_ARN")
if not STATE_MACHINE_ARN:
    raise RuntimeError("STATE_MACHINE_ARN not configured")

sfn = boto3.client("stepfunctions")


def _process_record(record: Dict[str, Any]) -> None:
    payload = json.loads(record.get("body", "{}"))
    sfn.start_execution(
        stateMachineArn=STATE_MACHINE_ARN,
        input=json.dumps(payload),
    )


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    for record in event.get("Records", []):
        try:
            _process_record(record)
        except ClientError as exc:
            logger.error("Failed to start state machine: %s", exc)
            return {"started": False, "error": str(exc)}
        except Exception as exc:  # pragma: no cover - unexpected runtime error
            logger.exception("Unexpected error starting state machine")
            return {"started": False, "error": str(exc)}
    return {"started": True}
