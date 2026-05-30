# Oh My Coder — Container imajı
# Coolify / Docker / herhangi bir PaaS için hazırdır
# PORT env değişkeni desteklenir (cloud konvansiyonu)

FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

# ===== Runtime =====
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY src/ ./src/
COPY docs/ ./docs/

RUN mkdir -p /app/.omc/state /app/.omc/checkpoints \
    && mkdir -p /root/.omc

ENV PORT=8080
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -fsS "http://localhost:${PORT}/" >/dev/null || exit 1

CMD uvicorn src.web.app:app --host 0.0.0.0 --port ${PORT:-8080}
