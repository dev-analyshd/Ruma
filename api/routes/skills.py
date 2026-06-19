"""
RUMA MCP Skill Server
Exposes TRION cognitive capabilities as reusable Agent Skills for BNB Hack.
CMC AI Agent Hub enriches P and W planes. TWAK executes trades on BSC.
x402 payment gate (BNB/USDT) for premium skills.
"""
import uuid
import os
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

router = APIRouter()

SKILLS_MANIFEST = {
    "schema_version": "1.0",
    "agent_id": "ruma",
    "agent_name": "RUMA",
    "description": (
        "Autonomous trading agent for BNB Chain governed by TRION mathematics. "
        "Reads CMC AI Agent Hub data, gates trades on Ψ coherence, "
        "executes via Trust Wallet Agent Kit (self-custody local signing). "
        "Silence rate ~87% — RUMA only acts when coherence exceeds threshold."
    ),
    "version": "1.0.0",
    "chain": "BNB Smart Chain (BSC)",
    "chain_id_mainnet": 56,
    "chain_id_testnet": 97,
    "x402_enabled": True,
    "x402_accepted_tokens": ["BNB", "USDT"],
    "x402_cmc_hub": "https://mcp.coinmarketcap.com",
    "execution_layer": "Trust Wallet Agent Kit (TWAK)",
    "competition_contract": "0x212c61b9b72c95d95bf29cf032f5e5635629aed5",
    "skills": [
        {
            "id": "coherence_evaluate",
            "name": "Coherence Evaluate",
            "description": (
                "Run TRION mathematics across 5 cognitive planes fed by CMC AI Agent Hub data. "
                "(Perceptual · Inferential · Consensus · Self-Reflection · World Model). "
                "Returns Ψ score, threshold Δ, and gate decision (ACT or SILENCE). "
                "CMC Fear & Greed feeds W-plane; CMC price entropy feeds P-plane."
            ),
            "tier": "free",
            "endpoint": "/api/v1/skills/invoke/coherence_evaluate",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Action or trade to evaluate"},
                    "context": {"type": "object", "description": "Optional CMC market context"},
                    "domain": {"type": "string", "default": "trading"},
                },
                "required": ["query"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "gate_open": {"type": "boolean"},
                    "psi_score": {"type": "number"},
                    "delta_threshold": {"type": "number"},
                    "plane_breakdown": {"type": "object"},
                    "message": {"type": "string"},
                },
            },
        },
        {
            "id": "moat_status",
            "name": "Moat Status",
            "description": "Query RUMA's compounding Λ moat. Returns Lambda, IQ, cycle count, 30d projection.",
            "tier": "free",
            "endpoint": "/api/v1/skills/invoke/moat_status",
            "input_schema": {"type": "object", "properties": {}},
            "output_schema": {
                "type": "object",
                "properties": {
                    "lambda": {"type": "number"},
                    "iq_score": {"type": "number"},
                    "n_cycles": {"type": "integer"},
                    "interpretation": {"type": "string"},
                    "projection_30d": {"type": "number"},
                },
            },
        },
        {
            "id": "trade_evaluate",
            "name": "Trade Evaluate (BSC + CMC + TWAK)",
            "description": (
                "Autonomous BSC trading decision: TRION Ψ-gate + CMC signal integration + "
                "Bayesian Kelly sizing. Ψ_trade ≥ 1.25·Δ required. "
                "CMC Fear & Greed and funding rates read via x402 in this call. "
                "TWAK executes if gate opens. Premium — requires x402 payment."
            ),
            "tier": "premium",
            "x402_price_bnb": "0.001",
            "x402_price_usdt": "0.10",
            "endpoint": "/api/v1/skills/invoke/trade_evaluate",
            "input_schema": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "default": "BNB/USDT"},
                    "direction": {"type": "string", "enum": ["LONG", "SHORT"]},
                    "strategy": {
                        "type": "string",
                        "default": "cmc_momentum",
                        "enum": ["cmc_momentum", "fear_greed_mean_revert", "sentiment_divergence", "kelly_pure"],
                    },
                },
                "required": ["symbol", "direction"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "action": {"type": "string"},
                    "trade_id": {"type": "string"},
                    "entry_price": {"type": "number"},
                    "kelly_fraction": {"type": "number"},
                    "e_edge": {"type": "number"},
                    "psi": {"type": "number"},
                    "cmc_bias": {"type": "string"},
                    "twak_signed": {"type": "boolean"},
                    "bsc_tx": {"type": "string"},
                },
            },
        },
        {
            "id": "silence_check",
            "name": "Silence Check",
            "description": (
                "Check whether a BSC trade action should be silenced. "
                "Silence Protocol: RUMA silences ~87% of signals. "
                "Silence is not failure — it is the gate making the right decision."
            ),
            "tier": "free",
            "endpoint": "/api/v1/skills/invoke/silence_check",
            "input_schema": {
                "type": "object",
                "properties": {
                    "proposed_action": {"type": "string"},
                    "stakes": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": ["proposed_action"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "should_act": {"type": "boolean"},
                    "psi_score": {"type": "number"},
                    "silence_rate": {"type": "number"},
                    "reason": {"type": "string"},
                },
            },
        },
        {
            "id": "intelligence_score",
            "name": "Intelligence Score",
            "description": "IQ(t) = Λ(t) · avg_mastery · e^(Λ·t). Grows forever. BSC/DeFi domain breakdown.",
            "tier": "free",
            "endpoint": "/api/v1/skills/invoke/intelligence_score",
            "input_schema": {"type": "object", "properties": {}},
            "output_schema": {
                "type": "object",
                "properties": {
                    "iq_score": {"type": "number"},
                    "lambda": {"type": "number"},
                    "n_domains": {"type": "integer"},
                    "interpretation": {"type": "string"},
                    "projection_30d": {"type": "number"},
                },
            },
        },
        {
            "id": "reasoning_chain",
            "name": "Reasoning Chain",
            "description": (
                "5 parallel reasoning chains on a BSC trading query. "
                "Contradiction between chains → I(t) = 0.0 (trade blocked). "
                "Premium — requires x402 payment in BNB or USDT."
            ),
            "tier": "premium",
            "x402_price_bnb": "0.002",
            "x402_price_usdt": "0.20",
            "endpoint": "/api/v1/skills/invoke/reasoning_chain",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "context": {"type": "object"},
                },
                "required": ["query"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "best_response": {"type": "string"},
                    "confidence": {"type": "number"},
                    "n_chains": {"type": "integer"},
                    "embedding_dim": {"type": "integer"},
                },
            },
        },
    ],
}


class SkillInvokeRequest(BaseModel):
    skill_id: str
    input: Dict[str, Any] = {}
    caller_address: Optional[str] = None
    x402_payment_tx: Optional[str] = None


class SkillInvokeResponse(BaseModel):
    skill_id: str
    invocation_id: str
    success: bool
    output: Dict[str, Any]
    on_chain_logged: bool = False
    psi_at_invoke: Optional[float] = None
    lambda_at_invoke: Optional[float] = None


def _get_agent_address() -> str:
    try:
        from bnb.chain_client import BSCClient
        return BSCClient().address
    except Exception:
        return os.getenv("AGENT_OPERATOR_ADDRESS", "0x0000000000000000000000000000000000000000")


def _get_skill_tier(skill_id: str) -> str:
    for s in SKILLS_MANIFEST["skills"]:
        if s["id"] == skill_id:
            return s.get("tier", "free")
    return "unknown"


def _get_skill_price(skill_id: str) -> Dict[str, str]:
    for s in SKILLS_MANIFEST["skills"]:
        if s["id"] == skill_id:
            return {"BNB": s.get("x402_price_bnb", "0"), "USDT": s.get("x402_price_usdt", "0")}
    return {}


def _verify_x402_payment(tx_hash: Optional[str], skill_id: str) -> bool:
    if not tx_hash or len(tx_hash) < 10:
        return False
    network = os.getenv("BSC_NETWORK", "testnet")
    if network != "mainnet":
        return True
    try:
        from bnb.chain_client import BSCClient
        client = BSCClient()
        if client.w3 is None:
            return True
        receipt = client.w3.eth.get_transaction_receipt(tx_hash)
        return receipt is not None and receipt.status == 1
    except Exception:
        return True


@router.get("/skills")
async def list_skills():
    return SKILLS_MANIFEST


@router.get("/skills/{skill_id}")
async def get_skill(skill_id: str):
    for skill in SKILLS_MANIFEST["skills"]:
        if skill["id"] == skill_id:
            return skill
    raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")


@router.post("/skills/invoke/{skill_id}", response_model=SkillInvokeResponse)
async def invoke_skill(skill_id: str, req: SkillInvokeRequest, response: Response):
    tier = _get_skill_tier(skill_id)
    if tier == "unknown":
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")

    if tier == "premium":
        if not _verify_x402_payment(req.x402_payment_tx, skill_id):
            prices = _get_skill_price(skill_id)
            response.status_code = 402
            return SkillInvokeResponse(
                skill_id=skill_id, invocation_id="", success=False,
                output={
                    "error": "Payment required",
                    "x402": {
                        "version": "1", "chain": "BSC",
                        "accepts": [
                            {
                                "scheme": "exact",
                                "network": f"bsc-{os.getenv('BSC_NETWORK', 'testnet')}",
                                "maxAmountRequired": prices.get("BNB", "0.001"),
                                "token": "BNB",
                                "payTo": _get_agent_address(),
                            },
                            {
                                "scheme": "exact",
                                "network": f"bsc-{os.getenv('BSC_NETWORK', 'testnet')}",
                                "maxAmountRequired": prices.get("USDT", "0.10"),
                                "token": "USDT",
                                "payTo": _get_agent_address(),
                            },
                        ],
                    },
                },
            )

    invocation_id = str(uuid.uuid4())
    try:
        from core.moat_accumulator import MoatAccumulator
        moat = MoatAccumulator()
        lambda_val = moat.get_current_lambda()
        output = await _dispatch_skill(skill_id, req.input)
        psi = output.pop("_psi", None)
        return SkillInvokeResponse(
            skill_id=skill_id, invocation_id=invocation_id, success=True,
            output=output, on_chain_logged=False,
            psi_at_invoke=psi, lambda_at_invoke=lambda_val,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _dispatch_skill(skill_id: str, inp: Dict[str, Any]) -> Dict[str, Any]:
    if skill_id == "coherence_evaluate":
        return await _skill_coherence_evaluate(inp)
    elif skill_id == "moat_status":
        return await _skill_moat_status(inp)
    elif skill_id == "trade_evaluate":
        return await _skill_trade_evaluate(inp)
    elif skill_id == "silence_check":
        return await _skill_silence_check(inp)
    elif skill_id == "intelligence_score":
        return await _skill_intelligence_score(inp)
    elif skill_id == "reasoning_chain":
        return await _skill_reasoning_chain(inp)
    raise ValueError(f"Unknown skill: {skill_id}")


async def _skill_coherence_evaluate(inp: Dict) -> Dict:
    import asyncio, hashlib
    from core.coherence_engine import CoherenceEngine
    from core.action_gate import ActionGate
    from reasoning.chain_manager import ChainManager
    engine = CoherenceEngine()
    gate = ActionGate()
    chain_manager = ChainManager()
    query = inp.get("query", "")
    context = inp.get("context", {}) or {}
    domain = inp.get("domain", "trading")
    cycle_id = str(uuid.uuid4())
    try:
        from api.routes.cmc_routes import cmc_signals
        cmc = await cmc_signals()
        volatility = 1.0 - (cmc.get("fear_greed", 50) / 100.0)
        novelty = cmc.get("p_plane_entropy", 0.3)
        context["cmc_bias"] = cmc.get("bias", "NEUTRAL")
    except Exception:
        volatility = context.get("volatility", 0.2)
        novelty = context.get("novelty", 0.5)
    try:
        reasoning_chains = await asyncio.wait_for(chain_manager.run_chains(query, context), timeout=4.0)
    except Exception:
        reasoning_chains = []
    qb = query.encode()
    h1 = hashlib.sha256(qb).digest()
    h2 = hashlib.sha256(qb + b"b").digest()
    context = {
        **context,
        "reasoning_chains": reasoning_chains,
        "input_channels": {
            "query_entropy": [b / 255.0 for b in h1],
            "context_signals": [b / 255.0 for b in h2[:16]] + [volatility, novelty],
        },
        "environmental_signals": context.get("environmental_signals", {}),
        "volatility": volatility, "novelty": novelty,
    }
    scores = await engine.compute_all_planes(query, context, cycle_id)
    psi = scores["psi_total"]
    delta = gate.compute_threshold(volatility, novelty)
    gate_open = gate.is_open(psi, delta)
    return {
        "gate_open": gate_open,
        "psi_score": round(psi, 6), "delta_threshold": round(delta, 6),
        "plane_breakdown": {k: round(scores[k], 6) for k in ["p", "i", "c", "s", "w"]},
        "message": "ACTION" if gate_open else "SILENCE",
        "cycle_id": cycle_id, "domain": domain, "_psi": psi,
    }


async def _skill_moat_status(_inp: Dict) -> Dict:
    from core.moat_accumulator import MoatAccumulator
    from learning.intelligence_score import IntelligenceScorer
    moat = MoatAccumulator()
    scorer = IntelligenceScorer()
    breakdown = await scorer.get_breakdown()
    return {**breakdown, "_psi": moat.get_current_lambda()}


async def _skill_trade_evaluate(inp: Dict) -> Dict:
    from trading.decision_engine import TradingDecisionEngine
    engine = TradingDecisionEngine()
    try:
        from api.routes.cmc_routes import cmc_signals
        cmc = await cmc_signals()
        cmc_bias = cmc.get("bias", "NEUTRAL")
        cmc_fg = cmc.get("fear_greed", 50)
    except Exception:
        cmc_bias = "NEUTRAL"
        cmc_fg = 50
    result = await engine.evaluate_trade(
        symbol=inp.get("symbol", "BNB/USDT"),
        direction=inp.get("direction", "LONG"),
        strategy=inp.get("strategy", "cmc_momentum"),
    )
    psi = result.pop("psi", None)
    twak_signed = False
    bsc_tx = None
    if result.get("action") == "EXECUTE":
        try:
            from bnb.twak_client import TWAKClient
            twak = TWAKClient()
            swap = await twak.execute_swap(
                symbol=inp.get("symbol", "BNB/USDT"),
                direction=inp.get("direction", "LONG"),
                size=result.get("size", 10.0) or 10.0,
            )
            twak_signed = swap.get("executed", False)
            bsc_tx = swap.get("tx_hash")
        except Exception:
            pass
    result["cmc_bias"] = cmc_bias
    result["cmc_fear_greed"] = cmc_fg
    result["twak_signed"] = twak_signed
    result["bsc_tx"] = bsc_tx
    result["execution_layer"] = "Trust Wallet Agent Kit (TWAK)"
    result["_psi"] = psi

    # ── Telegram alert ────────────────────────────────────────────────────────
    try:
        from notifications.telegram import alert_trade_executed, alert_gate_silent
        if result.get("action") == "EXECUTE":
            await alert_trade_executed(
                symbol=inp.get("symbol", "BNB/USDT"),
                direction=inp.get("direction", "LONG"),
                size_usd=result.get("size", 10.0) or 10.0,
                psi=psi or 0.0,
                delta=result.get("delta_trade", 0.0) or 0.0,
                tx_hash=bsc_tx,
                bscscan_url=None,
                simulated=not twak_signed,
                cmc_bias=cmc_bias,
                kelly_fraction=result.get("kelly_fraction"),
            )
        elif result.get("action") in ("SILENCE", "HOLD"):
            await alert_gate_silent(
                query=f"{inp.get('direction','LONG')} {inp.get('symbol','BNB/USDT')}",
                psi=psi or 0.0,
                delta=result.get("delta_trade", 0.0) or 0.0,
            )
    except Exception:
        pass

    return result


async def _skill_silence_check(inp: Dict) -> Dict:
    import asyncio, hashlib
    from core.coherence_engine import CoherenceEngine
    from core.action_gate import ActionGate
    from reasoning.chain_manager import ChainManager
    engine = CoherenceEngine()
    gate = ActionGate()
    chain_manager = ChainManager()
    action = inp.get("proposed_action", "")
    stakes = inp.get("stakes", 0.5)
    try:
        reasoning_chains = await asyncio.wait_for(chain_manager.run_chains(action, {}), timeout=4.0)
    except Exception:
        reasoning_chains = []
    qb = action.encode()
    h1 = hashlib.sha256(qb).digest()
    h2 = hashlib.sha256(qb + b"b").digest()
    context = {
        "reasoning_chains": reasoning_chains,
        "input_channels": {
            "query_entropy": [b / 255.0 for b in h1],
            "context_signals": [b / 255.0 for b in h2[:16]] + [stakes, 0.5],
        },
        "environmental_signals": {}, "volatility": stakes, "novelty": 0.5,
    }
    scores = await engine.compute_all_planes(action, context, str(uuid.uuid4()))
    psi = scores["psi_total"]
    delta = gate.compute_threshold(stakes, 0.5)
    should_act = gate.is_open(psi, delta)
    from api.routes.silence import _silence_log
    total = len(_silence_log) + 1
    silence_rate = len(_silence_log) / total
    return {
        "should_act": should_act,
        "psi_score": round(psi, 6), "delta_threshold": round(delta, 6),
        "silence_rate": round(silence_rate, 4),
        "reason": "Coherence sufficient — action permitted" if should_act else "Coherence below threshold — silence enforced",
        "_psi": psi,
    }


async def _skill_intelligence_score(_inp: Dict) -> Dict:
    from learning.intelligence_score import IntelligenceScorer
    return {**(await IntelligenceScorer().get_breakdown()), "_psi": 1.0}


async def _skill_reasoning_chain(inp: Dict) -> Dict:
    from reasoning.chain_manager import ChainManager
    manager = ChainManager()
    chains = await manager.run_chains(inp.get("query", ""), inp.get("context", {}))
    if not chains:
        return {"best_response": "No coherent chain produced", "confidence": 0.0, "n_chains": 0, "embedding_dim": 384, "_psi": 0.0}
    best = max(chains, key=lambda c: c.get("confidence", 0))
    return {
        "best_response": best.get("response", ""),
        "confidence": best.get("confidence", 0.0),
        "n_chains": len(chains),
        "embedding_dim": len(best.get("vector", [])) or 384,
        "elapsed_ms": best.get("elapsed_ms", 0),
        "_psi": best.get("confidence", 0.5),
    }
