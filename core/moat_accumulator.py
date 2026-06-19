"""
Moat Accumulator — RUMA ADAPT-Ω
==================================
Tracks Λ(t): the agent's accumulated reputation / competitive advantage.

Formula:
  log(Λ(t)) = log(Λ₀) + Σ log(1 + ηᵢ · ρᵢ · A_i)

ADAPT-Ω update: calibration score A_i now modulates moat growth.
  - A=1.0 → full moat increment (well-calibrated action)
  - A=0.5 → half moat increment
  - A=0.0 → no moat increment (poorly calibrated action earns nothing)

Why: The agent's reputation grows faster when it acts coherently AND
with well-calibrated parameters. A lucky trade at A=0.1 contributes
less than a precise trade at A=0.9.

Monotonic property preserved: Λ(t) never decreases.
"""
from __future__ import annotations
import math
import time
from dataclasses import dataclass, field


@dataclass
class MoatCycle:
    cycle_id: str
    eta: float           # Learning rate (base)
    rho: float           # Action quality (PnL fraction, 0–1+)
    calibration: float   # A(t) at time of action
    adjusted_rho: float  # rho * calibration
    increment: float     # log(1 + eta * adjusted_rho)
    lambda_before: float
    lambda_after: float
    timestamp: float = field(default_factory=time.time)


class MoatAccumulator:
    LAMBDA_0 = 0.01   # Starting moat (near zero — unproven)

    def __init__(self):
        self.log_lambda: float = math.log(self.LAMBDA_0)
        self.n_cycles: int = 0
        self._history: list[MoatCycle] = []
        self._calibration_history: list[float] = []

    # ── Core growth ───────────────────────────────────────────────────────────
    def accumulate(
        self,
        eta_i: float,
        rho_i: float,
        calibration_score: float = 1.0,
        cycle_id: str = "",
    ) -> MoatCycle | None:
        """
        Accumulate moat from one completed action cycle.

        eta_i             : learning rate (0 < η ≤ 0.1 typical)
        rho_i             : action quality, PnL-based (0 = loss, 1 = target hit)
        calibration_score : A(t) — how well was the action calibrated?
        """
        if eta_i <= 0 or rho_i <= 0 or calibration_score <= 0:
            return None   # Silenced or losing actions don't grow the moat

        lambda_before = self.get_current_lambda()

        # Calibrated actions compound faster — moat rewards calibration
        adjusted_rho = rho_i * calibration_score
        increment    = math.log(1.0 + eta_i * adjusted_rho)

        self.log_lambda += increment
        self.n_cycles   += 1
        self._calibration_history.append(calibration_score)

        lambda_after = self.get_current_lambda()

        cycle = MoatCycle(
            cycle_id=cycle_id or f"cycle_{self.n_cycles}",
            eta=round(eta_i, 6), rho=round(rho_i, 6),
            calibration=round(calibration_score, 4),
            adjusted_rho=round(adjusted_rho, 6),
            increment=round(increment, 8),
            lambda_before=round(lambda_before, 6),
            lambda_after=round(lambda_after, 6),
        )
        self._history.append(cycle)
        return cycle

    # ── Accessors ─────────────────────────────────────────────────────────────
    def get_current_lambda(self) -> float:
        return math.exp(self.log_lambda)

    def get_t_normalized(self) -> float:
        """Cycles as time proxy — used in e^(Λ·t) projections."""
        return max(1.0, float(self.n_cycles))

    def avg_calibration(self) -> float:
        if not self._calibration_history:
            return 0.0
        return sum(self._calibration_history) / len(self._calibration_history)

    def calibration_trend(self) -> str:
        """Is calibration improving, stable, or degrading?"""
        h = self._calibration_history
        if len(h) < 4:
            return "insufficient_data"
        recent = sum(h[-3:]) / 3
        older  = sum(h[-6:-3]) / max(len(h[-6:-3]), 1)
        delta  = recent - older
        if delta > 0.05:   return "improving"
        elif delta < -0.05: return "degrading"
        return "stable"

    def history_tail(self, n: int = 10) -> list[dict]:
        return [
            {
                "cycle_id": c.cycle_id,
                "calibration": c.calibration,
                "rho": c.rho,
                "adjusted_rho": c.adjusted_rho,
                "increment": c.increment,
                "lambda_after": c.lambda_after,
                "timestamp": c.timestamp,
            }
            for c in self._history[-n:]
        ]


# ── Process-level singleton ────────────────────────────────────────────────────
_moat = MoatAccumulator()

def get_moat() -> MoatAccumulator:
    return _moat
