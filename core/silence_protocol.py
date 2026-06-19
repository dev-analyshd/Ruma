"""
Silence Protocol — RUMA ADAPT-Ω
==================================
Two-tier silence system. Silence is not failure — it is information.

HARD SILENCE  — Ψ < Δ   : agent cannot act. The information content
                            of not-acting is preserved in the log.

SOFT SILENCE  — Ψ ≥ Δ   : coherent, but A(t) < 0.30 (poor calibration).
  but A < 0.30            Agent may act but only with 0.5% capital max.
                            This prevents poorly-calibrated actions while
                            still allowing the agent to participate.

OPEN          — both gates clear: full dynamic Φ(a,t) applies.

Philosophy: "An agent that knows it is poorly calibrated and says so
is more trustworthy than one that acts with false confidence."
"""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Literal


SilenceType = Literal["HARD", "SOFT", "NONE"]


@dataclass
class SilenceDecision:
    silence_type: SilenceType
    action_allowed: bool
    max_size_pct: float         # 0 = no action, 0.005 = SOFT, None = dynamic
    daily_risk_cap: float | None
    strategy_constraint: str | None
    reason: str
    psi: float
    delta: float
    adaptation: float | None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "silence_type": self.silence_type,
            "action_allowed": self.action_allowed,
            "max_size_pct": self.max_size_pct,
            "daily_risk_cap": self.daily_risk_cap,
            "strategy_constraint": self.strategy_constraint,
            "reason": self.reason,
            "psi": round(self.psi, 4),
            "delta": round(self.delta, 4),
            "adaptation_A": round(self.adaptation, 4) if self.adaptation is not None else None,
            "philosophy": "Silence is information. The absence of action is a decision.",
        }


class SilenceProtocol:
    """
    Two-tier silence evaluator. Called by the ActionGate after Ψ and A(t) are computed.
    Maintains a log of all silence decisions for audit purposes.
    """

    def __init__(self):
        self._log: list[SilenceDecision] = []

    def evaluate(
        self,
        psi: float,
        delta: float,
        adaptation: float | None = None,
        context: dict | None = None,
    ) -> SilenceDecision:
        """
        Evaluate silence tier.

        psi        : Ψ(t) — total coherence score
        delta      : Δ(t) — dynamic threshold
        adaptation : A(t) — adaptation plane score (None = not computed)
        context    : optional extra context for logging
        """
        # ── HARD SILENCE ──────────────────────────────────────────────────────
        if psi < delta:
            dec = SilenceDecision(
                silence_type="HARD",
                action_allowed=False,
                max_size_pct=0.0,
                daily_risk_cap=0.0,
                strategy_constraint="NO_ACTION",
                reason=f"Ψ={psi:.4f} < Δ={delta:.4f} — coherence insufficient",
                psi=psi, delta=delta, adaptation=adaptation,
            )
            self._log.append(dec)
            return dec

        # ── SOFT SILENCE ──────────────────────────────────────────────────────
        if adaptation is not None and adaptation < 0.30:
            dec = SilenceDecision(
                silence_type="SOFT",
                action_allowed=True,
                max_size_pct=0.005,      # 0.5% max
                daily_risk_cap=0.02,     # 2% daily cap
                strategy_constraint="CONSERVATIVE_ONLY",
                reason=(
                    f"A(t)={adaptation:.4f} < 0.30 — calibration poor. "
                    "Coherent but ill-calibrated. Minimum viable size only."
                ),
                psi=psi, delta=delta, adaptation=adaptation,
            )
            self._log.append(dec)
            return dec

        # ── OPEN ──────────────────────────────────────────────────────────────
        return SilenceDecision(
            silence_type="NONE",
            action_allowed=True,
            max_size_pct=-1.0,      # Sentinel: dynamic sizer decides
            daily_risk_cap=None,
            strategy_constraint=None,
            reason="All gates open — full dynamic Φ(a,t) applies",
            psi=psi, delta=delta, adaptation=adaptation,
        )

    @property
    def log(self) -> list[SilenceDecision]:
        return self._log

    def stats(self) -> dict:
        total = len(self._log)
        hard  = sum(1 for d in self._log if d.silence_type == "HARD")
        soft  = sum(1 for d in self._log if d.silence_type == "SOFT")
        return {
            "total_silences": total,
            "hard_silences": hard,
            "soft_silences": soft,
            "hard_rate": round(hard / max(total, 1), 4),
            "soft_rate": round(soft / max(total, 1), 4),
            "philosophy": "Higher silence rate = more discriminating agent",
        }


# ── Process-level singleton ────────────────────────────────────────────────────
_silence_protocol = SilenceProtocol()

def get_silence_protocol() -> SilenceProtocol:
    return _silence_protocol
