from fastapi import APIRouter
from learning.intelligence_score import IntelligenceScorer
from learning.domain_mastery import DomainMasteryEngine
from core.moat_accumulator import MoatAccumulator

router = APIRouter()


@router.get("/intelligence")
async def get_intelligence():
    scorer = IntelligenceScorer()
    data = await scorer.get_breakdown()
    return data


@router.get("/intelligence/domains")
async def get_domains():
    mastery = DomainMasteryEngine()
    return {"domains": mastery.get_all(), "top": mastery.get_top_domain()}


@router.get("/intelligence/moat")
async def get_moat_state():
    moat = MoatAccumulator()
    return {
        "lambda": moat.get_current_lambda(),
        "log_lambda": moat.log_lambda,
        "n_cycles": moat.n_cycles,
        "t_normalized": moat.get_t_normalized(),
    }
