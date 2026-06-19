"""
Dynamic Risk Manager — RUMA
============================
Replaces fixed 6% daily-pause + 30% drawdown rules with adaptive limits
that breathe with the market and the agent's track record.

Dynamic limits are functions of:
  - Moat size Λ (proven track record → more risk budget)
  - Win streak (consecutive good days → expand budget)
  - Market stress index (VIX-like → contract budget)
  - Time-of-day session (Asian/London/NYC liquidity)

Circuit breakers (dynamic, not fixed):
  1. Flash crash — 5% drop in 5m → SILENCE_ALL 30 min
  2. Liquidity dry — spread > 2% → REDUCE_SIZE 50% 60 min
  3. Agent confusion — Ψ < 0.4 × 3 consecutive → SILENCE_ALL 120 min
  4. Correlation spike — avg_corr > 0.8 → REDUCE_SIZE 70% 45 min

Hard competition caps (always enforced):
  - daily_risk ≤ 15%   (absolute ceiling — never DQ territory)
  - drawdown ≤ 28%     (2% buffer below 30% DQ line)
"""
from __future__ import annotations
import math
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

# ── Competition absolute caps ─────────────────────────────────────────────────
COMPETITION_DRAWDOWN_LIMIT  = 0.30    # 30% → disqualification
DRAWDOWN_BUFFER             = 0.02    # 2% buffer below DQ line
HARD_DRAWDOWN_CAP           = COMPETITION_DRAWDOWN_LIMIT - DRAWDOWN_BUFFER  # 28%
HARD_DAILY_RISK_CAP         = 0.15    # 15% daily absolute ceiling
BASE_DAILY_RISK             = 0.06    # Starting point (6%)
BASE_DRAWDOWN               = 0.20    # Starting operational drawdown tolerance


@dataclass
class CircuitBreaker:
    triggered: bool
    breaker_type: str     # FLASH_CRASH | LIQUIDITY_DRY | AGENT_CONFUSION | CORRELATION_SPIKE
    action: str           # SILENCE_ALL | REDUCE_SIZE_50 | REDUCE_SIZE_70
    duration_minutes: int
    triggered_at: float = field(default_factory=time.time)
    reason: str = ""

    def size_multiplier(self) -> float:
        if self.action == "SILENCE_ALL":        return 0.0
        if self.action == "REDUCE_SIZE_50":     return 0.5
        if self.action == "REDUCE_SIZE_70":     return 0.3
        return 1.0

    def is_active(self) -> bool:
        if not self.triggered:
            return False
        elapsed = (time.time() - self.triggered_at) / 60.0
        return elapsed < self.duration_minutes


@dataclass
class RiskLimits:
    daily_risk_budget: float          # fraction of capital (dynamic)
    drawdown_cap: float               # max allowed drawdown (dynamic, ≤ 28%)
    per_trade_max: float              # daily_risk / 3 (split across 3 trades)
    stress_index: float               # current market stress (0=calm, 2=crisis)
    circuit_breakers: list[CircuitBreaker]
    explanation: dict[str, float]
    effective_size_mult: float        # combined circuit breaker multiplier
    session: str                      # ASIAN | LONDON | NYC | OFF

    def to_dict(self) -> dict:
        return {
            "daily_risk_budget_pct": round(self.daily_risk_budget * 100, 3),
            "drawdown_cap_pct": round(self.drawdown_cap * 100, 3),
            "per_trade_max_pct": round(self.per_trade_max * 100, 3),
            "competition_dq_line_pct": round(COMPETITION_DRAWDOWN_LIMIT * 100, 1),
            "stress_index": round(self.stress_index, 3),
            "session": self.session,
            "effective_size_mult": round(self.effective_size_mult, 3),
            "circuit_breakers": [
                {
                    "type": cb.breaker_type,
                    "triggered": cb.triggered,
                    "active": cb.is_active(),
                    "action": cb.action,
                    "minutes_remaining": max(0, cb.duration_minutes - (time.time() - cb.triggered_at) / 60) if cb.triggered else 0,
                    "reason": cb.reason,
                }
                for cb in self.circuit_breakers
            ],
            "explanation": {k: round(v, 5) for k, v in self.explanation.items()},
        }


class DynamicRiskManager:
    """
    Adaptive risk limits — respects competition hard caps while expanding
    budget as the agent earns trust and contracting under stress.
    """

    def __init__(self):
        self._active_breakers: list[CircuitBreaker] = []
        self._last_compute_ts: float = 0.0
        self._cached_limits: RiskLimits | None = None

    # ── Session detection ──────────────────────────────────────────────────────
    @staticmethod
    def _get_session(hour_utc: int) -> tuple[str, float]:
        """(session_name, time_multiplier)"""
        if 0 <= hour_utc < 6:
            return "ASIAN", 0.70      # Low liquidity
        elif 6 <= hour_utc < 14:
            return "LONDON", 1.00     # Good liquidity
        elif 14 <= hour_utc < 21:
            return "NYC", 1.10        # Peak liquidity
        else:
            return "OFF", 0.85        # Between sessions

    # ── Market stress index ────────────────────────────────────────────────────
    @staticmethod
    def _compute_stress(fear_greed: int, vol_30d: float, price_change_5m: float) -> float:
        """
        Stress index [0, 3]:
          0 = calm market
          1 = elevated uncertainty
          2 = high stress
          3 = crisis / flash crash
        """
        fg_stress = max(0.0, (50 - fear_greed) / 50.0)   # FG < 50 → fear → stress
        vol_stress = min(1.0, vol_30d * 20)               # 5% vol → full vol stress
        crash_stress = 2.0 if price_change_5m < -0.05 else 0.0  # 5% drop in 5m
        return min(3.0, fg_stress + vol_stress + crash_stress)

    # ── Main compute ───────────────────────────────────────────────────────────
    def compute_dynamic_limits(
        self,
        lambda_val: float,
        consecutive_wins: int,
        fear_greed: int,
        vol_30d: float = 0.02,
        price_change_5m: float = 0.0,
        psi_history: list[float] | None = None,
        avg_correlation: float = 0.3,
        capital_deployed_pct: float = 0.0,
        competition_days_remaining: int = 7,
        current_drawdown_pct: float = 0.0,
    ) -> RiskLimits:

        now_utc = datetime.now(timezone.utc)
        session, time_mult = self._get_session(now_utc.hour)
        stress = self._compute_stress(fear_greed, vol_30d, price_change_5m)

        # ── 1. Moat-based risk expansion ────────────────────────────────────
        moat_mult = 1.0 + math.log(max(0.001, lambda_val) + 1.0) / 10.0
        # Λ=0→1.0, Λ=10→1.23, Λ=100→1.46, Λ=215→1.53

        # ── 2. Win streak expansion (capped at 1.5×) ────────────────────────
        streak_mult = min(1.50, 1.0 + consecutive_wins * 0.05)

        # ── 3. Market stress contraction ────────────────────────────────────
        stress_mult = 1.0 / (1.0 + stress)

        # ── 4. Time-of-day adjustment ───────────────────────────────────────
        # already in time_mult above

        # ── 5. Compute adaptive limits ──────────────────────────────────────
        daily_risk = BASE_DAILY_RISK * moat_mult * streak_mult * stress_mult * time_mult
        daily_risk = min(daily_risk, HARD_DAILY_RISK_CAP)

        drawdown_cap = BASE_DRAWDOWN * moat_mult * streak_mult * stress_mult
        drawdown_cap = min(drawdown_cap, HARD_DRAWDOWN_CAP)

        # Emergency: if already near DQ line, lock down
        if current_drawdown_pct >= 25.0:
            daily_risk = min(daily_risk, 0.02)
            drawdown_cap = min(drawdown_cap, COMPETITION_DRAWDOWN_LIMIT - 0.01)

        per_trade_max = daily_risk / 3.0

        # ── 6. Circuit breakers ─────────────────────────────────────────────
        breakers = self._evaluate_breakers(
            price_change_5m=price_change_5m,
            bid_ask_spread=0.001,       # TODO: live spread feed
            psi_history=psi_history or [],
            avg_correlation=avg_correlation,
        )

        # Effective size multiplier from active breakers
        eff_mult = 1.0
        for cb in breakers:
            if cb.is_active():
                eff_mult = min(eff_mult, cb.size_multiplier())

        return RiskLimits(
            daily_risk_budget=daily_risk,
            drawdown_cap=drawdown_cap,
            per_trade_max=per_trade_max,
            stress_index=stress,
            circuit_breakers=breakers,
            effective_size_mult=eff_mult,
            session=session,
            explanation={
                "base_daily_risk": BASE_DAILY_RISK,
                "moat_mult": moat_mult,
                "streak_mult": streak_mult,
                "stress_mult": stress_mult,
                "time_mult": time_mult,
                "final_daily_risk": daily_risk,
                "final_drawdown_cap": drawdown_cap,
                "per_trade_max": per_trade_max,
                "stress_index": stress,
                "lambda_val": lambda_val,
                "consecutive_wins": consecutive_wins,
            },
        )

    # ── Circuit breaker evaluations ────────────────────────────────────────────
    def _evaluate_breakers(
        self,
        price_change_5m: float,
        bid_ask_spread: float,
        psi_history: list[float],
        avg_correlation: float,
    ) -> list[CircuitBreaker]:
        breakers: list[CircuitBreaker] = []

        # 1. Flash crash: 5% drop in 5 min
        if price_change_5m < -0.05:
            breakers.append(CircuitBreaker(
                triggered=True, breaker_type="FLASH_CRASH",
                action="SILENCE_ALL", duration_minutes=30,
                reason=f"5m price drop {price_change_5m*100:.1f}%",
            ))

        # 2. Liquidity dry: bid-ask spread > 2%
        if bid_ask_spread > 0.02:
            breakers.append(CircuitBreaker(
                triggered=True, breaker_type="LIQUIDITY_DRY",
                action="REDUCE_SIZE_50", duration_minutes=60,
                reason=f"Spread {bid_ask_spread*100:.2f}%",
            ))

        # 3. Agent confusion: Ψ < 0.4 for 3 consecutive evals
        if len(psi_history) >= 3 and all(p < 0.4 for p in psi_history[-3:]):
            breakers.append(CircuitBreaker(
                triggered=True, breaker_type="AGENT_CONFUSION",
                action="SILENCE_ALL", duration_minutes=120,
                reason=f"Ψ < 0.4 × 3 consecutive: {psi_history[-3:]}",
            ))

        # 4. Correlation spike: everything moves together
        if avg_correlation > 0.80:
            breakers.append(CircuitBreaker(
                triggered=True, breaker_type="CORRELATION_SPIKE",
                action="REDUCE_SIZE_70", duration_minutes=45,
                reason=f"Avg correlation {avg_correlation:.2f}",
            ))

        # Merge with previous active breakers (don't reset timer on re-eval)
        merged: list[CircuitBreaker] = list(breakers)
        for prev in self._active_breakers:
            if prev.is_active() and not any(b.breaker_type == prev.breaker_type for b in merged):
                merged.append(prev)

        self._active_breakers = [b for b in merged if b.is_active()]
        return merged


# Singleton
_risk_mgr = DynamicRiskManager()

def get_risk_manager() -> DynamicRiskManager:
    return _risk_mgr
