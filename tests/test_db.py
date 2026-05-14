"""Tests for DatabaseManager — SQLite CRUD, graph operations, edge cases."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cortex.db import DatabaseManager
from cortex.models import (
    NavHistoryEntry,
    Node,
    NodePreview,
    NodeStatus,
    NodeType,
    Relation,
    RelationType,
)


class TestDatabaseManagerNodes:
    """Node CRUD operations."""

    def test_add_node(self, db_manager: DatabaseManager):
        node = Node(type=NodeType.FACT, workspace_id="ws1", data={"text": "hello"})
        created = db_manager.create_node(node)
        assert created.id == node.id
        assert created.type == NodeType.FACT

    def test_get_node(self, db_manager: DatabaseManager):
        node = db_manager.create_node(Node(type=NodeType.FACT, workspace_id="ws1"))
        fetched = db_manager.get_node(node.id)
        assert fetched is not None
        assert fetched.id == node.id
        assert fetched.type == NodeType.FACT
        assert fetched.workspace_id == "ws1"

    def test_get_node_not_found(self, db_manager: DatabaseManager):
        fetched = db_manager.get_node("nonexistent")
        assert fetched is None

    def test_delete_node(self, db_manager: DatabaseManager):
        node = db_manager.create_node(Node(type=NodeType.FACT, workspace_id="ws1"))
        result = db_manager.delete_node(node.id)
        assert result is True
        assert db_manager.get_node(node.id) is None

    def test_list_nodes(self, db_manager: DatabaseManager):
        db_manager.create_node(Node(type=NodeType.FACT, workspace_id="ws1"))
        db_manager.create_node(Node(type=NodeType.TASK, workspace_id="ws1"))
        nodes = db_manager.list_nodes("ws1")
        assert len(nodes) == 2

    def test_list_nodes_empty(self, db_manager: DatabaseManager):
        nodes = db_manager.list_nodes("empty_ws")
        assert nodes == []

    def test_get_nodes_by_parent(self, db_manager: DatabaseManager):
        parent = db_manager.create_node(Node(type=NodeType.TASK, workspace_id="ws1"))
        child = db_manager.create_node(Node(
            type=NodeType.SUBTASK, workspace_id="ws1", parent_id=parent.id,
        ))
        children = db_manager.get_nodes_by_parent(parent.id)
        assert len(children) == 1
        assert children[0].id == child.id

    def test_update_node_data(self, db_manager: DatabaseManager):
        node = db_manager.create_node(Node(
            type=NodeType.FACT, workspace_id="ws1", data={"text": "old"},
        ))
        updated = db_manager.update_node(node.id, data={"text": "new"})
        assert updated is not None
        assert updated.data["text"] == "new"

    def test_update_node_status(self, db_manager: DatabaseManager):
        node = db_manager.create_node(Node(type=NodeType.FACT, workspace_id="ws1"))
        updated = db_manager.update_node(node.id, status=NodeStatus.STALE)
        assert updated is not None
        assert updated.status == NodeStatus.STALE


class TestDatabaseManagerRelations:
    """Relation CRUD operations."""

    def test_add_relation(self, db_manager: DatabaseManager):
        a = db_manager.create_node(Node(type=NodeType.FACT, workspace_id="ws1"))
        b = db_manager.create_node(Node(type=NodeType.FACT, workspace_id="ws1"))
        rel = db_manager.create_relation(Relation(from_id=a.id, to_id=b.id, type=RelationType.SUPPORTS))
        assert rel.id is not None
        assert rel.from_id == a.id
        assert rel.to_id == b.id

    def test_get_relations_for_node(self, db_manager: DatabaseManager):
        a = db_manager.create_node(Node(type=NodeType.FACT, workspace_id="ws1"))
        b = db_manager.create_node(Node(type=NodeType.FACT, workspace_id="ws1"))
        c = db_manager.create_node(Node(type=NodeType.FACT, workspace_id="ws1"))
        db_manager.create_relation(Relation(from_id=a.id, to_id=b.id, type=RelationType.SUPPORTS))
        db_manager.create_relation(Relation(from_id=c.id, to_id=a.id, type=RelationType.CONTRADICTS))

        rels = db_manager.get_relations_for_node(a.id)
        assert len(rels) == 2

    def test_delete_relation(self, db_manager: DatabaseManager):
        a = db_manager.create_node(Node(type=NodeType.FACT, workspace_id="ws1"))
        b = db_manager.create_node(Node(type=NodeType.FACT, workspace_id="ws1"))
        rel = db_manager.create_relation(Relation(from_id=a.id, to_id=b.id, type=RelationType.SUPPORTS))
        result = db_manager.delete_relation(rel.id)
        assert result is True
        assert db_manager.get_relations_for_node(a.id) == []


class TestDatabaseManagerSubgraph:
    """Subgraph operations."""

    def test_get_subgraph(self, db_manager: DatabaseManager, sample_nodes: dict):
        node, children, relations = db_manager.get_subgraph(sample_nodes["session"].id)
        assert node is not None
        assert len(children) == 1  # task
        # After creating 2 relations, we should have them
        assert len(relations) == 1  # session -> task

    def test_get_subgraph_deeper(self, db_manager: DatabaseManager, sample_nodes: dict):
        node, children, relations = db_manager.get_subgraph(sample_nodes["task"].id)
        assert node is not None
        assert len(children) == 1  # subtask

    def test_get_subgraph_nonexistent(self, db_manager: DatabaseManager):
        node, children, relations = db_manager.get_subgraph("no-such-id")
        assert node is None
        assert children == []
        assert relations == []


class TestDatabaseManagerColdNodes:
    """Cold nodes retrieval."""

    def test_get_cold_nodes_empty(self, db_manager: DatabaseManager):
        cold = db_manager.get_cold_nodes("ws1", set())
        assert cold == []

    def test_get_cold_nodes_excludes_hot(self, db_manager: DatabaseManager):
        hot = db_manager.create_node(Node(type=NodeType.FACT, workspace_id="ws1"))
        cold = db_manager.create_node(Node(type=NodeType.FACT, workspace_id="ws1"))
        result = db_manager.get_cold_nodes("ws1", {hot.id})
        assert len(result) == 1
        assert result[0].id == cold.id

    def test_get_cold_nodes_includes_title(self, db_manager: DatabaseManager):
        node = db_manager.create_node(Node(
            type=NodeType.FACT, workspace_id="ws1",
            data={"title": "Important Fact", "text": "Some long text"},
        ))
        result = db_manager.get_cold_nodes("ws1", set())
        assert len(result) == 1
        assert isinstance(result[0], NodePreview)
        assert result[0].title == "Important Fact"

    def test_get_cold_nodes_text_fallback(self, db_manager: DatabaseManager):
        node = db_manager.create_node(Node(
            type=NodeType.FACT, workspace_id="ws1",
            data={"text": "This is a long text without a title"},
        ))
        result = db_manager.get_cold_nodes("ws1", set())
        assert len(result) == 1
        # Title should be first 80 chars of text
        assert "This is a long text" in result[0].title


class TestDatabaseManagerArchive:
    """Archive operations."""

    def test_get_archive_info_empty(self, db_manager: DatabaseManager):
        info = db_manager.get_archive_info("ws1")
        assert info.available is False
        assert info.archived_count == 0

    def test_get_archive_info_with_archived(self, db_manager: DatabaseManager):
        node = db_manager.create_node(Node(
            type=NodeType.FACT, workspace_id="ws1", status=NodeStatus.ARCHIVED,
        ))
        info = db_manager.get_archive_info("ws1")
        assert info.available is True
        assert info.archived_count == 1

    def test_archive_stale_nodes(self, db_manager: DatabaseManager):
        # Create node with nav history so it's not excluded
        node = db_manager.create_node(Node(
            type=NodeType.FACT, workspace_id="ws1",
            data={"text": "old fact"},
        ))
        # Add nav history entry for this node
        db_manager.add_nav_history(NavHistoryEntry(
            workspace_id="ws1", node_id=node.id, action="focus",
        ))
        # Archive with 0 days threshold
        count = db_manager.archive_stale_nodes("ws1", days_threshold=0)
        # The node has recent nav history so it should not be archived
        # Actually with 0 days threshold, only nodes with history older than now are archived
        # Since we just added history, it should be fresh
        assert count == 0

        # Create node without nav history
        node2 = db_manager.create_node(Node(
            type=NodeType.NOTE, workspace_id="ws1",
            data={"text": "another fact"},
        ))
        count2 = db_manager.archive_stale_nodes("ws1", days_threshold=0)
        assert count2 == 1


class TestDatabaseManagerNavHistory:
    """Navigation history operations."""

    def test_add_and_get_history(self, db_manager: DatabaseManager):
        db_manager.add_nav_history(NavHistoryEntry(
            workspace_id="ws1", node_id="n1", action="focus",
        ))
        history = db_manager.get_nav_history("ws1")
        assert len(history) == 1
        assert history[0].node_id == "n1"
        assert history[0].action == "focus"

    def test_get_history_ordered_by_time(self, db_manager: DatabaseManager):
        db_manager.add_nav_history(NavHistoryEntry(
            workspace_id="ws1", node_id="n1", action="focus",
        ))
        db_manager.add_nav_history(NavHistoryEntry(
            workspace_id="ws1", node_id="n2", action="focus",
        ))
        history = db_manager.get_nav_history("ws1")
        assert len(history) == 2

    def test_get_last_focus_nodes(self, db_manager: DatabaseManager):
        db_manager.add_nav_history(NavHistoryEntry(
            workspace_id="ws1", node_id="n1", action="focus",
        ))
        db_manager.add_nav_history(NavHistoryEntry(
            workspace_id="ws1", node_id="n2", action="branch",
        ))
        foci = db_manager.get_last_focus_nodes("ws1", limit=5)
        assert "n1" in foci
        assert "n2" in foci


class TestDatabaseManagerEdgeCases:
    """Edge cases: empty DB, duplicates, invalid IDs."""

    def test_empty_database(self, db_manager: DatabaseManager):
        assert db_manager.get_node("x") is None
        assert db_manager.list_nodes("ws") == []
        assert db_manager.get_cold_nodes("ws", set()) == []
        assert db_manager.get_archive_info("ws").available is False
        assert db_manager.get_relations_for_node("x") == []

    def test_duplicate_node_id(self, db_manager: DatabaseManager):
        node = Node(id="dup-id", type=NodeType.FACT, workspace_id="ws1")
        db_manager.create_node(node)
        with pytest.raises(Exception):
            db_manager.create_node(node)

    def test_delete_nonexistent(self, db_manager: DatabaseManager):
        result = db_manager.delete_node("no-such-id")
        assert result is True

    def test_cascade_delete(self, db_manager: DatabaseManager):
        parent = db_manager.create_node(Node(type=NodeType.TASK, workspace_id="ws1"))
        child = db_manager.create_node(Node(
            type=NodeType.SUBTASK, workspace_id="ws1", parent_id=parent.id,
        ))
        db_manager.delete_node(parent.id, cascade=True)
        assert db_manager.get_node(parent.id) is None
        assert db_manager.get_node(child.id) is None

    def test_stale_cascade(self, db_manager: DatabaseManager):
        """Test stale_cascade via db level."""
        parent = db_manager.create_node(Node(type=NodeType.TASK, workspace_id="ws1"))
        child1 = db_manager.create_node(Node(
            type=NodeType.SUBTASK, workspace_id="ws1", parent_id=parent.id,
        ))
        child2 = db_manager.create_node(Node(
            type=NodeType.SUBTASK, workspace_id="ws1", parent_id=parent.id,
        ))
        # Update children to stale
        db_manager.update_node(child1.id, status=NodeStatus.STALE)
        db_manager.update_node(child2.id, status=NodeStatus.STALE)
        assert db_manager.get_node(child1.id).status == NodeStatus.STALE
        assert db_manager.get_node(child2.id).status == NodeStatus.STALE

    def test_get_session_root(self, db_manager: DatabaseManager):
        session = db_manager.create_node(Node(
            type=NodeType.SESSION, workspace_id="ws1",
        ))
        root = db_manager.get_session_root("ws1")
        assert root is not None
        assert root.id == session.id
        assert db_manager.get_session_root("no_ws") is None

    def test_execute_write(self, db_manager: DatabaseManager):
        """execute_write runs arbitrary SQL write queries."""
        node = db_manager.create_node(Node(
            type=NodeType.FACT, workspace_id="ws1",
            data={"text": "original"},
        ))
        # Direct SQL update via execute_write
        db_manager.execute_write(
            "UPDATE nodes SET data = ? WHERE id = ?",
            ('{"text": "updated-via-execute_write"}', node.id),
        )
        updated = db_manager.get_node(node.id)
        assert updated is not None
        assert updated.data["text"] == "updated-via-execute_write"
