FROM python:3.11-slim-bookworm AS builder

RUN pip install --no-cache-dir \
    mcp>=1.0.0 \
    qdrant-client>=1.9.0 \
    fastembed>=0.3.0 \
    pydantic>=2.0.0 \
    pydantic-settings>=2.0.0

FROM python:3.11-slim-bookworm

# System dependencies for fastembed (ONNX runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r cortex && useradd -r -g cortex cortex

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Pre-download the embedding model during build
# This avoids runtime download failures and slow first-call latency
ENV FASTEMBED_CACHE=/model-cache
RUN mkdir -p /model-cache && \
    python3 -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')" && \
    rm -rf /root/.cache/huggingface

WORKDIR /workspace

COPY src/ ./src/
COPY pyproject.toml .

RUN mkdir -p /data && chown -R cortex:cortex /workspace /data /model-cache

USER cortex

# Keep container alive as daemon — MCP server runs via `docker exec`
CMD ["tail", "-f", "/dev/null"]
