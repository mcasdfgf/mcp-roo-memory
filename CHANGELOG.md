# Changelog

## [0.2.0] - 2026-05-16

### Added

- **Temporal Layer** — time as a first-class citizen in the graph. [ADR-008](plans/ADR-008-temporal-layer.md)
- **`temporal_walk`** — new MCP tool: chronological graph traversal, returns nodes sorted by `created_at` ASC within optional time range ([`graph.py`](src/cortex/graph.py))
- **`session_timeline`** — new MCP tool: flat timeline of all events (nodes + navigation) in a session ([`desktop.py`](src/cortex/desktop.py))
- **`graph_update_relation`** — new MCP tool: update relation metadata/weight with auto `updated_at` ([`db.py`](src/cortex/db.py))
- **Temporal vector search** — `vector_search()` now accepts `time_from` / `time_to` parameters, filters via Qdrant `DatetimeRange` ([`vector.py`](src/cortex/vector.py))
- **`updated_at` on Relations** — `Relation` model now includes `updated_at` field, auto-set on create and update ([`models.py`](src/cortex/models.py))
- **Deterministic anchor** — `desktop_open` uses `last_focus` + timestamp as deterministic entry point ([`desktop.py`](src/cortex/desktop.py))
- **Temporal indexes** — SQLite indexes on `nodes(workspace_id, created_at)`, `nodes(workspace_id, updated_at)`, `navigation_history(workspace_id, created_at)` ([`db.py`](src/cortex/db.py))
- **`time_range_query()`** — SQLite helper for time-sliced node queries ([`db.py`](src/cortex/db.py))

### Changed

- **README.md** — added temporal tools to overview table, ADR-008 to deep dive
- **CONCEPT.md** — new §5 Temporal Layer, ADR-008 in index, updated MCP Protocol table (18 tools), updated Conclusion
- **Migration**: `ALTER TABLE relations ADD COLUMN updated_at` — backwards-compatible

### Fixed

- Migration logic in `db.py._migrate_v1_temporal()` — adds `updated_at` column to relations if missing, populates from `created_at`

## [0.1.1] - 2026-05-13

### Added

- **CLI argument `--workspace` / `-w`** in [`__main__.py`](src/cortex/__main__.py) — each project can now specify its own workspace ID for memory isolation. Usage: `python -m src.cortex --workspace project-name`.
- **Cross-project search** — `vector_search()` and `graph_search()` without `workspace_id` now search across **all** workspaces (previously always scoped to caller's workspace). Add `workspace_id` parameter to narrow to a single project.
- **`_ws_opt()` helper** in [`server.py`](src/cortex/server.py) — separates write tools (use caller's workspace via `_ws()`) from search tools (optional workspace filter via `_ws_opt()`, `None` = all).

### Changed

- **Workspace resolution split**: write tools (`desktop_open`, `graph_add_node`, `vector_store`) always resolve to caller's workspace. Search tools (`vector_search`, `graph_search`) treat missing `workspace_id` as "search everywhere".

### Fixed

- Serialization bug in [`server.py`](src/cortex/server.py): `str(result)` replaced with `json.dumps()` — caused `JSONDecodeError` in Roo client for list-type results
- Pydantic node serialization in [`graph.py`](src/cortex/graph.py): `get_subgraph()` now returns `model_dump()` instead of raw Node objects
- SQL injection vulnerabilities in db.py and graph.py
- Hash collision in vector.py (migrated to stable UUID)
- Fastembed model caching (lazy singleton)
- Qdrant client timeout configuration
- Replaced print() with proper logging

## [0.1.0] - 2026-05-13

### Added

- Initial release of MCP Roo Memory
- Fractal memory architecture with 17 node types and 22 relation types
- Vector search via Qdrant + fastembed
- Desktop viewport with hot/cold/archive zones
- Mutation strategy with supersede pattern
- 15 MCP tools and 4 MCP resources
- Configuration via pydantic-settings (CORTEX_ env vars)
- 152+ tests with pytest