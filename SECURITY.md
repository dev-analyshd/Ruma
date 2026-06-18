# SOVEREIGN-Ω Security Model
## CertiK Skill Scanner Compliance Documentation

> CertiK Skill Scanner is the official security standard for the Pharos AI Agent Hackathon.
> This document maps every security property to its implementation.

---

## 1. Private Key Management

**Rule**: Keys are loaded from environment variables only. Never hardcoded. Never logged.

| Location | Implementation |
|----------|---------------|
| `pharos/chain_client.py` | `os.getenv("AGENT_PRIVATE_KEY") or os.getenv("DEPLOYER_PRIVATE_KEY")` |
| `api/routes/x402.py` | `_get_agent_address()` never logs the key, only the derived address |
| `.env.example` | Template with comment: "Set in Replit Secrets, NOT here" |
| `.gitignore` | `.env` is ignored |

**Simulation mode**: When no private key is set, the agent runs in simulation mode and logs a clear warning. No fake signing occurs.

---

## 2. Action Gate — No Override, No Bypass

**Rule**: The coherence gate cannot be bypassed by any code path.

```python
# core/action_gate.py
class ActionGate:
    def is_open(self, psi: float, delta: float) -> bool:
        return psi >= delta   # Pure math. No admin flag. No environment override.
```

Every action, trade, and social post goes through `ActionGate.is_open()`. There is no `force=True`, no admin bypass, no environment variable that disables it.

**Trading** requires `psi >= 1.25 * delta` — 25% higher bar than general actions.
**Social posts** require `psi >= 0.70` — enforced in `social/social_gate.py`.

---

## 3. x402 Payment Security

### Nonce Expiry (Replay Attack Prevention)
```python
# api/routes/x402.py
expires_at = int(time.time()) + 300  # 5-minute window
```
Payment nonces expire after 5 minutes. Replaying a nonce after expiry returns `verified=False`.

### Nonce Binding
Each nonce is bound to a specific `(tx_hash, skill_id)` pair. A nonce for `trade_evaluate` cannot be used to invoke `reasoning_chain`.

### On-Chain Verification (Production)
When `AGENT_PRIVATE_KEY` is set, payment is verified on Pharos chain via `w3.eth.get_transaction_receipt()`. Receipt status must be `1` (success).

---

## 4. Adversarial Input Protection

### Inferential Plane Contradiction Trap
```python
# planes/inferential.py
# Contradiction between reasoning chains → I(t) = 0.0 (hard zero)
```
If reasoning chains contradict each other, the Inferential plane returns 0.0, pulling the total Ψ below any reasonable threshold. Adversarial prompt injection designed to get contradictory chains fires an automatic hard stop.

### World Model Anomaly Detection
```python
# planes/world_model.py
# z-score > 3.0 → W(t) = 0.0 immediately
```
Environmental signals with z-score > 3σ from baseline immediately zero the World Model plane.

### Shannon Entropy Grounding
The Perceptual plane P(t) is computed from Shannon entropy of input signal channels — computed in **Rust** using ChaCha20 CSPRNG, not Python's `random`. This makes the score cryptographically grounded and resistant to deliberate manipulation of "noisy" inputs.

---

## 5. Silence Protocol

```python
# core/silence_protocol.py
# SILENCE is logged before any other action in that cycle (Rule 4)
```

The Silence Protocol is not a fallback — it is the first action in every cycle that falls below threshold. Silence episodes are logged to PostgreSQL with full plane breakdown for auditability.

**Higher silence rate = more discriminating agent** — not a bug.

---

## 6. Risk Manager Hard Limits

```python
# trading/risk_manager.py
MAX_POSITION_PCT = 0.02    # 2% of vault per trade — hard limit
DAILY_LOSS_LIMIT_PCT = 0.06  # 6% daily loss → trading paused until next day
```

These limits are enforced by `RiskManager.passes_risk_check()` before any trade execution. The trading decision engine calls this check and refuses to proceed if it fails.

---

## 7. Memory Integrity

```python
# memory/faiss_store.py
# Persists to disk on every write — no in-memory-only state
```

FAISS index is persisted to `data/faiss_index.bin` on every `add()` call. Moat state is persisted to `data/moat_state.json` on every `accumulate()` call. No state is lost on restart.

---

## 8. Moat Monotonicity

```python
# core/moat_accumulator.py
def accumulate(self, eta_i: float, rho_i: float, cycle_id: str = ""):
    if eta_i <= 0 or rho_i <= 0:
        return  # Guard: only positive contributions allowed
    increment = math.log(1 + eta_i * rho_i)  # Always ≥ 0
    self.log_lambda = old_log + increment      # Λ never decreases
```

The moat accumulator operates in log-space for numerical stability. Negative inputs are rejected at the guard. The moat is monotonically non-decreasing by mathematical construction.

---

## 9. API Security Properties

| Property | Implementation |
|----------|---------------|
| CORS | `allow_origins=["*"]` — public API by design for A2A |
| Input validation | Pydantic v2 with type enforcement on all endpoints |
| SQL injection | `asyncpg` parameterized queries only |
| Environment secrets | All secrets via `os.getenv()`, never in code |
| Error messages | Exceptions caught; internal details not exposed to callers |

---

## 10. Dependency Security

| Layer | Package | Note |
|-------|---------|------|
| Cryptography | `sovereign_entropy` (Rust) | ChaCha20, SHA-256, HMAC-SHA256 — no Python crypto |
| Web3 | `web3>=7.0.0`, `eth-account>=0.13.0` | Standard, audited libraries |
| API | `fastapi>=0.115.0`, `pydantic>=2.10.0` | Current stable versions |
| DB | `asyncpg>=0.30.0` | Async PostgreSQL, parameterized only |

---

## CertiK Skill Scanner Checklist

- [x] No hardcoded private keys
- [x] No hardcoded sensitive values in source
- [x] Action gate is non-bypassable
- [x] Payment nonces expire and are skill-bound
- [x] Replay attack prevention (5-minute nonce window)
- [x] Input sanitization via Pydantic
- [x] Risk limits enforced before execution
- [x] Monotonic moat — no manipulation possible
- [x] Silence protocol enforced before action
- [x] Cryptographic entropy (Rust, not Python random)
- [x] On-chain verification for payments (when key available)
- [x] No admin overrides or debug flags that weaken security
