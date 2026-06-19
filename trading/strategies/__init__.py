"""
RUMA Strategy Base — ADAPT-Ω Architecture
==========================================
All 10 strategies inherit from BaseStrategy and plug into the StrategyRegistry.

Each strategy is a self-calibrating module, not a fixed rule set:
  - opportunity_score()   → how good is the current signal? (0-1)
  - compute_dynamic_size()→ position size accounting for A(t), Ψ, regime
  - on_chain_record()     → structured dict for SovereignLearner.sol logging

The StrategyRegistry evaluates all 10 every cycle and picks the one with
the highest expected_edge = opportunity_score × Ψ × A(t).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StrategySignal:
    strategy_name: str
    opportunity_score: float    # 0-1 raw signal strength
    psi_requirement: float      # Minimum Ψ to act
    direction: str              # LONG | SHORT | NEUTRAL | HEDGE
    base_size_pct: float        # Base position as fraction of capital
    dynamic_size_pct: float     # After A(t) / Ψ / regime scaling
    expected_edge: float        # opportunity_score × psi × a_val
    rationale: str
    on_chain_fields: dict       # Fields logged to SovereignLearner.sol
    silence: bool = False       # True → agent should not trade this strategy


class BaseStrategy:
    """
    Base class for all RUMA ADAPT-Ω trading strategies.
    Subclasses override opportunity_score() and _base_size_pct().
    Dynamic sizing is handled here via A(t) and Ψ scaling.
    """
    name: str = "base"
    psi_requirement: float = 0.70
    max_size_pct: float = 0.10   # Hard cap: 10% of capital

    # ── Signal ────────────────────────────────────────────────────────────────
    def opportunity_score(self, snapshot: dict) -> float:
        """Return 0-1 confidence that NOW is a good time for this strategy."""
        raise NotImplementedError

    def direction(self, snapshot: dict) -> str:
        """Return LONG | SHORT | NEUTRAL | HEDGE."""
        return "LONG"

    # ── Sizing ────────────────────────────────────────────────────────────────
    def _base_size_pct(self, snapshot: dict) -> float:
        """Override per-strategy base size (fraction of capital)."""
        return 0.02

    def compute_dynamic_size(
        self,
        capital: float,
        psi: float,
        a_val: float,
        snapshot: dict,
        regime: str = "SIDEWAYS",
    ) -> float:
        """
        Dynamic sizing:  size = base × A(t) × Ψ² × regime_mult
        Capped at min(max_size_pct × capital, 1% of daily volume).
        """
        import math
        base = self._base_size_pct(snapshot)
        psi_sq = psi ** 2                                   # quadratic Ψ scaling
        regime_mult = {
            "BULL": 1.40, "BEAR": 1.20, "SIDEWAYS": 0.70,
            "VOLATILE": 0.40, "CRASH": 0.0, "RECOVERY": 1.10,
        }.get(regime, 1.0)

        raw_pct = base * a_val * psi_sq * regime_mult
        raw_pct = min(raw_pct, self.max_size_pct)

        size_usd = raw_pct * capital
        vol_cap  = snapshot.get("daily_volume_usd", snapshot.get("volume_24h", 1e8)) * 0.01
        return round(min(size_usd, vol_cap), 2)

    # ── On-chain record ───────────────────────────────────────────────────────
    def on_chain_fields(self, psi: float, a_val: float, snapshot: dict, size_usd: float) -> dict:
        """Fields sent to SovereignLearner.sol for on-chain provenance."""
        return {
            "strategy": self.name,
            "psi": round(psi, 4),
            "adaptation": round(a_val, 4),
            "opportunity_score": round(self.opportunity_score(snapshot), 4),
            "direction": self.direction(snapshot),
            "size_usd": size_usd,
            "fear_greed": snapshot.get("fear_greed", 50),
        }

    # ── Evaluate (called by registry) ─────────────────────────────────────────
    def evaluate(
        self,
        snapshot: dict,
        psi: float,
        a_val: float,
        capital: float,
        regime: str = "SIDEWAYS",
    ) -> StrategySignal:
        opp    = self.opportunity_score(snapshot)
        edge   = opp * psi * a_val
        size   = self.compute_dynamic_size(capital, psi, a_val, snapshot, regime)
        silent = (psi < self.psi_requirement) or (a_val < 0.20) or (size == 0.0)

        return StrategySignal(
            strategy_name=self.name,
            opportunity_score=opp,
            psi_requirement=self.psi_requirement,
            direction=self.direction(snapshot),
            base_size_pct=self._base_size_pct(snapshot),
            dynamic_size_pct=size / capital if capital > 0 else 0.0,
            expected_edge=round(edge, 4),
            rationale=self._rationale(snapshot, psi, a_val, opp),
            on_chain_fields=self.on_chain_fields(psi, a_val, snapshot, size),
            silence=silent,
        )

    def _rationale(self, snapshot: dict, psi: float, a_val: float, opp: float) -> str:
        return (
            f"{self.name}: opp={opp:.3f} Ψ={psi:.3f} A={a_val:.3f} "
            f"fg={snapshot.get('fear_greed', 50)} "
            f"p24h={snapshot.get('price_change_24h', 0.0):+.1f}%"
        )
