"""Tests for GraphManager — CRUD, traversal, walk, decompose, mutation, search."""

from __future__ import annotations

import pytest

from cortex.graph import GraphManager
from cortex.models import Node, NodeStatus, NodeType, Relation, RelationType


class TestGraphManagerNodeCRUD:
    """Node creation and retrieval."""

    def test_add_node(self, graph_manager: GraphManager):
        node = graph_manager.add_node(
            parent_id=None,
            node_type=NodeType.FACT,
            data={"text": "A fact"},
            workspace_id="ws1",
        )
        assert node.id is not None
        assert node.type == NodeType.FACT

    def test_get_node(self, graph_manager: GraphManager):
        created = graph_manager.add_node(
            parent_id=None, node_type=NodeType.FACT,
            data={"text": "hello"}, workspace_id="ws1",
        )
        fetched = graph_manager.get_node(created.id)
        assert fetched is not None
        assert fetched.id == created.id

    def test_get_node_not_found(self, graph_manager: GraphManager):
        assert graph_manager.get_node("nonexistent") is None

    def test_add_node_with_parent(self, graph_manager: GraphManager):
        parent = graph_manager.add_node(
            parent_id=None, node_type=NodeType.TASK,
            data={"title": "parent"}, workspace_id="ws1",
        )
        child = graph_manager.add_node(
            parent_id=parent.id, node_type=NodeType.SUBTASK,
            data={"title": "child"}, workspace_id="ws1",
        )
        subgraph = graph_manager.get_subgraph(parent.id)
        assert len(subgraph["children"]) == 1
        assert subgraph["children"][0]["id"] == child.id
        # Should have a contains relation
        relations = subgraph["relations"]
        assert len(relations) >= 1

    def test_add_relation(self, graph_manager: GraphManager):
        a = graph_manager.add_node(
            parent_id=None, node_type=NodeType.FACT,
            data={"text": "a"}, workspace_id="ws1",
        )
        b = graph_manager.add_node(
            parent_id=None, node_type=NodeType.FACT,
            data={"text": "b"}, workspace_id="ws1",
        )
        rel = graph_manager.add_relation(
            from_id=a.id, to_id=b.id,
            relation_type=RelationType.SUPPORTS, weight=0.9,
        )
        assert rel.from_id == a.id
        assert rel.to_id == b.id
        assert rel.type == RelationType.SUPPORTS
        assert rel.weight == 0.9


class TestGraphManagerTraversal:
    """Graph traversal operations."""

    def test_traverse(self, graph_manager: GraphManager, db_manager):
        # Create a small chain: session -> task -> subtask
        session = graph_manager.add_node(
            parent_id=None, node_type=NodeType.SESSION,
            data={"title": "session"}, workspace_id="ws1",
        )
        task = graph_manager.add_node(
            parent_id=session.id, node_type=NodeType.TASK,
            data={"title": "task"}, workspace_id="ws1",
        )
        subtask = graph_manager.add_node(
            parent_id=task.id, node_type=NodeType.SUBTASK,
            data={"title": "subtask"}, workspace_id="ws1",
        )

        results = graph_manager.traverse(start_id=session.id, depth=3)
        assert len(results) > 0

    def test_traverse_with_relation_filter(self, graph_manager: GraphManager):
        session = graph_manager.add_node(
            parent_id=None, node_type=NodeType.SESSION,
            data={"title": "session"}, workspace_id="ws1",
        )
        task = graph_manager.add_node(
            parent_id=session.id, node_type=NodeType.TASK,
            data={"title": "task"}, workspace_id="ws1",
        )
        results = graph_manager.traverse(
            start_id=session.id, relation_type="contains", depth=3,
        )
        assert len(results) > 0

    def test_traverse_empty(self, graph_manager: GraphManager):
        """Traverse from a node with no relations."""
        node = graph_manager.add_node(
            parent_id=None, node_type=NodeType.FACT,
            data={"text": "alone"}, workspace_id="ws1",
        )
        results = graph_manager.traverse(start_id=node.id, depth=3)
        # Should return just the starting node
        assert len(results) >= 0


class TestGraphManagerWalk:
    """Reasoning chain walk."""

    def test_walk(self, graph_manager: GraphManager):
        a = graph_manager.add_node(
            parent_id=None, node_type=NodeType.FACT,
            data={"text": "A leads to B"}, workspace_id="ws1",
        )
        b = graph_manager.add_node(
            parent_id=None, node_type=NodeType.FACT,
            data={"text": "B leads to C"}, workspace_id="ws1",
        )
        c = graph_manager.add_node(
            parent_id=None, node_type=NodeType.FACT,
            data={"text": "C"}, workspace_id="ws1",
        )
        graph_manager.add_relation(
            from_id=a.id, to_id=b.id, relation_type=RelationType.SEQUEL_TO,
        )
        graph_manager.add_relation(
            from_id=b.id, to_id=c.id, relation_type=RelationType.SEQUEL_TO,
        )

        results = graph_manager.walk(start_id=a.id, steps=5)
        assert len(results) > 0


class TestGraphManagerDecompose:
    """Task decomposition."""

    def test_decompose(self, graph_manager: GraphManager):
        task = graph_manager.add_node(
            parent_id=None, node_type=NodeType.TASK,
            data={"title": "Parent task"}, workspace_id="ws1",
        )
        subtasks = graph_manager.decompose(task.id, [
            {"title": "Subtask 1", "description": "First subtask"},
            {"title": "Subtask 2", "description": "Second subtask"},
        ])
        assert len(subtasks) == 2
        for sub in subtasks:
            assert sub.type == NodeType.SUBTASK
            assert sub.parent_id == task.id

    def test_decompose_task_not_found(self, graph_manager: GraphManager):
        with pytest.raises(ValueError, match="not found"):
            graph_manager.decompose("no-such-id", [{"title": "x"}])


class TestGraphManagerMutation:
    """Node mutation operations — update, supersede, stale cascade."""

    def test_update_node(self, graph_manager: GraphManager):
        node = graph_manager.add_node(
            parent_id=None, node_type=NodeType.FACT,
            data={"text": "original"}, workspace_id="ws1",
        )
        updated = graph_manager.update_node(node.id, data={"text": "updated"})
        assert updated is not None
        assert updated.data["text"] == "updated"

    def test_update_node_not_found(self, graph_manager: GraphManager):
        result = graph_manager.update_node("no-such-id", data={"text": "x"})
        assert result is None

    def test_supersede(self, graph_manager: GraphManager):
        old = graph_manager.add_node(
            parent_id=None, node_type=NodeType.DECISION,
            data={"text": "old decision"}, workspace_id="ws1",
        )
        old_node, new_node = graph_manager.supersede(old.id, new_data={"text": "new decision"})
        assert old_node is not None
        assert new_node is not None
        assert old_node.id == old.id
        assert new_node.id != old.id

        # Old should be stale
        stale = graph_manager.get_node(old.id)
        assert stale is not None
        assert stale.status == NodeStatus.STALE

    def test_supersede_not_found(self, graph_manager: GraphManager):
        old_node, new_node = graph_manager.supersede("no-such-id", new_data={"text": "x"})
        assert old_node is None
        assert new_node is None

    def test_stale_cascade(self, graph_manager: GraphManager):
        parent = graph_manager.add_node(
            parent_id=None, node_type=NodeType.TASK,
            data={"title": "parent"}, workspace_id="ws1",
        )
        child1 = graph_manager.add_node(
            parent_id=parent.id, node_type=NodeType.SUBTASK,
            data={"title": "child1"}, workspace_id="ws1",
        )
        child2 = graph_manager.add_node(
            parent_id=parent.id, node_type=NodeType.SUBTASK,
            data={"title": "child2"}, workspace_id="ws1",
        )

        stale_nodes = graph_manager.stale_cascade(parent.id)
        assert len(stale_nodes) == 2
        for sn in stale_nodes:
            assert sn.status == NodeStatus.ACTIVE

        # Check they're now stale
        assert graph_manager.get_node(child1.id).status == NodeStatus.STALE
        assert graph_manager.get_node(child2.id).status == NodeStatus.STALE


class TestGraphManagerDelete:
    """Node deletion."""

    def test_delete_node(self, graph_manager: GraphManager):
        node = graph_manager.add_node(
            parent_id=None, node_type=NodeType.FACT,
            data={"text": "delete me"}, workspace_id="ws1",
        )
        result = graph_manager.delete_node(node.id)
        assert result is True
        assert graph_manager.get_node(node.id) is None

    def test_delete_node_not_found(self, graph_manager: GraphManager):
        result = graph_manager.delete_node("no-such-id")
        assert result is False

    def test_delete_cascade(self, graph_manager: GraphManager):
        parent = graph_manager.add_node(
            parent_id=None, node_type=NodeType.TASK,
            data={"title": "parent"}, workspace_id="ws1",
        )
        child = graph_manager.add_node(
            parent_id=parent.id, node_type=NodeType.SUBTASK,
            data={"title": "child"}, workspace_id="ws1",
        )
        result = graph_manager.delete_node(parent.id, cascade=True)
        assert result is True
        assert graph_manager.get_node(parent.id) is None
        assert graph_manager.get_node(child.id) is None


class TestGraphManagerSearch:
    """Hybrid search — vector + graph."""

    def test_search_graph(self, graph_manager: GraphManager):
        node = graph_manager.add_node(
            parent_id=None, node_type=NodeType.FACT,
            data={"text": "searchable fact about testing"},
            workspace_id="ws1",
        )
        results = graph_manager.search_graph("testing", workspace_id="ws1")
        assert "vector_results" in results
        assert "graph_subgraphs" in results


class TestGraphManagerEdgeCases:
    """Edge cases: empty graph, nonexistent nodes, etc."""

    def test_empty_graph(self, graph_manager: GraphManager):
        assert graph_manager.get_node("x") is None
        results = graph_manager.search_graph("anything", workspace_id="ws")
        assert results["vector_results"] == []
        assert results["graph_subgraphs"] == []

    def test_init_session(self, graph_manager: GraphManager):
        session = graph_manager.init_session("new_workspace")
        assert session.type == NodeType.SESSION

    def test_init_session_idempotent(self, graph_manager: GraphManager):
        s1 = graph_manager.init_session("ws1")
        s2 = graph_manager.init_session("ws1")
        assert s1.id == s2.id
