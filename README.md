# MCP Roo Memory

**Persistent, graph-based memory for Roo Code via the Model Context Protocol (MCP).**

LLMs have a short memory. Every new conversation starts from scratch — context windows overflow, past decisions fade, and reasoning chains disappear.

**MCP Roo Memory** gives your AI agent a structured, persistent brain:
- **Graph memory** — knowledge is not a flat dump, but a fractal graph of tasks, entities, facts, and decisions
- **Semantic search** — find what matters by meaning, not keywords (50+ languages)
- **Context window control** — hot/cold/archive tiers so you don't drown in tokens
- **Knowledge evolution** — decisions can be superseded, facts can be updated, stale data gets archived

![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue)
![MIT](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-beta-yellow)
![Docker](https://img.shields.io/badge/docker-ready-2496ED)

> **⚠️ Disclaimer**
>
> This is an **experimental project** — a search for form and architecture.
> It works, it has tests, but treat it as a **Proof of Concept (PoC)**.
> The software is provided **"AS IS"**, without any warranty of any kind.
> Use it at your own risk. See [`LICENSE`](LICENSE) for details.

---

## Quick Start

### 🐳 Docker (recommended)

Zero system dependencies — just Docker. Everything runs in containers; no Python, no venv, no pip.

#### 1. Start the stack

```bash
git clone https://github.com/mcasdfgf/mcp-roo-memory.git
cd mcp-roo-memory
docker compose up -d
```

This starts two containers:

| Container | What it does |
|-----------|-------------|
| `cortex-qdrant` | Vector database (port 6333) |
| `cortex-mcp` | Cortex server (idle, waits for MCP connections) |

#### 2. Global MCP configuration

Add Cortex as a **global MCP server** for all your projects. The server is always running in Docker, so any project can connect.

Edit `~/.config/VSCodium/User/globalStorage/rooveterinaryinc.roo-cline/settings/mcp_settings.json` (or the equivalent path for VS Code):

```json
{
  "mcpServers": {
    "cortex": {
      "command": "docker",
      "args": ["exec", "-i", "cortex-mcp", "python3", "-m", "src.cortex"]
    }
  }
}
```

> **VSCode users:** replace `VSCodium` with `Code` in the path above.

#### 3. Project-level configuration (for workspace isolation)

If you want memory **isolated per project**, copy the reference `.roo/` directory into your project:

```bash
cp -r ./mcp-roo-memory/.roo ./your-project/
```

Then edit `.roo/mcp.json` in your project and add `--workspace your-project-name`:

```json
{
  "mcpServers": {
    "cortex": {
      "command": "docker",
      "args": [
        "exec", "-i", "cortex-mcp", "python3",
        "-m", "src.cortex", "--workspace", "your-project-name"
      ],
      "alwaysAllow": ["desktop_open", "graph_add_node", "vector_search", "graph_get_node",
                       "graph_add_relation", "graph_search", "desktop_focus",
                       "desktop_history", "graph_traverse", "graph_walk",
                       "graph_decompose", "graph_update_node", "graph_supersede",
                       "graph_delete_node", "vector_store"]
    }
  }
}
```

Replace `your-project-name` with a unique identifier — `mcp-roo-memory`, `researcher`, `ai-pulse`, etc.

> **How isolation works:**
> - `desktop_open()` and `graph_add_node()` — always write to **your project's** workspace
> - `vector_search()` without `workspace_id` — searches **across all projects** (cross-project recall)
> - `vector_search(workspace_id="project")` — narrows search to **one project**

#### 4. Done

Restart Roo Code. Your agent now has persistent memory — zero system pollution.

---

### 🏠 Native pip (advanced)

If you prefer running without Docker — or you're developing Cortex itself:

```bash
# Requirements: Python 3.11+
git clone https://github.com/mcasdfgf/mcp-roo-memory.git
cd mcp-roo-memory
python -m venv .venv
source .venv/bin/activate
pip install -e .

# Qdrant is still needed:
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant
```

MCP config:

```json
{
  "mcpServers": {
    "cortex": {
      "command": "python",
      "args": ["-m", "src.cortex"],
      "env": {
        "CORTEX_DB_PATH": "/path/to/cortex.db",
        "CORTEX_QDRANT_HOST": "localhost",
        "CORTEX_QDRANT_PORT": "6333"
      }
    }
  }
}
```

---

## Problems This Solves

| Problem | How Cortex solves it |
|---------|---------------------|
| **Flat memory** — facts are stored as unrelated chunks | **Fractal graph** — tasks decompose into subtasks, facts connect to decisions, entities index files |
| **Context window overflow** — everything grows unbounded | **Desktop Viewport** — Hot (always loaded) / Cold (on focus) / Archive (search only) tiers |
| **No navigation** — can't walk a reasoning chain | **Graph traversal** — follow `supersedes`, `derives_from`, `leads_to` relations like a path |
| **Stale facts linger** — old decisions pollute context | **Mutation strategy** — Update (typo fix) / Supersede (approach changed) / Stale-cascade (rework) |
| **Keyword search fails** — "auth implementation" doesn't find "JWT with RS256" | **Semantic vector search** — multilingual embeddings (50+ languages) via Qdrant + fastembed |

---

## Architecture

```
┌──────────────────────────────────────────────┐
│              MCP Client (Roo Code)            │
└──────────────────────┬───────────────────────┘
                        │ stdio (MCP protocol)
┌──────────────────────▼───────────────────────┐
│               CortexServer                     │
│         17 tools · 4 resources                 │
├──────────┬──────────┬──────────┬─────────────┤
│ Graph    │ Vector   │ Desktop  │ Database    │
│ CRUD,    │ Qdrant + │ Hot/     │ SQLite      │
│ traverse,│ fastembed│ Cold/    │ graph +     │
│ walk     │ semantic │ Archive  │ history     │
└──────────┴──────────┴──────────┴─────────────┘
```

**Three layers of intelligence:**
1. **Graph** (SQLite) — who relates to who, what decomposes into what
2. **Vector** (Qdrant) — what does this mean, what's semantically similar
3. **Desktop** (viewport) — what fits in the context window right now

---

## Using as Primary Roo Memory

Make Cortex your agent's default memory system by copying the `.roo/` directory into your project:

```bash
# Copy reference config from this repo
cp -r ./mcp-roo-memory/.roo ./your-project/
```

The `.roo/` directory contains ready-to-use reference configs:

| File / Dir | Purpose |
|------------|---------|
| [`custom_instructions.md`](.roo/custom_instructions.md) | Cortex bootstrap — mandatory sequence, core principles |
| [`mcp.json`](.roo/mcp.json) | Reference MCP server config (edit `--workspace` for your project) |
| [`rules/`](.roo/rules) | Boot, save, templates, triggers — memory lifecycle |
| [`rules-architect/`](.roo/rules-architect) | Memory rules for Architect mode |
| [`rules-ask/`](.roo/rules-ask) | Memory rules for Ask mode |
| [`rules-code/`](.roo/rules-code) | Memory rules for Code mode |
| [`rules-coding-teacher/`](.roo/rules-coding-teacher) | Memory rules for Coding Teacher mode |
| [`rules-debug/`](.roo/rules-debug) | Memory rules for Debug mode |
| [`rules-documentation-writer/`](.roo/rules-documentation-writer) | Memory rules for Documentation Writer mode |
| [`rules-orchestrator/`](.roo/rules-orchestrator) | Memory rules for Orchestrator mode |
| [`rules-project-research/`](.roo/rules-project-research) | Memory rules for Project Research mode |

For deep understanding of the memory model, see [`CONCEPT.md`](CONCEPT.md).

---

## Tools Overview

| Tool | What it does |
|------|-------------|
| `desktop_open` | Open/restore a workspace session |
| `desktop_focus` | Bring a node into hot context |
| `graph_add_node` | Store any knowledge: entity, fact, decision, task... |
| `graph_get_node` | Retrieve a node with its relations |
| `graph_traverse` | Walk the graph from a starting node |
| `graph_decompose` | Break a task into structured subtasks |
| `graph_supersede` | Replace outdated knowledge (keeps history) |
| `vector_search` | Find things by meaning, across 50+ languages |
| `graph_search` | Hybrid: semantic + graph filters |
| *(and 8 more)* | See full list in [`CONCEPT.md §7`](CONCEPT.md#7-mcp-protocol) |

---

## Configuration

All via `CORTEX_*` environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `CORTEX_DB_PATH` | `cortex.db` | SQLite database path |
| `CORTEX_QDRANT_HOST` | `localhost` | Qdrant host |
| `CORTEX_QDRANT_PORT` | `6333` | Qdrant port |
| `CORTEX_QDRANT_TIMEOUT` | `30` | Connection timeout (s) |
| `CORTEX_COLLECTION_NAME` | `cortex_memory` | Qdrant collection name |
| `CORTEX_EMBEDDING_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | Embedding model (50+ languages) |
| `CORTEX_ARCHIVE_DAYS_THRESHOLD` | `7` | Days before auto-archive |
| `CORTEX_DESKTOP_HOT_LIMIT` | `5` | Max hot nodes in viewport |
| `CORTEX_DESKTOP_HISTORY_LIMIT` | `10` | Max history entries |

---

## Project Structure

```
.
├── docker-compose.yml    ← Two services: cortex + qdrant
├── Dockerfile            ← Multi-stage, python:3.11-slim
├── .dockerignore
├── src/cortex/
│   ├── __init__.py    — Cortex factory (component assembly)
│   ├── __main__.py    — MCP server entry point (stdio)
│   ├── config.py      — Configuration (pydantic-settings)
│   ├── db.py          — DatabaseManager (SQLite)
│   ├── desktop.py     — DesktopManager (viewport)
│   ├── graph.py       — GraphManager (CRUD, navigation, mutation)
│   ├── models.py      — Pydantic models (Node, Relation, Viewport)
│   ├── server.py      — MCP server (17 tools, 4 resources)
│   └── vector.py      — VectorManager (Qdrant, embeddings)
└── tests/
```

---

## Deep Dive

| Document | What you'll find |
|----------|-----------------|
| [`CONCEPT.md`](CONCEPT.md) | Full philosophy, data model, node taxonomy (17 types), relation taxonomy (22 types), SQL schema |
| [`ADR-001`](plans/ADR-001-fractal-memory.md) | Fractal memory architecture decision |
| [`ADR-005`](plans/ADR-005-desktop-viewport.md) | Desktop Viewport — context window strategy |
| [`ADR-006`](plans/ADR-006-mutation-strategy.md) | Knowledge evolution: update / supersede / stale |
| [`ADR-007`](plans/ADR-007-regression-pattern.md) | Regression search: meaning → context → files |
| [`CHANGELOG.md`](CHANGELOG.md) | Project release history |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Development guidelines |

---

## Development

```bash
# Native install (inside venv)
pip install -e .
pip install pytest pytest-asyncio

# Run all tests (176+ tests)
pytest tests/ -v

# With coverage
pytest tests/ --cov=src.cortex -v
```

Tests cover every component: models (17), config (19), database (26), graph (19), desktop (14), vector (19), server (19), integration (3).

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for guidelines.

---

## License

MIT © 2026
