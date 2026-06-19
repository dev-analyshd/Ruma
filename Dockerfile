FROM python:3.11-slim

WORKDIR /app

# Suppress bytecode + force stdout flushing — critical for container logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps: build tools for web3, numpy, cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl gcc g++ libpq-dev libssl-dev libffi-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies (cached layer — only invalidated if requirements.txt changes)
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application source (after deps for better layer caching)
COPY . .

# Create persistent data directories used by FAISS and moat accumulator
RUN mkdir -p data memory/faiss_index logs

# Non-root user — never run as root in production
RUN groupadd -r sovereign && useradd -r -g sovereign sovereign && \
    chown -R sovereign:sovereign /app
USER sovereign

# Render injects PORT at runtime; default 5000 matches local workflow
ENV PORT=5000 \
    BSC_NETWORK=mainnet \
    TRADING_ENABLED=true \
    TWAK_AUTONOMOUS_MODE=true

EXPOSE ${PORT}

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/v1/health || exit 1

# workers=1 optimal for async FastAPI (asyncio event loop, not threads)
CMD uvicorn api.main:app \
    --host 0.0.0.0 \
    --port ${PORT} \
    --workers 1 \
    --log-level info \
    --access-log
