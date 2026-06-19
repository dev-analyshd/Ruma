"""
Intelligence Scorer — RUMA
============================
Computes a human-readable IQ-equivalent score for the agent based on:
  - Λ moat size (accumulated track record)
  - Calibration quality A(t) history
  - Silence rate (discriminating vs. indiscriminate)
  - Win rate on executed trades
  - Coherence Ψ history
"""
from __future__ import annotations
import math


class IntelligenceScorer:
    """Maps agent state to a 0–200 IQ-equivalent scale."""

    IQ_BASE = 100.0   # Baseline: average agent

    async def get_breakdown(self) -> dict:
        from core.moat_accumulator import get_moat
        from core.silence_protocol import get_silence_protocol

        moat = get_moat()
        silence = get_silence_protocol()

        lambda_val = moat.get_current_lambda()
        n_cycles   = moat.n_cycles
        avg_cal    = moat.avg_calibration()
        cal_trend  = moat.calibration_trend()
        silence_stats = silence.stats()

        # Moat component (0–50 IQ points)
        # Λ=0.01 (start) → 0, Λ=0.10 → 10, Λ=1 → 25, Λ=10 → 40, Λ=100 → 50
        moat_iq = min(50.0, math.log10(lambda_val / 0.01 + 1) * 25.0)

        # Calibration component (0–40 IQ points)
        cal_iq = avg_cal * 40.0

        # Silence rate component (0–30 IQ points)
        # 40-60% silence rate = peak discrimination (30 pts)
        silence_rate = (silence_stats["hard_rate"] + silence_stats["soft_rate"])
        if 0.3 <= silence_rate <= 0.65:
            silence_iq = 30.0 * min(1.0, 1.0 - abs(silence_rate - 0.47) / 0.20)
        elif silence_rate < 0.2:
            silence_iq = 10.0  # Too trigger-happy
        else:
            silence_iq = 20.0  # High but not penalised

        # Experience component (0–30 IQ points)
        exp_iq = min(30.0, math.log(n_cycles + 1) / math.log(100) * 30.0)

        iq = self.IQ_BASE + moat_iq + cal_iq + silence_iq + exp_iq - 100.0
        iq = round(max(50.0, min(200.0, iq)), 1)

        if iq >= 160:   interp = "Genius-level calibration — exceptional track record"
        elif iq >= 130: interp = "Highly capable — well-calibrated, strong discrimination"
        elif iq >= 110: interp = "Above average — coherent with growing track record"
        elif iq >= 90:  interp = "Average — early stage, calibration developing"
        else:           interp = "Developing — insufficient track record"

        return {
            "iq_score": iq,
            "interpretation": interp,
            "components": {
                "moat_iq": round(moat_iq, 2),
                "calibration_iq": round(cal_iq, 2),
                "silence_iq": round(silence_iq, 2),
                "experience_iq": round(exp_iq, 2),
            },
            "raw_inputs": {
                "lambda": round(lambda_val, 6),
                "n_cycles": n_cycles,
                "avg_calibration": round(avg_cal, 4),
                "calibration_trend": cal_trend,
                "silence_rate": round(silence_rate, 4),
            },
        }
