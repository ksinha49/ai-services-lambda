# ------------------------------------------------------------------------------
# app.py
# ------------------------------------------------------------------------------
"""PDF page classification Lambda.

This function runs for each single-page PDF written by the
``3-pdf-split`` step.  It inspects the page to determine whether any text
is present and then copies the page into one of two prefixes:

``PDF_TEXT_PAGE_PREFIX``
    Prefix for pages which contain embedded text.
``PDF_SCAN_PAGE_PREFIX``
    Prefix for scanned pages that require OCR.

Environment variables
---------------------
``BUCKET_NAME``
    Name of the S3 bucket used for both input and output. **Required.**
``PDF_PAGE_PREFIX``
    Prefix where single-page PDFs are written. Defaults to ``""``.
``PDF_TEXT_PAGE_PREFIX``
    Destination prefix for pages with embedded text. Defaults to
    ``"text-pages/"``.
``PDF_SCAN_PAGE_PREFIX``
    Destination prefix for scanned pages. Defaults to ``"scan-pages/"``.
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
PDF_PAGE_PREFIX = os.environ.get("PDF_PAGE_PREFIX", "")
PDF_TEXT_PAGE_PREFIX = os.environ.get("PDF_TEXT_PAGE_PREFIX", "text-pages/")
PDF_SCAN_PAGE_PREFIX = os.environ.get("PDF_SCAN_PAGE_PREFIX", "scan-pages/")

for name in ("PDF_PAGE_PREFIX", "PDF_TEXT_PAGE_PREFIX", "PDF_SCAN_PAGE_PREFIX"):
    val = globals()[name]
    if val and not val.endswith("/"):
        globals()[name] = val + "/"

if not BUCKET_NAME:
    raise RuntimeError("BUCKET_NAME environment variable must be set")


def _iter_records(event: dict) -> Iterable[dict]:
    """Yield S3 event records from *event*."""

    for record in event.get("Records", []):
        yield record


def _page_has_text(pdf_bytes: bytes) -> bool:
    """Return ``True`` if the single-page PDF contains any text."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if doc.page_count > 0:
            page = doc[0]
            return bool(page.get_text().strip())
    except Exception as exc:  # pragma: no cover - runtime safety
        logger.error("Failed to inspect PDF page: %s", exc)
    return False


def _copy_page(key: str, body: bytes, dest_prefix: str) -> None:
    """Write *body* to S3 under *dest_prefix* preserving the file name."""

    dest_key = dest_prefix + key[len(PDF_PAGE_PREFIX):]
    logger.info("Copying %s to %s", key, dest_key)
    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key=dest_key,
        Body=body,
        ContentType="application/pdf",
    )


def _handle_record(record: dict) -> None:
    """Inspect the PDF from *record* and copy it to the appropriate prefix."""

    bucket = record.get("s3", {}).get("bucket", {}).get("name")
    key = record.get("s3", {}).get("object", {}).get("key")
    if bucket != BUCKET_NAME or not key:
        logger.info("Skipping record with bucket=%s key=%s", bucket, key)
        return
    if not key.startswith(PDF_PAGE_PREFIX):
        logger.info("Key %s outside prefix %s - skipping", key, PDF_PAGE_PREFIX)
        return
    if not key.lower().endswith(".pdf"):
        logger.info("Key %s is not a PDF - skipping", key)
        return

    obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
    body = obj["Body"].read()
    has_text = _page_has_text(body)
    prefix = PDF_TEXT_PAGE_PREFIX if has_text else PDF_SCAN_PAGE_PREFIX
    logger.info("Page %s has text: %s", key, has_text)
    _copy_page(key, body, prefix)

def lambda_handler(event: dict, context: dict) -> dict:
    """Entry point for the Lambda function."""
    logger.info("Received event for 4-pdf-page-classifier: %s", event)
    for rec in _iter_records(event):
        try:
            _handle_record(rec)
        except Exception as exc:  # pragma: no cover - runtime safety
            logger.error("Error processing record %s: %s", rec, exc)
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "4-pdf-page-classifier executed"}),
    }
