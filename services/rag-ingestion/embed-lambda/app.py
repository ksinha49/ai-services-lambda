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

EMBED_MODEL = get_config("EMBED_MODEL") or os.environ.get("EMBED_MODEL", "dummy")


def _dummy_embed(text: str):
    return [float(ord(c) % 5) for c in text]


_MODEL_MAP = {
    "dummy": _dummy_embed,
}


def lambda_handler(event, context):
    chunks = event.get("chunks", [])
    embed_fn = _MODEL_MAP.get(EMBED_MODEL, _dummy_embed)
    embeddings = [embed_fn(c) for c in chunks]
    return {"embeddings": embeddings}
