"""
Action Gate — RUMA ADAPT-Ω
============================
Evaluates the full ADAPT-Ω decision gate:

  Ω(a,t) = [Ψ(t) ≥ Δ(t)] · [A(t) ≥ 0.30] · R(a,t) · e^(Λ·t) · Φ(a,t)

Two-tier gate:
  1. HARD SILENCE  — Ψ < Δ   → agent cannot act at all
  2. SOFT SILENCE  — Ψ ≥ Δ, A < 0.30 → agent can act, but max 0.5% capital
  3. FULL DYNAMIC  — both gates open → full Φ(a,t) calibration applies

The gate is the last check before execution. If it opens, the dynamic
action calibration Φ(a,t) determines every parameter of the action.
"""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Any


SOFT_SILENCE_THRESHOLD     = 0.30     # A(t) below this → SOFT SILENCE
SOFT_SILENCE_MAX_SIZE_PCT  = 0.005    # 0.5% of capital max
SOFT_SILENCE_DAILY_RISK    = 0.02     # 2% daily risk budget in SOFT SILENCE


@dataclass
class GateDecision:
    gate_type: str          # HARD_SILENCE | SOFT_SILENCE | OPEN
    action_allowed: bool
    psi: float
    delta: float
    adaptation: float
    max_size_pct: float | None    # None = dynamic sizer decides
    daily_risk_cap: float | None  # None = dynamic risk decides
    strategy_constraint: str | None  # None = selector decides
    reason: str
    omega: float            # Ω(a,t) value (0 if silenced)

    def to_dict(self) -> dict:
        return {
            "gate_type": self.gate_type,
            "action_allowed": self.action_allowed,
            "psi": round(self.psi, 4),
            "delta": round(self.delta, 4),
            "adaptation_A": round(self.adaptation, 4),
            "max_size_pct": self.max_size_pct,
            "daily_risk_cap": self.daily_risk_cap,
            "strategy_constraint": self.strategy_constraint,
            "reason": self.reason,
            "omega": round(self.omega, 6),
            "formula": "Ω = [Ψ ≥ Δ] · [A ≥ 0.30] · R · e^(Λ·t) · Φ(a,t)",
        }


class ActionGate:
    """
    ADAPT-Ω two-tier gate. Called after coherence evaluation.
    """

    def compute_threshold(
        self,
        volatility: float = 0.2,
        novelty: float = 0.5,
        lambda_val: float = 0.01,
        stress: float = 0.0,
        trades_last_hour: int = 0,
        fear_greed: int = 50,
        days_remaining: int = 7,
    ) -> float:
        """
        Dynamic Δ(t). Delegates to DynamicThreshold.
        Falls back to legacy formula if dynamic module unavailable.
        """
        try:
            from trading.dynamic_threshold import compute_delta
            return compute_delta(
                lambda_val=lambda_val,
                stress=stress,
                trades_last_hour=trades_last_hour,
                fear_greed=fear_greed,
                days_remaining=days_remaining,
            )
        except ImportError:
            # Legacy formula
            return 0.65 * (1 + 0.20 * volatility) * (1 + 0.15 * novelty)

    def is_open(self, psi: float, delta: float) -> bool:
        """Legacy single-gate check. Use evaluate() for full ADAPT-Ω."""
        return psi >= delta

    def evaluate(
        self,
        psi: float,
        delta: float,
        adaptation: float,
        lambda_val: float = 0.01,
        risk_free_rate: float = 0.0,
        t_normalized: float = 1.0,
    ) -> GateDecision:
        """
        Full ADAPT-Ω gate evaluation.
        Returns GateDecision with tier, constraints, and Ω value.
        """
        # ── 1. HARD SILENCE ───────────────────────────────────────────────────
        if psi < delta:
            return GateDecision(
                gate_type="HARD_SILENCE",
                action_allowed=False,
                psi=psi, delta=delta, adaptation=adaptation,
                max_size_pct=0.0, daily_risk_cap=0.0,
                strategy_constraint="NO_ACTION",
                reason=f"Ψ={psi:.4f} < Δ={delta:.4f} — coherence below threshold",
                omega=0.0,
            )

        # ── 2. SOFT SILENCE ───────────────────────────────────────────────────
        if adaptation < SOFT_SILENCE_THRESHOLD:
            # Agent is coherent but poorly calibrated — allow minimum viable size
            omega = psi * math.exp(min(lambda_val * t_normalized, 700.0))
            return GateDecision(
                gate_type="SOFT_SILENCE",
                action_allowed=True,
                psi=psi, delta=delta, adaptation=adaptation,
                max_size_pct=SOFT_SILENCE_MAX_SIZE_PCT,
                daily_risk_cap=SOFT_SILENCE_DAILY_RISK,
                strategy_constraint="CONSERVATIVE_ONLY",
                reason=f"A={adaptation:.4f} < 0.30 — poor calibration, minimum viable size only",
                omega=round(omega, 6),
            )

        # ── 3. FULL DYNAMIC ───────────────────────────────────────────────────
        exp_arg = min(lambda_val * t_normalized, 700.0)
        omega = psi * adaptation * math.exp(exp_arg)
        return GateDecision(
            gate_type="OPEN",
            action_allowed=True,
            psi=psi, delta=delta, adaptation=adaptation,
            max_size_pct=None,    # Dynamic sizer decides
            daily_risk_cap=None,  # Dynamic risk decides
            strategy_constraint=None,  # Dynamic selector decides
            reason=f"All gates open: Ψ={psi:.4f} ≥ Δ={delta:.4f}, A={adaptation:.4f} ≥ 0.30",
            omega=round(omega, 6),
        )
