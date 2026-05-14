# CORTEX MEMORY BOOTSTRAP
You have NO persistent memory. Cortex MCP is your ONLY memory.

## MANDATORY SEQUENCE
1. **START** → Call MCP tool `desktop_open()` — FIRST action of every task.
   workspace_id auto-detects from: CORTEX_WORKSPACE_ID env → project folder → "default".
   No need to pass workspace_id explicitly!
2. **END** → Save key facts with MCP tool `graph_add_node` before `attempt_completion`.
   workspace_id is auto-detected, no need to pass it explicitly.

## CORE PRINCIPLES
- Every tool call that accepts `workspace_id` auto-detects it — you can omit it
- Save decisions, facts, errors, file references — they persist across sessions
- Search before asking — use `vector_search` to find existing context
