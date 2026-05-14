# ADR-003: Qdrant for Vectors

**Status**: Accepted
**Date**: 2026-05-12
**Context**: [CONCEPT.md](../CONCEPT.md#2-system-architecture)

---

## Problem

The fractal graph memory system needs a vector index for semantic search. The vector store must support multi-layer indexing (Entity + Chunk + Fact), hybrid search (dense + sparse), and tight integration with the graph.

## Options

### Option A: ChromaDB (rejected)

Lightweight, embedded vector database.

**Pros**:
- Simple API
- Embedded (no separate server)
- Good for small projects

**Cons**:
- No sparse vector support
- Limited filtering capabilities
- Less mature than Qdrant
- Performance degrades at scale

### Option B: Pinecone (rejected)

Managed vector database as a service.

**Pros**:
- Fully managed
- Good performance
- Built-in hybrid search

**Cons**:
- External service dependency
- Cost per operation
- No local development without internet
- Data privacy concerns

### Option C: Qdrant (selected)

Open-source vector database with dense + sparse vector support.

**Pros**:
- Open source, self-hosted
- Dense + sparse vectors (hybrid search)
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
2. **Hybrid search** — dense + sparse vectors for better semantic search
3. **Payload filtering** — filter by workspace_id, node type, status
4. **Multi-layer indexing** — separate collections or payload-based filtering for Entity/Chunk/Fact
5. **Self-hosted** — no external API dependencies

### Implementation

```python
# Qdrant collection configuration
vectors_config = {
    "size": 384,  # paraphrase-multilingual-MiniLM-L12-v2
    "distance": "Cosine",
    "on_disk": True,
}
sparse_vectors_config = {
    "index": {"on_disk": True},
}

# Payload for each vector
payload = {
    "workspace_id": str,
    "node_id": str,
    "node_type": str,  # entity|fact|decision|chunk|...
    "status": str,     # active|stale|archived
    "text": str,       # original text for context
}
```

## Consequences

- Qdrant runs as a Docker container — adds deployment complexity
- Vectors are indexed by node_id — graph and vector stores are linked
- Payload filtering enables workspace isolation
- Sparse vectors enable keyword-style search alongside semantic search

## Related ADRs

- [ADR-001](ADR-001-fractal-memory.md): Custom MCP server for fractal memory
- [ADR-002](ADR-002-sqlite-graph.md): SQLite + JSON for graph
- [ADR-004](ADR-004-fastembed.md): fastembed for embeddings