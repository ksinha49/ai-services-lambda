"""Generative fallback router."""

from __future__ import annotations

from typing import Any, Dict, Optional

__all__ = [
    "GenerativeRouter",
    "handle_generative_route",
]


class GenerativeRouter:
    """Directly call an LLM backend when other routers do not apply."""

    def try_route(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # This stub simply marks the backend for later handling
        event = dict(event)
        event.setdefault("backend", "bedrock")
        return event


def handle_generative_route(prompt: str, config: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Route *prompt* using :class:`GenerativeRouter` with optional *config*."""
    event = {"prompt": prompt}
    if config:
        event.update(config)
    router = GenerativeRouter()
    result = router.try_route(event)
    if result is None:
        raise RuntimeError("Generative router returned no result")
    return result

