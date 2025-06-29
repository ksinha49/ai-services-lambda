import os
import json
import logging

from common_utils.get_ssm import get_config

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s", "%Y-%m-%dT%H:%M:%S%z")
)
logger.addHandler(_handler)

CHUNK_SIZE = int(get_config("CHUNK_SIZE") or os.environ.get("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(get_config("CHUNK_OVERLAP") or os.environ.get("CHUNK_OVERLAP", "100"))


def chunk_text(text: str):
    step = CHUNK_SIZE - CHUNK_OVERLAP
    if step <= 0:
        step = CHUNK_SIZE
    return [text[i:i + CHUNK_SIZE] for i in range(0, len(text), step)]


def lambda_handler(event, context):
    text = event.get("text", "")
    doc_type = event.get("docType") or event.get("type")
    chunks = chunk_text(text)
    payload = {"chunks": chunks}
    if doc_type:
        payload["docType"] = doc_type
    return payload
