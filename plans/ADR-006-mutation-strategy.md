# ADR-006: Mutation Strategy — Update/Supersedes/Stale-Cascade

**Status**: Accepted
**Date**: 2026-05-12
**Context**: [CONCEPT.md](../CONCEPT.md#6-mutation-strategy)

---

## Problem

During work, Roo constantly reworks decisions, corrects facts,
and changes architecture. A strategy is needed for updating graph nodes
and vectors in Qdrant to ensure:
1. Old information is not presented as current
2. Decision chains are preserved (why it was decided, what was rejected)
3. When a parent changes, child nodes do not remain current

## Options

### Option A: Full Replacement Only (rejected)

Any change → delete old node, create new one.
- Decision history is lost
- Impossible to understand "why it was decided this way"
- Links from other nodes to the old ID are broken

### Option B: Versioning Only (rejected for MVP)

Each change → new node version, old one in history.
- Complex for MVP
- Overkill for simple fixes
- Lots of dead data

### Option C: Three Strategies by Situation (selected)

| Situation | Strategy |
|-----------|----------|
| Fact fix / typo | Update (in-place) |
| Radical decision change | Supersedes (stale + new node) |
| Parent task changed | Stale-cascade (children → stale) |

## Decision

### Strategy A: Update (in-place)

For minor fixes where the node's essence doesn't change:
- `data` is modified, `updated_at` is refreshed
- Vector in Qdrant is re-indexed (delete + upsert by node_id)
- `node_id` stays the same — all relations are preserved

### Strategy B: Supersedes

For radical decision changes:
- Old node: `status: stale` (in SQLite only)
- New node created with `status: active`
- Relation `new → supersedes → old`
- New node is indexed in Qdrant
- Old vector remains in Qdrant with its original payload — it is **not** updated to `stale` in Qdrant (the SQLite graph is the source of truth for status)
- Stale nodes are filtered out in search via the default `status_filter="active"`, but only if their Qdrant payload still has `status=active` — this means the old vector may reappear if the filter is removed

### Strategy C: Stale-Cascade

When a task/decision that other nodes depend on changes:
- Parent node is updated (Update)
- All child nodes (via `parent_id`) get `status: stale`
- The `stale_cascade()` method in [`graph.py`](src/cortex/graph.py) marks direct children as stale
- **Note:** there is no automatic warning on `desktop_focus` — the stale status is visible in the node's `status` field, and Roo must check it explicitly

## Consequences

- Qdrant: stale nodes are filtered or ranked lower in search
- SQLite: `status` field is required for all nodes
- Cascade: updating a parent triggers mass update of children
- A `graph_supersede` tool is needed in the MCP protocol
