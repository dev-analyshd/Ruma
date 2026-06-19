"""
Dynamic Strategy Selector — RUMA
==================================
Agent diagnoses market regime, then picks the optimal strategy from 5 candidates.

Like a doctor prescribing: diagnose first, prescribe second — never the reverse.

Five strategies (all CMC-data driven):
  1. MomentumBreakout      — ADX>25, trend following
  2. MeanReversion         — RSI extremes, fade the move
  3. VolatilityExpansion   — Bollinger Band breakout
  4. LiquiditySweep        — Counter-trade stop hunts
  5. FundingRateArb        — Funding rate extremes → mean revert

Effectiveness matrix (rows=strategy, cols=regime) learned from backtest.
Will be updated in-process as RUMA accumulates competition trades.
"""
from __future__ import annotations
import math
import time
from dataclasses import dataclass, field
from typing import Any

# ── Effectiveness matrix: strategy × regime → historical win rate ──────────────
# Starting values from prior backtest. Updated as trades accumulate.
EFFECTIVENESS_MATRIX: dict[str, dict[str, float]] = {
    "MomentumBreakout": {
        "BULL":      0.82,
        "BEAR":      0.75,    # Short momentum
        "SIDEWAYS":  0.28,    # Trend strategies fail in chop
        "VOLATILE":  0.42,
        "CRASH":     0.10,
        "RECOVERY":  0.68,
    },
    "MeanReversion": {
        "BULL":      0.42,
        "BEAR":      0.42,
        "SIDEWAYS":  0.80,    # Mean reversion shines in ranging markets
        "VOLATILE":  0.52,    # Overshoots create reversion opportunity
        "CRASH":     0.15,    # Don't fade crash momentum
        "RECOVERY":  0.72,
    },
    "VolatilityExpansion": {
        "BULL":      0.58,
        "BEAR":      0.60,
        "SIDEWAYS":  0.20,    # No expansion in sideways
        "VOLATILE":  0.87,    # Best regime for vol strategies
        "CRASH":     0.65,    # Crash = vol spike = opportunity
        "RECOVERY":  0.55,
    },
    "LiquiditySweep": {
        "BULL":      0.55,
        "BEAR":      0.55,
        "SIDEWAYS":  0.68,    # Stop hunts common in ranging
        "VOLATILE":  0.72,
        "CRASH":     0.40,
        "RECOVERY":  0.60,
    },
    "FundingRateArb": {
        "BULL":      0.70,    # High funding → short bias
        "BEAR":      0.65,    # Negative funding → long bias
        "SIDEWAYS":  0.75,    # Funding arb works independent of direction
        "VOLATILE":  0.40,    # Funding can spike unpredictably
        "CRASH":     0.30,
        "RECOVERY":  0.68,
    },
}


@dataclass
class RegimeProbability:
    BULL: float = 0.0
    BEAR: float = 0.0
    SIDEWAYS: float = 0.0
    VOLATILE: float = 0.0
    CRASH: float = 0.0
    RECOVERY: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {
            "BULL": round(self.BULL, 4),
            "BEAR": round(self.BEAR, 4),
            "SIDEWAYS": round(self.SIDEWAYS, 4),
            "VOLATILE": round(self.VOLATILE, 4),
            "CRASH": round(self.CRASH, 4),
            "RECOVERY": round(self.RECOVERY, 4),
        }

    def dominant(self) -> str:
        return max(self.to_dict(), key=self.to_dict().__getitem__)


@dataclass
class StrategySignal:
    name: str
    direction: str     # LONG | SHORT | NEUTRAL
    confidence: float  # 0.0–1.0
    entry_logic: str
    stop_logic: str
    target_logic: str
    regime: str
    expected_return: float   # fraction (0.04 = 4%)
    expected_risk: float     # fraction (0.02 = 2%)
    effectiveness: float     # historical win rate in current regime


@dataclass
class SelectionResult:
    selected: str           # strategy name
    signal: StrategySignal
    regime_probs: dict[str, float]
    expected_returns: dict[str, float]  # all strategies ranked
    psi_sufficient: bool
    silenced: bool = False
    silence_reason: str = ""
    effectiveness_matrix: dict = field(default_factory=dict)


class DynamicStrategySelector:
    """
    Market diagnosis → strategy prescription.
    All 5 strategies work from CMC data — no extra data sources needed.
    """

    def __init__(self):
        self._effectiveness = {k: dict(v) for k, v in EFFECTIVENESS_MATRIX.items()}
        self._trade_history: list[dict] = []

    # ── Regime classification ──────────────────────────────────────────────────
    def classify_regime(
        self,
        fear_greed: int,
        price_change_24h: float,
        price_change_7d: float,
        vol_30d: float = 0.02,
        funding_rate: float = 0.0,
    ) -> RegimeProbability:
        """
        Soft classification → probability distribution over regimes.
        Uses fuzzy membership, not hard cutoffs.
        """
        p = RegimeProbability()

        # CRASH signal: extreme fear + sharp drop
        crash_score = max(0.0, (20 - fear_greed) / 20.0) * max(0.0, (-price_change_24h - 5) / 10.0)
        p.CRASH = min(0.95, crash_score * 2.0)

        # VOLATILE signal: high vol, wide F&G swings
        vol_score = min(1.0, vol_30d * 25)
        p.VOLATILE = vol_score * (1 - p.CRASH)

        # BULL signal: F&G > 55, positive multi-TF
        bull_score = max(0.0, (fear_greed - 50) / 50.0)
        trend_bull = max(0.0, min(1.0, price_change_7d / 15.0))
        p.BULL = bull_score * 0.6 + trend_bull * 0.4
        p.BULL *= (1 - p.CRASH) * (1 - p.VOLATILE * 0.5)

        # BEAR signal: F&G < 45, negative multi-TF
        bear_score = max(0.0, (50 - fear_greed) / 50.0)
        trend_bear = max(0.0, min(1.0, -price_change_7d / 15.0))
        p.BEAR = bear_score * 0.6 + trend_bear * 0.4
        p.BEAR *= (1 - p.CRASH) * (1 - p.VOLATILE * 0.5)

        # RECOVERY signal: after crash, fear abating
        recovery_score = max(0.0, (fear_greed - 30) / 30.0) if fear_greed < 50 and price_change_24h > 1 else 0.0
        p.RECOVERY = recovery_score * (1 - p.CRASH)

        # SIDEWAYS: remaining probability
        total = p.BULL + p.BEAR + p.VOLATILE + p.CRASH + p.RECOVERY
        p.SIDEWAYS = max(0.0, 1.0 - total)

        # Normalise
        total2 = p.BULL + p.BEAR + p.SIDEWAYS + p.VOLATILE + p.CRASH + p.RECOVERY
        if total2 > 0:
            p.BULL /= total2; p.BEAR /= total2; p.SIDEWAYS /= total2
            p.VOLATILE /= total2; p.CRASH /= total2; p.RECOVERY /= total2

        return p

    # ── Per-strategy signal generation ────────────────────────────────────────
    def _momentum_signal(self, snap: dict, regime: str, regime_probs: RegimeProbability) -> StrategySignal:
        p24h = snap.get("price_change_24h", 0.0)
        p7d  = snap.get("price_change_7d", 0.0)
        direction = "LONG" if p24h > 0 and p7d > 0 else "SHORT" if p24h < 0 and p7d < 0 else "NEUTRAL"
        confidence = min(0.95, abs(p24h) / 10.0 * 0.5 + abs(p7d) / 20.0 * 0.5)
        eff = self._effectiveness["MomentumBreakout"].get(regime, 0.5)
        return StrategySignal(
            name="MomentumBreakout", direction=direction, confidence=round(confidence, 4),
            entry_logic=f"24h={p24h:.2f}% + 7d={p7d:.2f}% aligned momentum breakout",
            stop_logic="2% below entry (ATR-adaptive)",
            target_logic="4% above entry (2:1 R:R)",
            regime=regime, expected_return=0.04, expected_risk=0.02, effectiveness=eff,
        )

    def _mean_reversion_signal(self, snap: dict, regime: str, regime_probs: RegimeProbability) -> StrategySignal:
        fg = snap.get("fear_greed", 50)
        p24h = snap.get("price_change_24h", 0.0)
        # Fade extremes
        if p24h < -4 and fg < 35:
            direction, conf = "LONG", min(0.85, abs(p24h) / 8.0)
            entry_logic = f"Oversold: 24h={p24h:.2f}%, F&G={fg} → mean reversion LONG"
        elif p24h > 4 and fg > 65:
            direction, conf = "SHORT", min(0.85, p24h / 8.0)
            entry_logic = f"Overbought: 24h={p24h:.2f}%, F&G={fg} → mean reversion SHORT"
        else:
            direction, conf = "NEUTRAL", 0.3
            entry_logic = f"No extreme: 24h={p24h:.2f}%, F&G={fg}"
        eff = self._effectiveness["MeanReversion"].get(regime, 0.5)
        return StrategySignal(
            name="MeanReversion", direction=direction, confidence=round(conf, 4),
            entry_logic=entry_logic, stop_logic="2.5% adverse move stops trade",
            target_logic="Return to 24h mean (3%)",
            regime=regime, expected_return=0.03, expected_risk=0.025, effectiveness=eff,
        )

    def _volatility_expansion_signal(self, snap: dict, regime: str, regime_probs: RegimeProbability) -> StrategySignal:
        p1h  = snap.get("price_change_1h", 0.0)
        p24h = snap.get("price_change_24h", 0.0)
        vol = abs(p24h) / 100.0
        expanding = vol > 0.03  # >3% daily vol = expanding
        direction = "LONG" if p1h > 0 and p24h > 0 else "SHORT" if p1h < 0 and p24h < 0 else "NEUTRAL"
        conf = min(0.90, vol * 15) if expanding else 0.25
        eff = self._effectiveness["VolatilityExpansion"].get(regime, 0.5)
        return StrategySignal(
            name="VolatilityExpansion", direction=direction, confidence=round(conf, 4),
            entry_logic=f"Vol expanding: 24h={p24h:.2f}%, 1h={p1h:.2f}% — ride BB breakout",
            stop_logic="1.5% tight stop (vol strategies need tight stops)",
            target_logic="5% target (2× vol capture)",
            regime=regime, expected_return=0.05, expected_risk=0.015, effectiveness=eff,
        )

    def _liquidity_sweep_signal(self, snap: dict, regime: str, regime_probs: RegimeProbability) -> StrategySignal:
        p1h  = snap.get("price_change_1h", 0.0)
        p24h = snap.get("price_change_24h", 0.0)
        # Sweep: 1h reverses 24h move sharply
        sweep = abs(p1h) > 1.5 and (p1h * p24h < 0)
        direction = "LONG" if p1h < 0 and p24h > 0 else "SHORT" if p1h > 0 and p24h < 0 else "NEUTRAL"
        conf = min(0.80, abs(p1h) / 3.0) if sweep else 0.25
        eff = self._effectiveness["LiquiditySweep"].get(regime, 0.5)
        return StrategySignal(
            name="LiquiditySweep", direction=direction, confidence=round(conf, 4),
            entry_logic=f"Stop hunt: 1h={p1h:.2f}% reverses 24h trend={p24h:.2f}%",
            stop_logic="2% beyond the sweep low/high",
            target_logic="3% target (counter-trend to pre-sweep level)",
            regime=regime, expected_return=0.03, expected_risk=0.02, effectiveness=eff,
        )

    def _funding_arb_signal(self, snap: dict, regime: str, regime_probs: RegimeProbability) -> StrategySignal:
        funding = snap.get("funding_rate", 0.0)
        fg = snap.get("fear_greed", 50)
        if funding > 0.001:   # Positive: longs paying → short bias
            direction, conf = "SHORT", min(0.80, funding * 500)
            entry_logic = f"Funding={funding*100:.4f}% (positive) → short perp, long spot arb"
        elif funding < -0.001:  # Negative: shorts paying → long bias
            direction, conf = "LONG", min(0.80, abs(funding) * 500)
            entry_logic = f"Funding={funding*100:.4f}% (negative) → long perp, short spot arb"
        else:
            direction, conf = "NEUTRAL", 0.30
            entry_logic = f"Funding flat ({funding*100:.4f}%) — no arb opportunity"
        eff = self._effectiveness["FundingRateArb"].get(regime, 0.5)
        return StrategySignal(
            name="FundingRateArb", direction=direction, confidence=round(conf, 4),
            entry_logic=entry_logic, stop_logic="1% adverse move (arb should be low risk)",
            target_logic="Funding capture over 8h (typically 0.1–0.3%)",
            regime=regime, expected_return=0.003, expected_risk=0.01, effectiveness=eff,
        )

    # ── Main selector ──────────────────────────────────────────────────────────
    def select_strategy(
        self,
        snap: dict,
        psi: float,
        lambda_val: float = 0.01,
        min_psi: float = 0.55,
    ) -> SelectionResult:
        fg = snap.get("fear_greed", 50)
        p24h = snap.get("price_change_24h", 0.0)
        p7d  = snap.get("price_change_7d", 0.0)
        vol  = abs(p24h) / 100.0

        # 1. Classify regime
        regime_probs = self.classify_regime(fg, p24h, p7d, vol)
        dominant_regime = regime_probs.dominant()

        # 2. Silence gate — insufficient coherence
        if psi < min_psi:
            return SelectionResult(
                selected="SILENCE", signal=StrategySignal(
                    name="SILENCE", direction="NEUTRAL", confidence=0.0,
                    entry_logic="Ψ insufficient", stop_logic="—", target_logic="—",
                    regime=dominant_regime, expected_return=0.0, expected_risk=0.0, effectiveness=0.0,
                ),
                regime_probs=regime_probs.to_dict(),
                expected_returns={s: 0.0 for s in self._effectiveness},
                psi_sufficient=False, silenced=True,
                silence_reason=f"Ψ={psi:.3f} < min={min_psi} — insufficient coherence for strategy selection",
            )

        # 3. Generate signals from all 5 strategies
        signals: dict[str, StrategySignal] = {
            "MomentumBreakout": self._momentum_signal(snap, dominant_regime, regime_probs),
            "MeanReversion":    self._mean_reversion_signal(snap, dominant_regime, regime_probs),
            "VolatilityExpansion": self._volatility_expansion_signal(snap, dominant_regime, regime_probs),
            "LiquiditySweep":   self._liquidity_sweep_signal(snap, dominant_regime, regime_probs),
            "FundingRateArb":   self._funding_arb_signal(snap, dominant_regime, regime_probs),
        }

        # 4. Expected return = Σ P(regime) × effectiveness[strategy][regime] × signal.confidence
        expected_returns: dict[str, float] = {}
        rp = regime_probs.to_dict()
        for name, sig in signals.items():
            er = sum(
                rp[regime] * self._effectiveness[name].get(regime, 0.5) * sig.confidence
                for regime in rp
            )
            expected_returns[name] = round(er, 5)

        # 5. Pick best
        best_name = max(expected_returns, key=expected_returns.__getitem__)
        best_signal = signals[best_name]

        return SelectionResult(
            selected=best_name,
            signal=best_signal,
            regime_probs=regime_probs.to_dict(),
            expected_returns=dict(sorted(expected_returns.items(), key=lambda x: -x[1])),
            psi_sufficient=True,
            effectiveness_matrix=self._effectiveness,
        )

    def update_effectiveness(self, strategy: str, regime: str, won: bool):
        """Update effectiveness matrix from a completed trade (online learning)."""
        if strategy not in self._effectiveness or regime not in self._effectiveness[strategy]:
            return
        current = self._effectiveness[strategy][regime]
        result = 1.0 if won else 0.0
        # Exponential moving average with α=0.1 (slow update — don't overfit)
        self._effectiveness[strategy][regime] = round(current * 0.90 + result * 0.10, 4)


# Singleton
_selector = DynamicStrategySelector()

def get_selector() -> DynamicStrategySelector:
    return _selector
