from fastapi import APIRouter, HTTPException
from api.schemas import TradeRequest, TradeResponse

router = APIRouter()

_decision_engine = None


def _get_engine():
    global _decision_engine
    if _decision_engine is None:
        from trading.decision_engine import TradingDecisionEngine
        _decision_engine = TradingDecisionEngine()
    return _decision_engine


@router.post("/trade/evaluate", response_model=TradeResponse)
async def evaluate_trade(req: TradeRequest):
    decision_engine = _get_engine()
    result = await decision_engine.evaluate_trade(
        symbol=req.symbol,
        direction=req.direction,
        strategy=req.strategy,
    )
    return TradeResponse(**{k: v for k, v in result.items() if k in TradeResponse.model_fields})


@router.post("/trade/close/{trade_id}")
async def close_trade(trade_id: str, exit_price: float, pnl: float, won: bool):
    await decision_engine.close_trade_on_outcome(trade_id, exit_price, pnl, won)
    return {"status": "closed", "trade_id": trade_id, "won": won, "pnl": pnl}
