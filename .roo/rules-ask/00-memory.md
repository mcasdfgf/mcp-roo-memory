# Ask: Memory Rules
1. Deep search before answering → call MCP tool `vector_search` + MCP tool `graph_get_node` + MCP tool `desktop_focus`
2. If answer reveals new insight → call MCP tool `graph_add_node(type=fact, tags: ["insight"])`
3. If question is about existing code → trace fileref nodes via MCP tool `graph_traverse(type=contains)`
