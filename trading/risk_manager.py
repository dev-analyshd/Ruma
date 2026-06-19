"""
Risk Manager — RUMA
====================
Thin wrapper around DynamicRiskManager for backward compatibility.
RiskManager is the public API; DynamicRiskManager is the implementation.
"""
from trading.dynamic_risk import DynamicRiskManager, get_risk_manager


class RiskManager(DynamicRiskManager):
    """Public alias for DynamicRiskManager with additional helpers."""

    def __init__(self):
        super().__init__()
        self._daily_loss_used: float = 0.0
        self._win_streak: int = 0
        self._lose_streak: int = 0
        self._total_drawdown_pct: float = 0.0

    def compute_limits(self, **kwargs):
        """
        Convenience alias for compute_dynamic_limits using current agent state.
        Called by twak_routes and other consumers.
        """
        from core.moat_accumulator import get_moat
        moat = get_moat()
        return self.compute_dynamic_limits(
            lambda_val=moat.get_current_lambda(),
            consecutive_wins=self._win_streak,
            fear_greed=kwargs.get("fear_greed", 50),
            vol_30d=kwargs.get("vol_30d", 0.02),
            price_change_5m=kwargs.get("price_change_5m", 0.0),
            psi_history=kwargs.get("psi_history"),
            avg_correlation=kwargs.get("avg_correlation", 0.3),
            capital_deployed_pct=kwargs.get("capital_deployed_pct", 0.0),
            competition_days_remaining=kwargs.get("competition_days_remaining", 7),
            current_drawdown_pct=self._total_drawdown_pct,
        )

    def daily_reset(self):
        """Reset daily risk counters (called at UTC 00:00)."""
        self._daily_loss_used = 0.0
        self._win_streak = max(0, self._win_streak)
        self._lose_streak = 0

    def record_trade(self, pnl_pct: float):
        """Update win/loss streak and drawdown on trade completion."""
        if pnl_pct > 0:
            self._win_streak += 1
            self._lose_streak = 0
        else:
            self._lose_streak += 1
            self._win_streak = 0
            self._daily_loss_used += abs(pnl_pct)
            self._total_drawdown_pct += abs(pnl_pct)

    def is_drawdown_halt(self) -> bool:
        """True if 28% hard drawdown cap is hit (2% buffer before 30% DQ line)."""
        return self._total_drawdown_pct >= 28.0

    def is_daily_loss_halt(self) -> bool:
        """True if 6% daily loss limit is hit."""
        return self._daily_loss_used >= 6.0

    def get_status(self) -> dict:
        limits = self.compute_limits()
        return {
            "status": "HALTED" if self.is_drawdown_halt() else "ACTIVE",
            "daily_risk_budget_pct": round(limits.daily_risk_budget * 100, 3),
            "drawdown_cap_pct": round(limits.drawdown_cap * 100, 3),
            "per_trade_max_pct": round(limits.per_trade_max * 100, 3),
            "session": limits.session,
            "stress_index": round(limits.stress_index, 3),
            "daily_loss_used_pct": round(self._daily_loss_used, 3),
            "total_drawdown_pct": round(self._total_drawdown_pct, 3),
            "win_streak": self._win_streak,
            "drawdown_halt": self.is_drawdown_halt(),
            "daily_loss_halt": self.is_daily_loss_halt(),
            "competition_dq_line_pct": 30.0,
        }
