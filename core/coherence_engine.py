"""
Coherence Engine — RUMA ADAPT-Ω
=================================
Computes Ψ(t) across 6 cognitive planes:

  Ψ(t) = 0.22·P + 0.25·I + 0.18·C + 0.13·S + 0.10·W + 0.12·A

  P — Perceptual       (was 0.25, now 0.22 to make room for A)
  I — Inferential      (was 0.30, now 0.25)
  C — Consensus        (was 0.20, now 0.18)
  S — Self-Reflection  (was 0.15, now 0.13)
  W — World Model      (unchanged 0.10)
  A — Adaptation       (NEW 0.12) — bridges should-I to how-should-I

The A(t) plane is the 6th plane: it measures how well-calibrated the
agent's action parameters are to the current environment.

When A(t) < 0.30: SOFT SILENCE (can act, but only at 0.5% max size).
When Ψ(t) < Δ(t): HARD SILENCE (cannot act at all).
"""
from __future__ import annotations
import hashlib
import math
import time
from dataclasses import dataclass
from typing import Any


# ── Plane weights (must sum to 1.0) ──────────────────────────────────────────
W_P = 0.22   # Perceptual
W_I = 0.25   # Inferential
W_C = 0.18   # Consensus
W_S = 0.13   # Self-Reflection
W_W = 0.10   # World Model
W_A = 0.12   # Adaptation (new)

assert abs(W_P + W_I + W_C + W_S + W_W + W_A - 1.0) < 1e-9, "Weights must sum to 1"


@dataclass
class PlaneScores:
    p: float; i: float; c: float; s: float; w: float; a: float
    psi_total: float
    adaptation_components: dict

    def to_dict(self) -> dict:
        return {
            "psi_total": round(self.psi_total, 4),
            "planes": {
                "P_perceptual":    round(self.p, 4),
                "I_inferential":   round(self.i, 4),
                "C_consensus":     round(self.c, 4),
                "S_self_ref":      round(self.s, 4),
                "W_world_model":   round(self.w, 4),
                "A_adaptation":    round(self.a, 4),
            },
            "weights": {"W_P": W_P,"W_I": W_I,"W_C": W_C,"W_S": W_S,"W_W": W_W,"W_A": W_A},
            "formula": "Ψ = 0.22·P + 0.25·I + 0.18·C + 0.13·S + 0.10·W + 0.12·A",
            "adaptation": self.adaptation_components,
        }


class CoherenceEngine:
    """
    Multi-plane coherence evaluator. Computes Ψ(t) with the full 6-plane ADAPT-Ω model.
    All plane computations are deterministic given the same input + context.
    """

    # ── P — Perceptual ────────────────────────────────────────────────────────
    @staticmethod
    def _compute_p(input_channels: dict) -> float:
        """
        Perceptual plane: how clearly can the agent perceive the inputs?
        Measures signal clarity — entropy, coverage, freshness.
        """
        qe = input_channels.get("query_entropy", [])
        cs = input_channels.get("context_signals", [])

        if not qe:
            return 0.50

        # Shannon entropy of query hash bytes — higher ≠ better
        # We want *structured* signal, not pure noise
        entropy = -sum(b * math.log(b + 1e-12) + (1-b) * math.log(1-b+1e-12) for b in qe[:16])
        entropy_norm = min(1.0, entropy / 16.0)

        # Context richness
        context_richness = min(1.0, len(cs) / 20.0)

        p = 0.60 * entropy_norm + 0.40 * context_richness
        return round(min(1.0, max(0.0, p)), 4)

    # ── I — Inferential ───────────────────────────────────────────────────────
    @staticmethod
    def _compute_i(reasoning_chains: list[dict]) -> float:
        """
        Inferential plane: how strong is the agent's reasoning?
        Measures chain depth, convergence, and confidence.
        """
        if not reasoning_chains:
            return 0.50

        confidences = [c.get("confidence", 0.5) for c in reasoning_chains]
        depths      = [c.get("depth", 1) for c in reasoning_chains]

        avg_conf  = sum(confidences) / len(confidences)
        avg_depth = min(1.0, sum(depths) / (len(depths) * 5.0))  # 5-step chains = 1.0

        # Convergence: std dev of confidences (lower = more convergent)
        if len(confidences) > 1:
            mean = avg_conf
            std  = math.sqrt(sum((x - mean)**2 for x in confidences) / len(confidences))
            convergence = max(0.0, 1.0 - std * 3.0)
        else:
            convergence = 0.70

        i = 0.40 * avg_conf + 0.35 * convergence + 0.25 * avg_depth
        return round(min(1.0, max(0.0, i)), 4)

    # ── C — Consensus ─────────────────────────────────────────────────────────
    @staticmethod
    def _compute_c(reasoning_chains: list[dict]) -> float:
        """
        Consensus plane: do multiple reasoning chains agree?
        Measures inter-chain agreement on direction/conclusion.
        """
        if len(reasoning_chains) < 2:
            return 0.55

        conclusions = [c.get("conclusion", "neutral") for c in reasoning_chains]
        # Simple majority agreement
        counts: dict[str, int] = {}
        for con in conclusions:
            counts[con] = counts.get(con, 0) + 1
        majority = max(counts.values())
        consensus = majority / len(conclusions)

        c = 0.70 * consensus + 0.30 * (majority / max(len(reasoning_chains), 1))
        return round(min(1.0, max(0.0, c)), 4)

    # ── S — Self-Reflection ───────────────────────────────────────────────────
    @staticmethod
    def _compute_s(query: str) -> float:
        """
        Self-reflection plane: is the query within the agent's domain?
        Measures relevance, specificity, and alignment with agent identity.
        """
        q = query.lower()

        # Trading/finance keywords → high S
        domain_keywords = [
            "trade", "swap", "buy", "sell", "price", "signal", "market",
            "bnb", "crypto", "defi", "strategy", "risk", "position",
            "momentum", "bullish", "bearish", "volume", "liquidity",
        ]
        hits = sum(1 for kw in domain_keywords if kw in q)
        domain_score = min(1.0, hits / 4.0)  # 4+ keywords = 1.0

        # Query length — too short = low specificity
        length_score = min(1.0, len(query) / 60.0)

        s = 0.65 * domain_score + 0.35 * length_score
        return round(min(1.0, max(0.0, s)), 4)

    # ── W — World Model ───────────────────────────────────────────────────────
    @staticmethod
    def _compute_w(environmental_signals: dict) -> float:
        """
        World model plane: how good is the agent's model of current environment?
        Measures data freshness, signal coverage, and consistency.
        """
        if not environmental_signals:
            return 0.45

        # Data freshness (age of signals)
        ages = [time.time() - v.get("timestamp", time.time()) for v in environmental_signals.values()
                if isinstance(v, dict) and "timestamp" in v]
        freshness = max(0.0, 1.0 - (sum(ages) / max(len(ages), 1)) / 300.0) if ages else 0.60

        # Coverage (how many signal types present)
        coverage = min(1.0, len(environmental_signals) / 6.0)  # 6 types = full coverage

        w = 0.55 * freshness + 0.45 * coverage
        return round(min(1.0, max(0.0, w)), 4)

    # ── A — Adaptation ───────────────────────────────────────────────────────
    @staticmethod
    def _compute_a(context: dict) -> tuple[float, dict]:
        """
        Adaptation plane: how well-calibrated are the agent's action parameters?
        Delegates to AdaptationPlane singleton.
        """
        from core.adaptation_plane import get_adaptation_plane
        plane = get_adaptation_plane()

        regime   = context.get("regime", "SIDEWAYS")
        strategy = context.get("selected_strategy", "MomentumBreakout")
        order_sz = context.get("order_size_usd", 10.0)
        vol_usd  = context.get("daily_volume_usd", 50_000_000.0)

        result = plane.compute(
            regime=regime,
            selected_strategy=strategy,
            order_size_usd=order_sz,
            daily_volume_usd=vol_usd,
        )
        return result.A, result.to_dict()

    # ── Main entry point ──────────────────────────────────────────────────────
    async def compute_all_planes(
        self, query: str, context: dict, cycle_id: str
    ) -> dict[str, Any]:
        """
        Compute all 6 planes and combine into Ψ(t).
        Returns dict with plane scores, Ψ total, and A(t) detail.
        """
        reasoning_chains = context.get("reasoning_chains", [])
        input_channels   = context.get("input_channels", {})
        env_signals      = context.get("environmental_signals", {})

        p = self._compute_p(input_channels)
        i = self._compute_i(reasoning_chains)
        c = self._compute_c(reasoning_chains)
        s = self._compute_s(query)
        w = self._compute_w(env_signals)
        a, a_detail = self._compute_a(context)

        psi = W_P*p + W_I*i + W_C*c + W_S*s + W_W*w + W_A*a
        psi = round(min(1.0, max(0.0, psi)), 4)

        return {
            "psi_total": psi,
            "p": p, "i": i, "c": c, "s": s, "w": w, "a": a,
            "adaptation_detail": a_detail,
            "cycle_id": cycle_id,
            "plane_scores": PlaneScores(
                p=p, i=i, c=c, s=s, w=w, a=a, psi_total=psi,
                adaptation_components=a_detail,
            ).to_dict(),
        }
