"""Cortex — factory that assembles all components."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .config import config
from .db import DatabaseManager
from .desktop import DesktopManager
from .graph import GraphManager
from .vector import VectorManager


class Cortex:
    """Factory — assembles all mcp-cortex components."""

    def __init__(
        self,
        db_path: str | Path | None = None,
        qdrant_host: str | None = None,
        qdrant_port: int | None = None,
    ):
        self.db = DatabaseManager(db_path or config.db_path)
        self.vector = VectorManager(
            host=qdrant_host or config.qdrant_host,
            port=qdrant_port or config.qdrant_port,
            collection=config.collection_name,
        )
        self.graph = GraphManager(self.db, self.vector)
        self.desktop = DesktopManager(self.db, self.graph)

    def start(self) -> None:
        """Start all components."""
        self.db.connect()
        self.vector.ensure_collection()

    def stop(self) -> None:
        """Stop all components."""
        self.db.close()

    @property
    def is_ready(self) -> bool:
        """All components are ready for operation."""
        return self.db.conn is not None and self.vector.is_ready()
