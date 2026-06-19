from fastapi import APIRouter, HTTPException
from api.schemas import TradeRequest, TradeResponse
import time, uuid

router = APIRouter()


@router.post("/trade/evaluate", response_model=TradeResponse)
async def evaluate_trade(req: TradeRequest):
    """
    Evaluate a proposed trade using TRION coherence gate + Bayesian Kelly sizing.
    Returns EXECUTE / WAIT / SILENCE decision with Kelly fraction and expected value.
    """
    try:
        from core.coherence_engine import CoherenceEngine
        from core.action_gate import ActionGate
        from core.moat_accumulator import MoatAccumulator

        engine = CoherenceEngine()
        gate = ActionGate()
        moat = MoatAccumulator()
        lambda_val = moat.get_current_lambda()

        query = f"Trade {req.direction} {req.symbol} via {req.strategy}"
        context = {
            "domain": "trading",
            "symbol": req.symbol,
            "direction": req.direction,
            "strategy": req.strategy,
        }
        cycle_id = str(uuid.uuid4())

        result = await engine.compute_all_planes(query, context, cycle_id)
        psi = result.get("psi_total", 0.5)

        delta = gate.compute_threshold(
            lambda_val=lambda_val,
            fear_greed=50,
        )
        gate_open = psi >= delta

        # Bayesian Kelly sizing
        p_win = 0.5 + min(0.3, psi * 0.3)
        rr = 2.0
        kelly = max(0.0, min(0.02, (p_win * rr - (1 - p_win)) / rr * 0.25))
        e_edge = round(p_win * rr - (1 - p_win), 4)

        if not gate_open:
            action = "SILENCE"
            reason = f"Coherence below threshold (Ψ={psi:.3f} < Δ={delta:.3f})"
        elif e_edge <= 0:
            action = "WAIT"
            reason = f"Expected edge negative (EV={e_edge:.4f})"
        else:
            action = "EXECUTE"
            reason = f"Gate open (Ψ={psi:.3f} ≥ Δ={delta:.3f}), EV={e_edge:.4f}"

        return TradeResponse(
            action=action,
            trade_id=str(uuid.uuid4()) if action == "EXECUTE" else None,
            symbol=req.symbol,
            direction=req.direction,
            entry_price=None,
            size=None,
            stop_loss=None,
            kelly_fraction=round(kelly, 5) if action == "EXECUTE" else 0.0,
            e_edge=e_edge,
            psi=round(psi, 4),
            delta_trade=round(delta, 4),
            p_win=round(p_win, 4),
            bsc_tx=None,
            twak_signed=False,
            cmc_bias=None,
            reason=reason,
            t_value=round(time.time(), 2),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trade/close/{trade_id}")
async def close_trade(trade_id: str, exit_price: float, pnl: float, won: bool):
    """Record trade outcome for on-chain learning loop (moat accumulation)."""
    try:
        from core.moat_accumulator import MoatAccumulator
        moat = MoatAccumulator()
        rho = max(0.01, min(1.0, pnl / 10.0)) if won else 0.0
        if won and rho > 0:
            moat.accumulate(eta_i=0.02, rho_i=rho, calibration_score=1.0, cycle_id=trade_id)
        new_lambda = moat.get_current_lambda()
        return {
            "status": "closed",
            "trade_id": trade_id,
            "won": won,
            "pnl": pnl,
            "exit_price": exit_price,
            "lambda_after": round(new_lambda, 8),
            "moat_grown": won and rho > 0,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
