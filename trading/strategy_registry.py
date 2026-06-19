"""
RUMA Strategy Registry — ADAPT-Ω Architecture
===============================================
Evaluates all 10 self-calibrating strategies every cycle and selects the one
with the highest expected_edge = opportunity_score × Ψ × A(t).

How it works:
  1. Receive snapshot (CMC data + agent state)
  2. For each of the 10 strategies:
       a. Compute opportunity_score(snapshot)
       b. Check Ψ ≥ psi_requirement
       c. Get A(t) from AdaptationPlane
       d. expected_edge = opportunity_score × Ψ × A(t)
  3. Return the strategy with the highest expected_edge
  4. If no strategy clears the edge threshold → SILENCE

On-chain learning:
  After each trade resolves, call registry.record_outcome() to update
  the effectiveness matrix and feed A(t) calibration (κ) forward.
"""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any

from trading.strategies import BaseStrategy, StrategySignal
from trading.strategies.all_ten import ALL_STRATEGIES, STRATEGY_MAP


# ── Edge threshold: minimum expected_edge to act ──────────────────────────────
EDGE_THRESHOLD = 0.22   # opp × Ψ × A must exceed this to trade
# At Ψ=0.742 A=0.550: funding_rate_arb opp=0.652 → edge=0.266 > 0.22 → trades.
# At Ψ=0.45  A=0.15:  max edge ≈ 0.044 → SILENCE (correct — low coherence).


@dataclass
class RegistryResult:
    selected: str                    # strategy name or "SILENCE"
    action: str                      # LONG | SHORT | NEUTRAL | HEDGE | SILENCE
    expected_edge: float
    size_usd: float
    psi: float
    a_val: float
    rationale: str
    all_signals: list[dict]          # All 10 scored (for transparency)
    on_chain_record: dict            # Fields to log to SovereignLearner.sol
    silenced: bool = False

    def to_dict(self) -> dict:
        return {
            "selected_strategy": self.selected,
            "action": self.action,
            "expected_edge": round(self.expected_edge, 4),
            "size_usd": self.size_usd,
            "psi": round(self.psi, 4),
            "adaptation": round(self.a_val, 4),
            "rationale": self.rationale,
            "silenced": self.silenced,
            "ranked_strategies": self.all_signals[:5],   # top 5 only in API response
            "on_chain_record": self.on_chain_record,
        }


class StrategyRegistry:
    """
    Evaluates all 10 ADAPT-Ω strategies each decision cycle.
    Plugs into the coherence engine pipeline after Ψ is computed.
    """

    def __init__(self, strategies: list[BaseStrategy] | None = None):
        self._strategies = strategies or ALL_STRATEGIES
        self._outcome_history: list[dict] = []    # For strategy learning

    # ── Main interface ─────────────────────────────────────────────────────────
    def evaluate_all(
        self,
        snapshot: dict,
        psi: float,
        a_val: float,
        capital: float = 500.0,
        regime: str = "SIDEWAYS",
    ) -> list[dict]:
        """
        Score all 10 strategies.
        Returns list of signal dicts sorted by expected_edge descending.
        """
        signals = []
        for strategy in self._strategies:
            sig: StrategySignal = strategy.evaluate(snapshot, psi, a_val, capital, regime)
            signals.append({
                "strategy":          sig.strategy_name,
                "opportunity_score": sig.opportunity_score,
                "psi_required":      sig.psi_requirement,
                "psi_met":           psi >= sig.psi_requirement,
                "direction":         sig.direction,
                "base_size_pct":     round(sig.base_size_pct, 4),
                "dynamic_size_pct":  round(sig.dynamic_size_pct, 4),
                "size_usd":          sig.dynamic_size_pct * capital,
                "expected_edge":     sig.expected_edge if not sig.silence else 0.0,
                "rationale":         sig.rationale,
                "silenced":          sig.silence,
                "on_chain_fields":   sig.on_chain_fields,
            })

        signals.sort(key=lambda x: x["expected_edge"], reverse=True)
        return signals

    def select_best(
        self,
        snapshot: dict,
        psi: float,
        a_val: float,
        capital: float = 500.0,
        regime: str = "SIDEWAYS",
        edge_threshold: float = EDGE_THRESHOLD,
    ) -> RegistryResult:
        """
        Select the single best strategy, or return SILENCE if none qualify.
        """
        all_signals = self.evaluate_all(snapshot, psi, a_val, capital, regime)
        top = all_signals[0] if all_signals else None

        if (
            top is None
            or top["silenced"]
            or top["expected_edge"] < edge_threshold
        ):
            return RegistryResult(
                selected="SILENCE",
                action="SILENCE",
                expected_edge=0.0,
                size_usd=0.0,
                psi=psi,
                a_val=a_val,
                rationale=(
                    f"No strategy clears edge threshold {edge_threshold:.2f}. "
                    f"Best was {(top or {}).get('strategy','N/A')} "
                    f"edge={(top or {}).get('expected_edge', 0.0):.4f}"
                ),
                all_signals=all_signals,
                on_chain_record={"action": "SILENCE", "psi": psi, "a_val": a_val},
                silenced=True,
            )

        on_chain = dict(top["on_chain_fields"])
        on_chain.update({
            "expected_edge": top["expected_edge"],
            "all_strategies_evaluated": len(all_signals),
            "timestamp_utc": time.time(),
        })

        return RegistryResult(
            selected=top["strategy"],
            action=top["direction"],
            expected_edge=top["expected_edge"],
            size_usd=round(top["size_usd"], 2),
            psi=psi,
            a_val=a_val,
            rationale=top["rationale"],
            all_signals=all_signals,
            on_chain_record=on_chain,
            silenced=False,
        )

    # ── On-chain learning loop ─────────────────────────────────────────────────
    def record_outcome(
        self,
        strategy_name: str,
        psi_at_entry: float,
        a_val_at_entry: float,
        predicted_return: float,
        actual_return: float,
        regime: str,
        won: bool,
    ) -> None:
        """
        Record trade outcome. Updates:
          1. EFFECTIVENESS_MATRIX (in-process online learning)
          2. AdaptationPlane calibration history (κ update)
        """
        from trading.strategies.all_ten import STRATEGY_MAP
        from trading.strategy_selector import EFFECTIVENESS_MATRIX

        # Update effectiveness matrix
        strategy = STRATEGY_MAP.get(strategy_name)
        if strategy:
            pass   # Strategy instance tracks its own stats via history

        # Update DynamicStrategySelector's effectiveness matrix
        try:
            from trading.strategy_selector import DynamicStrategySelector, EFFECTIVENESS_MATRIX
            if strategy_name in EFFECTIVENESS_MATRIX and regime in EFFECTIVENESS_MATRIX[strategy_name]:
                old = EFFECTIVENESS_MATRIX[strategy_name][regime]
                n   = len([o for o in self._outcome_history if o.get("strategy") == strategy_name and o.get("regime") == regime])
                new_wr = (old * n + (1.0 if won else 0.0)) / (n + 1)
                EFFECTIVENESS_MATRIX[strategy_name][regime] = round(new_wr, 4)
        except Exception:
            pass

        # Ignore SILENCE outcomes — nothing to learn from a no-trade
        if strategy_name == "SILENCE":
            return

        # Record for future reference
        self._outcome_history.append({
            "strategy":         strategy_name,
            "regime":           regime,
            "psi":              psi_at_entry,
            "a_val":            a_val_at_entry,
            "predicted_return": predicted_return,
            "actual_return":    actual_return,
            "won":              won,
            "timestamp":        time.time(),
        })

        # Feed into AdaptationPlane calibration
        try:
            from core.adaptation_plane import get_adaptation_plane
            get_adaptation_plane().update_calibration(predicted_return, actual_return)
        except Exception:
            pass

    def strategy_performance_summary(self) -> list[dict]:
        """Return per-strategy win rates from recorded outcomes."""
        from collections import defaultdict
        stats: dict[str, dict] = defaultdict(lambda: {"trades": 0, "wins": 0, "total_pnl": 0.0})
        for o in self._outcome_history:
            s = o["strategy"]
            stats[s]["trades"] += 1
            stats[s]["wins"]   += 1 if o["won"] else 0
            stats[s]["total_pnl"] += o["actual_return"]

        result = []
        for name, st in stats.items():
            result.append({
                "strategy":       name,
                "trades":         st["trades"],
                "win_rate":       round(st["wins"] / st["trades"], 4) if st["trades"] > 0 else 0.0,
                "total_pnl_pct":  round(st["total_pnl"] * 100, 2),
                "psi_threshold":  STRATEGY_MAP[name].psi_requirement if name in STRATEGY_MAP else None,
            })
        result.sort(key=lambda x: x["win_rate"], reverse=True)
        return result

    def __len__(self) -> int:
        return len(self._strategies)


# ── Process-level singleton ───────────────────────────────────────────────────
_registry = StrategyRegistry()

def get_registry() -> StrategyRegistry:
    return _registry
