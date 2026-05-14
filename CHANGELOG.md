# Changelog

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