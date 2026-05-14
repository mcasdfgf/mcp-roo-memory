# Coding Teacher: Memory Rules
1. Search for related concepts before teaching → call MCP tool `vector_search`
2. Save ALL teaching decisions (what approach was explained) → call MCP tool `graph_add_node(type=decision)`
3. If code was written as example → call MCP tool `graph_add_node(type=fileref, tags: ["example"])`
4. Note student's understanding level → call MCP tool `graph_add_node(type=note, tags: ["teaching"])`
