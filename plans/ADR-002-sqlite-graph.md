# ADR-002: SQLite + JSON for Graph Instead of Neo4j/Cayley

**Status**: Accepted
**Date**: 2026-05-12
**Context**: [CONCEPT.md](../CONCEPT.md#3-data-model)

---

## Problem

The fractal graph memory system needs a storage backend for nodes and relations. The options range from full-featured graph databases (Neo4j, Cayley) to lightweight embedded solutions (SQLite).

## Options

### Option A: Neo4j (rejected)

Full graph database with ACID, Cypher query language, and mature ecosystem.

**Pros**:
- Native graph traversal
- Rich query language (Cypher)
- Production-ready

**Cons**:
- Heavy dependency (Java runtime, separate server)
- Overkill for hundreds to thousands of nodes
- Complex Docker setup
- No built-in vector integration

### Option B: Cayley (rejected)

Open-source graph database in Go.

**Pros**:
- Lighter than Neo4j
- Supports multiple store backends
- GraphQL-inspired query language

**Cons**:
- Less mature ecosystem
- Still requires a separate process
- Limited JSON support
- Community is less active

### Option C: SQLite + JSON (selected)

Use SQLite as the graph store with JSON blobs for flexible node data.

**Pros**:
- Zero dependencies (stdlib)
- Embedded — no separate process
- JSON columns for flexible metadata
- ACID transactions
- Fast enough for our scale (hundreds to thousands of nodes)
- Easy backup (single file)

**Cons**:
- Graph traversal requires recursive CTEs (less expressive than Cypher)
- No built-in graph algorithms
- Must implement graph operations manually

## Decision

Use SQLite with JSON columns for graph storage.

### Rationale

1. **Simplicity** — SQLite is in Python stdlib, no external dependencies
2. **Scale-appropriate** — our graph is small (hundreds to thousands of nodes), SQLite handles this easily
3. **Portability** — single file, easy to backup, copy, or version
4. **JSON flexibility** — node data is schema-less, different node types have different fields
5. **Recursive CTEs** — sufficient for graph traversal at our scale

### Implementation

```sql
-- Nodes table
CREATE TABLE nodes (
    id          TEXT PRIMARY KEY,
    type        TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    parent_id   TEXT,
    data        JSON NOT NULL DEFAULT '{}',
    status      TEXT NOT NULL DEFAULT 'active',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Relations table
CREATE TABLE relations (
    id          TEXT PRIMARY KEY,
    from_id     TEXT NOT NULL REFERENCES nodes(id),
    to_id       TEXT NOT NULL REFERENCES nodes(id),
    type        TEXT NOT NULL,
    weight      REAL DEFAULT 1.0,
    data        JSON NOT NULL DEFAULT '{}',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Consequences

- Graph traversal is done via recursive CTEs — less expressive but sufficient
- No built-in graph algorithms (shortest path, centrality) — not needed for MVP
- JSON data means no schema enforcement at DB level — validated in application layer
- Single-file storage makes multi-process access tricky — use WAL mode

## Related ADRs

- [ADR-001](ADR-001-fractal-memory.md): Custom MCP server for fractal memory
- [ADR-003](ADR-003-qdrant-vectors.md): Qdrant for vectors
- [ADR-004](ADR-004-fastembed.md): fastembed for embeddings