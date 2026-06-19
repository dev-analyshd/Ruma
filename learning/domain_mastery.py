"""
Domain Mastery Engine — RUMA
==============================
Tracks mastery scores across trading/intelligence domains.
M(d,t) = knowledge_count / (knowledge_count + decay_factor)
"""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class DomainRecord:
    domain: str
    knowledge_count: int = 0
    mastery_score: float = 0.0
    last_updated: float = field(default_factory=time.time)


_DOMAINS = [
    "technical_analysis",
    "on_chain_metrics",
    "sentiment_analysis",
    "risk_management",
    "market_microstructure",
    "funding_rates",
    "liquidity_analysis",
    "momentum_signals",
    "correlation_analysis",
    "volatility_modeling",
]


class DomainMasteryEngine:
    DECAY_FACTOR = 10.0  # knowledge_count needed for 50% mastery

    def __init__(self):
        self._domains: Dict[str, DomainRecord] = {
            d: DomainRecord(domain=d) for d in _DOMAINS
        }

    def learn(self, domain: str, increment: int = 1) -> DomainRecord:
        if domain not in self._domains:
            self._domains[domain] = DomainRecord(domain=domain)
        rec = self._domains[domain]
        rec.knowledge_count += increment
        rec.mastery_score = rec.knowledge_count / (rec.knowledge_count + self.DECAY_FACTOR)
        rec.last_updated = time.time()
        return rec

    def get(self, domain: str) -> dict:
        rec = self._domains.get(domain)
        if not rec:
            return {"domain": domain, "mastery_score": 0.0, "knowledge_count": 0}
        return {
            "domain": rec.domain,
            "mastery_score": round(rec.mastery_score, 6),
            "knowledge_count": rec.knowledge_count,
            "last_updated": rec.last_updated,
        }

    def get_all(self) -> List[dict]:
        return [
            {
                "domain": rec.domain,
                "mastery_score": round(rec.mastery_score, 6),
                "knowledge_count": rec.knowledge_count,
                "last_updated": rec.last_updated,
            }
            for rec in sorted(self._domains.values(), key=lambda r: r.mastery_score, reverse=True)
        ]

    def get_top_domain(self) -> dict | None:
        if not self._domains:
            return None
        top = max(self._domains.values(), key=lambda r: r.mastery_score)
        return self.get(top.domain)
