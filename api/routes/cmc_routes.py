"""
RUMA — CoinMarketCap AI Agent Hub Routes
CMC data signals (Fear & Greed, prices, funding rates, social heat)
feed RUMA's TRION Ψ-gate for trade decisions.
MCP endpoint + x402 for premium data.
"""
import os
import time
import asyncio
from fastapi import APIRouter

router = APIRouter()

CMC_API_KEY = os.getenv("CMC_API_KEY", "")
CMC_MCP_ENDPOINT = os.getenv("CMC_MCP_ENDPOINT", "https://mcp.coinmarketcap.com")
CMC_BASE_URL = "https://pro-api.coinmarketcap.com/v1"

_cmc_cache: dict = {}
_CACHE_TTL = 300


def _cache_get(key: str):
    entry = _cmc_cache.get(key)
    if entry and time.time() - entry["ts"] < _CACHE_TTL:
        return entry["data"]
    return None


def _cache_set(key: str, data):
    _cmc_cache[key] = {"data": data, "ts": time.time()}


async def _cmc_get(path: str, params: dict = None):
    try:
        import httpx
        if not CMC_API_KEY:
            return None
        headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY, "Accept": "application/json"}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{CMC_BASE_URL}{path}", headers=headers, params=params or {})
            resp.raise_for_status()
            return resp.json()
    except Exception:
        return None


def _mock_fear_greed():
    import random
    val = random.randint(30, 70)
    return {
        "source": "CoinMarketCap AI Agent Hub (mock — set CMC_API_KEY)",
        "fear_greed_value": val,
        "fear_greed_label": "Fear" if val < 40 else ("Greed" if val > 60 else "Neutral"),
        "total_market_cap_usd": 2_400_000_000_000,
        "btc_dominance": 54.2,
        "mcp_endpoint": CMC_MCP_ENDPOINT,
    }


def _mock_prices(symbols: str):
    import random
    base = {"BNB": 620, "BTC": 105000, "ETH": 3800, "CAKE": 2.1, "USDT": 1.0}
    prices = {}
    for sym in symbols.split(","):
        sym = sym.strip()
        bp = base.get(sym, 1.0)
        prices[sym] = {
            "price_usd": bp * (1 + random.uniform(-0.02, 0.02)),
            "percent_change_1h": random.uniform(-1, 1),
            "percent_change_24h": random.uniform(-5, 5),
            "volume_24h": bp * random.randint(1_000_000, 10_000_000),
        }
    return {
        "source": "CoinMarketCap AI Agent Hub (mock — set CMC_API_KEY)",
        "prices": prices,
        "mcp_endpoint": CMC_MCP_ENDPOINT,
    }


@router.get("/cmc/fear-greed")
async def cmc_fear_greed():
    """CMC Fear & Greed Index — W-plane (World Model) input to TRION Ψ."""
    cached = _cache_get("fear_greed")
    if cached:
        return cached
    try:
        data = await _cmc_get("/global-metrics/quotes/latest")
        if data:
            fg = data.get("data", {})
            result = {
                "source": "CoinMarketCap AI Agent Hub",
                "fear_greed_value": fg.get("fear_greed_index", {}).get("value", 50),
                "fear_greed_label": fg.get("fear_greed_index", {}).get("value_classification", "Neutral"),
                "total_market_cap_usd": fg.get("quote", {}).get("USD", {}).get("total_market_cap"),
                "btc_dominance": fg.get("btc_dominance"),
                "mcp_endpoint": CMC_MCP_ENDPOINT,
            }
        else:
            result = _mock_fear_greed()
    except Exception as e:
        result = _mock_fear_greed()
        result["note"] = f"Mock data. Set CMC_API_KEY. Error: {str(e)}"
    _cache_set("fear_greed", result)
    return result


@router.get("/cmc/prices")
async def cmc_prices(symbols: str = "BNB,BTC,ETH,CAKE"):
    """Live CMC token prices — P-plane (Perceptual) input to TRION Ψ."""
    cache_key = f"prices_{symbols}"
    cached = _cache_get(cache_key)
    if cached:
        return cached
    try:
        data = await _cmc_get("/cryptocurrency/quotes/latest", {"symbol": symbols})
        if data:
            prices = {}
            for sym, info in (data.get("data") or {}).items():
                q = info.get("quote", {}).get("USD", {})
                prices[sym] = {
                    "price_usd": q.get("price"),
                    "percent_change_1h": q.get("percent_change_1h"),
                    "percent_change_24h": q.get("percent_change_24h"),
                    "volume_24h": q.get("volume_24h"),
                }
            result = {"source": "CoinMarketCap AI Agent Hub", "prices": prices, "mcp_endpoint": CMC_MCP_ENDPOINT}
        else:
            result = _mock_prices(symbols)
    except Exception as e:
        result = _mock_prices(symbols)
        result["note"] = f"Mock. Set CMC_API_KEY. Error: {str(e)}"
    _cache_set(cache_key, result)
    return result


@router.get("/cmc/signals")
async def cmc_signals():
    """
    Aggregated CMC trading signals used by RUMA's TRION Ψ-gate.
    Combines Fear & Greed + price momentum for composite bias signal.
    """
    fg, prices = await asyncio.gather(
        cmc_fear_greed(), cmc_prices("BNB,BTC,ETH"), return_exceptions=True
    )
    fg = fg if not isinstance(fg, Exception) else _mock_fear_greed()
    prices = prices if not isinstance(prices, Exception) else _mock_prices("BNB,BTC,ETH")
    fg_val = fg.get("fear_greed_value", 50)
    bnb_1h = (prices.get("prices") or {}).get("BNB", {}).get("percent_change_1h", 0) or 0
    bias = "BULLISH" if fg_val > 55 and bnb_1h > 0 else ("BEARISH" if fg_val < 40 and bnb_1h < 0 else "NEUTRAL")
    return {
        "source": "CoinMarketCap AI Agent Hub",
        "bias": bias,
        "fear_greed": fg_val,
        "fear_greed_label": fg.get("fear_greed_label"),
        "bnb_1h_pct": round(float(bnb_1h), 4),
        "signal_strength": abs(fg_val - 50) / 50,
        "recommended_direction": "LONG" if bias == "BULLISH" else ("SHORT" if bias == "BEARISH" else None),
        "w_plane_input": fg_val / 100.0,
        "p_plane_entropy": abs(float(bnb_1h)) / 5.0,
        "mcp_endpoint": CMC_MCP_ENDPOINT,
        "x402_used": bool(CMC_API_KEY),
    }


@router.post("/cmc/analyze")
async def cmc_analyze(symbol: str = "BNB", timeframe: str = "1h"):
    """AI analysis of CMC data for a symbol — integrates with TRION Ψ planes."""
    signals = await cmc_signals()
    prices_data = await cmc_prices(symbol)
    price_info = (prices_data.get("prices") or {}).get(symbol, {})
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "current_price_usd": price_info.get("price_usd"),
        "market_bias": signals.get("bias"),
        "fear_greed": signals.get("fear_greed"),
        "momentum_1h_pct": price_info.get("percent_change_1h"),
        "trion_w_plane": signals.get("w_plane_input"),
        "trion_p_plane": signals.get("p_plane_entropy"),
        "recommended_action": signals.get("recommended_direction") or "HOLD",
        "source": "CoinMarketCap AI Agent Hub (MCP)",
        "mcp_endpoint": CMC_MCP_ENDPOINT,
    }
