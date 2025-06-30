# ------------------------------------------------------------------------------
# app.py
# ------------------------------------------------------------------------------
"""
Lambda to invoke an LLM backend.

This function abstracts the Bedrock/Ollama API calls so the router and
routing strategies can delegate all model interactions here.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from llm_invocation.backends import (
    BEDROCK_OPENAI_ENDPOINTS,
    invoke_bedrock_openai,
    invoke_bedrock_runtime,
    invoke_ollama,
)
from httpx import HTTPStatusError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s", "%Y-%m-%dT%H:%M:%S%z")
)
if not logger.handlers:
    logger.addHandler(_handler)




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
            if BEDROCK_OPENAI_ENDPOINTS:
                return invoke_bedrock_openai(payload)
            return invoke_bedrock_runtime(prompt, payload.get("model"))
        return invoke_ollama(payload)
    except HTTPStatusError as e:
        logger.error(
            "LLM request failed [%d]: %s", e.response.status_code, e.response.text
        )
        raise
    except Exception:
        logger.exception("Unexpected error in llm invocation")
        raise
