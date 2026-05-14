# ADR-005: Desktop Viewport — Hot/Cold/Archive for Context Window Control

**Status**: Accepted
**Date**: 2026-05-12
**Context**: [CONCEPT.md](../CONCEPT.md#5-context-window-strategy-desktop-viewport)

---

## Problem

The fractal graph of mcp-cortex grows over time. When starting a new task,
loading the **entire** graph into Roo's context window consumes excessive tokens
and makes work impossible. A lazy loading and archiving mechanism is needed.

## Options

### Option A: Always Load the Full Graph (rejected)

Simple to implement, but:
- With 50+ nodes the context window overflows
- Roo sees tons of irrelevant context
- Impossible to scale for long-lived projects

### Option B: Vector Search Only, No Graph (rejected)

- Loss of structure and navigation
- Cannot walk reasoning chains
- Graph becomes useless

### Option C: Desktop Viewport with Three-Tier Access (selected)

The graph remains complete in SQLite, but Roo only sees the viewport:
- Hot: current focus + direct relations (3-10 nodes)
- Cold: other nodes, titles only (10-100)
- Archive: old tasks, metadata only (100+)

## Decision

Desktop Manager implements lazy loading with three tiers:

1. **Hot nodes**: determined by `navigation_history` (last N focuses)
   and by relations (direct connections of current focus). Always in `desktop_open` response.

2. **Cold nodes**: all other session nodes with `active` status.
   Only titles returned (id, type, title) without full text.
   Full data only via `desktop_focus(node_id)`.

3. **Archive**: nodes with `archived` status (>7 days without focus).
   Not returned in `desktop_open` at all. Only accessible via `vector_search()`.

4. **GC**: triggered on `desktop_open()` — marks nodes without focus
   for more than N days as `archived`.

### Rationale

- `desktop_open` returns ~2-5 KB instead of 50-100 KB
- Graph structure is preserved (cold nodes visible by title)
- Vector search still finds archived nodes
- GC is automatic, no manual intervention needed

## Consequences

- Desktop Manager must be aware of node statuses (active/stale/archived)
- An index on `status` in SQLite is required
- `navigation_history` becomes a critical component — determines hot nodes
- GC does not delete data, only changes status
