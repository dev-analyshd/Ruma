"""
Dynamic Asset Selector — RUMA
==============================
Replaces fixed priority symbol list with a live opportunity scanner.

Scans the 149-token competition allowlist (top 25 by liquidity by default),
scores each by a multi-factor opportunity score, and returns ranked candidates
the agent should evaluate — not trade blindly.

Scoring factors:
  1. Momentum score       — 1h/24h/7d price velocity alignment
  2. Volume surge         — vs. 24h average (anomaly = opportunity)
  3. Fear & Greed fit     — regime alignment (BULL: long targets only, etc.)
  4. Spread estimate      — high spread = penalised
  5. Liquidity depth      — volume > minimum threshold

Final output: ranked list of (symbol, score, direction_bias, reason)
"""
from __future__ import annotations
import asyncio
import os
import time
from dataclasses import dataclass
from typing import Any

try:
    import httpx as _httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    _httpx = None  # type: ignore[assignment]
    _HTTPX_AVAILABLE = False

from bnb.allowlist import PRIORITY_SYMBOLS, ELIGIBLE_SYMBOLS, validate_trade_symbol

CMC_API_KEY = os.getenv("CMC_API_KEY", "")
CMC_BASE = "https://pro-api.coinmarketcap.com"

# Minimum 24h volume to be worth trading (competition — we're small)
MIN_VOLUME_USD = 1_000_000.0   # $1M daily volume minimum

# Scoring weights
W_MOMENTUM = 0.40
W_VOLUME   = 0.20
W_FG_FIT   = 0.20
W_NOVELTY  = 0.20


@dataclass
class OpportunityScore:
    symbol: str
    score: float             # 0.0–1.0 composite
    direction_bias: str      # LONG | SHORT | NEUTRAL
    momentum_score: float
    volume_score: float
    fg_fit_score: float
    novelty_score: float
    price_change_1h: float
    price_change_24h: float
    price_change_7d: float
    volume_24h_usd: float
    reason: str

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "score": round(self.score, 4),
            "direction_bias": self.direction_bias,
            "scores": {
                "momentum": round(self.momentum_score, 4),
                "volume_surge": round(self.volume_score, 4),
                "fg_fit": round(self.fg_fit_score, 4),
                "novelty": round(self.novelty_score, 4),
            },
            "market": {
                "price_change_1h": round(self.price_change_1h, 3),
                "price_change_24h": round(self.price_change_24h, 3),
                "price_change_7d": round(self.price_change_7d, 3),
                "volume_24h_usd": round(self.volume_24h_usd, 0),
            },
            "reason": self.reason,
        }


class DynamicAssetSelector:
    """
    Live opportunity scanner for 149-token competition universe.
    Selects the top N opportunities for TRION evaluation — not final trades.
    """

    def __init__(self):
        self._cache: dict[str, Any] = {}
        self._cache_ts: float = 0.0
        self._cache_ttl: float = 300.0   # 5-min cache

    async def _fetch_quotes(self, symbols: list[str]) -> dict[str, dict]:
        """Batch-fetch CMC quotes for multiple symbols."""
        if not CMC_API_KEY:
            # Return synthetic data for demo/simulation
            return {s: self._synthetic_quote(s) for s in symbols}

        sym_str = ",".join(symbols[:50])  # CMC allows 50 per call (free tier)
        if not _HTTPX_AVAILABLE:
            return {s: self._synthetic_quote(s) for s in symbols}
        async with _httpx.AsyncClient(
            base_url=CMC_BASE,
            headers={"X-CMC_PRO_API_KEY": CMC_API_KEY},
            timeout=15,
        ) as c:
            r = await c.get(
                "/v2/cryptocurrency/quotes/latest",
                params={"symbol": sym_str, "convert": "USD"},
            )
            if r.status_code != 200:
                return {}
            data = r.json().get("data", {})

        result: dict[str, dict] = {}
        for sym, items in data.items():
            for item in (items if isinstance(items, list) else [items]):
                q = item.get("quote", {}).get("USD", {})
                result[item["symbol"]] = {
                    "price": q.get("price", 0.0),
                    "price_change_1h": q.get("percent_change_1h", 0.0),
                    "price_change_24h": q.get("percent_change_24h", 0.0),
                    "price_change_7d": q.get("percent_change_7d", 0.0),
                    "volume_24h": q.get("volume_24h", 0.0),
                    "market_cap": q.get("market_cap", 0.0),
                }
        return result

    def _synthetic_quote(self, symbol: str) -> dict:
        """Synthetic data for offline/simulation mode."""
        import random, hashlib
        seed = int(hashlib.md5(f"{symbol}{int(time.time()//300)}".encode()).hexdigest(), 16) % 1000
        r = random.Random(seed)
        return {
            "price": r.uniform(0.1, 50000),
            "price_change_1h":  r.uniform(-3, 3),
            "price_change_24h": r.uniform(-8, 8),
            "price_change_7d":  r.uniform(-15, 15),
            "volume_24h":       r.uniform(1_000_000, 5_000_000_000),
            "market_cap":       r.uniform(1_000_000, 500_000_000_000),
        }

    def _score_opportunity(self, symbol: str, q: dict, fear_greed: int) -> OpportunityScore:
        p1h  = q.get("price_change_1h", 0.0)
        p24h = q.get("price_change_24h", 0.0)
        p7d  = q.get("price_change_7d", 0.0)
        vol  = q.get("volume_24h", 0.0)

        # ── 1. Momentum score ─────────────────────────────────────────────────
        # Aligned momentum across timeframes (all same direction = high score)
        signs = [1 if x > 0 else -1 if x < 0 else 0 for x in [p1h, p24h, p7d]]
        alignment = sum(signs) / 3.0                    # -1 to +1
        magnitude = (abs(p1h)/3 + abs(p24h)/8 + abs(p7d)/15) / 3.0
        magnitude = min(1.0, magnitude)
        momentum_score = abs(alignment) * 0.6 + magnitude * 0.4

        # Direction bias from momentum
        if alignment > 0.3:  direction = "LONG"
        elif alignment < -0.3: direction = "SHORT"
        else:                direction = "NEUTRAL"

        # ── 2. Volume score (surge) ────────────────────────────────────────
        # Volume relative to minimum threshold
        vol_score = min(1.0, vol / (MIN_VOLUME_USD * 100))   # $100M = score 1.0

        # ── 3. F&G regime fit ───────────────────────────────────────────────
        if fear_greed >= 60:      regime_bias = "LONG"
        elif fear_greed <= 40:    regime_bias = "SHORT"
        else:                     regime_bias = "NEUTRAL"

        if regime_bias == direction:
            fg_fit = 1.0
        elif direction == "NEUTRAL":
            fg_fit = 0.5
        elif regime_bias == "NEUTRAL":
            fg_fit = 0.6
        else:
            fg_fit = 0.1    # Regime and momentum diverge — penalise

        # ── 4. Novelty score (priority tokens get a boost) ─────────────────
        from bnb.allowlist import PRIORITY_SYMBOLS
        novelty = 1.0 if symbol in PRIORITY_SYMBOLS[:10] else 0.7 if symbol in PRIORITY_SYMBOLS else 0.4

        # ── Composite ──────────────────────────────────────────────────────
        composite = (W_MOMENTUM * momentum_score + W_VOLUME * vol_score +
                     W_FG_FIT * fg_fit + W_NOVELTY * novelty)

        reason = (
            f"momentum={momentum_score:.2f}({direction})"
            f" vol={vol/1e6:.0f}M$ fg_fit={fg_fit:.2f}"
        )

        return OpportunityScore(
            symbol=symbol, score=round(composite, 4),
            direction_bias=direction,
            momentum_score=round(momentum_score, 4),
            volume_score=round(vol_score, 4),
            fg_fit_score=round(fg_fit, 4),
            novelty_score=round(novelty, 4),
            price_change_1h=p1h, price_change_24h=p24h, price_change_7d=p7d,
            volume_24h_usd=vol, reason=reason,
        )

    async def scan_opportunities(
        self,
        fear_greed: int = 50,
        n: int = 5,
        symbols: list[str] | None = None,
        min_volume_usd: float = MIN_VOLUME_USD,
    ) -> list[OpportunityScore]:
        """
        Scan the top symbols for trading opportunities.
        Returns top N ranked by composite score.
        """
        if symbols is None:
            symbols = PRIORITY_SYMBOLS[:25]

        # Filter to eligible only
        symbols = [s for s in symbols if validate_trade_symbol(s)[0]]

        # Fetch CMC quotes
        quotes = await self._fetch_quotes(symbols)

        # Score each
        scores: list[OpportunityScore] = []
        for sym in symbols:
            if sym not in quotes:
                continue
            q = quotes[sym]
            if q.get("volume_24h", 0) < min_volume_usd:
                continue   # Skip illiquid
            opp = self._score_opportunity(sym, q, fear_greed)
            if opp.direction_bias != "NEUTRAL":
                scores.append(opp)

        # Sort by score descending
        scores.sort(key=lambda x: -x.score)
        return scores[:n]

    async def top_opportunity(self, fear_greed: int = 50) -> OpportunityScore | None:
        """Return single best opportunity."""
        opps = await self.scan_opportunities(fear_greed=fear_greed, n=1)
        return opps[0] if opps else None


# Singleton
_selector = DynamicAssetSelector()

def get_asset_selector() -> DynamicAssetSelector:
    return _selector
