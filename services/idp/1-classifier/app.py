"""
Classifier Lambda function.

This function routes newly uploaded objects from the RAW_PREFIX into
either OFFICE_PREFIX or PDF_RAW_PREFIX based on file type.  PDFs are
inspected with PyMuPDF to determine whether they contain embedded text.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Iterable

import boto3
from common_utils import get_config
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
if not logger.handlers:
    logger.addHandler(_handler)

s3_client = boto3.client("s3")


def _pdf_has_text(pdf_bytes: bytes) -> bool:
    """Return True if any page in the PDF has text."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page in doc:
            if page.get_text().strip():
                return True
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Failed to inspect PDF: %s", exc)
    return False

def _copy_to_prefix(bucket_name: str, raw_prefix: str, key: str, body: bytes, dest_prefix: str, content_type: str | None = None) -> None:
    dest_key = dest_prefix + key[len(raw_prefix):]
    logger.info("Copying %s to %s", key, dest_key)
    put_kwargs = {"Bucket": bucket_name, "Key": dest_key, "Body": body}
    if content_type:
        put_kwargs["ContentType"] = content_type
    s3_client.put_object(**put_kwargs)

def _handle_record(record: dict) -> None:
    bucket = record.get("s3", {}).get("bucket", {}).get("name")
    key = record.get("s3", {}).get("object", {}).get("key")
    bucket_name = get_config("BUCKET_NAME", bucket, key)
    raw_prefix = get_config("RAW_PREFIX", bucket, key) or ""
    office_prefix = get_config("OFFICE_PREFIX", bucket, key) or "office-docs/"
    pdf_raw_prefix = get_config("PDF_RAW_PREFIX", bucket, key) or "pdf-raw/"
    if raw_prefix and not raw_prefix.endswith("/"):
        raw_prefix += "/"
    if office_prefix and not office_prefix.endswith("/"):
        office_prefix += "/"
    if pdf_raw_prefix and not pdf_raw_prefix.endswith("/"):
        pdf_raw_prefix += "/"
    if bucket != bucket_name or not key:
        logger.info("Skipping record with bucket=%s key=%s", bucket, key)
        return
    if not key.startswith(raw_prefix):
        logger.info("Key %s outside prefix %s - skipping", key, raw_prefix)
        return

    logger.info("Processing %s", key)
    obj = s3_client.get_object(Bucket=bucket_name, Key=key)
    body = obj["Body"].read()
    content_type = obj.get("ContentType")

    ext = os.path.splitext(key)[1].lower()
    if ext == ".pdf":
        has_text = _pdf_has_text(body)
        logger.info("PDF %s has embedded text: %s", key, has_text)
        prefix = office_prefix if has_text else pdf_raw_prefix
    else:
        prefix = office_prefix
    _copy_to_prefix(bucket_name, raw_prefix, key, body, prefix, content_type)

def _iter_records(event: dict) -> Iterable[dict]:
    for record in event.get("Records", []):
        yield record

def lambda_handler(event: dict, context) -> dict:
    logger.info("Received event: %s", event)
    for rec in _iter_records(event):
        try:
            _handle_record(rec)
        except Exception as exc:  # pragma: no cover - runtime safety
            logger.error("Error processing record %s: %s", rec, exc)
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "1-classifier executed"}),
    }
