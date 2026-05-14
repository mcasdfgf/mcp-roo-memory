# Project Research: Memory Rules
1. Start with full context gathering: call MCP tool `desktop_open` + MCP tool `desktop_history` + MCP tool `vector_search`
2. Save ALL discovered entities → call MCP tool `graph_add_node(type=entity, tags: ["discovered"])`
3. Save ALL architectural discoveries → call MCP tool `graph_add_node(type=fact, tags: ["architecture"])`
4. Link new discoveries to existing context → call MCP tool `graph_add_relation` as appropriate
5. Save research session as note → call MCP tool `graph_add_node(type=note, tags: ["research"])`
