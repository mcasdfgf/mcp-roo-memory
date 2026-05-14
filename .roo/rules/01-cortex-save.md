# Cortex Consolidation Procedure
Before `attempt_completion`, execute consolidation:
1. Save outcomes → Call MCP tool `graph_add_node(type=fact|decision|note, parent_id=<current_session>, data={title, text, tags})`
2. If a file was created → Call MCP tool `graph_add_node(type=fileref, data={path, description})`
3. If a decision changed → Call MCP tool `graph_supersede(old_id=<stale>, new_data=<updated>)`
4. Link to session → Call MCP tool `graph_add_relation(from=<session_id>, to=<node_id>, type=contains)`
5. Focus outcome → Call MCP tool `desktop_focus(node_id=<main_outcome>)`

**Minimum viable consolidation** (when you're short on tokens):
At minimum: title + 1-sentence summary as a `fact` node linked to session.

**Note:** workspace_id is auto-detected for all tools above. Do NOT pass it explicitly.
