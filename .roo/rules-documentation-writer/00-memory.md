# Documentation Writer: Memory Rules
1. Read existing context via MCP tool `vector_search` + MCP tool `graph_get_node` before writing
2. Save ALL documentation decisions → call MCP tool `graph_add_node(type=decision, tags: ["docs"])`
3. Save ALL documented files → call MCP tool `graph_add_node(type=fileref, tags: ["documented"])`
