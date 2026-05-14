# Orchestrator: Memory Rules
1. ALWAYS call MCP tool `desktop_open` first — must see full context
2. Decompose complex tasks → call MCP tool `graph_decompose` with all subtask descriptions
3. Save ALL planning decisions → call MCP tool `graph_add_node(type=decision, tags: ["plan"])`
4. Before subtask creation → search for existing similar work via MCP tool `vector_search`
5. Track subtask progress → update nodes as subtasks complete
