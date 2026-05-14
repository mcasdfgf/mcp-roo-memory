"""Desktop Manager — navigation, viewport, history."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from .config import config
from .db import DatabaseManager
from .graph import GraphManager
from .models import (
    NavHistoryEntry,
    Node,
    Viewport,
)


class DesktopManager:
    """Desktop management: viewport, focus, history."""

    def __init__(self, db: DatabaseManager, graph: GraphManager):
        self.db = db
        self.graph = graph

    def open(self, workspace_id: str) -> dict[str, Any]:
        """Open a workspace session and return its Desktop Viewport."""
        # 1. Session initialization
        session = self.graph.init_session(workspace_id)

        # 2. GC — archive stale nodes
        archived_count = self.db.archive_stale_nodes(workspace_id)

        # 3. Last focuses = Hot nodes
        hot_ids = self.db.get_last_focus_nodes(workspace_id, limit=config.desktop_hot_limit)
        hot_nodes = []
        for hid in hot_ids:
            node = self.db.get_node(hid)
            if node and node.status.value == "active":
                hot_nodes.append(node)

        # If no focus history, use the session root
        if not hot_nodes and session:
            hot_nodes = [session]
            hot_ids = {session.id}

        # 4. Cold nodes
        cold_nodes = self.db.get_cold_nodes(workspace_id, hot_ids)

        # 5. Archive info
        archive_info = self.db.get_archive_info(workspace_id)

        # 6. Navigation history
        history = self.db.get_nav_history(workspace_id, limit=config.desktop_history_limit)

        # 7. Record in history
        self.db.add_nav_history(
            NavHistoryEntry(
                workspace_id=workspace_id,
                node_id=session.id,
                action="open",
                context={"archived": archived_count},
            )
        )

        # 8. Build viewport
        viewport = Viewport(
            session=session,
            hot_nodes=hot_nodes,
            cold_nodes=cold_nodes,
            archive=archive_info,
            last_focus=next(iter(hot_ids)) if hot_ids else session.id,
            history=history[:5],
        )

        return viewport.model_dump()

    def focus(self, node_id: str, workspace_id: str) -> dict[str, Any]:
        """Focus on a node — show its subgraph."""
        subgraph = self.graph.get_subgraph(node_id)

        # Record in history
        self.db.add_nav_history(
            NavHistoryEntry(
                workspace_id=workspace_id,
                node_id=node_id,
                action="focus",
                context={},
            )
        )

        return subgraph

    def get_history(
        self, workspace_id: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        """Navigation history."""
        entries = self.db.get_nav_history(workspace_id, limit)
        return [e.model_dump() for e in entries]

    def branch(
        self, from_node_id: str, workspace_id: str, context: Optional[dict] = None
    ) -> None:
        """Create a reasoning branch."""
        self.db.add_nav_history(
            NavHistoryEntry(
                workspace_id=workspace_id,
                node_id=from_node_id,
                action="branch",
                context=context or {},
            )
        )

    def subgraph(self, node_id: str, depth: int = 2) -> dict[str, Any]:
        """Show a node's subgraph."""
        return self.graph.get_subgraph(node_id, depth)
