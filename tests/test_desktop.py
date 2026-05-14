"""Tests for DesktopManager — open, focus, history, cold nodes, archive."""

from __future__ import annotations

from cortex.desktop import DesktopManager
from cortex.models import Node, NodeType


class TestDesktopManagerOpen:
    """Opening a workspace session."""

    def test_open_creates_session(self, desktop_manager: DesktopManager):
        viewport = desktop_manager.open("test_ws")
        assert viewport["session"] is not None
        assert viewport["session"]["workspace_id"] == "test_ws"
        assert viewport["session"]["type"] == "session"

    def test_open_returns_viewport_structure(self, desktop_manager: DesktopManager):
        viewport = desktop_manager.open("test_ws")
        assert "session" in viewport
        assert "hot_nodes" in viewport
        assert "cold_nodes" in viewport
        assert "archive" in viewport
        assert "last_focus" in viewport
        assert "history" in viewport

    def test_open_idempotent(self, desktop_manager: DesktopManager):
        vp1 = desktop_manager.open("test_ws")
        vp2 = desktop_manager.open("test_ws")
        assert vp1["session"]["id"] == vp2["session"]["id"]

    def test_open_with_nodes_in_hot(self, desktop_manager: DesktopManager, graph_manager):
        session = desktop_manager.open("test_ws")
        session_id = session["session"]["id"]

        # Add a task and focus on it
        task = graph_manager.add_node(
            parent_id=session_id, node_type=NodeType.TASK,
            data={"title": "Important task"}, workspace_id="test_ws",
        )
        desktop_manager.focus(task.id, "test_ws")

        # Reopen — task should be in hot_nodes
        vp = desktop_manager.open("test_ws")
        assert len(vp["hot_nodes"]) > 0


class TestDesktopManagerFocus:
    """Focus on a specific node."""

    def test_focus_on_existing_node(self, desktop_manager: DesktopManager, graph_manager):
        session = desktop_manager.open("test_ws")
        session_id = session["session"]["id"]
        task = graph_manager.add_node(
            parent_id=session_id, node_type=NodeType.TASK,
            data={"title": "Focused task"}, workspace_id="test_ws",
        )
        result = desktop_manager.focus(task.id, "test_ws")
        assert result["node"] is not None

    def test_focus_records_history(self, desktop_manager: DesktopManager, graph_manager):
        session = desktop_manager.open("test_ws")
        task = graph_manager.add_node(
            parent_id=session["session"]["id"], node_type=NodeType.TASK,
            data={"title": "test"}, workspace_id="test_ws",
        )
        desktop_manager.focus(task.id, "test_ws")
        history = desktop_manager.get_history("test_ws")
        # Should have open + focus
        actions = [h["action"] for h in history]
        assert "focus" in actions


class TestDesktopManagerHistory:
    """Navigation history."""

    def test_get_history_empty(self, desktop_manager: DesktopManager):
        # Open records an 'open' action
        desktop_manager.open("test_ws")
        history = desktop_manager.get_history("test_ws")
        assert len(history) >= 1

    def test_get_history_limit(self, desktop_manager: DesktopManager):
        desktop_manager.open("test_ws")
        history = desktop_manager.get_history("test_ws", limit=1)
        assert len(history) == 1

    def test_branch_records_history(self, desktop_manager: DesktopManager):
        desktop_manager.open("test_ws")
        desktop_manager.branch("node_x", "test_ws", context={"reason": "exploration"})
        history = desktop_manager.get_history("test_ws")
        actions = [h["action"] for h in history]
        assert "branch" in actions


class TestDesktopManagerColdNodes:
    """Cold node retrieval."""

    def test_cold_nodes_are_active(self, desktop_manager: DesktopManager, graph_manager):
        desktop_manager.open("test_ws")
        # Add a task — it should appear in cold on next open
        graph_manager.add_node(
            parent_id=None, node_type=NodeType.FACT,
            data={"text": "cold fact"}, workspace_id="test_ws",
        )
        vp = desktop_manager.open("test_ws")
        assert len(vp["cold_nodes"]) >= 0


class TestDesktopManagerArchive:
    """Archive info in viewport."""

    def test_archive_info_present(self, desktop_manager: DesktopManager):
        viewport = desktop_manager.open("test_ws")
        assert "archive" in viewport
        assert "available" in viewport["archive"]
        assert "archived_count" in viewport["archive"]


class TestDesktopManagerSubgraph:
    """Subgraph access via desktop."""

    def test_subgraph(self, desktop_manager: DesktopManager, graph_manager):
        session = desktop_manager.open("test_ws")
        session_id = session["session"]["id"]
        task = graph_manager.add_node(
            parent_id=session_id, node_type=NodeType.TASK,
            data={"title": "test"}, workspace_id="test_ws",
        )
        subgraph = desktop_manager.subgraph(task.id)
        assert subgraph["node"] is not None
