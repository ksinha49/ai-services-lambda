"""Cascading routing logic for selecting an LLM backend.

The :class:`CascadingRouter` orchestrates a sequence of routing
strategies:

1. :class:`HeuristicRouter` for simple rule based decisions.
2. :class:`PredictiveRouter` for ML driven routing.
3. :class:`GenerativeRouter` as a final fallback.

``handle_cascading_route`` exposes the *weak then strong* pattern used
by the router Lambda.  It first tries a cheaper Bedrock model and only
escalates to a more powerful one when the initial response fails a
quality check.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from heuristic_router import HeuristicRouter
from predictive_router import PredictiveRouter
from generative_router import GenerativeRouter

__all__ = [
    "CascadingRouter",
    "handle_cascading_route",
    "invoke_bedrock_model",
    "is_response_sufficient",
]


class CascadingRouter:
    """Route requests through multiple strategies until one succeeds."""

    def __init__(self) -> None:
        self.heuristic = HeuristicRouter()
        self.predictive = PredictiveRouter()
        self.generative = GenerativeRouter()

    def route(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Return a response from the first router that yields one."""
        for router in (self.heuristic, self.predictive, self.generative):
            resp = router.try_route(event)
            if resp is not None:
                return resp
        raise RuntimeError("No router produced a response")

def invoke_bedrock_model(bedrock_runtime: Any, model_id: str, prompt: str) -> str:
    """Invoke a Bedrock model and return the generated text."""
    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2048,
            "messages": [{"role": "user", "content": prompt}],
        }
    )
    response = bedrock_runtime.invoke_model(body=body, modelId=model_id)
    response_body = json.loads(response.get("body").read())
    return response_body["content"]["text"]


def is_response_sufficient(response: str) -> bool:
    """Basic heuristic to decide if ``response`` should be accepted."""
    response_lower = response.lower()
    insufficient_phrases = [
        "i can't",
        "i am unable",
        "i do not know",
        "as an ai",
        "i cannot provide",
    ]
    if any(phrase in response_lower for phrase in insufficient_phrases):
        return False
    if len(response.split()) < 20:
        return False
    return True


def handle_cascading_route(
    prompt: str, config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Return a response for ``prompt`` using weak/strong Bedrock models.

    The function first calls the cheaper *weak* model.  If
    :func:`is_response_sufficient` determines the reply is inadequate it
    escalates to the more powerful model. ``config`` may contain a
    ``bedrock_runtime`` client along with optional ``weak_model_id`` and
    ``strong_model_id`` values.  Missing identifiers are read from the
    ``WEAK_MODEL_ID`` and ``STRONG_MODEL_ID`` environment variables
    respectively, and a runtime client is lazily created when not
    supplied.
    """
    config = config or {}
    bedrock_runtime = config.get("bedrock_runtime")
    if bedrock_runtime is None:
        import boto3

        bedrock_runtime = boto3.client("bedrock-runtime")

    weak_model_id = config.get("weak_model_id") or os.environ.get("WEAK_MODEL_ID")
    strong_model_id = config.get("strong_model_id") or os.environ.get("STRONG_MODEL_ID")

    weak_model_response = invoke_bedrock_model(bedrock_runtime, weak_model_id, prompt)

    if is_response_sufficient(weak_model_response):
        return {
            "routed_by": "cascading",
            "model_used": weak_model_id,
            "response": weak_model_response,
            "trace": ["Attempted weak model, response was sufficient."],
        }

    strong_model_response = invoke_bedrock_model(bedrock_runtime, strong_model_id, prompt)
    return {
        "routed_by": "cascading",
        "model_used": strong_model_id,
        "response": strong_model_response,
        "trace": [
            "Attempted weak model, response was insufficient.",
            f"Weak model response: {weak_model_response[:100]}...",
            "Escalated to strong model.",
        ],
    }

