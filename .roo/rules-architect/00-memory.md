# Architect: Memory Rules
1. Save ALL architecture decisions → Call MCP tool `graph_add_node(type=decision, tags: ["arch", "decision"])`
2. Save ALL design patterns discovered → Call MCP tool `graph_add_node(type=pattern, tags: ["arch"])`
3. Link decisions to requirements → Call MCP tool `graph_add_relation(type=implements)`
4. On completion: ensure all key architectural nodes are focused (call MCP tool `desktop_focus`)
5. ALWAYS call MCP tool `desktop_open` first — architecture work depends on full context
