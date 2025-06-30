"""Cascading routing logic for selecting an LLM backend.

The :class:`CascadingRouter` tries a series of routing strategies in
order:

1. :class:`HeuristicRouter` for simple rule-based decisions.
2. :class:`PredictiveRouter` for ML based routing.
3. :class:`GenerativeRouter` as a fallback that directly generates a
   response.
"""

from __future__ import annotations

import json
from typing import Any, Dict

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
    """Invoke a Bedrock model and return the text response."""
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
    """Return ``True`` if ``response`` is deemed sufficient."""
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


def handle_cascading_route(prompt: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Route ``prompt`` using a weak then strong Bedrock model."""
    bedrock_runtime = config["bedrock_runtime"]
    weak_model_id = config["weak_model_id"]
    strong_model_id = config["strong_model_id"]

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

