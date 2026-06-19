"""
Chain Manager — RUMA ADAPT-Ω
==============================
Runs multiple parallel reasoning chains over a query and context.
Each chain is a different analytical lens — the ensemble produces
the I (Inferential) and C (Consensus) plane inputs.

5 reasoning chains:
  1. Trend   — momentum and directional analysis
  2. Risk    — downside identification and circuit breakers
  3. Regime  — market regime classification
  4. Micro   — microstructure (spread, liquidity, volume)
  5. Sentiment — Fear & Greed and social signal analysis

All chains are async and run concurrently.
"""
from __future__ import annotations
import asyncio
import hashlib
import math
from dataclasses import dataclass
from typing import Any


@dataclass
class ChainResult:
    chain_name: str
    conclusion: str     # "bullish" | "bearish" | "neutral" | "uncertain"
    confidence: float   # 0.0 – 1.0
    depth: int          # reasoning steps
    reasoning: str      # human-readable summary
    signals: dict       # raw signal values


class ChainManager:
    """
    Manages 5 reasoning chains that provide the I and C plane inputs
    to the CoherenceEngine.
    """

    async def run_chains(self, query: str, context: dict) -> list[dict]:
        """
        Run all 5 chains concurrently.
        Returns list of dicts suitable for CoherenceEngine consumption.
        """
        results = await asyncio.gather(
            self._trend_chain(query, context),
            self._risk_chain(query, context),
            self._regime_chain(query, context),
            self._micro_chain(query, context),
            self._sentiment_chain(query, context),
            return_exceptions=True,
        )
        output = []
        for r in results:
            if isinstance(r, Exception):
                output.append({"chain": "error", "confidence": 0.3,
                                "depth": 1, "conclusion": "uncertain"})
            else:
                output.append({
                    "chain":      r.chain_name,
                    "conclusion": r.conclusion,
                    "confidence": r.confidence,
                    "depth":      r.depth,
                    "reasoning":  r.reasoning,
                    "signals":    r.signals,
                })
        return output

    # ── 1. Trend chain ─────────────────────────────────────────────────────────
    async def _trend_chain(self, query: str, context: dict) -> ChainResult:
        fg    = context.get("fear_greed", 50)
        p24h  = context.get("price_change_24h", 0.0)
        p7d   = context.get("price_change_7d", 0.0)

        steps = 0

        # Step 1: multi-TF momentum direction
        steps += 1
        direction_24h = "up" if p24h > 0 else "down"
        direction_7d  = "up" if p7d  > 0 else "down"

        # Step 2: alignment
        steps += 1
        aligned = direction_24h == direction_7d
        strength = (abs(p24h) + abs(p7d) * 0.5) / 1.5

        # Step 3: F&G confirmation
        steps += 1
        fg_confirms = (fg > 55 and p7d > 0) or (fg < 45 and p7d < 0)

        # Step 4: conclusion
        steps += 1
        if aligned and strength > 3 and fg_confirms:
            conclusion = "bullish" if p24h > 0 else "bearish"
            conf = min(0.90, 0.5 + strength / 15.0)
        elif aligned and strength > 1:
            conclusion = "bullish" if p24h > 0 else "bearish"
            conf = min(0.70, 0.4 + strength / 20.0)
        else:
            conclusion = "neutral"
            conf = 0.40

        return ChainResult(
            chain_name="trend", conclusion=conclusion,
            confidence=round(conf, 4), depth=steps,
            reasoning=f"24h={p24h:.1f}% {'aligned' if aligned else 'diverged'} with 7d={p7d:.1f}%, FG={fg}",
            signals={"p24h": p24h, "p7d": p7d, "fg": fg, "aligned": aligned},
        )

    # ── 2. Risk chain ─────────────────────────────────────────────────────────
    async def _risk_chain(self, query: str, context: dict) -> ChainResult:
        vol    = context.get("volatility", 0.02)
        p24h   = context.get("price_change_24h", 0.0)
        p5m    = context.get("price_change_5m", 0.0)

        steps = 0

        steps += 1
        crash_risk = p5m < -0.04   # 4% in 5m

        steps += 1
        high_vol = vol > 0.04

        steps += 1
        risk_score = (1.0 if crash_risk else 0.0) + (0.5 if high_vol else 0.0) + min(1.0, abs(p24h) / 8.0) * 0.5

        steps += 1
        if crash_risk:
            conclusion, conf = "bearish", 0.90
        elif risk_score > 1.0:
            conclusion, conf = "bearish", 0.65
        elif risk_score < 0.3:
            conclusion, conf = "neutral", 0.60
        else:
            conclusion, conf = "uncertain", 0.45

        return ChainResult(
            chain_name="risk", conclusion=conclusion,
            confidence=round(conf, 4), depth=steps,
            reasoning=f"Risk score={risk_score:.2f}, crash_risk={crash_risk}, high_vol={high_vol}",
            signals={"vol": vol, "crash_risk": crash_risk, "risk_score": risk_score},
        )

    # ── 3. Regime chain ───────────────────────────────────────────────────────
    async def _regime_chain(self, query: str, context: dict) -> ChainResult:
        fg   = context.get("fear_greed", 50)
        p7d  = context.get("price_change_7d", 0.0)
        p24h = context.get("price_change_24h", 0.0)

        steps = 3

        if abs(p24h) > 6 or abs(p7d) > 15:
            regime, conf = "volatile", 0.80
            conclusion = "uncertain"
        elif fg >= 65 and p7d > 5:
            regime, conf = "BULL", 0.82
            conclusion = "bullish"
        elif fg <= 35 and p7d < -5:
            regime, conf = "BEAR", 0.78
            conclusion = "bearish"
        elif abs(p7d) < 4:
            regime, conf = "SIDEWAYS", 0.72
            conclusion = "neutral"
        else:
            regime, conf = "TRANSITION", 0.50
            conclusion = "uncertain"

        return ChainResult(
            chain_name="regime", conclusion=conclusion,
            confidence=round(conf, 4), depth=steps,
            reasoning=f"Regime={regime}, FG={fg}, 7d={p7d:.1f}%",
            signals={"regime": regime, "fg": fg, "p7d": p7d},
        )

    # ── 4. Micro chain ────────────────────────────────────────────────────────
    async def _micro_chain(self, query: str, context: dict) -> ChainResult:
        vol_usd = context.get("daily_volume_usd", 50_000_000.0)
        spread  = context.get("bid_ask_spread", 0.001)
        p1h     = context.get("price_change_1h", 0.0)

        steps = 3

        liq_score = min(1.0, math.log10(max(vol_usd, 1)) / 9.0)  # $1B vol = 1.0
        spread_ok = spread < 0.005

        if liq_score > 0.7 and spread_ok:
            conclusion, conf = "bullish", 0.65
        elif liq_score < 0.3 or not spread_ok:
            conclusion, conf = "bearish", 0.60   # Microstructure warns
        else:
            conclusion, conf = "neutral", 0.55

        return ChainResult(
            chain_name="micro", conclusion=conclusion,
            confidence=round(conf, 4), depth=steps,
            reasoning=f"Liquidity={liq_score:.2f}, spread={spread*100:.3f}%",
            signals={"liq_score": liq_score, "spread": spread, "p1h": p1h},
        )

    # ── 5. Sentiment chain ────────────────────────────────────────────────────
    async def _sentiment_chain(self, query: str, context: dict) -> ChainResult:
        fg     = context.get("fear_greed", 50)
        social = context.get("social_score", 50.0)
        p24h   = context.get("price_change_24h", 0.0)

        steps = 3

        fg_norm     = (fg - 50) / 50.0           # -1 to +1
        social_norm = (social - 50) / 50.0 if social else 0.0
        sentiment   = 0.6 * fg_norm + 0.4 * social_norm
        divergence  = abs(sentiment - (p24h / 10.0))  # sentiment vs price

        if sentiment > 0.3 and divergence < 0.3:
            conclusion, conf = "bullish", 0.72
        elif sentiment < -0.3 and divergence < 0.3:
            conclusion, conf = "bearish", 0.70
        elif divergence > 0.5:
            conclusion, conf = "uncertain", 0.45   # Sentiment/price diverge
        else:
            conclusion, conf = "neutral", 0.55

        return ChainResult(
            chain_name="sentiment", conclusion=conclusion,
            confidence=round(conf, 4), depth=steps,
            reasoning=f"FG={fg}, sentiment={sentiment:.2f}, divergence={divergence:.2f}",
            signals={"fg": fg, "sentiment": sentiment, "divergence": divergence},
        )
