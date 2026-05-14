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
- Old node: `status: stale`
- New node created with `status: active`
- Relation `new → supersedes → old`
- Old vector remains in Qdrant (but with payload.status=stale)
- Stale nodes have lower priority in search results

### Strategy C: Stale-Cascade

When a task/decision that other nodes depend on changes:
- Parent node is updated (Update)
- All child nodes (via `contains` relation) get `status: stale`
- On `desktop_focus` of a child node, Roo sees a warning:
  "Parent task has changed, verify relevance"

## Consequences

- Qdrant: stale nodes are filtered or ranked lower in search
- SQLite: `status` field is required for all nodes
- Cascade: updating a parent triggers mass update of children
- A `graph_supersede` tool is needed in the MCP protocol
