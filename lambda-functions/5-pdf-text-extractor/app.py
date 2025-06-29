# ------------------------------------------------------------------------------
# app.py
# ------------------------------------------------------------------------------
"""PDF text extraction Lambda.

Triggered for each single-page PDF under ``PDF_TEXT_PAGE_PREFIX``. The
page is read using :mod:`fitz` and the result of ``get_text("json")`` is
written to ``TEXT_PAGE_PREFIX/{documentId}/page_NNN.json``.

Environment variables
---------------------
``BUCKET_NAME``
    Name of the S3 bucket used for both input and output. **Required.**
``PDF_TEXT_PAGE_PREFIX``
    Prefix where single-page PDFs with embedded text are stored. Defaults
    to ``"text-pages/"``.
``TEXT_PAGE_PREFIX``
    Destination prefix for the extracted JSON. Defaults to ``"text-pages/"``.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Iterable

import boto3
import fitz  # PyMuPDF

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
PDF_TEXT_PAGE_PREFIX = os.environ.get("PDF_TEXT_PAGE_PREFIX", "text-pages/")
TEXT_PAGE_PREFIX = os.environ.get("TEXT_PAGE_PREFIX", "text-pages/")

for name in ("PDF_TEXT_PAGE_PREFIX", "TEXT_PAGE_PREFIX"):
    val = globals()[name]
    if val and not val.endswith("/"):
        globals()[name] = val + "/"

if not BUCKET_NAME:
    raise RuntimeError("BUCKET_NAME environment variable must be set")


def _iter_records(event: dict) -> Iterable[dict]:
    """Yield S3 event records from *event*."""

    for record in event.get("Records", []):
        yield record


def _extract_text(pdf_bytes: bytes) -> str:
    """Return JSON text for the first page of the PDF."""

    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        if doc.page_count:
            page = doc[0]
            return page.get_text("json")
    return ""


def _handle_record(record: dict) -> None:
    """Process a single S3 event record."""

    bucket = record.get("s3", {}).get("bucket", {}).get("name")
    key = record.get("s3", {}).get("object", {}).get("key")
    if bucket != BUCKET_NAME or not key:
        logger.info("Skipping record with bucket=%s key=%s", bucket, key)
        return
    if not key.startswith(PDF_TEXT_PAGE_PREFIX):
        logger.info("Key %s outside prefix %s - skipping", key, PDF_TEXT_PAGE_PREFIX)
        return
    if not key.lower().endswith(".pdf"):
        logger.info("Key %s is not a PDF - skipping", key)
        return

    obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
    body = obj["Body"].read()
    try:
        text_json = _extract_text(body)
    except Exception as exc:  # pragma: no cover - runtime safety
        logger.error("Failed to extract text from %s: %s", key, exc)
        return

    rel_key = key[len(PDF_TEXT_PAGE_PREFIX):]
    dest_key = TEXT_PAGE_PREFIX + os.path.splitext(rel_key)[0] + ".json"
    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key=dest_key,
        Body=text_json.encode("utf-8"),
        ContentType="application/json",
    )
    logger.info("Wrote %s", dest_key)

def lambda_handler(event: dict, context: dict) -> dict:
    """Entry point for the Lambda function."""
    logger.info("Received event for 5-pdf-text-extractor: %s", event)
    for rec in _iter_records(event):
        try:
            _handle_record(rec)
        except Exception as exc:  # pragma: no cover - runtime safety
            logger.error("Error processing record %s: %s", rec, exc)
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "5-pdf-text-extractor executed"})
    }
