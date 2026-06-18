# Deploying SOVEREIGN-Ω on Render

## Prerequisites
- GitHub repo pushed: `https://github.com/dev-analyshd/sovereign-omega`
- Render account: https://render.com (free Starter plan works)

---

## Option A — One-Click Blueprint (recommended)

1. Go to https://dashboard.render.com/blueprints
2. Click **New Blueprint Instance**
3. Connect your GitHub repo (`dev-analyshd/sovereign-omega`)
4. Render auto-detects `render.yaml` and configures everything
5. Set the 2 secret environment variables (see below)
6. Click **Apply** — build starts (~5–8 min)

---

## Option B — Manual Web Service

1. https://dashboard.render.com → **New → Web Service**
2. Connect repo: `dev-analyshd/sovereign-omega`
3. Settings:
   - **Runtime**: Docker
   - **Dockerfile path**: `./Dockerfile`
   - **Region**: Oregon (or closest to you)
   - **Plan**: Starter ($7/mo) or Free (spins down after 15min inactivity)
4. Add environment variables (table below)
5. **Create Web Service**

---

## Environment Variables

Set these in Render Dashboard → your service → **Environment**:

### Required (set manually — never commit these)

| Variable | Value | Notes |
|---|---|---|
| `DEPLOYER_PRIVATE_KEY` | `0x...` your wallet key | Pharos testnet deployer — keep secret |

### Pre-filled by render.yaml (verify these)

| Variable | Value |
|---|---|
| `PHAROS_NETWORK` | `testnet` |
| `PHAROS_REGISTRY` | `0x6EAB7862385329BdaaD32f2b9587a66E768018Ba` |
| `PHAROS_VAULT` | `0xAbC106D943a6Aff91A0B29f4a77E4009323d7A66` |
| `PHAROS_LEARNER` | `0x799006C9b1e946d3A2909b81F3C3087D71bB9F84` |
| `AGENT_OPERATOR_ADDRESS` | `0xdBbf66CAD621dA3Ec186D18b29a135d2A5d42d20` |
| `TRADING_ENABLED` | `true` |

### Optional (set if you want them)

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Real Claude LLM reasoning — without it, agent runs in mock mode (Ψ ~0.82) |
| `DATABASE_URL` | PostgreSQL connection string — e.g. from Render PostgreSQL add-on |
| `DISCORD_BOT_TOKEN` | Discord social bot |
| `TELEGRAM_BOT_TOKEN` | Telegram social bot |
| `TWITTER_API_KEY` + secrets | Twitter/X social bot |

---

## Build Timeline

| Step | Time |
|---|---|
| Pulling Docker base image | ~1 min |
| Installing Python deps | ~3–4 min |
| Building Rust entropy module | ~1–2 min |
| Container start + health check | ~30 sec |
| **Total** | **~6–8 min** |

---

## After Deploy

Your permanent URL will be:
```
https://sovereign-omega.onrender.com
```
(or similar — Render generates it)

Test it:
```bash
# Health check
curl https://sovereign-omega.onrender.com/api/v1/health

# Free skill
curl -X POST https://sovereign-omega.onrender.com/api/v1/skills/invoke/coherence_evaluate \
  -H "Content-Type: application/json" \
  -d '{"skill_id":"coherence_evaluate","input":{"query":"Test from Render"}}'

# Agent card
curl https://sovereign-omega.onrender.com/.well-known/agent.json

# Live dashboard
open https://sovereign-omega.onrender.com/dashboard
```

---

## Update URLs After Deploy

Once you have your Render URL, run this to update all docs:

```bash
OLD="3b0fe305-de58-4f8c-9b1f-6ac365d51561-00-2cx3283bumy11.kirk.replit.dev"
NEW="sovereign-omega.onrender.com"   # ← your actual Render URL

sed -i "s|https://${OLD}|https://${NEW}|g" SKILLS.md SKILL.md HACKATHON.md README.md
sed -i "s|https://${OLD}|https://${NEW}|g" examples/standalone_skill_usage.py
sed -i "s|https://${OLD}|https://${NEW}|g" examples/langchain_orchestrator.py
sed -i "s|https://${OLD}|https://${NEW}|g" examples/pharos_skill_composition.py

git add -A && git commit -m "docs: update live URL to Render deployment" && git push
```

---

## Render Free Plan Notes

- Free plan **spins down after 15 minutes of inactivity** — first request after idle takes ~30s to boot
- For the hackathon, **Starter plan ($7/mo)** keeps it always-on — worth it for judging period (June 18–22)
- Add a Render PostgreSQL add-on if you want persistent data across restarts

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Build fails on `faiss-cpu` | Ensure `build-essential` is in Dockerfile apt packages ✅ |
| Rust entropy module fails | Fine — Python fallback is used automatically ✅ |
| `DEPLOYER_PRIVATE_KEY` missing | Set it manually in Render → Environment tab |
| Health check fails | Check logs — usually a missing env var |
| `PORT` mismatch | Render injects `$PORT` — CMD uses `${PORT}` ✅ |
