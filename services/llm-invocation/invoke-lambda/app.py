# ------------------------------------------------------------------------------
# app.py
# ------------------------------------------------------------------------------
"""
Lambda to invoke an LLM backend.

This function abstracts the Bedrock/Ollama API calls so the router and
routing strategies can delegate all model interactions here.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

import boto3
import httpx
from httpx import HTTPStatusError

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


def _invoke_bedrock_runtime(prompt: str, model_id: str | None = None) -> Dict[str, Any]:
    runtime = boto3.client("bedrock-runtime")
    model_id = model_id or os.environ.get("STRONG_MODEL_ID") or os.environ.get("WEAK_MODEL_ID")
    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2048,
            "messages": [{"role": "user", "content": prompt}],
        }
    )
    resp = runtime.invoke_model(body=body, modelId=model_id)
    data = json.loads(resp.get("body").read())
    return {"reply": data.get("content", {}).get("text", "")}


def _invoke_bedrock_openai(payload: Dict[str, Any]) -> Dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if BEDROCK_API_KEY:
        headers["Authorization"] = f"Bearer {BEDROCK_API_KEY}"
    resp = httpx.post(BEDROCK_OPENAI_ENDPOINT, json=payload, headers=headers)
    resp.raise_for_status()
    return resp.json()


def _invoke_ollama(payload: Dict[str, Any]) -> Dict[str, Any]:
    payload.setdefault("model", OLLAMA_DEFAULT_MODEL)
    resp = httpx.post(OLLAMA_ENDPOINT, json=payload)
    resp.raise_for_status()
    return resp.json()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Invoke the selected backend and return the raw response."""
    backend = event.get("backend")
    prompt = event.get("prompt")
    if not backend or not prompt:
        return {"message": "Missing backend or prompt"}

    payload = dict(event)
    payload.pop("backend", None)

    try:
        if backend == "bedrock":
            if BEDROCK_OPENAI_ENDPOINT:
                return _invoke_bedrock_openai(payload)
            return _invoke_bedrock_runtime(prompt, payload.get("model"))
        return _invoke_ollama(payload)
    except HTTPStatusError as e:
        logger.error(
            "LLM request failed [%d]: %s", e.response.status_code, e.response.text
        )
        raise
    except Exception:
        logger.exception("Unexpected error in llm invocation")
        raise
