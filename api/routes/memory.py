from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

router = APIRouter()


class MemorySearchRequest(BaseModel):
    query: str = Field(..., description="Natural language query to search memories by similarity")
    k: int = Field(default=10, ge=1, le=50, description="Number of results to return")
    domain: Optional[str] = Field(default=None, description="Filter by domain (e.g. 'trading', 'general')")
    gate_open: Optional[bool] = Field(default=None, description="Filter by whether gate was open (True=action, False=silence)")


class MemoryResult(BaseModel):
    rank: int
    distance: float
    similarity: float
    cycle_id: Optional[str]
    domain: Optional[str]
    gate_open: Optional[bool]
    psi: Optional[float]
    timestamp: Optional[str]


class MemorySearchResponse(BaseModel):
    query: str
    total_memories: int
    results: List[MemoryResult]
    store: str


@router.post("/memory/search", response_model=MemorySearchResponse, tags=["Memory"])
async def search_memory(req: MemorySearchRequest):
    """
    Semantic search over the agent's stored memories using pgvector cosine similarity.
    Each memory is a reasoning cycle embedding — query in natural language to find
    what the agent was thinking about in similar situations.
    """
    from memory.timescale_store import TimescaleStore, _get_pool
    from reasoning.embedding_engine import EmbeddingEngine

    pool = await _get_pool()
    if pool is None:
        raise HTTPException(status_code=503, detail="TimescaleDB not available")

    embedder = EmbeddingEngine()
    vec = embedder.embed(req.query)

    from memory.timescale_store import _vec_str
    import json

    vs = _vec_str(vec)

    where_clauses = []
    args = [vs, req.k]
    arg_idx = 3

    if req.domain is not None:
        where_clauses.append(f"domain ILIKE ${arg_idx}")
        args.append(f"%{req.domain}%")
        arg_idx += 1

    if req.gate_open is not None:
        where_clauses.append(f"gate_open = ${arg_idx}")
        args.append(req.gate_open)
        arg_idx += 1

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    rows = await pool.fetch(
        f"""
        SELECT
            cycle_id,
            domain,
            gate_open,
            psi,
            timestamp,
            meta_json,
            (embedding <=> $1::vector) AS distance
        FROM memory_strands
        {where_sql}
        ORDER BY embedding <=> $1::vector
        LIMIT $2
        """,
        *args,
    )

    total = await pool.fetchval("SELECT COUNT(*) FROM memory_strands")

    results = []
    for rank, row in enumerate(rows, 1):
        dist = float(row["distance"])
        results.append(MemoryResult(
            rank=rank,
            distance=round(dist, 6),
            similarity=round(1 - dist, 6),
            cycle_id=row["cycle_id"],
            domain=row["domain"],
            gate_open=row["gate_open"],
            psi=round(float(row["psi"]), 4) if row["psi"] is not None else None,
            timestamp=row["timestamp"].isoformat() if row["timestamp"] else None,
        ))

    return MemorySearchResponse(
        query=req.query,
        total_memories=int(total),
        results=results,
        store="timescaledb+pgvector",
    )


@router.get("/memory/stats", tags=["Memory"])
async def memory_stats():
    """Overview of stored memories — total count, domain breakdown, gate-open ratio."""
    from memory.timescale_store import _get_pool

    pool = await _get_pool()
    if pool is None:
        raise HTTPException(status_code=503, detail="TimescaleDB not available")

    total = await pool.fetchval("SELECT COUNT(*) FROM memory_strands")
    domains = await pool.fetch("""
        SELECT domain, COUNT(*) AS n, AVG(psi) AS avg_psi,
               SUM(CASE WHEN gate_open THEN 1 ELSE 0 END) AS actions,
               SUM(CASE WHEN NOT gate_open THEN 1 ELSE 0 END) AS silences
        FROM memory_strands
        GROUP BY domain
        ORDER BY n DESC
        LIMIT 20
    """)
    oldest = await pool.fetchval("SELECT MIN(timestamp) FROM memory_strands")
    newest = await pool.fetchval("SELECT MAX(timestamp) FROM memory_strands")

    return {
        "total_memories": int(total),
        "oldest": oldest.isoformat() if oldest else None,
        "newest": newest.isoformat() if newest else None,
        "store": "timescaledb+pgvector",
        "vector_dim": 384,
        "index": "hnsw (vector_cosine_ops)",
        "domains": [
            {
                "domain": r["domain"],
                "count": int(r["n"]),
                "avg_psi": round(float(r["avg_psi"]), 4) if r["avg_psi"] else None,
                "actions": int(r["actions"]),
                "silences": int(r["silences"]),
            }
            for r in domains
        ],
    }
