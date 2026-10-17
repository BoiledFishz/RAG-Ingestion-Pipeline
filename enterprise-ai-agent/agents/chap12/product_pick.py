"""Model-assisted product resolution with program validation (item 8).

The model only chooses a number from a short, program-built list of catalogue products
(products of the caller's authorized top BM25 documents). The program validates the choice:
anything that is not an integer inside the list, or 0, means "no product" and the caller
falls back to the deterministic rule or asks for clarification. The model can never introduce
a product outside the list, so a prompt injected into the question can at worst select another
authorized candidate, which the response labels as model-picked.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

from models.errors import DependencyUnavailable

PickMode = Literal["off", "fallback", "first"]
PICK_FILE = Path(__file__).resolve().parents[2] / "evaluation/chap12/tune/product_pick.json"
PROMPT = (
    "KIND: PRODUCT_PICK\n"
    "Choose the IBM product that the question is about from the numbered catalogue list.\n"
    "Answer 0 if none of the listed products is clearly the product asked about.\n"
    "Return JSON {{\"choice\": <number>}} only.\n\nQUESTION:\n{query}\n\nCANDIDATES:\n{lines}")


def pick_mode() -> PickMode:
    """Env override, else the mode adopted on the tune split, else fallback-only."""
    configured = os.getenv("CHAP12_PRODUCT_PICK", "")
    if configured in {"off", "fallback", "first"}:
        return configured  # type: ignore[return-value]
    if PICK_FILE.is_file():
        adopted = json.loads(PICK_FILE.read_text(encoding="utf-8")).get("adopted_mode")
        if adopted in {"off", "fallback", "first"}:
            return adopted  # type: ignore[no-any-return]
    return "fallback"


class ProductPicker:
    def __init__(self, model: Any) -> None:
        self.model = model
        self.errors = 0

    async def pick(self, query: str, candidates: list[tuple[str, str]]) -> str | None:
        """candidates: (product_id, name). Returns a product_id from the list, or None."""
        if not candidates:
            return None
        lines = "\n".join(f"{i}. {name} ({pid})" for i, (pid, name) in enumerate(candidates, 1))
        schema = {"type": "object", "required": ["choice"], "properties": {
            "choice": {"type": "integer", "minimum": 0, "maximum": len(candidates)}}}
        try:
            raw = await self.model.generate(PROMPT.format(query=query[:2000], lines=lines),
                                            schema)
            choice = json.loads(raw).get("choice")
        except (DependencyUnavailable, ValueError, TypeError, AttributeError):
            self.errors += 1
            return None
        if isinstance(choice, bool) or not isinstance(choice, int):
            return None
        index: int = choice
        if 1 <= index <= len(candidates):
            return candidates[index - 1][0]
        return None
