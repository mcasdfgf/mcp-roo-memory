"""Centralized configuration for mcp-cortex using pydantic-settings."""

from __future__ import annotations

import os
from pathlib import Path
from typing import ClassVar

from pydantic_settings import BaseSettings


class CortexConfig(BaseSettings):
    """Configuration loaded from environment variables or .env file.

    All values can be overridden via environment variables with the
    ``CORTEX_`` prefix, e.g. ``CORTEX_DB_PATH``, ``CORTEX_QDRANT_HOST``.
    """

    # ── SQLite ────────────────────────────────────
    db_path: str = "cortex.db"

    # ── Qdrant ────────────────────────────────────
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_timeout: int = 30
    collection_name: str = "cortex_memory"

    # ── Embedding ─────────────────────────────────
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_size: int = 384

    # ── Desktop / Viewport ────────────────────────
    archive_days_threshold: int = 7
    desktop_hot_limit: int = 5
    desktop_history_limit: int = 10

    # ── Graph walk ────────────────────────────────
    walk_relation_types: list[str] = [
        "sequel_to",
        "derives_from",
        "leads_to",
    ]

    # ── Workspace ─────────────────────────────────
    # Default workspace ID used when none is explicitly provided.
    # Resolution order: explicit arg > CORTEX_WORKSPACE_ID env > cwd basename > "default"
    workspace_id: str = ""

    model_config: ClassVar[dict] = {
        "env_prefix": "CORTEX_",
        "env_file": ".env",
        "extra": "ignore",
    }


def resolve_workspace_id(explicit: str | None = None) -> str:
    """Resolve workspace ID with fallback chain:

    1. Explicit argument (from tool call)
    2. CORTEX_WORKSPACE_ID environment variable
    3. Current working directory basename (project folder name)
    4. Fallback 'default'
    """
    if explicit and explicit.strip():
        return explicit.strip()

    env_ws = os.environ.get("CORTEX_WORKSPACE_ID", "").strip()
    if env_ws:
        return env_ws

    try:
        cwd = Path.cwd().name
        if cwd and cwd != "/":
            return cwd
    except Exception:
        pass

    return "default"


# Singleton instance — import this everywhere
config = CortexConfig()