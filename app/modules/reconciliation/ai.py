from __future__ import annotations
import datetime as dt
from dataclasses import dataclass
from app.core.config import settings

class AIUnavailableError(Exception):
    pass

@dataclass(frozen=True)
class ExplainContext:
    invoice_amount: float
    invoice_date: dt.date | None
    invoice_description: str | None
    tx_amount: float
    tx_posted_at: dt.datetime
    tx_description: str
    score: float
    reasons: list[str]

class AIClient:
    def explain(self, ctx: ExplainContext) -> str:
        raise NotImplementedError

class StubAIClient(AIClient):
    def __init__(self, api_key: str | None):
        self.api_key = api_key

    def explain(self, ctx: ExplainContext) -> str:
        if not self.api_key:
            raise AIUnavailableError("Missing AI_API_KEY")
        # Deliberately simple: integration > prompt engineering
        confidence = "high" if ctx.score >= 70 else "medium" if ctx.score >= 40 else "low"
        return (
            f"This match looks {confidence} confidence: the amounts {'match' if 'amount_exact' in ctx.reasons else 'do not exactly match'}, "
            f"the dates are close, and the descriptions share overlapping cues. "
            f"Overall score {ctx.score:.1f} based on deterministic heuristics."
        )

class AIExplainService:
    def __init__(self, client: AIClient | None = None):
        self.client = client or StubAIClient(settings.ai_api_key)

    def explain_or_fallback(self, ctx: ExplainContext) -> str:
        try:
            return self.client.explain(ctx)
        except Exception:
            # deterministic fallback
            parts = []
            if "amount_exact" in ctx.reasons:
                parts.append("Amount is an exact match.")
            else:
                parts.append("Amount does not exactly match.")
            date_reason = next((r for r in ctx.reasons if r.startswith("date_within_")), None)
            if date_reason:
                parts.append(f"Transaction date is close to the invoice date ({date_reason.replace('_', ' ')}).")
            if "text_contains" in ctx.reasons or "text_overlap" in ctx.reasons:
                parts.append("Descriptions contain overlapping keywords.")
            parts.append(f"Deterministic score: {ctx.score:.1f}.")
            return " ".join(parts)
