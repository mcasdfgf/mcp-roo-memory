# Debug: Memory Rules
1. Search for similar past errors → call MCP tool `vector_search(query="<error symptoms>")`
2. Save EVERY bug found → call MCP tool `graph_add_node(type=error, data={title, text: "cause + fix"}, tags: ["bug"])`
3. Link bug to the file where it was found → call MCP tool `graph_add_relation(type=indexes)`
4. If a workaround was used → call MCP tool `graph_add_node(type=note, tags: ["workaround"])`
5. On fix: add relation `resolves` from fix-node to error-node via MCP tool `graph_add_relation`
