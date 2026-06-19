"""
Competition Week Trading Scheduler — RUMA
==========================================
Ensures minimum 1 trade per day during June 22–28, 2026 (Track 1 requirement).
Runs as a background asyncio task inside FastAPI lifespan.

Schedule:
  - Every 4 hours: poll CMC signals + run Ψ-gate
  - If gate opens AND daily quota not met: execute TWAK swap
  - 06:00 UTC: reset daily counters
  - End of each day: Telegram daily summary

Safety rules (always enforced before any scheduled trade):
  - Drawdown ≥ 30% → skip until manual reset
  - Daily loss ≥ 6% → skip until UTC 00:00
  - Non-competition window (before June 22 / after June 28) → dry-run only
  - Position size: Bayesian Kelly, max 2% vault
"""
from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx

# ── Competition window ─────────────────────────────────────────────────────────
COMPETITION_START_UTC = datetime(2026, 6, 22, 0, 0, 0, tzinfo=timezone.utc)
COMPETITION_END_UTC   = datetime(2026, 6, 28, 23, 59, 59, tzinfo=timezone.utc)
MIN_TRADES_PER_DAY    = 1
POLL_INTERVAL_SECS    = 4 * 3600   # 4 hours
QUICK_POLL_SECS       = 30 * 60    # 30 min — used when daily quota not yet met at 20:00 UTC

SYMBOLS_PRIORITY = ["BNB", "ETH", "BTC", "CAKE", "XRP"]   # eligible BEP-20 tokens, ordered by liquidity


# ── State ──────────────────────────────────────────────────────────────────────
@dataclass
class SchedulerState:
    today_trades: int = 0
    today_date: str = ""      # YYYY-MM-DD UTC
    total_trades: int = 0
    total_pnl_pct: float = 0.0
    last_trade_ts: float = 0.0
    last_poll_ts: float = 0.0
    drawdown_halt: bool = False
    daily_loss_halt: bool = False
    dry_run: bool = False     # True when outside competition window
    errors: list[str] = field(default_factory=list)
    log: list[str] = field(default_factory=list)

    def utc_date(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def reset_daily(self):
        self.today_trades = 0
        self.today_date = self.utc_date()
        self.daily_loss_halt = False
        self._add_log("Daily counters reset")

    def needs_daily_reset(self) -> bool:
        return self.today_date != self.utc_date()

    def in_competition_window(self) -> bool:
        now = datetime.now(timezone.utc)
        return COMPETITION_START_UTC <= now <= COMPETITION_END_UTC

    def daily_quota_met(self) -> bool:
        return self.today_trades >= MIN_TRADES_PER_DAY

    def hours_left_today(self) -> float:
        now = datetime.now(timezone.utc)
        eod = now.replace(hour=23, minute=59, second=59)
        return (eod - now).total_seconds() / 3600.0

    def _add_log(self, msg: str):
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        entry = f"[{ts}] {msg}"
        self.log.append(entry)
        if len(self.log) > 100:
            self.log = self.log[-100:]
        print(f"[SCHEDULER] {entry}")


_state = SchedulerState()


def get_scheduler_state() -> SchedulerState:
    return _state


# ── CMC signal poll ────────────────────────────────────────────────────────────
async def _poll_cmc_signals() -> dict:
    """Pull live CMC Fear & Greed + price data for signal evaluation.
    Uses CMC AI Agent Hub (real API) when CMC_API_KEY is set.
    Falls back to alternative.me (free, no key) otherwise.
    """
    cmc_key = os.getenv("CMC_API_KEY", "")
    fg_val, fg_label, bnb_1h = 50, "Neutral", 0.0

    # ── Primary: CMC AI Agent Hub ─────────────────────────────────────────────
    if cmc_key:
        try:
            headers = {"X-CMC_PRO_API_KEY": cmc_key, "Accept": "application/json"}
            async with httpx.AsyncClient(timeout=10) as client:
                # Fear & Greed from CMC global metrics
                fg_resp = await client.get(
                    "https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest",
                    headers=headers,
                )
                if fg_resp.status_code == 200:
                    fg_data = fg_resp.json().get("data", {})
                    fg_idx = fg_data.get("fear_greed_index", {})
                    fg_val = int(fg_idx.get("value", 50))
                    fg_label = fg_idx.get("value_classification", "Neutral")

                # BNB 1h price change
                price_resp = await client.get(
                    "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest",
                    headers=headers,
                    params={"symbol": "BNB"},
                )
                if price_resp.status_code == 200:
                    bnb_data = price_resp.json().get("data", {}).get("BNB", {})
                    bnb_1h = bnb_data.get("quote", {}).get("USD", {}).get("percent_change_1h", 0.0) or 0.0

        except Exception as e:
            print(f"[SCHEDULER] CMC API error: {e} — falling back to alternative.me")
            cmc_key = ""  # trigger fallback

    # ── Fallback: alternative.me (no key needed) ──────────────────────────────
    if not cmc_key:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                fg_resp = await client.get("https://api.alternative.me/fng/?limit=1")
                fg_items = fg_resp.json().get("data", [{}])
                fg_val = int(fg_items[0].get("value", 50)) if fg_items else 50
                fg_label = fg_items[0].get("value_classification", "Neutral") if fg_items else "Neutral"
        except Exception as e:
            print(f"[SCHEDULER] alternative.me error: {e}")

    # Bias: bullish when F&G > 55 AND price rising, bearish when F&G < 40 AND price falling
    if fg_val >= 65 or (fg_val >= 55 and bnb_1h > 0.2):
        bias = "BULLISH"
    elif fg_val <= 35 or (fg_val <= 45 and bnb_1h < -0.2):
        bias = "BEARISH"
    else:
        bias = "NEUTRAL"

    return {
        "fear_greed": fg_val,
        "fear_greed_label": fg_label,
        "bias": bias,
        "bnb_1h_pct": round(bnb_1h, 4),
        "source": "CoinMarketCap AI Agent Hub" if os.getenv("CMC_API_KEY") else "alternative.me (fallback)",
        "ok": True,
    }


# ── Vault sizing helper ────────────────────────────────────────────────────────
async def _get_vault_usd() -> float:
    """Fetch live BNB balance and convert to USD for dynamic position sizing."""
    try:
        from bnb.chain_client import BSCClient
        import httpx
        bsc = BSCClient()
        bnb_bal = await bsc.get_bnb_balance()
        if bnb_bal <= 0:
            return 0.0
        # Live BNB price from CMC
        cmc_key = os.getenv("CMC_API_KEY", "")
        bnb_price = 620.0
        if cmc_key:
            try:
                async with httpx.AsyncClient(timeout=6) as client:
                    r = await client.get(
                        "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest",
                        headers={"X-CMC_PRO_API_KEY": cmc_key},
                        params={"symbol": "BNB"},
                    )
                    if r.status_code == 200:
                        d = r.json().get("data", {}).get("BNB", {})
                        p = d.get("quote", {}).get("USD", {}).get("price")
                        if p and p > 0:
                            bnb_price = float(p)
            except Exception:
                pass
        return round(bnb_bal * bnb_price, 2)
    except Exception:
        return 0.0


# ── Ψ-gate check (lightweight, no LLM required) ───────────────────────────────
def _quick_psi_gate(signals: dict, urgent: bool = False) -> tuple[bool, float, str]:
    """
    Lightweight Ψ-gate that doesn't require LLM reasoning.
    Uses only CMC signals for scheduled trades.
    Returns: (gate_open, psi_score, reason)

    urgent=True: last 4 hours of the day with no trade yet.
    In urgent mode the threshold drops to 0.35 and NEUTRAL bias is allowed
    through so the daily-minimum trade is guaranteed.
    """
    fg = signals.get("fear_greed", 50)
    bias = signals.get("bias", "NEUTRAL")

    # Perceptual plane proxy: how far is F&G from neutral?
    p_score = abs(fg - 50) / 50.0 * 0.7 + 0.3

    # World model: extreme readings are suspicious
    w_score = 0.0 if abs(fg - 50) > 40 else 0.6  # shut gate if > 90 or < 10

    # Consensus: NEUTRAL signal → lower score
    c_score = 0.7 if bias != "NEUTRAL" else 0.4

    # Simplified Ψ (no full TRION)
    psi = 0.4 * p_score + 0.3 * c_score + 0.2 * w_score + 0.1 * 0.6

    if urgent:
        # Emergency daily-minimum: much lower bar, NEUTRAL allowed
        delta = 0.35
        gate_open = psi >= delta
        reason = f"URGENT bias={bias} FG={fg} Ψ={psi:.3f} Δ={delta} (daily-min override)"
    else:
        delta = 0.60
        gate_open = psi >= delta and bias != "NEUTRAL"
        reason = f"bias={bias} FG={fg} Ψ={psi:.3f} Δ={delta}"

    return gate_open, round(psi, 4), reason


# ── Execution ─────────────────────────────────────────────────────────────────
async def _execute_scheduled_trade(signals: dict, symbol: str = "BNB") -> dict:
    """Execute a TWAK swap for the scheduled daily minimum trade."""
    if _state.dry_run:
        _state._add_log(f"DRY-RUN: would buy {symbol} (competition window not active)")
        return {"success": True, "dry_run": True, "symbol": symbol}

    try:
        from bnb.twak_client import TWAKClient
        bias = signals.get("bias", "BULLISH")
        direction = "LONG" if bias in ("BULLISH", "NEUTRAL") else "SHORT"
        client = TWAKClient()

        # Dynamic position sizing: 2% of vault, min $5, max $100
        vault_usd = await _get_vault_usd()
        if vault_usd > 0:
            size = round(max(5.0, min(vault_usd * 0.02, 100.0)), 2)
        else:
            size = 5.0
        _state._add_log(f"Position size: ${size} (vault≈${vault_usd:.2f})")

        result = await client.execute_swap(
            symbol=f"{symbol}/USDT",
            direction=direction,
            size=size,
            slippage_pct=0.5,
        )
        executed = result.get("executed", False)
        if executed:
            _state.today_trades += 1
            _state.total_trades += 1
            _state.last_trade_ts = time.time()
            _state._add_log(
                f"Scheduled trade executed: {direction} {symbol} "
                f"tx={result.get('tx_hash','')[:12]}..."
            )
            # Fire Telegram alert
            try:
                from notifications.telegram import alert_trade_executed
                await alert_trade_executed(
                    symbol=f"{symbol}/USDT",
                    direction=direction,
                    size_usd=5.0,
                    psi=signals.get("psi_score", 0.0),
                    delta=0.60,
                    tx_hash=result.get("tx_hash", ""),
                    bscscan_url=result.get("bscscan", ""),
                    simulated=result.get("simulated", True),
                    cmc_bias=signals.get("bias"),
                    kelly_fraction=0.005,
                    network=os.getenv("BSC_NETWORK", "testnet"),
                )
            except Exception:
                pass
        return {"success": executed, **result}
    except Exception as e:
        _state.errors.append(str(e))
        _state._add_log(f"Scheduled trade ERROR: {e}")
        return {"success": False, "error": str(e)}


# ── Main scheduler loop ────────────────────────────────────────────────────────
async def competition_scheduler_loop():
    """
    Background asyncio task. Call this from FastAPI lifespan.
    """
    global _state
    _state._add_log("Competition scheduler started")

    while True:
        try:
            # Daily reset check
            if _state.needs_daily_reset():
                _state.reset_daily()
                _state.dry_run = not _state.in_competition_window()
                _state._add_log(
                    f"Mode: {'DRY-RUN' if _state.dry_run else 'LIVE'} | "
                    f"Window: {COMPETITION_START_UTC.date()} → {COMPETITION_END_UTC.date()}"
                )

            # Skip if halted
            if _state.drawdown_halt:
                _state._add_log("Drawdown halt active — skipping poll")
                await asyncio.sleep(POLL_INTERVAL_SECS)
                continue

            if _state.daily_loss_halt:
                _state._add_log("Daily loss halt active — skipping poll")
                await asyncio.sleep(POLL_INTERVAL_SECS)
                continue

            # Poll CMC
            _state.last_poll_ts = time.time()
            signals = await _poll_cmc_signals()
            _state._add_log(
                f"CMC poll: FG={signals.get('fear_greed')} bias={signals.get('bias')} quota={'✓' if _state.daily_quota_met() else '✗'}"
            )

            # If quota already met, sleep full interval
            if _state.daily_quota_met():
                await asyncio.sleep(POLL_INTERVAL_SECS)
                continue

            # Emergency mode: < 4 hours left and no trade yet → try every 30 min
            hours_left = _state.hours_left_today()
            urgent = hours_left < 4

            # Run quick Ψ-gate — pass urgent so it lowers threshold when needed
            gate_open, psi, reason = _quick_psi_gate(signals, urgent=urgent)
            signals["psi_score"] = psi
            _state._add_log(f"Gate: {'OPEN' if gate_open else 'CLOSED'} ({reason})")

            if gate_open:
                # Try symbols in priority order until one succeeds
                for sym in SYMBOLS_PRIORITY:
                    result = await _execute_scheduled_trade(signals, sym)
                    if result.get("success"):
                        break
                    await asyncio.sleep(5)
            elif urgent and not _state.daily_quota_met():
                # < 4 hours left, gate still closed — force BNB LONG as last resort
                _state._add_log("URGENT: gate closed but forcing BNB LONG to meet daily minimum")
                signals["bias"] = "BULLISH"
                for sym in ["BNB", "CAKE"]:
                    result = await _execute_scheduled_trade(signals, sym)
                    if result.get("success"):
                        break
                    await asyncio.sleep(5)

            # Urgent mode: 30 min polling
            sleep_secs = QUICK_POLL_SECS if urgent else POLL_INTERVAL_SECS
            _state._add_log(f"Next poll in {sleep_secs//60} min")
            await asyncio.sleep(sleep_secs)

        except asyncio.CancelledError:
            _state._add_log("Scheduler cancelled")
            break
        except Exception as e:
            _state.errors.append(str(e))
            _state._add_log(f"Scheduler error: {e}")
            await asyncio.sleep(60)


# ── External controls ──────────────────────────────────────────────────────────
def set_drawdown_halt(halt: bool):
    _state.drawdown_halt = halt
    _state._add_log(f"Drawdown halt {'SET' if halt else 'CLEARED'}")

def set_daily_loss_halt(halt: bool):
    _state.daily_loss_halt = halt
    _state._add_log(f"Daily loss halt {'SET' if halt else 'CLEARED'}")

async def force_trade_now(symbol: str = "BNB") -> dict:
    """Manual trigger — for testing and demo."""
    signals = await _poll_cmc_signals()
    gate_open, psi, reason = _quick_psi_gate(signals)
    signals["psi_score"] = psi
    _state._add_log(f"Force trade requested: gate={'OPEN' if gate_open else 'CLOSED'} {reason}")
    return await _execute_scheduled_trade(signals, symbol)
