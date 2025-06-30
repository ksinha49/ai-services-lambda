"""Backend invocation helpers for the LLM invocation Lambda."""

from __future__ import annotations

import json
import os
from itertools import cycle
from typing import Any, Callable, Dict, List, Sequence

import boto3
import httpx


BEDROCK_API_KEY = os.environ.get("BEDROCK_API_KEY")
OLLAMA_DEFAULT_MODEL = os.environ.get("OLLAMA_DEFAULT_MODEL", "")


def _get_endpoints(plural_var: str, single_var: str) -> List[str]:
    raw = os.environ.get(plural_var)
    if raw:
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        if parts:
            return parts
    single = os.environ.get(single_var)
    return [single] if single else []


def _make_selector(endpoints: Sequence[str]) -> Callable[[], str]:
    """Return a round-robin selector over ``endpoints``."""

    if not endpoints:
        def _select() -> str:
            raise RuntimeError("No endpoints configured")
        return _select

    cyc = cycle(endpoints)

    def _select() -> str:
        return next(cyc)

    return _select


BEDROCK_OPENAI_ENDPOINTS = _get_endpoints(
    "BEDROCK_OPENAI_ENDPOINTS", "BEDROCK_OPENAI_ENDPOINT"
)
OLLAMA_ENDPOINTS = _get_endpoints("OLLAMA_ENDPOINTS", "OLLAMA_ENDPOINT")

choose_bedrock_openai_endpoint = _make_selector(BEDROCK_OPENAI_ENDPOINTS)
choose_ollama_endpoint = _make_selector(OLLAMA_ENDPOINTS)


def invoke_bedrock_runtime(prompt: str, model_id: str | None = None) -> Dict[str, Any]:
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


def invoke_bedrock_openai(payload: Dict[str, Any]) -> Dict[str, Any]:
    endpoint = choose_bedrock_openai_endpoint()
    headers = {"Content-Type": "application/json"}
    if BEDROCK_API_KEY:
        headers["Authorization"] = f"Bearer {BEDROCK_API_KEY}"
    resp = httpx.post(endpoint, json=payload, headers=headers)
    resp.raise_for_status()
    return resp.json()


def invoke_ollama(payload: Dict[str, Any]) -> Dict[str, Any]:
    endpoint = choose_ollama_endpoint()
    payload.setdefault("model", OLLAMA_DEFAULT_MODEL)
    resp = httpx.post(endpoint, json=payload)
    resp.raise_for_status()
    return resp.json()


__all__ = [
    "choose_bedrock_openai_endpoint",
    "choose_ollama_endpoint",
    "invoke_bedrock_openai",
    "invoke_bedrock_runtime",
    "invoke_ollama",
]

# TODO: support more advanced endpoint selection algorithms (e.g., health checks)
