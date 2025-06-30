"""Generative fallback router."""

from __future__ import annotations

from typing import Any, Dict, Optional


class GenerativeRouter:
    """Directly call an LLM backend when other routers do not apply."""

    def try_route(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # This stub simply marks the backend for later handling
        event = dict(event)
        event.setdefault("backend", "bedrock")
        return event

