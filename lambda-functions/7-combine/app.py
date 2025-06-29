# ------------------------------------------------------------------------------
# app.py
# ------------------------------------------------------------------------------
"""Combine per-page text outputs into a single document JSON.

Triggered whenever a page-level text object is written.  Once all page
outputs exist for a document (as indicated by the ``manifest.json`` from
``PDF_PAGE_PREFIX``), the individual page results are merged in page order
and written to ``TEXT_DOC_PREFIX/{documentId}.json``.

Environment variables
---------------------
``BUCKET_NAME``
    Name of the S3 bucket used for input and output. **Required.**
``PDF_PAGE_PREFIX``
    Prefix where PDF pages and the ``manifest.json`` are stored. Defaults to
    ``"pdf-pages/"``.
``TEXT_PAGE_PREFIX``
    Prefix containing per-page text outputs. Defaults to ``"text-pages/"``.
``TEXT_DOC_PREFIX``
    Destination prefix for the combined document JSON. Defaults to
    ``"text-docs/"``.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Iterable

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
PDF_PAGE_PREFIX = os.environ.get("PDF_PAGE_PREFIX", "pdf-pages/")
TEXT_PAGE_PREFIX = os.environ.get("TEXT_PAGE_PREFIX", "text-pages/")
TEXT_DOC_PREFIX = os.environ.get("TEXT_DOC_PREFIX", "text-docs/")

for name in ("PDF_PAGE_PREFIX", "TEXT_PAGE_PREFIX", "TEXT_DOC_PREFIX"):
    val = globals()[name]
    if val and not val.endswith("/"):
        globals()[name] = val + "/"

if not BUCKET_NAME:
    raise RuntimeError("BUCKET_NAME environment variable must be set")


def _iter_records(event: dict) -> Iterable[dict]:
    """Yield S3 event records from *event*."""

    for record in event.get("Records", []):
        yield record


def _load_manifest(doc_id: str) -> dict | None:
    """Return the manifest dictionary for *doc_id* or ``None`` if missing."""

    key = f"{PDF_PAGE_PREFIX}{doc_id}/manifest.json"
    try:
        obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
    except s3_client.exceptions.NoSuchKey:  # pragma: no cover - defensive
        logger.info("Manifest %s not found", key)
        return None
    return json.loads(obj["Body"].read())


def _page_key(doc_id: str, page_num: int) -> str | None:
    """Return the S3 key for page ``page_num`` of ``doc_id`` if it exists."""

    base = f"{TEXT_PAGE_PREFIX}{doc_id}/page_{page_num:03d}"
    for ext in (".json", ".md"):
        key = base + ext
        try:
            s3_client.head_object(Bucket=BUCKET_NAME, Key=key)
        except s3_client.exceptions.ClientError as exc:  # pragma: no cover - defensive
            if exc.response.get("Error", {}).get("Code") == "404":
                continue
            raise
        else:
            return key
    return None


def _read_page(key: str):
    """Return the parsed content for page ``key``."""

    obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
    body = obj["Body"].read()
    if key.endswith(".json"):
        try:
            return json.loads(body)
        except Exception:  # pragma: no cover - defensive
            return json.loads(body.decode("utf-8"))
    return body.decode("utf-8")


def _combine_document(doc_id: str) -> None:
    """If all page outputs for ``doc_id`` exist, merge them and upload."""

    manifest = _load_manifest(doc_id)
    if not manifest:
        return

    page_count = int(manifest.get("pages", 0))

    page_keys: list[str] = []
    for idx in range(1, page_count + 1):
        key = _page_key(doc_id, idx)
        if not key:
            logger.info("Waiting for page %03d of %s", idx, doc_id)
            return
        page_keys.append(key)

    pages = [_read_page(k) for k in page_keys]
    payload = {"documentId": doc_id, "type": "pdf", "pages": pages}

    dest_key = f"{TEXT_DOC_PREFIX}{doc_id}.json"
    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key=dest_key,
        Body=json.dumps(payload).encode("utf-8"),
        ContentType="application/json",
    )
    logger.info("Wrote %s", dest_key)


def _handle_record(record: dict) -> None:
    """Process a single S3 event record."""

    bucket = record.get("s3", {}).get("bucket", {}).get("name")
    key = record.get("s3", {}).get("object", {}).get("key")
    if bucket != BUCKET_NAME or not key:
        logger.info("Skipping record with bucket=%s key=%s", bucket, key)
        return
    if not key.startswith(TEXT_PAGE_PREFIX):
        logger.info("Key %s outside prefix %s - skipping", key, TEXT_PAGE_PREFIX)
        return

    rel = key[len(TEXT_PAGE_PREFIX):]
    parts = rel.split("/", 1)
    if not parts:
        logger.info("Unexpected key structure: %s", key)
        return
    doc_id = parts[0]
    _combine_document(doc_id)


def lambda_handler(event: dict, context: dict) -> dict:
    """Entry point for the Lambda function."""

    logger.info("Received event for 7-combine: %s", event)
    for rec in _iter_records(event):
        try:
            _handle_record(rec)
        except Exception as exc:  # pragma: no cover - runtime safety
            logger.error("Error processing record %s: %s", rec, exc)
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "7-combine executed"})
    }
