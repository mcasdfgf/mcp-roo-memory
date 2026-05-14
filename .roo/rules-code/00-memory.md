# Code: Memory Rules
1. Save ALL created files → Call MCP tool `graph_add_node(type=fileref, tags: ["file", "created"])`
2. Save ALL modified files with change summary → Call MCP tool `graph_add_node(type=fileref, tags: ["file", "modified"])`
3. Save ALL important implementation decisions → Call MCP tool `graph_add_node(type=decision, tags: ["impl"])`
4. Link files to the feature they implement → Call MCP tool `graph_add_relation(type=implements)`
