FROM python:3.11-slim

WORKDIR /app

# Suppress bytecode + force stdout flushing — critical for container logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps: build tools for faiss-cpu, web3, numpy, psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl git gcc g++ libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Rust toolchain (for sovereign_entropy ChaCha20 extension)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | \
    sh -s -- -y --default-toolchain stable --profile minimal
ENV PATH="/root/.cargo/bin:${PATH}"

# Install Python dependencies first (cached layer — only invalidated if requirements.txt changes)
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install maturin && \
    pip install -r requirements.txt

# Build Rust entropy module (falls back gracefully to Python SHA256 if build fails)
COPY entropy/ entropy/
RUN cd entropy && \
    maturin build --release 2>/dev/null && \
    pip install target/wheels/*.whl 2>/dev/null || \
    echo "[INFO] Rust entropy module not built — using Python fallback (safe)"

# Copy application source (after deps for better layer caching)
COPY . .

# Create persistent data directories used by FAISS and moat accumulator
RUN mkdir -p data memory/faiss_index logs

# Non-root user — never run as root in production
RUN groupadd -r sovereign && useradd -r -g sovereign sovereign && \
    chown -R sovereign:sovereign /app
USER sovereign

# Render injects PORT; local Docker defaults to 8000
ENV PORT=8000 \
    PHAROS_NETWORK=testnet \
    TRADING_ENABLED=true

EXPOSE ${PORT}

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/v1/health || exit 1

# Workers=1 optimal for async FastAPI (uses asyncio event loop, not threads)
# --log-level info gives structured access logs in Render/Docker log streams
CMD uvicorn api.main:app \
    --host 0.0.0.0 \
    --port ${PORT} \
    --workers 1 \
    --log-level info \
    --access-log
