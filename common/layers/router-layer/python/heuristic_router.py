"""Rule based LLM router."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

__all__ = [
    "HeuristicRouter",
    "handle_heuristic_route",
]

DEFAULT_PROMPT_COMPLEXITY_THRESHOLD = 20
PROMPT_COMPLEXITY_THRESHOLD = int(
    os.environ.get("PROMPT_COMPLEXITY_THRESHOLD", str(DEFAULT_PROMPT_COMPLEXITY_THRESHOLD))
)


def _prompt_text(event: Dict[str, Any]) -> str:
    if isinstance(event.get("prompt"), str):
        return event.get("prompt", "")
    if isinstance(event.get("messages"), list):
        return " ".join(str(m.get("content", "")) for m in event["messages"] if isinstance(m, dict))
    return ""


class HeuristicRouter:
    """Select a backend purely from simple heuristics."""

    def try_route(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        prompt = _prompt_text(event)
        word_count = len(prompt.split())
        event = dict(event)
        if word_count >= PROMPT_COMPLEXITY_THRESHOLD:
            event["backend"] = "bedrock"
        else:
            event["backend"] = "ollama"
        return event


def handle_heuristic_route(prompt: str, config: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Route *prompt* using :class:`HeuristicRouter` with optional *config*."""
    event = {"prompt": prompt}
    if config:
        event.update(config)
    router = HeuristicRouter()
    result = router.try_route(event)
    if result is None:
        raise RuntimeError("Heuristic router returned no result")
    return result

