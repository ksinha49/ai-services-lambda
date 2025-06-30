# ------------------------------------------------------------------------------
# app.py
# ------------------------------------------------------------------------------
"""
Module: app.py
Description:
  Simple router Lambda that directs prompts to either a Bedrock
  OpenAI-compatible endpoint or an Ollama endpoint based on prompt
  complexity.
Version: 1.0.0
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict

import json
from main_router import route_event

import httpx
from httpx import HTTPStatusError

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

BEDROCK_OPENAI_ENDPOINT = os.environ.get("BEDROCK_OPENAI_ENDPOINT")
BEDROCK_API_KEY = os.environ.get("BEDROCK_API_KEY")
OLLAMA_ENDPOINT = os.environ.get("OLLAMA_ENDPOINT")
OLLAMA_DEFAULT_MODEL = os.environ.get("OLLAMA_DEFAULT_MODEL", "")

DEFAULT_PROMPT_COMPLEXITY_THRESHOLD = 20
PROMPT_COMPLEXITY_THRESHOLD = int(
    os.environ.get("PROMPT_COMPLEXITY_THRESHOLD", str(DEFAULT_PROMPT_COMPLEXITY_THRESHOLD))
)
def _choose_backend(prompt: str) -> str:
    """Return which backend to use based on prompt complexity."""
    complexity = len(prompt.split())
    if complexity >= PROMPT_COMPLEXITY_THRESHOLD:
        return "bedrock"
    return "ollama"


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Entry point for the router Lambda."""
    body_content = event.get("body")
    if body_content is not None:
        try:
            payload = json.loads(body_content or "{}")
        except json.JSONDecodeError:
            return {"statusCode": 400, "body": json.dumps({"message": "Invalid JSON"})}
    else:
        payload = dict(event)

    if not payload.get("prompt"):
        return {"statusCode": 400, "body": json.dumps({"message": "Missing 'prompt'"})}

    backend = payload.get("backend")
    strategy = payload.get("strategy")

    if not backend:
        if strategy and strategy != "complexity":
            logger.info("Strategy '%s' not implemented, using complexity", strategy)
        backend = route_event(payload).get("backend")

    url = BEDROCK_OPENAI_ENDPOINT if backend == "bedrock" else OLLAMA_ENDPOINT
    if not url:
        raise RuntimeError(f"{backend} endpoint not configured")

    request_payload = dict(payload)
    request_payload.pop("backend", None)
    request_payload.pop("strategy", None)
    headers = {"Content-Type": "application/json"}
    if backend == "bedrock":
        headers["Authorization"] = f"Bearer {BEDROCK_API_KEY}" if BEDROCK_API_KEY else ""
    else:
        request_payload.setdefault("model", OLLAMA_DEFAULT_MODEL)

    try:
        response = httpx.post(url, json=request_payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        data["backend"] = backend
        return {"statusCode": 200, "body": json.dumps(data)}
    except HTTPStatusError as e:
        logger.error(
            "Request to %s failed [%d]: %s", backend, e.response.status_code, e.response.text
        )
        raise
    except Exception:
        logger.exception("Unexpected error in router lambda")
        raise


