"""
Adaptation Plane — A(t) — RUMA ADAPT-Ω
=========================================
The 6th cognitive plane. Bridges "should I act?" → "how should I act?"

A(t) = σ(κ(t)) · ρ(t) · λ_liq(t) · τ(t)

Components:
  κ(t) — Calibration   : how well do past predictions match outcomes?
  ρ(t) — Regime Fit    : is the current strategy appropriate for this regime?
  λ_liq(t) — Liquidity  : is position size aligned with available liquidity?
  τ(t) — Temporal      : is the agent trading at the right time of day?

Hard rule: A(t) < 0.30 → SOFT SILENCE (max 0.5% size only)
"""
from __future__ import annotations
import math
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _sigmoid(x: float) -> float:
    """Standard sigmoid, numerically stable."""
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    e = math.exp(x)
    return e / (1.0 + e)


# ── Session liquidity profile ─────────────────────────────────────────────────
# Fraction of daily volume traded per hour (UTC), sum ≈ 1.0
SESSION_LIQUIDITY: dict[int, float] = {
    0:  0.020, 1:  0.015, 2:  0.012, 3:  0.010, 4:  0.012,
    5:  0.018, 6:  0.030, 7:  0.040, 8:  0.055, 9:  0.060,
    10: 0.060, 11: 0.055, 12: 0.050, 13: 0.058, 14: 0.072,
    15: 0.070, 16: 0.068, 17: 0.062, 18: 0.055, 19: 0.048,
    20: 0.040, 21: 0.035, 22: 0.030, 23: 0.025,
}
# Verify: 0.020+0.015+0.012+0.010+0.012+0.018+0.030+0.040+0.055+0.060
#       + 0.060+0.055+0.050+0.058+0.072+0.070+0.068+0.062+0.055+0.048
#       + 0.040+0.035+0.030+0.025 = 1.000
MAX_SESSION_LIQUIDITY = max(SESSION_LIQUIDITY.values())   # hour 15


@dataclass
class AdaptationComponents:
    kappa: float    # Calibration  (0–1)
    rho:   float    # Regime fit   (0–1)
    liq:   float    # Liquidity alignment (0–1)
    tau:   float    # Temporal     (0–1)
    A:     float    # Final A(t)   (0–1)
    interpretation: str
    soft_silence: bool   # A < 0.30 → SOFT SILENCE

    def to_dict(self) -> dict:
        return {
            "A_t": round(self.A, 4),
            "kappa_calibration": round(self.kappa, 4),
            "rho_regime_fit": round(self.rho, 4),
            "lambda_liquidity": round(self.liq, 4),
            "tau_temporal": round(self.tau, 4),
            "formula": "A(t) = σ(κ) · ρ · λ_liq · τ",
            "soft_silence_triggered": self.soft_silence,
            "soft_silence_threshold": 0.30,
            "interpretation": self.interpretation,
        }


class AdaptationPlane:
    """
    Computes A(t) — the 6th cognitive plane.
    Maintains a rolling calibration history (last 20 predictions).
    """

    SOFT_SILENCE_THRESHOLD = 0.30
    CALIBRATION_WINDOW = 20

    def __init__(self):
        self._calibration_history: list[float] = []   # past |pred - actual|
        self._regime_fit_history:  list[float] = []   # past ρ values
        self._last_regime: str = "SIDEWAYS"

    # ── κ(t) ─────────────────────────────────────────────────────────────────
    def update_calibration(self, predicted_return: float, actual_return: float):
        """Call after each trade resolves. Updates κ rolling window."""
        error = abs(predicted_return - actual_return)
        self._calibration_history.append(error)
        if len(self._calibration_history) > self.CALIBRATION_WINDOW:
            self._calibration_history.pop(0)

    def _compute_kappa(self) -> float:
        """κ(t) = 1 - mean(|pred - actual|), mapped to [0,1]."""
        if not self._calibration_history:
            return 0.70   # Prior: assume decent calibration (70%)
        mean_error = sum(self._calibration_history) / len(self._calibration_history)
        # mean_error of 0 → κ=1.0, mean_error of 0.10 (10%) → κ≈0.0
        kappa = max(0.0, 1.0 - mean_error * 10.0)
        return round(min(1.0, kappa), 4)

    # ── ρ(t) ─────────────────────────────────────────────────────────────────
    def _compute_rho(self, regime: str, selected_strategy: str) -> float:
        """ρ(t) = effectiveness of selected_strategy in current regime."""
        from trading.strategy_selector import EFFECTIVENESS_MATRIX
        self._last_regime = regime
        eff = EFFECTIVENESS_MATRIX.get(selected_strategy, {}).get(regime, 0.50)
        return round(eff, 4)

    # ── λ_liq(t) ─────────────────────────────────────────────────────────────
    def _compute_liquidity(self, order_size_usd: float, daily_volume_usd: float) -> float:
        """λ_liq(t) = min(1.0, (daily_volume × 1%) / order_size).
        Score = 1 when order ≤ 1% of daily volume, degrades as size grows."""
        if daily_volume_usd <= 0 or order_size_usd <= 0:
            return 0.70   # Default: assume adequate liquidity
        liquidity_1pct = daily_volume_usd * 0.01
        liq = min(1.0, liquidity_1pct / order_size_usd)
        return round(liq, 4)

    # ── τ(t) ─────────────────────────────────────────────────────────────────
    def _compute_temporal(self, override_hour: int | None = None) -> float:
        """τ(t) = session_liquidity[current_hour] / max_session_liquidity.

        Args:
            override_hour: UTC hour 0-23 to use instead of wall-clock time.
                           Useful for backtesting and deterministic unit tests.
        """
        hour = override_hour if override_hour is not None else datetime.now(timezone.utc).hour
        tau = SESSION_LIQUIDITY.get(hour, 0.030) / MAX_SESSION_LIQUIDITY
        return round(tau, 4)

    # ── Main compute ──────────────────────────────────────────────────────────
    def compute(
        self,
        regime: str = "SIDEWAYS",
        selected_strategy: str = "MomentumBreakout",
        order_size_usd: float = 10.0,
        daily_volume_usd: float = 50_000_000.0,
        override_hour: int | None = None,
    ) -> AdaptationComponents:
        kappa = self._compute_kappa()
        rho   = self._compute_rho(regime, selected_strategy)
        liq   = self._compute_liquidity(order_size_usd, daily_volume_usd)
        tau   = self._compute_temporal(override_hour)

        # A(t) = σ(κ) · ρ · λ_liq · τ
        # σ(κ) maps κ ∈ [0,1] → slightly expanded via sigmoid on (κ-0.5)*4
        sigma_kappa = _sigmoid((kappa - 0.50) * 4.0)
        A = sigma_kappa * rho * liq * tau
        A = round(min(1.0, max(0.0, A)), 4)

        soft = A < self.SOFT_SILENCE_THRESHOLD

        if A >= 0.70:
            interp = f"Well-calibrated (A={A:.3f}) — full dynamic action permitted"
        elif A >= 0.50:
            interp = f"Adequate (A={A:.3f}) — normal dynamic action"
        elif A >= 0.30:
            interp = f"Marginal (A={A:.3f}) — proceed with caution"
        else:
            interp = f"SOFT SILENCE (A={A:.3f} < 0.30) — max 0.5% size"

        return AdaptationComponents(
            kappa=kappa, rho=rho, liq=liq, tau=tau, A=A,
            interpretation=interp, soft_silence=soft,
        )


# ── Process-level singleton ────────────────────────────────────────────────────
_adaptation_plane = AdaptationPlane()

def get_adaptation_plane() -> AdaptationPlane:
    return _adaptation_plane
