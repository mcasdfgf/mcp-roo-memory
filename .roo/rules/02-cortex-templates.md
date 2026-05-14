# Cortex Operation Templates

## Save a fact
Call MCP tool `graph_add_node` with:
```json
{
  "parent_id": "<session_id>",
  "type": "fact",
  "data": {
    "title": "<concise title>",
    "text": "<detailed fact description>",
    "tags": ["<tag1>", "<tag2>"]
  }
}
```

## Save a decision
Call MCP tool `graph_add_node` with:
```json
{
  "parent_id": "<session_id>",
  "type": "decision",
  "data": {
    "title": "<decision title>",
    "text": "<rationale and outcome>",
    "tags": ["decision", "<domain>"]
  }
}
```

## Save an error / lesson learned
Call MCP tool `graph_add_node` with:
```json
{
  "parent_id": "<session_id>",
  "type": "error",
  "data": {
    "title": "<error title>",
    "text": "<root cause + solution>",
    "tags": ["error", "lesson"]
  }
}
```

## Save a file reference
Call MCP tool `graph_add_node` with:
```json
{
  "parent_id": "<session_id>",
  "type": "fileref",
  "data": {
    "path": "<relative/file/path>",
    "description": "<what this file does>",
    "tags": ["file"]
  }
}
```

## Search context
```
Step 1: Call MCP tool `vector_search(query="<natural language query>", top_k=10)`
Step 2: Call MCP tool `graph_get_node(node_id=<best_match_id>, depth=2)`
Step 3: Call MCP tool `desktop_focus(node_id=<best_match_id>)`
```

**Note:** workspace_id is auto-detected for all tools. Do NOT pass it explicitly.
