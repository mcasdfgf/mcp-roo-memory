# Cortex Boot Procedure
ALWAYS execute on first tool call of any task:
1. Call MCP tool `desktop_open()` — get hot/cold/archive context (workspace_id auto-detected)
2. Review `hot_nodes` for current focus context
3. If task relates to cold concept → call MCP tool `vector_search(query="<concept>")`
4. If past work exists → call MCP tool `desktop_history(limit=10)`

**Note:** workspace_id is auto-detected (env → CWD → "default"). Do NOT pass it explicitly unless you need a specific workspace different from the current project.
