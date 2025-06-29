# ------------------------------------------------------------------------------
# app.py
# ------------------------------------------------------------------------------
"""
Module: app.py
Description:
  Basic Lambda handler for 8-output.
Version: 1.0.0
"""

from __future__ import annotations
import json
import logging
import os
import urllib.error
import urllib.request

import boto3

__author__ = "Balakrishna"
__version__ = "1.0.0"
__modified_by__ = "Koushik Sinha"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s", "%Y-%m-%dT%H:%M:%S%z")
)
logger.addHandler(_handler)

s3_client = boto3.client("s3")

BUCKET_NAME = os.environ.get("BUCKET_NAME")
TEXT_DOC_PREFIX = os.environ.get("TEXT_DOC_PREFIX", "text-docs/")
EDI_SEARCH_API_URL = os.environ.get("EDI_SEARCH_API_URL")
EDI_SEARCH_API_KEY = os.environ.get("EDI_SEARCH_API_KEY")

if TEXT_DOC_PREFIX and not TEXT_DOC_PREFIX.endswith("/"):
    TEXT_DOC_PREFIX += "/"

if not BUCKET_NAME:
    raise RuntimeError("BUCKET_NAME environment variable must be set")
if not EDI_SEARCH_API_URL:
    raise RuntimeError("EDI_SEARCH_API_URL environment variable must be set")


def _iter_records(event: dict):
    """Yield S3 event records from *event*."""

    for record in event.get("Records", []):
        yield record


def _post_to_api(payload: dict) -> bool:
    """Send *payload* to the external API and return ``True`` on success."""

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(EDI_SEARCH_API_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if EDI_SEARCH_API_KEY:
        req.add_header("x-api-key", EDI_SEARCH_API_KEY)

    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.getcode()
            if 200 <= status < 300:
                return True
            logger.error("API returned status %s for %s", status, payload.get("documentId"))
    except urllib.error.HTTPError as exc:
        msg = exc.read().decode()
        logger.error(
            "HTTP error posting %s: %s %s",
            payload.get("documentId"),
            exc.code,
            msg,
        )
    except Exception as exc:
        logger.error("Failed to post %s: %s", payload.get("documentId"), exc)
    return False


def _handle_record(record: dict) -> None:
    """Process a single S3 event record."""

    bucket = record.get("s3", {}).get("bucket", {}).get("name")
    key = record.get("s3", {}).get("object", {}).get("key")
    if bucket != BUCKET_NAME or not key:
        logger.info("Skipping record with bucket=%s key=%s", bucket, key)
        return
    if not key.startswith(TEXT_DOC_PREFIX) or not key.lower().endswith(".json"):
        logger.info("Key %s outside prefix %s - skipping", key, TEXT_DOC_PREFIX)
        return

    try:
        obj = s3_client.get_object(Bucket=bucket, Key=key)
        body = obj["Body"].read()
        payload = json.loads(body)
    except Exception as exc:
        logger.error("Failed to read %s: %s", key, exc)
        return

    if _post_to_api(payload):
        logger.info("Successfully posted %s", key)
    else:
        logger.error("Failed to post %s", key)

def lambda_handler(event: dict, context: dict) -> dict:
    """Entry point for the Lambda function."""

    logger.info("Received event for 8-output: %s", event)
    for rec in _iter_records(event):
        try:
            _handle_record(rec)
        except Exception as exc:  # pragma: no cover - runtime safety
            logger.error("Error processing record %s: %s", rec, exc)

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "8-output executed"})
    }
