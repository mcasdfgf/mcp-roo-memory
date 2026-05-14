# Cortex Trigger Rules

## File creation trigger
IF you create a new file AND the file is meaningful (not temp/config):
THEN before continuing: Call MCP tool `graph_add_node(type=fileref, data={path, description})` + Call MCP tool `graph_add_relation(from=session, to=fileref, type=contains)`

## Decision change trigger
IF you change an approach/architecture/implementation that was previously decided:
THEN: Call MCP tool `graph_supersede(old_id=<original_decision>, new_data=<new_decision>)`

## Bug fix trigger
IF you fix a bug that was non-trivial (not typo):
THEN: Call MCP tool `graph_add_node(type=error, data={title, text: "root cause + fix"})` + link to affected files

## Task decomposition trigger
IF the task has >3 distinct sub-steps:
THEN: Call MCP tool `graph_decompose(task_id=<current_session>, subtasks=[...])`

**Note:** workspace_id is auto-detected for all tools above. Do NOT pass it explicitly.
