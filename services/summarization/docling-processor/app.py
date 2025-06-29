"""Docling processor Lambda.

Triggered for objects written under ``TEXT_DOC_PREFIX``. The document
content is sent to the Docling service specified by ``DOCLING_ENDPOINT``
and the JSON response is stored under ``DOCLING_RESULTS_PREFIX``.

Environment variables
---------------------
``BUCKET_NAME``
    S3 bucket containing input and output objects. **Required.**
``DOCLING_ENDPOINT``
    URL for the Docling HTTP service. **Required.**
``TEXT_DOC_PREFIX``
    Prefix for input documents. Defaults to ``"text-docs/"``.
``DOCLING_RESULTS_PREFIX``
    Prefix for Docling output JSON. Defaults to ``"docling-results/"``.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Iterable

import boto3
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s", "%Y-%m-%dT%H:%M:%S%z")
)
logger.addHandler(_handler)

s3_client = boto3.client("s3")

BUCKET_NAME = os.environ.get("BUCKET_NAME")
DOCLING_ENDPOINT = os.environ.get("DOCLING_ENDPOINT")
TEXT_DOC_PREFIX = os.environ.get("TEXT_DOC_PREFIX", "text-docs/")
DOCLING_RESULTS_PREFIX = os.environ.get("DOCLING_RESULTS_PREFIX", "docling-results/")

for name in ("TEXT_DOC_PREFIX", "DOCLING_RESULTS_PREFIX"):
    val = globals()[name]
    if val and not val.endswith("/"):
        globals()[name] = val + "/"

if not BUCKET_NAME:
    raise RuntimeError("BUCKET_NAME environment variable must be set")
if not DOCLING_ENDPOINT:
    raise RuntimeError("DOCLING_ENDPOINT environment variable must be set")


def _iter_records(event: dict) -> Iterable[dict]:
    """Yield S3 event records from *event*."""
    for record in event.get("Records", []):
        yield record


def _post_docling(data: bytes) -> dict:
    """Send *data* to Docling and return the parsed JSON response."""
    resp = httpx.post(DOCLING_ENDPOINT, content=data)
    resp.raise_for_status()
    return resp.json()


def _handle_record(record: dict) -> None:
    """Process a single S3 event record."""
    bucket = record.get("s3", {}).get("bucket", {}).get("name")
    key = record.get("s3", {}).get("object", {}).get("key")
    if bucket != BUCKET_NAME or not key:
        logger.info("Skipping record with bucket=%s key=%s", bucket, key)
        return
    if not key.startswith(TEXT_DOC_PREFIX):
        logger.info("Key %s outside prefix %s - skipping", key, TEXT_DOC_PREFIX)
        return

    obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
    body = obj["Body"].read()
    try:
        result = _post_docling(body)
    except Exception as exc:  # pragma: no cover - runtime safety
        logger.error("Docling request failed for %s: %s", key, exc)
        return

    base = os.path.splitext(key[len(TEXT_DOC_PREFIX):])[0]
    dest_key = f"{DOCLING_RESULTS_PREFIX}{base}.json"
    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key=dest_key,
        Body=json.dumps(result).encode("utf-8"),
        ContentType="application/json",
    )
    logger.info("Wrote %s", dest_key)


def lambda_handler(event: dict, context: dict) -> dict:
    """Entry point for the Lambda function."""
    logger.info("Received event for docling-processor: %s", event)
    for rec in _iter_records(event):
        try:
            _handle_record(rec)
        except Exception as exc:  # pragma: no cover - runtime safety
            logger.error("Error processing record %s: %s", rec, exc)
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "docling-processor executed"})
    }
