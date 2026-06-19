"""
RUMA — All 10 ADAPT-Ω Trading Strategies
==========================================
Each strategy is a self-calibrating module that plugs into the StrategyRegistry.
Signals are scored from available market data (CMC snapshot + derived metrics).

Signal derivation philosophy:
  - Use what's available: fear_greed, price_change_*, volume_24h, funding_rate
  - Estimate what's missing: ADX from price velocity, RV from vol proxy, etc.
  - Never silence because data is missing — degrade gracefully

Strategy hierarchy (by Ψ requirement):
  9. CrossExchangeBasis    Ψ≥0.80  (precision arbitrage)
  7. OnChainFlowImbalance  Ψ≥0.75  (slow but reliable)
  1. PsiGatedMomentum      Ψ≥0.75  (trend following)
  5. LiquiditySweepReversal Ψ≥0.72 (counter-trade)
  6. VolatilityRegimeSwitch Ψ≥0.70 (regime detection)
 10. BlackSwanInsurance     Ψ≥0.70  (tail risk hedge)
  3. FundingRateArb         Ψ≥0.70  (funding cycle)
  4. SentimentDivergence    Ψ≥0.68  (social signal)
  2. MeanReversionFear      Ψ≥0.65  (fear fade)
  8. LambdaCompoundingDCA   Ψ≥0.50  (time-based accumulation)
"""
from __future__ import annotations
import math
import time
from datetime import datetime, timezone
from typing import Any

from trading.strategies import BaseStrategy


# ═══════════════════════════════════════════════════════════════════════════════
# Helper utilities
# ═══════════════════════════════════════════════════════════════════════════════

def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))

def _momentum_alignment(p1h: float, p24h: float, p7d: float) -> float:
    """Returns -1 to +1: how aligned the 3 timeframes are in direction."""
    signs = [1 if x > 0 else -1 if x < 0 else 0 for x in [p1h, p24h, p7d]]
    return sum(signs) / 3.0

def _adx_estimate(p1h: float, p24h: float, p7d: float) -> float:
    """Estimate ADX-like trend strength (0-50) from price changes."""
    alignment = abs(_momentum_alignment(p1h, p24h, p7d))
    magnitude = (abs(p24h) / 8.0 + abs(p7d) / 15.0) / 2.0
    return _clamp(alignment * 30 + magnitude * 20, 0, 50)

def _rsi_estimate(p1h: float, p24h: float) -> float:
    """Rough RSI proxy (0-100) from short-term vs medium-term momentum."""
    base = 50.0
    base += p1h * 5.0
    base += p24h * 1.5
    return _clamp(base, 5, 95)

def _vol_surge_score(volume_24h: float, baseline_vol: float = 1_000_000_000.0) -> float:
    """Score 0-1: how much volume_24h exceeds expected baseline."""
    if baseline_vol <= 0:
        return 0.5
    ratio = volume_24h / baseline_vol
    return _clamp(math.log(max(ratio, 0.01) + 1) / math.log(3), 0.0, 1.0)

def _utc_hour() -> int:
    return datetime.now(timezone.utc).hour

def _is_liquid_session(hour: int | None = None) -> bool:
    """True during UTC 8-20 (London open through NYSE close)."""
    h = hour if hour is not None else _utc_hour()
    return 8 <= h <= 20


# ═══════════════════════════════════════════════════════════════════════════════
# Strategy 1: Ψ-Gated Momentum Surge
# ═══════════════════════════════════════════════════════════════════════════════

class PsiGatedMomentum(BaseStrategy):
    """
    Trade when momentum is confirmed by high coherence AND the adaptation plane
    confirms the momentum is sustainable.

    Trigger: ADX > 25 + RSI breakout + volume surge
    Ψ requirement: Ψ ≥ 0.75
    """
    name = "momentum_surge"
    psi_requirement = 0.75
    max_size_pct = 0.10

    def opportunity_score(self, snapshot: dict) -> float:
        p1h  = snapshot.get("price_change_1h",  0.0)
        p24h = snapshot.get("price_change_24h", 0.0)
        p7d  = snapshot.get("price_change_7d",  0.0)
        vol  = snapshot.get("daily_volume_usd", snapshot.get("volume_24h", 1e9))
        fg   = snapshot.get("fear_greed", 50)

        adx  = _adx_estimate(p1h, p24h, p7d)
        rsi  = _rsi_estimate(p1h, p24h)
        alignment = _momentum_alignment(p1h, p24h, p7d)
        vol_score = _vol_surge_score(vol)
        liquid    = 1.0 if _is_liquid_session() else 0.4

        if adx < 20:
            return 0.05     # No trend → near-zero score
        if abs(alignment) < 0.33:
            return 0.10     # Mixed signals

        adx_score = _clamp((adx - 20) / 30.0)                  # 0→0 at ADX=20, 1→1 at ADX=50
        rsi_score = _clamp(abs(rsi - 50) / 45.0)               # high at extremes (breakout)
        fg_bonus  = 0.2 if (alignment > 0 and fg >= 60) else \
                    0.2 if (alignment < 0 and fg <= 40) else 0.0

        raw = 0.35 * adx_score + 0.30 * abs(alignment) + 0.20 * vol_score + 0.15 * rsi_score
        return _clamp(raw * liquid + fg_bonus)

    def direction(self, snapshot: dict) -> str:
        p1h  = snapshot.get("price_change_1h",  0.0)
        p24h = snapshot.get("price_change_24h", 0.0)
        p7d  = snapshot.get("price_change_7d",  0.0)
        alignment = _momentum_alignment(p1h, p24h, p7d)
        if alignment > 0.33:  return "LONG"
        if alignment < -0.33: return "SHORT"
        return "NEUTRAL"

    def _base_size_pct(self, snapshot: dict) -> float:
        return 0.03     # 3% base

    def on_chain_fields(self, psi, a_val, snapshot, size_usd):
        base = super().on_chain_fields(psi, a_val, snapshot, size_usd)
        p1h  = snapshot.get("price_change_1h",  0.0)
        p24h = snapshot.get("price_change_24h", 0.0)
        p7d  = snapshot.get("price_change_7d",  0.0)
        base.update({
            "adx_estimate": round(_adx_estimate(p1h, p24h, p7d), 2),
            "rsi_estimate": round(_rsi_estimate(p1h, p24h), 2),
            "momentum_alignment": round(_momentum_alignment(p1h, p24h, p7d), 3),
            "volume_24h_usd": snapshot.get("daily_volume_usd", 0),
            "regime": snapshot.get("regime", "UNKNOWN"),
        })
        return base


# ═══════════════════════════════════════════════════════════════════════════════
# Strategy 2: Mean Reversion with Fear Calibration
# ═══════════════════════════════════════════════════════════════════════════════

class MeanReversionFear(BaseStrategy):
    """
    Buy fear, sell greed — only when calibration confirms the fear is real.

    Trigger: price > 2σ below VWAP + Fear < 25 + funding negative
    Ψ requirement: Ψ ≥ 0.65
    """
    name = "mean_reversion_fear"
    psi_requirement = 0.65
    max_size_pct = 0.06

    def opportunity_score(self, snapshot: dict) -> float:
        fg      = snapshot.get("fear_greed", 50)
        p24h    = snapshot.get("price_change_24h", 0.0)
        p1h     = snapshot.get("price_change_1h", 0.0)
        funding = snapshot.get("funding_rate", 0.0)

        # Fear signal: the lower the F&G, the stronger the signal
        if fg > 35:
            return 0.05   # Not fearful enough
        fear_score = _clamp((35 - fg) / 35.0)                   # 0→fg=35, 1→fg=0

        # Price extension: big drop = better reversion opportunity
        drop_score = _clamp((-p24h - 3.0) / 20.0)              # meaningful above -3%
        if p24h >= 0:
            drop_score = 0.0

        # Funding: negative funding confirms shorts are paying longs
        funding_score = _clamp(-funding / 0.002)                 # ±0.2% = full score

        # Recency: short-term bounce starting? (p1h > 0 after big drop)
        bounce_hint = 0.15 if (p1h > 0 and p24h < -5) else 0.0

        raw = 0.40 * fear_score + 0.30 * drop_score + 0.20 * funding_score
        return _clamp(raw + bounce_hint)

    def direction(self, snapshot: dict) -> str:
        fg = snapshot.get("fear_greed", 50)
        return "LONG" if fg < 35 else "SHORT"

    def _base_size_pct(self, snapshot: dict) -> float:
        fg = snapshot.get("fear_greed", 50)
        if fg < 10:   return 0.04   # Extreme fear → 4%
        if fg < 25:   return 0.02
        return 0.015

    def on_chain_fields(self, psi, a_val, snapshot, size_usd):
        base = super().on_chain_fields(psi, a_val, snapshot, size_usd)
        base.update({
            "fear_index": snapshot.get("fear_greed", 50),
            "funding_rate": snapshot.get("funding_rate", 0.0),
            "vwap_distance_est": snapshot.get("price_change_24h", 0.0),
            "bounce_hint": snapshot.get("price_change_1h", 0.0) > 0,
        })
        return base


# ═══════════════════════════════════════════════════════════════════════════════
# Strategy 3: Funding Rate Arbitrage with Regime Filter
# ═══════════════════════════════════════════════════════════════════════════════

class FundingRateArb(BaseStrategy):
    """
    Exploit funding rate divergences between spot and perpetuals.

    Trigger: |Funding| > 0.05% + spot-perp spread > 0.02%
    Ψ requirement: Ψ ≥ 0.70
    """
    name = "funding_rate_arb"
    psi_requirement = 0.70
    max_size_pct = 0.10

    def opportunity_score(self, snapshot: dict) -> float:
        funding = abs(snapshot.get("funding_rate", 0.0))
        vol     = snapshot.get("daily_volume_usd", snapshot.get("volume_24h", 1e9))
        p1h     = snapshot.get("price_change_1h", 0.0)

        if funding < 0.0005:     # < 0.05% — not worth it
            return 0.05

        # Funding score: stronger divergence = better arb
        funding_score = _clamp(funding / 0.003)                  # 0.3% = max score

        # Liquidity score: need enough volume
        liq_score = _vol_surge_score(vol, 5e8)                   # $500M baseline

        # Near funding payment? (every 8h = UTC 0, 8, 16)
        h = _utc_hour()
        hours_to_payment = min(h % 8, 8 - (h % 8))
        timing_bonus = 0.15 if hours_to_payment <= 1 else 0.0

        # Low 1h volatility → easier to execute both legs cleanly
        low_vol_bonus = 0.10 if abs(p1h) < 0.5 else 0.0

        raw = 0.50 * funding_score + 0.30 * liq_score + 0.20 * (1.0 if _is_liquid_session() else 0.3)
        return _clamp(raw + timing_bonus + low_vol_bonus)

    def direction(self, snapshot: dict) -> str:
        funding = snapshot.get("funding_rate", 0.0)
        if funding > 0:   return "SHORT"    # Positive funding → long dominant → short perp
        if funding < 0:   return "LONG"
        return "NEUTRAL"

    def _base_size_pct(self, snapshot: dict) -> float:
        funding = abs(snapshot.get("funding_rate", 0.0))
        if funding > 0.001:   return 0.06
        if funding > 0.0005:  return 0.04
        return 0.02

    def on_chain_fields(self, psi, a_val, snapshot, size_usd):
        base = super().on_chain_fields(psi, a_val, snapshot, size_usd)
        funding = snapshot.get("funding_rate", 0.0)
        base.update({
            "funding_rate": funding,
            "funding_annualised_pct": round(funding * 3 * 365 * 100, 2),
            "spot_perp_spread_est": round(abs(funding) * 0.8, 5),
            "hours_to_payment": min(_utc_hour() % 8, 8 - (_utc_hour() % 8)),
            "near_payment_window": min(_utc_hour() % 8, 8 - (_utc_hour() % 8)) <= 1,
        })
        return base


# ═══════════════════════════════════════════════════════════════════════════════
# Strategy 4: Social Sentiment Divergence
# ═══════════════════════════════════════════════════════════════════════════════

class SentimentDivergence(BaseStrategy):
    """
    Trade when social sentiment and price action diverge.

    Trigger: Sentiment > 80 + price flat/down (divergence)
    Ψ requirement: Ψ ≥ 0.68
    """
    name = "sentiment_divergence"
    psi_requirement = 0.68
    max_size_pct = 0.05

    def opportunity_score(self, snapshot: dict) -> float:
        sentiment = snapshot.get("sentiment_score", snapshot.get("fear_greed", 50))
        p24h  = snapshot.get("price_change_24h", 0.0)
        p1h   = snapshot.get("price_change_1h", 0.0)
        bot_r = snapshot.get("bot_ratio", 0.3)

        # Divergence: high sentiment but price not following
        if sentiment < 65:
            return 0.05
        if p24h > 5.0:
            return 0.05   # Price already caught up

        sentiment_score = _clamp((sentiment - 65) / 35.0)
        divergence_score = _clamp((-p24h) / 8.0) if p24h < 0 else \
                           _clamp((5 - p24h) / 10.0)           # Flat is also divergent

        # Bot ratio penalty (high bot activity makes sentiment unreliable)
        bot_penalty = 1.0 - _clamp(bot_r * 1.5)

        # Liquidity session bonus
        session_mult = 1.0 if _is_liquid_session() else 0.6

        raw = (0.45 * sentiment_score + 0.35 * divergence_score + 0.20 * bot_penalty)
        return _clamp(raw * session_mult)

    def direction(self, snapshot: dict) -> str:
        sentiment = snapshot.get("sentiment_score", snapshot.get("fear_greed", 50))
        return "LONG" if sentiment >= 65 else "SHORT"

    def _base_size_pct(self, snapshot: dict) -> float:
        sentiment = snapshot.get("sentiment_score", snapshot.get("fear_greed", 50))
        p24h = snapshot.get("price_change_24h", 0.0)
        if sentiment > 90 and p24h < -5: return 0.05
        if sentiment > 80:               return 0.025
        return 0.015

    def on_chain_fields(self, psi, a_val, snapshot, size_usd):
        base = super().on_chain_fields(psi, a_val, snapshot, size_usd)
        base.update({
            "sentiment_score": snapshot.get("sentiment_score", snapshot.get("fear_greed", 50)),
            "bot_ratio": snapshot.get("bot_ratio", 0.3),
            "price_change_4h_est": snapshot.get("price_change_1h", 0.0) * 2.0,
            "divergence_strength": round(-snapshot.get("price_change_24h", 0.0) / 8.0, 3),
        })
        return base


# ═══════════════════════════════════════════════════════════════════════════════
# Strategy 5: Liquidity Sweep Reversal
# ═══════════════════════════════════════════════════════════════════════════════

class LiquiditySweepReversal(BaseStrategy):
    """
    Trade after liquidity sweeps — when stops are triggered and price reverses.

    Trigger: Price sweeps below key support + immediate reversal + volume spike
    Ψ requirement: Ψ ≥ 0.72
    """
    name = "liquidity_sweep"
    psi_requirement = 0.72
    max_size_pct = 0.07

    def opportunity_score(self, snapshot: dict) -> float:
        p1h  = snapshot.get("price_change_1h", 0.0)
        p24h = snapshot.get("price_change_24h", 0.0)
        p7d  = snapshot.get("price_change_7d", 0.0)
        vol  = snapshot.get("daily_volume_usd", snapshot.get("volume_24h", 1e9))

        # Classic sweep pattern: significant 24h drop but short-term 1h reversal
        # i.e., p24h negative but p1h turning positive (or at least less negative)
        if p24h >= -2.0:
            return 0.05   # No meaningful sweep

        sweep_depth = _clamp((-p24h - 2.0) / 18.0)             # Score increases with drop depth
        reversal    = _clamp((p1h + 1.0) / 4.0) if p1h > -1.0 else 0.0  # Bounce started?
        vol_surge   = _vol_surge_score(vol)                     # Volume on the sweep

        # Weekly context: short-term sweep within longer bullish trend?
        weekly_bullish_context = 0.15 if p7d > 2 else 0.0

        # Only during liquid sessions (low-liquidity sweeps are traps)
        if not _is_liquid_session():
            return 0.05   # Off-hours sweeps are traps

        raw = 0.35 * sweep_depth + 0.35 * reversal + 0.30 * vol_surge
        return _clamp(raw + weekly_bullish_context)

    def direction(self, snapshot: dict) -> str:
        p24h = snapshot.get("price_change_24h", 0.0)
        return "LONG" if p24h < 0 else "SHORT"

    def _base_size_pct(self, snapshot: dict) -> float:
        p24h = snapshot.get("price_change_24h", 0.0)
        if p24h < -10: return 0.05   # Deep sweep → higher conviction
        if p24h < -5:  return 0.035
        return 0.025

    def on_chain_fields(self, psi, a_val, snapshot, size_usd):
        base = super().on_chain_fields(psi, a_val, snapshot, size_usd)
        base.update({
            "sweep_depth_pct": abs(snapshot.get("price_change_24h", 0.0)),
            "reversal_candle_1h": snapshot.get("price_change_1h", 0.0),
            "volume_surge": _vol_surge_score(snapshot.get("daily_volume_usd", 1e9)),
            "session_liquid": _is_liquid_session(),
        })
        return base


# ═══════════════════════════════════════════════════════════════════════════════
# Strategy 6: Volatility Regime Switch
# ═══════════════════════════════════════════════════════════════════════════════

class VolatilityRegimeSwitch(BaseStrategy):
    """
    Detect volatility regime changes and switch between long-vol and short-vol.

    Trigger: Realized vol crosses implied vol + regime change detected
    Ψ requirement: Ψ ≥ 0.70
    """
    name = "volatility_regime_switch"
    psi_requirement = 0.70
    max_size_pct = 0.05

    def opportunity_score(self, snapshot: dict) -> float:
        p24h = snapshot.get("price_change_24h", 0.0)
        p1h  = snapshot.get("price_change_1h", 0.0)
        p7d  = snapshot.get("price_change_7d", 0.0)
        fg   = snapshot.get("fear_greed", 50)

        # Realized vol proxy: avg |daily move| over short window
        realized_vol = (abs(p24h) + abs(p1h) * 4) / 2.0        # annualised estimate
        # Implied vol proxy: use fear_greed as VIX-like proxy
        implied_vol  = (100 - fg) / 5.0                        # fg=0→IV=20, fg=100→IV=0

        vol_spread = realized_vol - implied_vol
        regime_conf = abs(vol_spread) / (implied_vol + 1e-6)   # How big is the divergence?

        if abs(vol_spread) < 2.0:
            return 0.05   # Spread too tight — no edge

        spread_score = _clamp(abs(vol_spread) / 15.0)          # Normalise
        conf_score   = _clamp(regime_conf / 2.0)

        # Regime change detection: alignment breaking down
        alignment = _momentum_alignment(p1h, p24h, p7d)
        regime_break = _clamp(1.0 - abs(alignment))             # High when signals disagree

        raw = 0.40 * spread_score + 0.30 * conf_score + 0.30 * regime_break
        return _clamp(raw)

    def direction(self, snapshot: dict) -> str:
        p24h = snapshot.get("price_change_24h", 0.0)
        fg   = snapshot.get("fear_greed", 50)
        realized_vol = abs(p24h)
        implied_vol  = (100 - fg) / 5.0
        # RV > IV → vol expanding → LONG vol (buy puts/perps)
        # RV < IV → vol contracting → SHORT vol (sell premium)
        return "LONG" if realized_vol > implied_vol else "SHORT"

    def _base_size_pct(self, snapshot: dict) -> float:
        return 0.02

    def on_chain_fields(self, psi, a_val, snapshot, size_usd):
        base = super().on_chain_fields(psi, a_val, snapshot, size_usd)
        p24h = snapshot.get("price_change_24h", 0.0)
        fg   = snapshot.get("fear_greed", 50)
        base.update({
            "realized_vol_proxy": round(abs(p24h), 3),
            "implied_vol_proxy": round((100 - fg) / 5.0, 3),
            "vol_spread": round(abs(p24h) - (100 - fg) / 5.0, 3),
            "regime_direction": self.direction(snapshot),
        })
        return base


# ═══════════════════════════════════════════════════════════════════════════════
# Strategy 7: On-Chain Flow Imbalance
# ═══════════════════════════════════════════════════════════════════════════════

class OnChainFlowImbalance(BaseStrategy):
    """
    Trade when on-chain flows show institutional accumulation or distribution.

    Trigger: Exchange outflows > 2σ + whale accumulation + stable price
    Ψ requirement: Ψ ≥ 0.75
    """
    name = "onchain_flow"
    psi_requirement = 0.75
    max_size_pct = 0.07

    def opportunity_score(self, snapshot: dict) -> float:
        outflow_z  = snapshot.get("onchain_outflow_zscore", 0.0)
        whale_cnt  = snapshot.get("whale_count", 0)
        p24h       = snapshot.get("price_change_24h", 0.0)
        p7d        = snapshot.get("price_change_7d", 0.0)
        vol        = snapshot.get("daily_volume_usd", snapshot.get("volume_24h", 1e9))

        # Outflow z-score: >2σ means significant coins leaving exchanges (bullish)
        if outflow_z < 1.5 and whale_cnt < 3:
            # Estimate from available data if not present
            # Use low p24h with high volume as a proxy for accumulation
            if abs(p24h) < 2.0 and vol > 5e8:
                outflow_z = 1.8   # Estimated accumulation
                whale_cnt = 2

        outflow_score = _clamp((outflow_z - 1.0) / 3.0)       # 0 at z=1, 1 at z=4
        whale_score   = _clamp(whale_cnt / 8.0)               # 0→0 whales, 1→8 whales

        # Price stability: accumulation happens when price isn't moving much
        stability_score = _clamp(1.0 - abs(p24h) / 10.0)

        # Weekly trend context: accumulation in bull trend is most reliable
        weekly_score = _clamp((p7d + 5.0) / 20.0) if p7d > -5 else 0.2

        raw = 0.35 * outflow_score + 0.25 * whale_score + 0.25 * stability_score + 0.15 * weekly_score
        return _clamp(raw)

    def direction(self, snapshot: dict) -> str:
        outflow_z = snapshot.get("onchain_outflow_zscore", 1.0)
        return "LONG" if outflow_z > 0 else "SHORT"

    def _base_size_pct(self, snapshot: dict) -> float:
        outflow_z = snapshot.get("onchain_outflow_zscore", 0.0)
        whale_cnt = snapshot.get("whale_count", 0)
        if outflow_z > 3 and whale_cnt > 5: return 0.05
        if outflow_z > 2:                   return 0.035
        return 0.02

    def on_chain_fields(self, psi, a_val, snapshot, size_usd):
        base = super().on_chain_fields(psi, a_val, snapshot, size_usd)
        base.update({
            "outflow_zscore": snapshot.get("onchain_outflow_zscore", 0.0),
            "whale_count": snapshot.get("whale_count", 0),
            "price_stability": round(1.0 - abs(snapshot.get("price_change_24h", 0.0)) / 10.0, 3),
            "supply_squeeze_score": round(snapshot.get("onchain_outflow_zscore", 0.0) / 4.0, 3),
        })
        return base


# ═══════════════════════════════════════════════════════════════════════════════
# Strategy 8: Λ-Compounding DCA with Market Timing
# ═══════════════════════════════════════════════════════════════════════════════

class LambdaCompoundingDCA(BaseStrategy):
    """
    Dollar-cost average, dynamically adjusted by moat size + market conditions.
    The safest strategy — lowest Ψ requirement.

    Trigger: Time-based (24h cycle) + market condition filter
    Ψ requirement: Ψ ≥ 0.50
    """
    name = "lambda_dca"
    psi_requirement = 0.50
    max_size_pct = 0.04

    def opportunity_score(self, snapshot: dict) -> float:
        fg    = snapshot.get("fear_greed", 50)
        p24h  = snapshot.get("price_change_24h", 0.0)
        p7d   = snapshot.get("price_change_7d", 0.0)
        lam   = snapshot.get("lambda_val", 0.01)

        # DCA always has some base score (it's time-based)
        base_score = 0.40

        # Extreme fear → buy more (this is the time to accumulate)
        if fg < 20:
            return 0.95   # Extreme fear = strong DCA signal
        if fg > 80:
            return 0.10   # Extreme greed = pause DCA

        # Price below MA proxy: p24h negative and p7d negative = buy the dip
        dip_bonus = 0.20 if p24h < -3 else 0.10 if p24h < 0 else 0.0

        # Moat bonus: proven agent → larger DCA
        moat_bonus = _clamp(math.log(max(lam, 0.01) + 1) / 5.0) * 0.15

        # Session: prefer low-slippage hours
        session_score = 0.10 if _is_liquid_session() else 0.0

        raw = base_score + dip_bonus + moat_bonus + session_score
        return _clamp(raw)

    def direction(self, snapshot: dict) -> str:
        return "LONG"   # DCA is always long accumulation

    def _base_size_pct(self, snapshot: dict) -> float:
        fg  = snapshot.get("fear_greed", 50)
        lam = snapshot.get("lambda_val", 0.01)
        p24h = snapshot.get("price_change_24h", 0.0)

        base = 0.01   # 1% standard DCA
        if lam > 10:         base += 0.01   # Proven agent → bigger
        if p24h < -3:        base += 0.01   # Buying dip → bigger
        if fg < 20:          base += 0.005  # Extreme fear → biggest
        return min(base, 0.04)

    def on_chain_fields(self, psi, a_val, snapshot, size_usd):
        base = super().on_chain_fields(psi, a_val, snapshot, size_usd)
        base.update({
            "dca_amount_usd": size_usd,
            "fear_greed_at_purchase": snapshot.get("fear_greed", 50),
            "ma_distance_proxy": snapshot.get("price_change_24h", 0.0),
            "lambda_at_purchase": snapshot.get("lambda_val", 0.01),
            "dca_type": "fear_buy" if snapshot.get("fear_greed", 50) < 25 else "standard",
        })
        return base


# ═══════════════════════════════════════════════════════════════════════════════
# Strategy 9: Cross-Exchange Basis Arbitrage
# ═══════════════════════════════════════════════════════════════════════════════

class CrossExchangeBasis(BaseStrategy):
    """
    Exploit price differences between BSC DEXs and CEXs.
    Requires the highest Ψ (0.80) — arbitrage demands precision.

    Trigger: |BSC price - CEX price| > 0.3% + both venues liquid
    Ψ requirement: Ψ ≥ 0.80
    """
    name = "cross_exchange_basis"
    psi_requirement = 0.80
    max_size_pct = 0.12   # Arbitrage is lower-risk → slightly larger cap

    def opportunity_score(self, snapshot: dict) -> float:
        basis_spread = abs(snapshot.get("basis_spread", snapshot.get("funding_rate", 0.0) * 0.5))
        gas_cost     = snapshot.get("gas_cost_usd", 2.0)
        vol          = snapshot.get("daily_volume_usd", snapshot.get("volume_24h", 1e9))
        p1h          = snapshot.get("price_change_1h", 0.0)

        # Minimum viable spread after gas costs
        if basis_spread < 0.002:   # < 0.2%
            return 0.05
        if gas_cost > 10.0:
            return 0.05   # Gas eats the profit

        spread_score = _clamp((basis_spread - 0.002) / 0.010)   # 0.2% min, 1.2% = full
        gas_adjusted = 1.0 - _clamp(gas_cost / 20.0)           # Higher gas → lower score
        liq_score    = _vol_surge_score(vol)

        # Low volatility required: need stable price to execute both legs
        low_vol_req  = _clamp(1.0 - abs(p1h) / 3.0)

        # Gas/network congestion proxy: not during volatile hours
        congestion   = 1.0 if _is_liquid_session() else 0.5

        raw = (0.40 * spread_score + 0.25 * gas_adjusted +
               0.20 * liq_score + 0.15 * low_vol_req)
        return _clamp(raw * congestion)

    def direction(self, snapshot: dict) -> str:
        return "NEUTRAL"   # Arbitrage is delta-neutral (both legs)

    def _base_size_pct(self, snapshot: dict) -> float:
        basis = abs(snapshot.get("basis_spread", 0.003))
        if basis > 0.01:  return 0.12
        if basis > 0.005: return 0.08
        return 0.05

    def on_chain_fields(self, psi, a_val, snapshot, size_usd):
        base = super().on_chain_fields(psi, a_val, snapshot, size_usd)
        base.update({
            "basis_spread": snapshot.get("basis_spread", 0.003),
            "gas_cost_usd": snapshot.get("gas_cost_usd", 2.0),
            "leg1_venue": "BSC_DEX",
            "leg2_venue": "CEX",
            "holding_time_est_minutes": 2,
            "net_spread_after_gas": round(
                snapshot.get("basis_spread", 0.003) -
                snapshot.get("gas_cost_usd", 2.0) / max(size_usd, 1), 5
            ),
        })
        return base


# ═══════════════════════════════════════════════════════════════════════════════
# Strategy 10: Black Swan Insurance (Tail Risk Hedge)
# ═══════════════════════════════════════════════════════════════════════════════

class BlackSwanInsurance(BaseStrategy):
    """
    Buy crash protection when the world model detects elevated tail risk.
    This is insurance, not speculation. Premium is a cost, not a loss.

    Trigger: W(t) < 0.5 (anomaly detected) + Ψ > 0.70 (coherent enough to act)
    Ψ requirement: Ψ ≥ 0.70
    """
    name = "black_swan_insurance"
    psi_requirement = 0.70
    max_size_pct = 0.02   # Insurance hard cap: 2% of capital

    def opportunity_score(self, snapshot: dict) -> float:
        w_score  = snapshot.get("w_score", 0.60)     # World model score
        fg       = snapshot.get("fear_greed", 50)
        p24h     = snapshot.get("price_change_24h", 0.0)
        p7d      = snapshot.get("price_change_7d", 0.0)
        vix_like = snapshot.get("vix_proxy", (100 - fg) / 5.0)

        # Only deploy insurance when W(t) < 0.5 (world anomaly)
        if w_score >= 0.55:
            # Also trigger on standalone market stress signals
            market_stress = abs(p24h) > 5 or abs(p7d) > 15 or fg < 20
            if not market_stress:
                return 0.05

        # Tail risk score: lower W → higher urgency
        tail_score = _clamp((0.65 - w_score) / 0.65)

        # Greed + anomaly = dangerous combo (complacency before crash)
        greed_anomaly = 0.20 if (fg > 70 and w_score < 0.45) else 0.0

        # VIX-like signal
        vix_score = _clamp((vix_like - 15) / 25.0)   # Score above VIX=15

        # Exclude: don't buy insurance when already crashing (too late, too expensive)
        if p24h < -8 and p7d < -15:
            return 0.05   # Crash already in progress — insurance is too expensive now

        raw = 0.50 * tail_score + 0.30 * vix_score + 0.20 * (1.0 - fg / 100.0)
        return _clamp(raw + greed_anomaly)

    def direction(self, snapshot: dict) -> str:
        return "HEDGE"   # This is a hedge, not a directional bet

    def _base_size_pct(self, snapshot: dict) -> float:
        w_score = snapshot.get("w_score", 0.60)
        vix_like = snapshot.get("vix_proxy", (100 - snapshot.get("fear_greed", 50)) / 5.0)
        if w_score < 0.30 or vix_like > 30: return 0.015
        if w_score < 0.45 or vix_like > 20: return 0.010
        return 0.005    # Minimum insurance premium

    def on_chain_fields(self, psi, a_val, snapshot, size_usd):
        base = super().on_chain_fields(psi, a_val, snapshot, size_usd)
        fg = snapshot.get("fear_greed", 50)
        base.update({
            "w_score": snapshot.get("w_score", 0.60),
            "vix_proxy": snapshot.get("vix_proxy", (100 - fg) / 5.0),
            "hedge_type": "inverse_perp",
            "strike_distance_est_pct": 25.0,
            "expiry_days": 30,
            "premium_paid_usd": size_usd,
            "event_type": "tail_risk_hedge",
        })
        return base


# ═══════════════════════════════════════════════════════════════════════════════
# All strategies, ordered by descending Ψ requirement
# ═══════════════════════════════════════════════════════════════════════════════

ALL_STRATEGIES: list[BaseStrategy] = [
    CrossExchangeBasis(),       # Ψ ≥ 0.80 — highest precision required
    OnChainFlowImbalance(),     # Ψ ≥ 0.75
    PsiGatedMomentum(),         # Ψ ≥ 0.75
    LiquiditySweepReversal(),   # Ψ ≥ 0.72
    FundingRateArb(),           # Ψ ≥ 0.70
    BlackSwanInsurance(),       # Ψ ≥ 0.70
    VolatilityRegimeSwitch(),   # Ψ ≥ 0.70
    SentimentDivergence(),      # Ψ ≥ 0.68
    MeanReversionFear(),        # Ψ ≥ 0.65
    LambdaCompoundingDCA(),     # Ψ ≥ 0.50 — most permissive
]

STRATEGY_MAP: dict[str, BaseStrategy] = {s.name: s for s in ALL_STRATEGIES}
