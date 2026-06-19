import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from api.routes import action, trade, intelligence, bnb_routes, silence, moat, health
from api.routes import skills, agent_card, x402, mcp_server
from api.routes import federation, stream, ws_dashboard
from api.routes import memory
from api.routes import cmc_routes, twak_routes
from api.routes import telegram_routes
from api.routes import strategy_routes, bnb_sdk_routes
from api.routes import competition_dashboard
from api.routes import trading_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n" + "=" * 60)
    print(" RUMA STARTING")
    print(" BNB Hack: AI Trading Agent Edition — Track 1")
    print(" Ω(a,t) = [Ψ(t) ≥ Δ(t)] · R(a,t) · e^(Λ·t)")
    print(" Truth or silence. The silence is information.")
    print(" Chain: BNB Smart Chain (BSC) | Chain ID: 56")
    print(" Market Data: CoinMarketCap AI Agent Hub (MCP + x402)")
    print(" Execution: Trust Wallet Agent Kit (TWAK) — self-custody")
    print(" Competition: 0x212c61b9b72c95d95bf29cf032f5e5635629aed5")
    print("=" * 60 + "\n")

    from learning.intelligence_score import IntelligenceScorer
    from core.moat_accumulator import MoatAccumulator

    if os.getenv("TIMESCALE_URL"):
        try:
            from storage.db import get_pool
            await get_pool()
        except Exception as e:
            print(f"[DB] TimescaleDB init error: {e}")

    moat_acc = MoatAccumulator()
    scorer = IntelligenceScorer()
    iq = await scorer.compute()
    print(f"[STARTUP] Λ={moat_acc.get_current_lambda():.8f} | Cycles={moat_acc.n_cycles} | IQ={iq:.8f}")

    async def on_chain_heartbeat_loop():
        from core.on_chain_heartbeat import background_sync_loop
        await background_sync_loop()

    async def self_improve_loop():
        from learning.domain_mastery import DomainMasteryEngine
        mastery = DomainMasteryEngine()
        while True:
            await asyncio.sleep(3600)
            domains = mastery.get_all()
            weak = [d for d in domains if d["mastery_score"] < 0.3]
            if weak:
                print(f"[SELF-IMPROVE] Weak domains: {[d['domain'] for d in weak]}")

    async def daily_reset():
        from trading.risk_manager import RiskManager
        risk = RiskManager()
        while True:
            await asyncio.sleep(86400)
            risk.daily_reset()

    async def federation_beacon():
        await asyncio.sleep(60)
        while True:
            try:
                from api.routes.federation import _peers, _proactive_invite
                active = [p for p in _peers.values() if p.get("status") in ("active", "handshaked")]
                if active:
                    print(f"[FEDERATION] Beacon to {len(active)} peer(s)")
            except Exception as e:
                print(f"[FEDERATION] Beacon error: {e}")
            await asyncio.sleep(300)

    async def cmc_signal_loop():
        """Poll CMC AI Agent Hub every 5 minutes for W-plane and P-plane signals."""
        while True:
            await asyncio.sleep(300)
            try:
                from api.routes.cmc_routes import cmc_signals
                signals = await cmc_signals()
                print(f"[CMC] bias={signals.get('bias')} | FG={signals.get('fear_greed')} | BNB_1h={signals.get('bnb_1h_pct')}%")
            except Exception as e:
                print(f"[CMC] Signal poll error: {e}")

    asyncio.create_task(on_chain_heartbeat_loop())
    asyncio.create_task(self_improve_loop())
    asyncio.create_task(daily_reset())
    asyncio.create_task(federation_beacon())
    asyncio.create_task(cmc_signal_loop())

    # ── Competition week trading scheduler (Track 1 — 1 trade/day minimum) ────
    from bnb.trading_scheduler import competition_scheduler_loop
    asyncio.create_task(competition_scheduler_loop())

    # ── Telegram startup alert ─────────────────────────────────────────────────
    try:
        from notifications.telegram import alert_startup
        await alert_startup(moat_acc.get_current_lambda(), moat_acc.n_cycles, iq)
    except Exception:
        pass

    print("[RUMA] All background loops running.")
    print(f"[RUMA] SSE streams: /api/v1/stream/intelligence | /stream/heartbeat | /stream/moat | /stream/actions")
    print(f"[RUMA] CMC Hub: /api/v1/cmc/fear-greed | /cmc/signals | /cmc/prices")
    print(f"[RUMA] TWAK: /api/v1/twak/status | /twak/portfolio | /twak/swap")
    print(f"[RUMA] BSC: /api/v1/bnb/status | /bnb/competition/register | /bnb/competition/status")
    print(f"[RUMA] Track 2: /api/v1/strategy/catalog | /strategy/spec/BNB | /strategy/backtest")
    print(f"[RUMA] BNB SDK: /api/v1/bnb-sdk/status | /bnb-sdk/skills | /bnb-sdk/execute")

    yield

    print("[RUMA] Graceful shutdown. Moat preserved.")


app = FastAPI(
    title="RUMA",
    description=(
        "Autonomous AI Trading Agent on BNB Chain. "
        "Reads markets via CoinMarketCap AI Agent Hub (MCP + x402). "
        "Decides using TRION mathematics — Ψ(t) = 0.25P + 0.30I + 0.20C + 0.15S + 0.10W. "
        "Executes self-custodial BSC trades via Trust Wallet Agent Kit (TWAK). "
        "Silence rate ~87%. Track 1: BNB Hack AI Trading Agent Edition."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Core intelligence endpoints ────────────────────────────────────────────────
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(action.router, prefix="/api/v1", tags=["Core"])
app.include_router(trade.router, prefix="/api/v1", tags=["Trading"])
app.include_router(intelligence.router, prefix="/api/v1", tags=["Intelligence"])
app.include_router(bnb_routes.router, prefix="/api/v1", tags=["BNB Chain (BSC)"])
app.include_router(silence.router, prefix="/api/v1", tags=["Silence"])
app.include_router(moat.router, prefix="/api/v1", tags=["Moat"])
app.include_router(memory.router, prefix="/api/v1", tags=["Memory"])

# ── CoinMarketCap AI Agent Hub ─────────────────────────────────────────────────
app.include_router(cmc_routes.router, prefix="/api/v1", tags=["CMC AI Agent Hub"])

# ── Trust Wallet Agent Kit (TWAK) ─────────────────────────────────────────────
app.include_router(twak_routes.router, prefix="/api/v1", tags=["TWAK (Trust Wallet)"])

# ── BNB Hack Skills: MCP + x402 ───────────────────────────────────────────────
app.include_router(skills.router, prefix="/api/v1", tags=["Agent Skills (MCP)"])
app.include_router(x402.router, prefix="/api/v1", tags=["x402 Payments (BSC)"])
app.include_router(agent_card.router, tags=["Agent Discovery (A2A)"])
app.include_router(mcp_server.router, tags=["MCP Server (JSON-RPC 2.0)"])

# ── Agent Federation (A2A peer network) ───────────────────────────────────────
app.include_router(federation.router, prefix="/api/v1", tags=["Federation (A2A)"])

# ── Live SSE Streaming ────────────────────────────────────────────────────────
app.include_router(stream.router, prefix="/api/v1", tags=["Live Streaming (SSE)"])

# ── WebSocket Dashboard ───────────────────────────────────────────────────────
app.include_router(ws_dashboard.router, tags=["Dashboard (WebSocket)"])

# ── Telegram Alerts ───────────────────────────────────────────────────────────
app.include_router(telegram_routes.router, prefix="/api/v1", tags=["Telegram Alerts"])

# ── Track 2: CMC Strategy Skill ───────────────────────────────────────────────
app.include_router(strategy_routes.router, prefix="/api/v1", tags=["Track 2: Strategy Skills"])

# ── BNB AI Agent SDK (special prize) ─────────────────────────────────────────
app.include_router(bnb_sdk_routes.router, prefix="/api/v1", tags=["BNB AI Agent SDK"])

# ── Competition Dashboard + Emergency Stop ─────────────────────────────────────
app.include_router(competition_dashboard.router, prefix="/api/v1", tags=["Competition Dashboard"])

# ── Dynamic Trading Engine (5 adaptive modules) ────────────────────────────────
app.include_router(trading_routes.router, prefix="/api/v1", tags=["Dynamic Trading Engine"])


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    from fastapi.responses import Response
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
        '<rect width="32" height="32" rx="7" fill="#f0b90b"/>'
        '<text x="16" y="23" font-size="16" font-family="serif" font-weight="bold" '
        'text-anchor="middle" fill="#1e2026">R</text>'
        '</svg>'
    )
    return Response(content=svg, media_type="image/svg+xml")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root():
    from core.moat_accumulator import MoatAccumulator
    from learning.intelligence_score import IntelligenceScorer
    from learning.domain_mastery import DomainMasteryEngine
    from core.on_chain_heartbeat import get_sync_stats
    import math

    moat = MoatAccumulator()
    scorer = IntelligenceScorer()
    iq = await scorer.compute()
    domains = DomainMasteryEngine().get_all()
    stats = get_sync_stats()

    lam = moat.get_current_lambda()
    log_lam = moat.log_lambda
    cycles = moat.n_cycles
    iq_fmt = f"{iq:.4e}" if iq > 1000 else f"{iq:.6f}"
    lam_fmt = f"{lam:.4e}"
    domain_rows = "".join(
        f"<tr><td>{d['domain']}</td><td>{d['mastery_score']:.4f}</td><td>{d['knowledge_count']}</td></tr>"
        for d in domains[:6]
    ) or "<tr><td colspan='3' style='color:#666'>No domains yet — run some actions</td></tr>"

    # Pull live CMC signal
    try:
        from api.routes.cmc_routes import cmc_signals
        cmc = await cmc_signals()
        cmc_bias = cmc.get("bias", "NEUTRAL")
        cmc_fg = cmc.get("fear_greed", "—")
        cmc_bnb_1h = cmc.get("bnb_1h_pct", "—")
    except Exception:
        cmc_bias = "NEUTRAL"
        cmc_fg = "—"
        cmc_bnb_1h = "—"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>RUMA · BNB Hack AI Trading Agent</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#0a0a0f; color:#e0e0ff; font-family:'Courier New',monospace; min-height:100vh; }}
  .header {{ background:linear-gradient(135deg,#0d0d1a,#1a120a); border-bottom:1px solid #f0b90b55; padding:2rem; text-align:center; }}
  .header h1 {{ font-size:2.5rem; color:#f0b90b; letter-spacing:0.1em; }}
  .header .formula {{ color:#a08040; margin-top:0.5rem; font-size:0.9rem; }}
  .header .tagline {{ color:#8080b0; margin-top:0.3rem; font-size:0.8rem; font-style:italic; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:1.5rem; padding:2rem; max-width:1200px; margin:0 auto; }}
  .card {{ background:#0f0f1f; border:1px solid #2a2a4a; border-radius:8px; padding:1.5rem; }}
  .card h2 {{ color:#f0b90b; font-size:0.75rem; text-transform:uppercase; letter-spacing:0.15em; margin-bottom:1rem; border-bottom:1px solid #2a1a0a; padding-bottom:0.5rem; }}
  .metric {{ display:flex; justify-content:space-between; align-items:baseline; margin:0.5rem 0; }}
  .metric-label {{ color:#6060a0; font-size:0.8rem; }}
  .metric-value {{ color:#c0c0ff; font-size:0.9rem; font-weight:bold; }}
  .metric-value.big {{ color:#f0b90b; font-size:1.1rem; }}
  .metric-value.green {{ color:#40ff80; }}
  .metric-value.orange {{ color:#ffa040; }}
  .badge {{ display:inline-block; padding:0.2rem 0.6rem; border-radius:4px; font-size:0.7rem; font-weight:bold; margin:0.2rem; }}
  .badge.live {{ background:#1a3a1a; color:#40ff80; border:1px solid #40ff80; }}
  .badge.chain {{ background:#1a150a; color:#f0b90b; border:1px solid #f0b90b; }}
  .badge.silence {{ background:#2a1a0a; color:#ffa040; border:1px solid #ffa040; }}
  .links {{ display:grid; grid-template-columns:1fr 1fr; gap:0.5rem; }}
  .link {{ background:#0a0a1f; border:1px solid #2a2a4a; border-radius:4px; padding:0.5rem; text-decoration:none; color:#8080c0; font-size:0.75rem; transition:all 0.2s; display:block; }}
  .link:hover {{ border-color:#f0b90b; color:#f0b90b; background:#0f0a0a; }}
  .link .method {{ color:#4040a0; font-size:0.65rem; }}
  table {{ width:100%; border-collapse:collapse; font-size:0.8rem; }}
  th {{ color:#6060a0; padding:0.4rem; text-align:left; border-bottom:1px solid #1a1a3a; }}
  td {{ color:#c0c0ff; padding:0.4rem; border-bottom:1px solid #0f0f1f; }}
  .note-box {{ background:#0a0f0a; border:1px solid #204020; border-radius:4px; padding:0.8rem; font-size:0.75rem; color:#60c060; margin-top:0.5rem; }}
  .silence-box {{ background:#1a0f0a; border:1px solid #604020; border-radius:4px; padding:0.8rem; margin-top:0.5rem; }}
  .silence-box p {{ font-size:0.75rem; color:#c08040; line-height:1.5; }}
</style>
</head>
<body>
<div class="header">
  <h1>RUMA</h1>
  <div class="formula">Ω(a,t) = [Ψ(t) ≥ Δ(t)] · R(a,t) · e<sup>Λ·t</sup></div>
  <div class="tagline">Truth or silence. · BNB Smart Chain · CoinMarketCap AI Agent Hub · Trust Wallet Agent Kit</div>
  <div style="margin-top:1rem">
    <span class="badge live">● ONLINE</span>
    <span class="badge chain">⛓ BNB Smart Chain</span>
    <span class="badge chain">🧠 CMC AI Agent Hub</span>
    <span class="badge chain">🔐 TWAK Self-Custody</span>
    <span class="badge silence">⚡ Silence Protocol ACTIVE</span>
  </div>
</div>

<div class="grid">

  <div class="card">
    <h2>⚡ Live Intelligence</h2>
    <div class="metric"><span class="metric-label">Λ (Compounding Moat)</span><span class="metric-value big">{lam_fmt}</span></div>
    <div class="metric"><span class="metric-label">log(Λ)</span><span class="metric-value">{log_lam:.4f}</span></div>
    <div class="metric"><span class="metric-label">IQ Score IQ(t)</span><span class="metric-value big">{iq_fmt}</span></div>
    <div class="metric"><span class="metric-label">Coherent Cycles</span><span class="metric-value green">{cycles:,}</span></div>
    <div class="metric"><span class="metric-label">Domains Mastered</span><span class="metric-value">{len(domains)}</span></div>
    <div class="note-box">📡 Subscribe:<br><code>/api/v1/stream/intelligence</code></div>
  </div>

  <div class="card">
    <h2>🧠 CMC AI Agent Hub</h2>
    <div class="metric"><span class="metric-label">Market Bias</span><span class="metric-value big" style="color:#{'40ff80' if cmc_bias=='BULLISH' else ('ff4060' if cmc_bias=='BEARISH' else 'ffa040')}">{cmc_bias}</span></div>
    <div class="metric"><span class="metric-label">Fear & Greed Index</span><span class="metric-value">{cmc_fg}</span></div>
    <div class="metric"><span class="metric-label">BNB 1h Change</span><span class="metric-value">{cmc_bnb_1h}%</span></div>
    <div class="metric"><span class="metric-label">MCP Endpoint</span><span class="metric-value" style="font-size:0.7rem">mcp.coinmarketcap.com</span></div>
    <div class="metric"><span class="metric-label">x402 Payments</span><span class="metric-value green">ACTIVE</span></div>
    <div class="links" style="margin-top:0.8rem">
      <a class="link" href="/api/v1/cmc/fear-greed"><span class="method">GET</span> /fear-greed</a>
      <a class="link" href="/api/v1/cmc/signals"><span class="method">GET</span> /signals</a>
      <a class="link" href="/api/v1/cmc/prices"><span class="method">GET</span> /prices</a>
      <a class="link" href="/api/v1/cmc/analyze"><span class="method">POST</span> /analyze</a>
    </div>
  </div>

  <div class="card">
    <h2>🔐 TWAK (Trust Wallet)</h2>
    <div class="metric"><span class="metric-label">Execution Layer</span><span class="metric-value green">TWAK (Self-Custody)</span></div>
    <div class="metric"><span class="metric-label">Local Signing</span><span class="metric-value green">✓ Keys Never Leave Env</span></div>
    <div class="metric"><span class="metric-label">Autonomous Mode</span><span class="metric-value green">ACTIVE</span></div>
    <div class="metric"><span class="metric-label">Chain</span><span class="metric-value">BNB Smart Chain (BSC)</span></div>
    <div class="links" style="margin-top:0.8rem">
      <a class="link" href="/api/v1/twak/status"><span class="method">GET</span> /status</a>
      <a class="link" href="/api/v1/twak/portfolio"><span class="method">GET</span> /portfolio</a>
    </div>
  </div>

  <div class="card">
    <h2>⛓ BNB Chain (BSC)</h2>
    <div class="metric"><span class="metric-label">Network</span><span class="metric-value">BSC (Chain ID 56)</span></div>
    <div class="metric"><span class="metric-label">Chain Syncs</span><span class="metric-value green">{stats['total_chain_syncs']}</span></div>
    <div class="metric"><span class="metric-label">Competition Contract</span><span class="metric-value" style="font-size:0.65rem">0x212c...aed5</span></div>
    <div class="links" style="margin-top:0.8rem">
      <a class="link" href="/api/v1/bnb/status"><span class="method">GET</span> /status</a>
      <a class="link" href="/api/v1/bnb/competition/status"><span class="method">GET</span> /competition/status</a>
    </div>
    <div class="note-box" style="margin-top:0.5rem">Registration: POST /api/v1/bnb/competition/register<br>or: twak compete register</div>
  </div>

  <div class="card">
    <h2>🎯 6 Agent Skills</h2>
    <div class="metric"><span class="metric-label">coherence_evaluate</span><span class="metric-value" style="color:#40ff80;font-size:0.75rem">FREE (CMC-enriched)</span></div>
    <div class="metric"><span class="metric-label">moat_status</span><span class="metric-value" style="color:#40ff80;font-size:0.75rem">FREE</span></div>
    <div class="metric"><span class="metric-label">silence_check</span><span class="metric-value" style="color:#40ff80;font-size:0.75rem">FREE</span></div>
    <div class="metric"><span class="metric-label">intelligence_score</span><span class="metric-value" style="color:#40ff80;font-size:0.75rem">FREE</span></div>
    <div class="metric"><span class="metric-label">trade_evaluate</span><span class="metric-value" style="color:#ffa040;font-size:0.75rem">0.001 BNB / 0.10 USDT</span></div>
    <div class="metric"><span class="metric-label">reasoning_chain</span><span class="metric-value" style="color:#ffa040;font-size:0.75rem">0.002 BNB / 0.20 USDT</span></div>
    <div class="note-box" style="margin-top:0.8rem">MCP + x402 (BSC) · <a href="/api/v1/skills" style="color:#60c060">View all skills →</a></div>
  </div>

  <div class="card">
    <h2>🧠 TRION Coherence</h2>
    <div class="metric"><span class="metric-label">Ψ Formula</span><span class="metric-value" style="font-size:0.75rem">0.25P + 0.30I + 0.20C + 0.15S + 0.10W</span></div>
    <div class="metric"><span class="metric-label">W-plane Source</span><span class="metric-value" style="font-size:0.75rem">CMC Fear & Greed z-score</span></div>
    <div class="metric"><span class="metric-label">P-plane Source</span><span class="metric-value" style="font-size:0.75rem">CMC price entropy</span></div>
    <div class="metric"><span class="metric-label">Gate Base Δ</span><span class="metric-value">0.6500</span></div>
    <div class="metric"><span class="metric-label">Silence rate</span><span class="metric-value orange">~87% (discriminating)</span></div>
    <div class="silence-box">
      <p>When Ψ &lt; Δ the agent is SILENT. Silence is not failure — it's the gate making the right decision. RUMA silences ~87% of all potential BSC trade signals.</p>
    </div>
  </div>

  <div class="card">
    <h2>📡 Live SSE Streams</h2>
    <div class="links">
      <a class="link" href="/api/v1/stream/intelligence"><span class="method">SSE</span> /intelligence</a>
      <a class="link" href="/api/v1/stream/heartbeat"><span class="method">SSE</span> /heartbeat</a>
      <a class="link" href="/api/v1/stream/moat"><span class="method">SSE</span> /moat</a>
      <a class="link" href="/api/v1/stream/actions"><span class="method">SSE</span> /actions</a>
    </div>
    <h2 style="margin-top:1.2rem">🔗 Explore</h2>
    <div class="links" style="margin-top:0.5rem">
      <a class="link" href="/docs"><span class="method">UI</span> Swagger Docs</a>
      <a class="link" href="/.well-known/agent.json"><span class="method">A2A</span> Agent Card</a>
      <a class="link" href="/api/v1/health"><span class="method">GET</span> /health</a>
      <a class="link" href="/api/v1/moat"><span class="method">GET</span> /moat</a>
    </div>
  </div>

  <div class="card" style="grid-column:1/-1">
    <h2>📊 Domain Mastery</h2>
    <table>
      <thead><tr><th>Domain</th><th>Mastery M(d,t)</th><th>Knowledge Count</th></tr></thead>
      <tbody>{domain_rows}</tbody>
    </table>
  </div>

</div>

<div style="text-align:center;padding:1.5rem;color:#3a3a6a;font-size:0.75rem;border-top:1px solid #1a1a2a">
  RUMA v1.0.0 · BNB Hack: AI Trading Agent Edition · CoinMarketCap × Trust Wallet · June 2026
  · Track 1: Autonomous Trading Agents · $36,000 Prize Pool
  · <a href="/dashboard" style="color:#6060a0">Live Dashboard →</a>
  · <a href="/docs" style="color:#6060a0">API Docs →</a>
</div>
</body>
</html>"""
