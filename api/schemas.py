from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class ActionRequest(BaseModel):
    query: str
    context: Dict[str, Any] = {}
    stakes_weight: float = Field(default=0.5, ge=0.1, le=1.0)
    domain: str = "trading"


class ActionResponse(BaseModel):
    cycle_id: str
    gate_open: bool
    action_output: Optional[str] = None
    silence_reason: Optional[str] = None
    psi_score: float
    delta_threshold: float
    lambda_value: float
    omega_value: float
    plane_breakdown: Dict[str, float]
    message: str


class TradeRequest(BaseModel):
    symbol: str = Field(default="BNB/USDT")
    direction: str = Field(default="LONG")
    strategy: str = Field(default="cmc_momentum")


class TradeResponse(BaseModel):
    action: str
    trade_id: Optional[str] = None
    symbol: Optional[str] = None
    direction: Optional[str] = None
    entry_price: Optional[float] = None
    size: Optional[float] = None
    stop_loss: Optional[float] = None
    kelly_fraction: Optional[float] = None
    e_edge: Optional[float] = None
    psi: Optional[float] = None
    delta_trade: Optional[float] = None
    p_win: Optional[float] = None
    bsc_tx: Optional[str] = None
    twak_signed: Optional[bool] = None
    cmc_bias: Optional[str] = None
    reason: Optional[str] = None
    t_value: Optional[float] = None
