"""
RUMA — Telegram Alert Module
Fires when Ψ-gate opens and a trade executes on BSC via TWAK.
Also alerts on: drawdown limits hit, daily loss pause, Λ milestones.

Required env vars:
  TELEGRAM_BOT_TOKEN  — from @BotFather
  TELEGRAM_CHAT_ID    — channel ID (negative) or user ID

Optional:
  TELEGRAM_ALERTS_ENABLED=true  (default true if token is set)
  TELEGRAM_THREAD_ID             — for forum topic threads
"""
import os
import time
from typing import Optional, Dict, Any

_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")
_THREAD_ID = os.getenv("TELEGRAM_THREAD_ID", "")
_ENABLED   = os.getenv("TELEGRAM_ALERTS_ENABLED", "true").lower() == "true"

# In-memory alert dedup: suppress identical alerts within 60 s
_recent: Dict[str, float] = {}
_DEDUP_TTL = 60


def _is_configured() -> bool:
    return bool(_BOT_TOKEN and _CHAT_ID and _ENABLED)


def _dedup_key(kind: str, symbol: str = "") -> str:
    return f"{kind}:{symbol}"


def _should_send(key: str) -> bool:
    now = time.time()
    last = _recent.get(key, 0)
    if now - last < _DEDUP_TTL:
        return False
    _recent[key] = now
    return True


async def _send(text: str, parse_mode: str = "HTML") -> bool:
    """Send a message to the configured Telegram chat. Returns True on success."""
    if not _is_configured():
        return False
    try:
        import httpx
        url = f"https://api.telegram.org/bot{_BOT_TOKEN}/sendMessage"
        payload: Dict[str, Any] = {
            "chat_id": _CHAT_ID,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }
        if _THREAD_ID:
            payload["message_thread_id"] = int(_THREAD_ID)
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.post(url, json=payload)
            return r.status_code == 200
    except Exception as e:
        print(f"[TELEGRAM] Send error: {e}")
        return False


# ── Public alert functions ────────────────────────────────────────────────────

async def alert_trade_executed(
    symbol: str,
    direction: str,
    size_usd: float,
    psi: float,
    delta: float,
    tx_hash: Optional[str],
    bscscan_url: Optional[str],
    simulated: bool = False,
    cmc_bias: Optional[str] = None,
    kelly_fraction: Optional[float] = None,
    network: str = "testnet",
) -> bool:
    """
    Fire when Ψ-gate opens and a BSC trade executes via TWAK.
    This is the primary competition alert.
    """
    key = _dedup_key("trade", symbol)
    if not _should_send(key):
        return False

    net_badge = "🟡 TESTNET" if network != "mainnet" else "🟢 MAINNET"
    sim_badge = " <i>(simulation)</i>" if simulated else ""
    dir_emoji = "📈" if direction == "LONG" else "📉"
    bias_str  = f" | CMC: <b>{cmc_bias}</b>" if cmc_bias else ""
    kelly_str = f"\nKelly f*: <code>{kelly_fraction:.4f}</code>" if kelly_fraction else ""

    tx_line = ""
    if tx_hash and not simulated:
        scan = bscscan_url or f"https://{'testnet.' if network != 'mainnet' else ''}bscscan.com/tx/{tx_hash}"
        tx_line = f"\n🔗 <a href='{scan}'>{tx_hash[:10]}…</a>"
    elif tx_hash:
        tx_line = f"\nTx: <code>{tx_hash[:18]}…</code>"

    text = (
        f"{dir_emoji} <b>RUMA TRADE EXECUTED</b>{sim_badge} {net_badge}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Pair:  <b>{symbol}</b>  {direction}{bias_str}\n"
        f"Size:  <code>${size_usd:.2f}</code>\n"
        f"Ψ:     <code>{psi:.4f}</code>  Δ: <code>{delta:.4f}</code>{kelly_str}\n"
        f"Gate:  ✅ OPEN (Ψ ≥ 1.25·Δ){tx_line}\n"
        f"DEX:   PancakeSwap V2 via TWAK"
    )
    return await _send(text)


async def alert_gate_silent(
    query: str,
    psi: float,
    delta: float,
    plane_breakdown: Optional[Dict[str, float]] = None,
) -> bool:
    """Alert when Ψ-gate silences a trade. Sent at most once per minute per query type."""
    key = _dedup_key("silence", query[:20])
    if not _should_send(key):
        return False

    planes = ""
    if plane_breakdown:
        planes = (
            f"\nP={plane_breakdown.get('p', 0):.3f}  "
            f"I={plane_breakdown.get('i', 0):.3f}  "
            f"C={plane_breakdown.get('c', 0):.3f}  "
            f"S={plane_breakdown.get('s', 0):.3f}  "
            f"W={plane_breakdown.get('w', 0):.3f}"
        )

    text = (
        f"🤫 <b>RUMA SILENT</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Query: <code>{query[:60]}</code>\n"
        f"Ψ: <code>{psi:.4f}</code>  Δ: <code>{delta:.4f}</code>  (Ψ &lt; Δ){planes}\n"
        f"Gate: ❌ CLOSED → silence enforced"
    )
    return await _send(text)


async def alert_drawdown_halt(
    current_drawdown_pct: float,
    max_drawdown_pct: float,
    vault_usd: float,
) -> bool:
    """Alert when drawdown limit is hit and TWAK signing is disabled."""
    key = _dedup_key("drawdown_halt")
    if not _should_send(key):
        return False

    text = (
        f"🚨 <b>RUMA DRAWDOWN HALT</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Drawdown: <code>{current_drawdown_pct:.1f}%</code> ≥ limit <code>{max_drawdown_pct:.0f}%</code>\n"
        f"Vault: <code>${vault_usd:.2f}</code>\n"
        f"TWAK signing: <b>DISABLED</b>\n"
        f"Status: Agent paused until manual reset"
    )
    return await _send(text)


async def alert_daily_loss_pause(
    daily_loss_pct: float,
    limit_pct: float,
) -> bool:
    """Alert when daily loss limit is hit — trading pauses until UTC reset."""
    key = _dedup_key("daily_pause")
    if not _should_send(key):
        return False

    text = (
        f"⏸ <b>RUMA DAILY PAUSE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Daily loss: <code>{daily_loss_pct:.1f}%</code> ≥ limit <code>{limit_pct:.0f}%</code>\n"
        f"Trading paused until next UTC 00:00\n"
        f"Λ continues to accumulate during pause"
    )
    return await _send(text)


async def alert_lambda_milestone(
    lambda_val: float,
    n_cycles: int,
    iq: float,
) -> bool:
    """Alert when Λ crosses a round milestone (0.1, 0.5, 1.0, 2.0, 5.0 …)."""
    milestones = [0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 25.0, 50.0, 100.0]
    hit = any(
        (lambda_val >= m and (lambda_val - 0.01) < m)
        for m in milestones
    )
    if not hit:
        return False

    key = _dedup_key("lambda", str(round(lambda_val, 2)))
    if not _should_send(key):
        return False

    text = (
        f"🏆 <b>RUMA Λ MILESTONE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Λ = <code>{lambda_val:.6f}</code>  🎯\n"
        f"Cycles: <code>{n_cycles:,}</code>\n"
        f"IQ: <code>{iq:.6f}</code>\n"
        f"<i>The moat never shrinks.</i>"
    )
    return await _send(text)


async def alert_competition_registered(
    agent_address: str,
    tx_hash: Optional[str],
    network: str = "mainnet",
) -> bool:
    """Alert when agent is registered in BNB Hack competition contract."""
    key = _dedup_key("competition_registered")
    if not _should_send(key):
        return False

    tx_line = f"\nTx: <code>{tx_hash}</code>" if tx_hash else ""
    text = (
        f"🏁 <b>RUMA COMPETITION REGISTERED</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"BNB Hack: AI Trading Agent Edition\n"
        f"Track 1 — Autonomous Trading Agents\n"
        f"Agent: <code>{agent_address}</code>\n"
        f"Contract: <code>0x212c61b9b72c95d95bf29cf032f5e5635629aed5</code>\n"
        f"Network: <b>{network}</b>{tx_line}\n"
        f"Trading window: <b>June 22–28, 2026</b>\n"
        f"<i>Truth or silence. The silence is information.</i>"
    )
    return await _send(text)


async def alert_startup(lambda_val: float, n_cycles: int, iq: float) -> bool:
    """Alert when RUMA comes online."""
    key = _dedup_key("startup")
    if not _should_send(key):
        return False

    text = (
        f"🟢 <b>RUMA ONLINE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"BNB Hack: AI Trading Agent Edition\n"
        f"Chain: BNB Smart Chain (BSC)\n"
        f"DEX: PancakeSwap V2 via TWAK\n"
        f"Λ: <code>{lambda_val:.6f}</code>  Cycles: <code>{n_cycles:,}</code>  IQ: <code>{iq:.4f}</code>\n"
        f"CMC AI Agent Hub: connected\n"
        f"Ψ-gate: ACTIVE (silence rate ~87%)"
    )
    return await _send(text)


async def test_alert() -> Dict[str, Any]:
    """Send a test message and return result. Called from /api/v1/telegram/test."""
    if not _is_configured():
        return {
            "sent": False,
            "configured": False,
            "note": "Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env",
        }
    ok = await _send(
        "🔔 <b>RUMA Alert Test</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Telegram alerts are working!\n"
        "RUMA will notify you when:\n"
        "• Ψ-gate opens → trade executes\n"
        "• Drawdown limit hit → trading paused\n"
        "• Λ milestone crossed\n"
        "• Competition registration confirmed"
    )
    return {"sent": ok, "configured": True, "chat_id": _CHAT_ID}
