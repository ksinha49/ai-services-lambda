# ------------------------------------------------------------------------------
# app.py
# ------------------------------------------------------------------------------
"""OCR extraction Lambda for scanned PDF pages.

Triggered for each single-page PDF under ``PDF_SCAN_PAGE_PREFIX``. The
page is rasterised using :mod:`fitz` at ``DPI`` resolution and passed to
the configured OCR engine via helpers from :mod:`ocr_module`.  The
recognised text is stored as Markdown under ``TEXT_PAGE_PREFIX`` using
the same relative path as the source page.

Environment variables
---------------------
``BUCKET_NAME``
    Name of the S3 bucket used for input and output. **Required.**
``PDF_SCAN_PAGE_PREFIX``
    Prefix where scanned single-page PDFs are stored. Defaults to
    ``"scan-pages/"``.
``TEXT_PAGE_PREFIX``
    Destination prefix for the extracted Markdown. Defaults to
    ``"text-pages/"``.
``DPI``
    Rasterisation resolution for PyMuPDF. Defaults to ``300``.
``OCR_ENGINE``
    OCR engine to use, ``"easyocr"``, ``"paddleocr"`` or ``"trocr"``. Defaults to
    ``"easyocr"``.
``TROCR_ENDPOINT``
    HTTP endpoint for the TrOCR engine when ``OCR_ENGINE`` is ``"trocr"``.
``DOCLING_ENDPOINT``
    HTTP endpoint for the Docling engine when ``OCR_ENGINE`` is ``"docling"``.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Iterable

import boto3
import fitz  # PyMuPDF
import cv2
import numpy as np
from paddleocr import PaddleOCR

from ocr_module import (
    easyocr,
    _perform_ocr,
    post_process_text,
    convert_to_markdown,
)

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

DPI = int(os.environ.get("DPI", "300"))
BUCKET_NAME = os.environ.get("BUCKET_NAME")
PDF_SCAN_PAGE_PREFIX = os.environ.get("PDF_SCAN_PAGE_PREFIX", "scan-pages/")
TEXT_PAGE_PREFIX = os.environ.get("TEXT_PAGE_PREFIX", "text-pages/")
OCR_ENGINE = os.environ.get("OCR_ENGINE", "easyocr").lower()
TROCR_ENDPOINT = os.environ.get("TROCR_ENDPOINT")
DOCLING_ENDPOINT = os.environ.get("DOCLING_ENDPOINT")

for name in ("PDF_SCAN_PAGE_PREFIX", "TEXT_PAGE_PREFIX"):
    val = globals()[name]
    if val and not val.endswith("/"):
        globals()[name] = val + "/"

if not BUCKET_NAME:
    raise RuntimeError("BUCKET_NAME environment variable must be set")


def _iter_records(event: dict) -> Iterable[dict]:
    """Yield S3 event records from *event*."""

    for record in event.get("Records", []):
        yield record


def _rasterize_page(pdf_bytes: bytes, dpi: int) -> np.ndarray | None:
    """Return an image array for the first page of *pdf_bytes*."""

    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        if not doc.page_count:
            return None
        page = doc[0]
        matrix = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=matrix)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, pix.n
        )
        if pix.alpha:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        return img


def _ocr_image(img: np.ndarray) -> str:
    """Run OCR on *img* and return Markdown text."""

    # Encode the image to bytes for the OCR helper
    ok, encoded = cv2.imencode(".png", img)
    if not ok:
        raise ValueError("Failed to encode image for OCR")

    engine = OCR_ENGINE
    if engine == "paddleocr":
        reader = PaddleOCR()
        ctx = reader
    elif engine == "trocr":
        ctx = None
    elif engine == "docling":
        ctx = None
    else:
        reader = easyocr.Reader(["en"], gpu=False)
        ctx = reader
        engine = "easyocr"
    text, _ = _perform_ocr(ctx, engine, bytes(encoded))
    text = post_process_text(text)
    return convert_to_markdown(text, 1)


def _handle_record(record: dict) -> None:
    """Process a single S3 event record."""

    bucket = record.get("s3", {}).get("bucket", {}).get("name")
    key = record.get("s3", {}).get("object", {}).get("key")
    if bucket != BUCKET_NAME or not key:
        logger.info("Skipping record with bucket=%s key=%s", bucket, key)
        return
    if not key.startswith(PDF_SCAN_PAGE_PREFIX):
        logger.info("Key %s outside prefix %s - skipping", key, PDF_SCAN_PAGE_PREFIX)
        return
    if not key.lower().endswith(".pdf"):
        logger.info("Key %s is not a PDF - skipping", key)
        return

    obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
    body = obj["Body"].read()
    try:
        img = _rasterize_page(body, DPI)
        if img is None:
            logger.info("No pages in %s", key)
            return
        text = _ocr_image(img)
    except Exception as exc:  # pragma: no cover - runtime safety
        logger.error("Failed to OCR %s: %s", key, exc)
        return

    rel_key = key[len(PDF_SCAN_PAGE_PREFIX):]
    dest_key = TEXT_PAGE_PREFIX + os.path.splitext(rel_key)[0] + ".md"
    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key=dest_key,
        Body=text.encode("utf-8"),
        ContentType="text/markdown",
    )
    logger.info("Wrote %s", dest_key)

def lambda_handler(event: dict, context: dict) -> dict:
    """Entry point for the Lambda function."""

    logger.info("Received event for 6-pdf-ocr-extractor: %s", event)
    for rec in _iter_records(event):
        try:
            _handle_record(rec)
        except Exception as exc:  # pragma: no cover - runtime safety
            logger.error("Error processing record %s: %s", rec, exc)
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "6-pdf-ocr-extractor executed"})
    }
