"""
Dynamic Position Sizer — RUMA
==============================
Replaces the fixed 2% cap with a 5-factor adaptive model:
  1. Bayesian Kelly (signal-driven)
  2. Regime multiplier (trending/ranging/volatile/crash/recovery)
  3. Confidence gate (Ψ² quadratic scaling)
  4. Volatility adjustment (1 / (1 + vol_30d))
  5. Liquidity cap (max 1% of daily volume)
  + Correlation penalty (concentration risk)
  + Hard ceiling: min(raw, liquidity_cap, capital × 0.10)
"""
from __future__ import annotations
import math
import time
from dataclasses import dataclass, field
from typing import Any

# ── Regime multipliers ────────────────────────────────────────────────────────
REGIME_MULTIPLIERS: dict[str, float] = {
    "BULL":      1.40,   # Strong trend → increase size
    "BEAR":      1.20,   # Downtrend also tradeable (shorts), slightly larger
    "SIDEWAYS":  0.70,   # Choppy — reduce conviction
    "VOLATILE":  0.40,   # High vol — protect capital
    "CRASH":     0.00,   # Silence — no position
    "RECOVERY":  1.10,   # Post-crash mean reversion bonus
}

ABSOLUTE_CEILING = 0.10   # Hard max: 10% of capital (competition + safety)
KELLY_FRACTION   = 0.25   # Fractional Kelly multiplier (conservative)
LIQUIDITY_PCT    = 0.01   # Max 1% of daily volume


@dataclass
class MarketState:
    regime: str = "SIDEWAYS"          # BULL|BEAR|SIDEWAYS|VOLATILE|CRASH|RECOVERY
    volatility_30d: float = 0.02      # Realised vol (daily %, 0.02 = 2%)
    daily_volume_usd: float = 1_000_000.0  # Asset 24h volume USD
    bid_ask_spread: float = 0.001     # Spread fraction (0.001 = 0.1%)
    avg_correlation: float = 0.3      # Portfolio avg correlation
    price_change_5m: float = 0.0      # 5-min price change (for flash crash)
    fear_greed: int = 50
    adx: float = 25.0                 # ADX trend strength (>25 = trending)

    @classmethod
    def from_cmc_snap(cls, snap: dict) -> "MarketState":
        fg = snap.get("fear_greed", 50)
        p24h = snap.get("price_change_24h", 0.0)
        p7d  = snap.get("price_change_7d", 0.0)
        vol  = abs(p24h) / 100.0

        if fg >= 60 and p7d > 5:
            regime = "BULL"
        elif fg <= 30 and p7d < -5:
            regime = "BEAR"
        elif vol > 0.06:
            regime = "VOLATILE"
        elif abs(p7d) < 3 and abs(p24h) < 2:
            regime = "SIDEWAYS"
        else:
            regime = "SIDEWAYS"

        return cls(
            regime=regime,
            volatility_30d=max(0.005, vol),
            daily_volume_usd=snap.get("volume_24h", 1_000_000),
            fear_greed=fg,
        )


@dataclass
class AgentState:
    psi: float = 0.7                  # Current Ψ coherence score
    lambda_val: float = 0.1           # Moat accumulator Λ
    consecutive_wins: int = 0
    portfolio_correlation: float = 0.3
    capital_deployed: float = 0.0
    total_capital: float = 500.0
    psi_history: list[float] = field(default_factory=list)


@dataclass
class SizingResult:
    size_usd: float
    size_pct: float                   # % of capital
    kelly_raw: float
    regime_mult: float
    confidence_mult: float
    vol_mult: float
    liquidity_cap_usd: float
    correlation_penalty: float
    regime: str
    reasoning: str
    components: dict[str, float]

    def to_dict(self) -> dict:
        return {
            "size_usd": round(self.size_usd, 4),
            "size_pct": round(self.size_pct * 100, 3),
            "kelly_raw": round(self.kelly_raw, 5),
            "regime_mult": self.regime_mult,
            "confidence_mult": round(self.confidence_mult, 4),
            "vol_mult": round(self.vol_mult, 4),
            "liquidity_cap_usd": round(self.liquidity_cap_usd, 2),
            "correlation_penalty": round(self.correlation_penalty, 4),
            "regime": self.regime,
            "reasoning": self.reasoning,
            "components": {k: round(v, 5) for k, v in self.components.items()},
        }


class DynamicPositionSizer:
    """
    Adaptive Kelly-based position sizer.
    Replaces the fixed 2% cap everywhere in the codebase.
    """

    @staticmethod
    def bayesian_kelly(p_win: float, avg_win: float, avg_loss: float) -> float:
        """Full Kelly: f* = (p·b - q) / b  where b = avg_win/avg_loss."""
        if avg_loss <= 0:
            return 0.0
        b = avg_win / avg_loss
        q = 1.0 - p_win
        kelly = (p_win * b - q) / b
        return max(0.0, min(kelly * KELLY_FRACTION, ABSOLUTE_CEILING))

    def compute_size(
        self,
        capital: float,
        psi: float,
        market: MarketState,
        agent: AgentState,
        win_probability: float = 0.55,
        avg_win_pct: float = 0.04,    # 4% target
        avg_loss_pct: float = 0.02,   # 2% stop
    ) -> SizingResult:
        # 1. Base Kelly
        kelly = self.bayesian_kelly(win_probability, avg_win_pct, avg_loss_pct)

        # 2. Regime multiplier
        regime_mult = REGIME_MULTIPLIERS.get(market.regime, 0.70)
        if regime_mult == 0.0:
            return SizingResult(
                size_usd=0.0, size_pct=0.0, kelly_raw=kelly,
                regime_mult=0.0, confidence_mult=0.0, vol_mult=0.0,
                liquidity_cap_usd=0.0, correlation_penalty=0.0,
                regime=market.regime,
                reasoning=f"CRASH regime — no position (silence enforced)",
                components={"regime_mult": 0.0},
            )

        # 3. Confidence gate: Ψ² quadratic scaling
        confidence_mult = psi ** 2

        # 4. Volatility adjustment: tighter vol → larger size
        vol_mult = 1.0 / (1.0 + market.volatility_30d * 10)

        # 5. Liquidity cap: max 1% of daily volume
        liquidity_cap = market.daily_volume_usd * LIQUIDITY_PCT

        # 6. Correlation penalty (reduce if portfolio is concentrated)
        corr = max(0.0, min(1.0, agent.portfolio_correlation))
        correlation_penalty = 1.0 - corr * 0.5   # 0.3 correlation → 0.85 penalty

        # 7. Compute raw size
        raw_size = capital * kelly * regime_mult * confidence_mult * vol_mult * correlation_penalty
        final_size = min(raw_size, liquidity_cap, capital * ABSOLUTE_CEILING)
        final_size = max(0.0, final_size)
        size_pct = final_size / capital if capital > 0 else 0.0

        # 8. Build reasoning string
        reasoning = (
            f"Kelly={kelly:.4f} × regime[{market.regime}]={regime_mult} "
            f"× Ψ²={confidence_mult:.3f} × vol_adj={vol_mult:.3f} "
            f"× corr_penalty={correlation_penalty:.3f} "
            f"→ ${final_size:.2f} ({size_pct*100:.2f}% of capital)"
        )

        return SizingResult(
            size_usd=round(final_size, 4),
            size_pct=round(size_pct, 6),
            kelly_raw=round(kelly, 5),
            regime_mult=regime_mult,
            confidence_mult=round(confidence_mult, 4),
            vol_mult=round(vol_mult, 4),
            liquidity_cap_usd=round(liquidity_cap, 2),
            correlation_penalty=round(correlation_penalty, 4),
            regime=market.regime,
            reasoning=reasoning,
            components={
                "capital": capital,
                "kelly_raw": kelly,
                "regime_mult": regime_mult,
                "confidence_mult": confidence_mult,
                "vol_mult": vol_mult,
                "correlation_penalty": correlation_penalty,
                "raw_size": raw_size,
                "liquidity_cap": liquidity_cap,
                "ceiling_10pct": capital * ABSOLUTE_CEILING,
                "final_size": final_size,
            },
        )

    def size_from_psi_and_snap(
        self, capital: float, psi: float, snap: dict, agent: AgentState | None = None
    ) -> SizingResult:
        """Convenience: compute size from live CMC snapshot dict."""
        market = MarketState.from_cmc_snap(snap)
        if agent is None:
            agent = AgentState(psi=psi, total_capital=capital)
        win_prob = 0.5 + (psi - 0.5) * 0.4  # map Ψ → win probability
        return self.compute_size(capital, psi, market, agent,
                                  win_probability=win_prob)


# Singleton
_sizer = DynamicPositionSizer()

def get_sizer() -> DynamicPositionSizer:
    return _sizer
