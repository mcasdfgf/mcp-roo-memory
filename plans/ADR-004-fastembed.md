# ADR-004: fastembed for Embeddings

**Status**: Accepted
**Date**: 2026-05-12
**Context**: [CONCEPT.md](../CONCEPT.md#2-system-architecture)

---

## Problem

The vector index (Qdrant) needs an embedding model to convert text into vectors. The model must support multilingual text (English + Russian), be lightweight enough for local deployment, and integrate well with the existing stack.

## Options

### Option A: OpenAI Embeddings (rejected)

Use `text-embedding-3-small` or `text-embedding-3-large` via API.

**Pros**:
- State-of-the-art quality
- Multilingual support
- No local compute needed

**Cons**:
- External API dependency
- Cost per token
- Latency for each embedding call
- No offline operation
- Data sent to third party

### Option B: sentence-transformers (rejected)

Use `sentence-transformers` library with local models.

**Pros**:
- Local, no API dependency
- Good model selection
- Well-established library

**Cons**:
- Heavy dependency (PyTorch)
- Slow on CPU
- Complex installation
- Large model downloads

### Option C: fastembed (selected)

Use `fastembed` library from Qdrant team, built into `qdrant-client`.

**Pros**:
- Built into qdrant-client — no extra dependency
- Lightweight (ONNX runtime, not PyTorch)
- Fast on CPU
- Multilingual models available
- Easy to use

**Cons**:
- Smaller model selection than sentence-transformers
- ONNX runtime has its own quirks
- Less flexible for custom models

## Decision

Use `fastembed` with `paraphrase-multilingual-MiniLM-L12-v2` model (384 dimensions).

### Rationale

1. **Zero extra dependency** — fastembed is bundled with qdrant-client
2. **Multilingual** — supports both English and Russian (critical for this project)
3. **Lightweight** — ONNX runtime is much lighter than PyTorch
4. **384 dimensions** — good balance of quality and performance
5. **CPU-friendly** — runs well on CPU, no GPU needed

### Implementation

```python
from qdrant_client import QdrantClient

client = QdrantClient(...)
# fastembed is auto-configured via qdrant-client
# Model: paraphrase-multilingual-MiniLM-L12-v2
# Dimensions: 384
# Distance: Cosine
```

## Consequences

- Embedding quality is good but not state-of-the-art — acceptable for code/documentation search
- 384 dimensions mean smaller vector storage and faster search
- Multilingual support enables searching across English code and Russian documentation
- No external API calls — fully offline operation

## Related ADRs

- [ADR-001](ADR-001-fractal-memory.md): Custom MCP server for fractal memory
- [ADR-002](ADR-002-sqlite-graph.md): SQLite + JSON for graph
- [ADR-003](ADR-003-qdrant-vectors.md): Qdrant for vectors