# Contributing to MCP Roo Memory

Thanks for your interest! This is a small project that aims to solve a big problem: giving LLM agents persistent, structured memory.

## Quick Start

```bash
git clone https://github.com/mcasdfgf/mcp-roo-memory.git
cd mcp-roo-memory
python -m venv .venv
source .venv/bin/activate
pip install -e .
pip install pytest pytest-asyncio
```

## Development Guidelines

### Code Style

- All docstrings and comments in **English**
- Type hints required for all functions and methods
- Follow [PEP 8](https://peps.python.org/pep-0008/)
- Use descriptive variable names — code is documentation too

### Architecture

Before diving in, read [`CONCEPT.md`](CONCEPT.md) to understand the fractal graph model.

Key components:

| Component | File | Responsibility |
|-----------|------|---------------|
| Core factory | [`src/cortex/__init__.py`](src/cortex/__init__.py) | Assembles all managers |
| MCP server | [`src/cortex/server.py`](src/cortex/server.py) | 15 tools, 4 resources |
| Graph | [`src/cortex/graph.py`](src/cortex/graph.py) | CRUD, traversal, mutation |
| Database | [`src/cortex/db.py`](src/cortex/db.py) | SQLite operations |
| Vector | [`src/cortex/vector.py`](src/cortex/vector.py) | Qdrant + fastembed |
| Desktop | [`src/cortex/desktop.py`](src/cortex/desktop.py) | Viewport management |

### Testing

- **All tests must pass** before submitting a PR
- Write tests for all new features and bug fixes
- Run the full suite:

```bash
pytest tests/ -v
```

Coverage is checked but not strictly enforced — just don't lower it significantly.

### Documentation

- Update [`README.md`](README.md) if you change the API or add features
- Update [`CONCEPT.md`](CONCEPT.md) if you change the data model
- For significant architectural decisions, add an ADR in [`plans/`](plans/)
- Tag decisions with `ADRNNN` in commit messages

### Commits

- Use conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`
- Reference issues/ADRs: `feat: add graph_walk tool (refs ADR-005)`

## Pull Request Process

1. Fork the repo and create your branch from `main`
2. If you added new functionality, add tests
3. Update documentation if the API changed
4. Ensure the test suite passes
5. Update `CHANGELOG.md` if applicable
6. Open the PR with a clear description

## Questions?

Open an issue. We're friendly.
