# ------------------------------------------------------------------------------
# app.py
# ------------------------------------------------------------------------------
"""PDF page splitter."""

from __future__ import annotations

import io
import json
import logging
import os
from typing import Iterable

import boto3
from PyPDF2 import PdfReader, PdfWriter

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
PDF_RAW_PREFIX = os.environ.get("PDF_RAW_PREFIX", "")
PDF_PAGE_PREFIX = os.environ.get("PDF_PAGE_PREFIX", "pdf-pages/")

for name in ("PDF_RAW_PREFIX", "PDF_PAGE_PREFIX"):
    val = globals()[name]
    if val and not val.endswith("/"):
        globals()[name] = val + "/"

if not BUCKET_NAME:
    raise RuntimeError("BUCKET_NAME environment variable must be set")


def _iter_records(event: dict) -> Iterable[dict]:
    for record in event.get("Records", []):
        yield record


def _split_pdf(key: str) -> None:
    obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
    pdf_bytes = obj["Body"].read()
    doc = PdfReader(io.BytesIO(pdf_bytes))
    doc_id = os.path.splitext(os.path.basename(key))[0]
    for idx, page in enumerate(doc.pages, start=1):
        writer = PdfWriter()
        writer.add_page(page)
        buf = io.BytesIO()
        writer.write(buf)
        buf.seek(0)
        dest_key = f"{PDF_PAGE_PREFIX}{doc_id}/page_{idx:03d}.pdf"
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=dest_key,
            Body=buf.getvalue(),
            ContentType="application/pdf",
        )
        logger.info("Wrote %s", dest_key)

    manifest_key = f"{PDF_PAGE_PREFIX}{doc_id}/manifest.json"
    manifest = {
        "documentId": doc_id,
        "pages": len(doc.pages),
    }
    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key=manifest_key,
        Body=json.dumps(manifest).encode("utf-8"),
        ContentType="application/json",
    )
    logger.info("Wrote %s", manifest_key)


def _handle_record(record: dict) -> None:
    bucket = record.get("s3", {}).get("bucket", {}).get("name")
    key = record.get("s3", {}).get("object", {}).get("key")
    if bucket != BUCKET_NAME or not key:
        logger.info("Skipping record with bucket=%s key=%s", bucket, key)
        return
    if not key.startswith(PDF_RAW_PREFIX):
        logger.info("Key %s outside prefix %s - skipping", key, PDF_RAW_PREFIX)
        return
    if not key.lower().endswith(".pdf"):
        logger.info("Key %s is not a PDF - skipping", key)
        return
    logger.info("Splitting %s", key)
    _split_pdf(key)

def lambda_handler(event: dict, context: dict) -> dict:
    logger.info("Received event for 3-pdf-split: %s", event)
    for rec in _iter_records(event):
        try:
            _handle_record(rec)
        except Exception as exc:  # pragma: no cover - runtime safety
            logger.error("Error processing record %s: %s", rec, exc)
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "3-pdf-split executed"})
    }
