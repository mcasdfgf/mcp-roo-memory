# ADR-001: Custom MCP Server for Fractal Memory

**Status**: Accepted
**Date**: 2026-05-12
**Context**: [CONCEPT.md](../CONCEPT.md)

---

## Problem

To implement fractal graph memory for the Roo agent, a choice must be made
between extending the existing Memory MCP server and creating a custom one.

## Options

### Option A: Extend Existing Memory MCP

**Pros**:
- No need to write from scratch
- Already works in the current configuration
- Has basic CRUD operations

**Cons**:
- Third-party code, no control
- Limited API: no graph traversal, no hybrid search
- No fractality (parent_id, contains)
- No Qdrant integration
- Difficult to add Desktop Manager

### Option B: Custom MCP Server (selected)

**Pros**:
- Full control over architecture
- Fractality out of the box
- Native Qdrant + graph integration
- Desktop Manager with navigation history
- Lightweight (SQLite + JSON, no Neo4j)

**Cons**:
- Must be written from scratch
- Duplicates basic CRUD already present in Memory MCP

## Decision

Create a custom MCP server `mcp-cortex` in Python.

### Rationale

1. **Fractality** — key feature that cannot be added to existing Memory MCP without forking
2. **Hybrid search** — vector + graph requires tight integration of two stores at the server level
3. **Desktop Manager** — navigation with history is a separate component not present in existing solutions
4. **Simplicity** — SQLite + JSON is sufficient for a graph of this size (hundreds to thousands of nodes, not millions)

### Consequences

- Need to implement: GraphManager, VectorManager, DesktopManager, EmbeddingService
- Existing Memory MCP remains for other tasks
- mcp-cortex will be the single source of truth for Roo memory

## Related ADRs

- ADR-002: SQLite + JSON for graph
- ADR-003: Qdrant for vectors
- ADR-004: fastembed for embeddings (built into qdrant-client)