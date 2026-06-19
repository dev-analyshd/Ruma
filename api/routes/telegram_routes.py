"""
RUMA — Telegram Alert Routes
Configure and test Telegram notifications.
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/telegram/status")
async def telegram_status():
    import os
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    enabled = os.getenv("TELEGRAM_ALERTS_ENABLED", "true").lower() == "true"
    return {
        "configured": bool(token and chat_id),
        "enabled": enabled,
        "token_set": bool(token),
        "chat_id_set": bool(chat_id),
        "chat_id_preview": f"…{chat_id[-6:]}" if len(chat_id) > 6 else "not set",
        "alerts": [
            "trade_executed — Ψ-gate open + BSC swap confirmed",
            "gate_silent   — Ψ < Δ, trade silenced",
            "drawdown_halt — 30% drawdown cap hit, TWAK disabled",
            "daily_pause   — 6% daily loss limit, UTC reset",
            "lambda_milestone — Λ crosses 0.1, 0.25, 0.5, 1.0 …",
            "competition_registered — agent registered on-chain",
            "startup — RUMA comes online",
        ],
        "setup": "Set TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID in .env",
        "bot_father": "https://t.me/BotFather",
    }


@router.post("/telegram/test")
async def telegram_test():
    """Send a test alert to verify Telegram is configured."""
    from notifications.telegram import test_alert
    result = await test_alert()
    return result


@router.post("/telegram/alert/trade")
async def telegram_alert_trade_manual(
    symbol: str = "BNB/USDT",
    direction: str = "LONG",
    size_usd: float = 10.0,
    psi: float = 0.75,
    delta: float = 0.65,
):
    """Manually fire a trade alert (for testing)."""
    from notifications.telegram import alert_trade_executed
    sent = await alert_trade_executed(
        symbol=symbol, direction=direction, size_usd=size_usd,
        psi=psi, delta=delta, tx_hash=None, bscscan_url=None,
        simulated=True, cmc_bias="BULLISH",
    )
    return {"sent": sent}
