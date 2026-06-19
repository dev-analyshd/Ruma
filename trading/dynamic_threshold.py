"""
Dynamic Δ(t) Threshold — RUMA
==============================
Replaces the fixed 0.65 gate with a context-aware threshold that:
  - Rises when the market is chaotic (harder to act)
  - Rises when the agent is fatigued (many recent trades)
  - Rises when too much capital is deployed
  - Falls when close to competition deadline (urgency mode)
  - Falls as Λ (moat) grows (proven agent earns lower bar)

Result: the gate breathes. Conservative when uncertain, permissive
when the agent has earned trust and the market is clear.

Bounds: [0.40, 0.95] — never trivially open or permanently closed.
"""
from __future__ import annotations
import math
from dataclasses import dataclass
from datetime import datetime, timezone


# ── Competition deadline ──────────────────────────────────────────────────────
COMPETITION_END = datetime(2026, 6, 28, 23, 59, 59, tzinfo=timezone.utc)


@dataclass
class ThresholdContext:
    # Market
    market_stress: float = 0.0       # 0=calm, 3=crisis (from DynamicRiskManager)
    volatility_30d: float = 0.02
    fear_greed: int = 50

    # Agent
    trades_last_hour: int = 0        # Fatigue proxy
    lambda_val: float = 0.01         # Moat accumulator Λ
    capital_deployed: float = 0.0
    total_capital: float = 500.0

    # Competition
    competition_days_remaining: int = 7

    @property
    def deployed_pct(self) -> float:
        if self.total_capital <= 0:
            return 0.0
        return min(1.0, self.capital_deployed / self.total_capital)

    @classmethod
    def from_state(cls, lambda_val: float, trades_last_hour: int,
                   capital_deployed: float, total_capital: float,
                   stress: float, fear_greed: int) -> "ThresholdContext":
        now = datetime.now(timezone.utc)
        days_left = max(0, (COMPETITION_END - now).days)
        return cls(
            market_stress=stress,
            fear_greed=fear_greed,
            trades_last_hour=trades_last_hour,
            lambda_val=lambda_val,
            capital_deployed=capital_deployed,
            total_capital=total_capital,
            competition_days_remaining=days_left,
        )


@dataclass
class ThresholdResult:
    delta: float
    components: dict[str, float]
    interpretation: str

    def to_dict(self) -> dict:
        return {
            "delta": round(self.delta, 4),
            "components": {k: round(v, 5) for k, v in self.components.items()},
            "interpretation": self.interpretation,
            "gate_is_permissive": self.delta < 0.60,
            "gate_is_strict": self.delta > 0.75,
        }


class DynamicThreshold:
    """
    Ψ gate threshold Δ(t) — the bar RUMA must clear before acting.
    Higher = stricter = agent stays silent more often.
    """

    BASE = 0.60   # Starting point — lower than the old fixed 0.65

    def compute(self, ctx: ThresholdContext) -> ThresholdResult:
        components: dict[str, float] = {"base": self.BASE}

        # 1. Market stress: chaos → raise bar
        stress_component = ctx.market_stress * 0.25
        # Stress=0→+0, Stress=1→+0.25, Stress=2→+0.50, Stress=3→+0.75 (capped)
        stress_component = min(stress_component, 0.30)
        components["stress"] = stress_component

        # 2. Agent fatigue: many recent trades → raise bar (avoid overtrading)
        fatigue = min(ctx.trades_last_hour * 0.025, 0.15)
        # 0 trades→+0, 4 trades→+0.10, 6+→+0.15
        components["fatigue"] = fatigue

        # 3. Capital deployment: more deployed → harder to add
        deployment_penalty = ctx.deployed_pct * 0.20
        # 0%→+0, 50%→+0.10, 100%→+0.20
        components["deployment"] = deployment_penalty

        # 4. Time pressure: competition deadline approaching → lower bar
        d = ctx.competition_days_remaining
        if d == 0:
            time_pressure = -0.20   # Last day — be more aggressive
        elif d <= 2:
            time_pressure = -0.15
        elif d <= 4:
            time_pressure = -0.08
        elif d >= 10:
            time_pressure = +0.05   # Early on — be conservative
        else:
            time_pressure = 0.0
        components["time_pressure"] = time_pressure

        # 5. Moat bonus: proven agent earns a lower gate
        moat_bonus = -math.log(max(0.001, ctx.lambda_val) + 1.0) / 18.0
        # Λ=0→0, Λ=10→-0.133, Λ=100→-0.256, Λ=215→-0.296
        moat_bonus = max(moat_bonus, -0.25)   # cap benefit
        components["moat_bonus"] = moat_bonus

        # 6. Fear & Greed: extreme readings → raise bar (anomaly)
        if ctx.fear_greed >= 85 or ctx.fear_greed <= 15:
            fg_component = 0.10    # Extreme F&G → be cautious
        elif 65 <= ctx.fear_greed <= 80 or 20 <= ctx.fear_greed <= 35:
            fg_component = 0.03
        else:
            fg_component = 0.0
        components["fear_greed_caution"] = fg_component

        # Sum and clamp
        delta = self.BASE + sum(v for k, v in components.items() if k != "base")
        delta = max(0.40, min(delta, 0.95))
        components["final"] = delta

        # Human interpretation
        if delta < 0.50:
            interp = f"Very permissive (Δ={delta:.3f}) — Λ={ctx.lambda_val:.2f}, deadline approaching"
        elif delta < 0.65:
            interp = f"Permissive (Δ={delta:.3f}) — normal conditions, earned trust"
        elif delta < 0.75:
            interp = f"Moderate (Δ={delta:.3f}) — elevated caution"
        elif delta < 0.85:
            interp = f"Strict (Δ={delta:.3f}) — market stress or fatigue"
        else:
            interp = f"Very strict (Δ={delta:.3f}) — crisis conditions"

        return ThresholdResult(delta=delta, components=components, interpretation=interp)

    def compute_simple(
        self,
        lambda_val: float,
        trades_last_hour: int = 0,
        stress: float = 0.0,
        fear_greed: int = 50,
        days_remaining: int = 7,
    ) -> ThresholdResult:
        ctx = ThresholdContext(
            market_stress=stress,
            fear_greed=fear_greed,
            trades_last_hour=trades_last_hour,
            lambda_val=lambda_val,
            competition_days_remaining=days_remaining,
        )
        return self.compute(ctx)


# Singleton
_threshold = DynamicThreshold()

def get_threshold() -> DynamicThreshold:
    return _threshold

def compute_delta(lambda_val: float = 0.01, stress: float = 0.0,
                  trades_last_hour: int = 0, fear_greed: int = 50,
                  days_remaining: int = 7) -> float:
    """Quick one-liner for use in gate checks."""
    return _threshold.compute_simple(
        lambda_val=lambda_val, trades_last_hour=trades_last_hour,
        stress=stress, fear_greed=fear_greed, days_remaining=days_remaining,
    ).delta
