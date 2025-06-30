"""Cascading routing logic for selecting an LLM backend.

The :class:`CascadingRouter` tries a series of routing strategies in
order:

1. :class:`HeuristicRouter` for simple rule-based decisions.
2. :class:`PredictiveRouter` for ML based routing.
3. :class:`GenerativeRouter` as a fallback that directly generates a
   response.
"""

from __future__ import annotations

from typing import Any, Dict

from heuristic_router import HeuristicRouter
from predictive_router import PredictiveRouter
from generative_router import GenerativeRouter


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

