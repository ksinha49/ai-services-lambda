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

# Default sampling parameters for Bedrock models
DEFAULT_BEDROCK_TEMPERATURE = 0.5
DEFAULT_BEDROCK_NUM_CTX = 4096
DEFAULT_BEDROCK_MAX_TOKENS = 2048
DEFAULT_BEDROCK_TOP_P = 0.9
DEFAULT_BEDROCK_TOP_K = 50
DEFAULT_BEDROCK_MAX_TOKENS_TO_SAMPLE = 2048

BEDROCK_TEMPERATURE = float(
    os.environ.get("BEDROCK_TEMPERATURE", str(DEFAULT_BEDROCK_TEMPERATURE))
)
BEDROCK_NUM_CTX = int(os.environ.get("BEDROCK_NUM_CTX", str(DEFAULT_BEDROCK_NUM_CTX)))
BEDROCK_MAX_TOKENS = int(
    os.environ.get("BEDROCK_MAX_TOKENS", str(DEFAULT_BEDROCK_MAX_TOKENS))
)
BEDROCK_TOP_P = float(os.environ.get("BEDROCK_TOP_P", str(DEFAULT_BEDROCK_TOP_P)))
BEDROCK_TOP_K = int(os.environ.get("BEDROCK_TOP_K", str(DEFAULT_BEDROCK_TOP_K)))
BEDROCK_MAX_TOKENS_TO_SAMPLE = int(
    os.environ.get(
        "BEDROCK_MAX_TOKENS_TO_SAMPLE", str(DEFAULT_BEDROCK_MAX_TOKENS_TO_SAMPLE)
    )
)

# Default sampling parameters for Ollama
DEFAULT_OLLAMA_NUM_CTX = 4096
DEFAULT_OLLAMA_REPEAT_LAST_N = 64
DEFAULT_OLLAMA_REPEAT_PENALTY = 1.1
DEFAULT_OLLAMA_TEMPERATURE = 0.7
DEFAULT_OLLAMA_SEED = 42
DEFAULT_OLLAMA_STOP = "AI assistant:"
DEFAULT_OLLAMA_NUM_PREDICT = 42
DEFAULT_OLLAMA_TOP_K = 40
DEFAULT_OLLAMA_TOP_P = 0.9
DEFAULT_OLLAMA_MIN_P = 0.05

OLLAMA_NUM_CTX = int(os.environ.get("OLLAMA_NUM_CTX", str(DEFAULT_OLLAMA_NUM_CTX)))
OLLAMA_REPEAT_LAST_N = int(
    os.environ.get("OLLAMA_REPEAT_LAST_N", str(DEFAULT_OLLAMA_REPEAT_LAST_N))
)
OLLAMA_REPEAT_PENALTY = float(
    os.environ.get("OLLAMA_REPEAT_PENALTY", str(DEFAULT_OLLAMA_REPEAT_PENALTY))
)
OLLAMA_TEMPERATURE = float(
    os.environ.get("OLLAMA_TEMPERATURE", str(DEFAULT_OLLAMA_TEMPERATURE))
)
OLLAMA_SEED = int(os.environ.get("OLLAMA_SEED", str(DEFAULT_OLLAMA_SEED)))
OLLAMA_STOP = os.environ.get("OLLAMA_STOP", DEFAULT_OLLAMA_STOP)
OLLAMA_NUM_PREDICT = int(
    os.environ.get("OLLAMA_NUM_PREDICT", str(DEFAULT_OLLAMA_NUM_PREDICT))
)
OLLAMA_TOP_K = int(os.environ.get("OLLAMA_TOP_K", str(DEFAULT_OLLAMA_TOP_K)))
OLLAMA_TOP_P = float(os.environ.get("OLLAMA_TOP_P", str(DEFAULT_OLLAMA_TOP_P)))
OLLAMA_MIN_P = float(os.environ.get("OLLAMA_MIN_P", str(DEFAULT_OLLAMA_MIN_P)))


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
    """Call Bedrock using its OpenAI compatible runtime."""

    runtime = boto3.client("bedrock-runtime")
    model_id = model_id or os.environ.get("STRONG_MODEL_ID") or os.environ.get("WEAK_MODEL_ID")

    body = json.dumps(
        {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": BEDROCK_TEMPERATURE,
            "num_ctx": BEDROCK_NUM_CTX,
            "max_tokens": BEDROCK_MAX_TOKENS,
            "top_p": BEDROCK_TOP_P,
            "top_k": BEDROCK_TOP_K,
            "max_tokens_to_sample": BEDROCK_MAX_TOKENS_TO_SAMPLE,
        }
    )

    resp = runtime.invoke_model(
        modelId=model_id,
        body=body,
        contentType="application/json",
        accept="application/json",
    )

    data = json.loads(resp.get("body").read())
    reply = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    return {"reply": reply}


def invoke_bedrock_openai(payload: Dict[str, Any]) -> Dict[str, Any]:
    endpoint = choose_bedrock_openai_endpoint()
    headers = {"Content-Type": "application/json"}
    if BEDROCK_API_KEY:
        headers["Authorization"] = f"Bearer {BEDROCK_API_KEY}"
    payload.setdefault("temperature", BEDROCK_TEMPERATURE)
    payload.setdefault("num_ctx", BEDROCK_NUM_CTX)
    payload.setdefault("max_tokens", BEDROCK_MAX_TOKENS)
    payload.setdefault("top_p", BEDROCK_TOP_P)
    payload.setdefault("top_k", BEDROCK_TOP_K)
    payload.setdefault("max_tokens_to_sample", BEDROCK_MAX_TOKENS_TO_SAMPLE)
    resp = httpx.post(endpoint, json=payload, headers=headers)
    resp.raise_for_status()
    return resp.json()


def invoke_ollama(payload: Dict[str, Any]) -> Dict[str, Any]:
    endpoint = choose_ollama_endpoint()
    payload.setdefault("model", OLLAMA_DEFAULT_MODEL)
    payload.setdefault("num_ctx", OLLAMA_NUM_CTX)
    payload.setdefault("repeat_last_n", OLLAMA_REPEAT_LAST_N)
    payload.setdefault("repeat_penalty", OLLAMA_REPEAT_PENALTY)
    payload.setdefault("temperature", OLLAMA_TEMPERATURE)
    payload.setdefault("seed", OLLAMA_SEED)
    payload.setdefault("stop", OLLAMA_STOP)
    payload.setdefault("num_predict", OLLAMA_NUM_PREDICT)
    payload.setdefault("top_k", OLLAMA_TOP_K)
    payload.setdefault("top_p", OLLAMA_TOP_P)
    payload.setdefault("min_p", OLLAMA_MIN_P)
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
