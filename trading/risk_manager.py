"""
Risk Manager — RUMA
====================
Thin wrapper around DynamicRiskManager for backward compatibility.
RiskManager is the public API; DynamicRiskManager is the implementation.
"""
from trading.dynamic_risk import DynamicRiskManager, get_risk_manager


class RiskManager(DynamicRiskManager):
    """Public alias for DynamicRiskManager."""

    def daily_reset(self):
        """Reset daily risk counters."""
        self._daily_loss_used = 0.0
        self._win_streak = max(0, getattr(self, '_win_streak', 0))
        self._lose_streak = 0

    def get_status(self) -> dict:
        limits = self.compute_limits()
        return {
            "status": "ok",
            "daily_risk_budget_pct": round(limits.daily_risk_budget * 100, 3),
            "drawdown_cap_pct": round(limits.drawdown_cap * 100, 3),
            "session": limits.session,
            "stress_index": round(limits.stress_index, 3),
        }
