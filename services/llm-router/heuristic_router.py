"""Rule based LLM router."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

PROMPT_COMPLEXITY_THRESHOLD = int(os.environ.get("PROMPT_COMPLEXITY_THRESHOLD", "0"))


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

