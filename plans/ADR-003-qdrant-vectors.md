# ADR-003: Qdrant for Vectors

**Status**: Accepted
**Date**: 2026-05-12
**Context**: [CONCEPT.md](../CONCEPT.md#2-system-architecture)

---

## Problem

The fractal graph memory system needs a vector index for semantic search. The vector store must support multi-layer indexing (Entity + Chunk + Fact), payload filtering, and tight integration with the graph.

## Options

### Option A: ChromaDB (rejected)

Lightweight, embedded vector database.

**Pros**:
- Simple API
- Embedded (no separate server)
- Good for small projects

**Cons**:
- Limited filtering capabilities
- Less mature than Qdrant
- Performance degrades at scale

### Option B: Pinecone (rejected)

Managed vector database as a service.

**Pros**:
- Fully managed
- Good performance

**Cons**:
- External service dependency
- Cost per operation
- No local development without internet
- Data privacy concerns

### Option C: Qdrant (selected)

Open-source vector database with dense vector support and rich payload filtering.

**Pros**:
- Open source, self-hosted
- Rich filtering with payload
- Good performance
- Docker deployment
- Active development

**Cons**:
- Requires a running server (Docker)
- More complex setup than ChromaDB
- Resource usage for Docker container

## Decision

Use Qdrant as the vector index.

### Rationale

1. **Already in use** — Qdrant was already part of the project's Docker setup
2. **Payload filtering** — filter by workspace_id, node type, status
3. **Multi-layer indexing** — payload-based filtering for Entity/Chunk/Fact layers
4. **Self-hosted** — no external API dependencies
5. **Dual vector config** — default unnamed vector (for Qdrant admin UI) + named vector `"primary"` (for query_points search)

### Implementation

```python
# Qdrant collection configuration — dual vector setup
vectors_config = {
    "": VectorParams(size=384, distance=Distance.COSINE),       # default (admin UI)
    "primary": VectorParams(size=384, distance=Distance.COSINE), # named (search)
}

# Payload for each vector
payload = {
    "workspace_id": str,
    "node_id": str,
    "node_type": str,  # entity|fact|decision|chunk|...
    "layer": str,      # entity|chunk|fact
    "status": str,     # active|stale|archived
    "text": str,       # original text for context (truncated to 500 chars)
    "tags": str,       # JSON-encoded array
}
```

## Consequences

- Qdrant runs as a Docker container — adds deployment complexity
- Vectors are indexed by node_id — graph and vector stores are linked
- Payload filtering enables workspace isolation
- Embedding is duplicated into both default and named vectors for UI compatibility
- Sparse vectors (BM25-style) are **not used** — search relies on dense cosine similarity only

## Related ADRs

- [ADR-001](ADR-001-fractal-memory.md): Custom MCP server for fractal memory
- [ADR-002](ADR-002-sqlite-graph.md): SQLite + JSON for graph
- [ADR-004](ADR-004-fastembed.md): fastembed for embeddings