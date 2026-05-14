"""Integration tests for mcp-cortex — full cycle with real DB and mocked Qdrant."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from cortex.models import NodeType, RelationType


class TestFullCycle:
    """Full integration: session -> task -> decomposition -> facts -> search -> focus -> mutation."""

    def test_full_cycle(self, cortex):
        """Complete workflow test.

        Covers: open, add_node, decompose, add_relation, search, focus,
        supersede, stale_cascade, traverse, walk, history.
        """
        # ── Step 1: Open session ──
        viewport = cortex.desktop.open("test_project")
        assert viewport["session"] is not None
        session_id = viewport["session"]["id"]

        # ── Step 2: Add task ──
        task = cortex.graph.add_node(
            parent_id=session_id,
            node_type=NodeType.TASK,
            data={"title": "Develop authentication module"},
            workspace_id="test_project",
        )
        assert task.id is not None

        # ── Step 3: Decomposition ──
        subtasks = cortex.graph.decompose(task.id, [
            {"title": "Implement JWT", "description": "JWT access + refresh tokens"},
            {"title": "Implement OAuth", "description": "OAuth 2.0 integration"},
        ])
        assert len(subtasks) == 2

        # ── Step 4: Fact (vectorized) ──
        fact = cortex.graph.add_node(
            parent_id=subtasks[0].id,
            node_type=NodeType.FACT,
            data={
                "text": "JWT tokens expire after 24 hours, using RS256",
                "tags": ["jwt", "auth", "security"],
            },
            workspace_id="test_project",
        )
        assert fact.type == NodeType.FACT

        # ── Step 5: Decision (vectorized) ──
        decision = cortex.graph.add_node(
            parent_id=session_id,
            node_type=NodeType.DECISION,
            data={"text": "Using RS256 for JWT signing"},
            workspace_id="test_project",
        )
        assert decision.type == NodeType.DECISION

        # ── Step 6: Relation: fact supports decision ──
        rel = cortex.graph.add_relation(
            from_id=fact.id,
            to_id=decision.id,
            relation_type=RelationType.SUPPORTS,
            weight=0.9,
        )
        assert rel.id is not None
        assert rel.weight == 0.9

        # ── Step 7: Entity (vectorized) ──
        entity = cortex.graph.add_node(
            parent_id=subtasks[0].id,
            node_type=NodeType.ENTITY,
            data={
                "text": "JWT Access Token",
                "title": "JWT Token",
                "tags": ["jwt", "token"],
            },
            workspace_id="test_project",
        )
        assert entity.type == NodeType.ENTITY

        # ── Step 8: Fileref (NOT vectorized) ──
        fileref = cortex.graph.add_node(
            parent_id=subtasks[0].id,
            node_type=NodeType.FILEREF,
            data={
                "path": "src/auth/jwt.py",
                "filetype": "python",
                "description": "JWT implementation",
            },
            workspace_id="test_project",
        )
        assert fileref.type == NodeType.FILEREF

        # ── Step 9: Entity indexes Fileref ──
        cortex.graph.add_relation(
            from_id=entity.id,
            to_id=fileref.id,
            relation_type=RelationType.INDEXES,
        )

        # ── Step 10: Vector search ──
        results = cortex.vector.search(
            "authentication token",
            workspace_id="test_project",
            top_k=5,
        )
        # With mocked embedding, results come from MockQdrantClient
        assert isinstance(results, list)

        # ── Step 11: Subgraph ──
        subgraph = cortex.graph.get_subgraph(subtasks[0].id)
        assert subgraph["node"] is not None
        assert isinstance(subgraph["children"], list)
        assert isinstance(subgraph["relations"], list)

        # ── Step 12: Hybrid search ──
        hybrid = cortex.graph.search_graph("RS256", workspace_id="test_project")
        assert "vector_results" in hybrid
        assert "graph_subgraphs" in hybrid

        # ── Step 13: Desktop focus ──
        focused = cortex.desktop.focus(subtasks[0].id, "test_project")
        assert focused["node"] is not None

        # ── Step 14: Desktop reopen (viewport) ──
        viewport2 = cortex.desktop.open("test_project")
        assert len(viewport2["hot_nodes"]) > 0
        assert isinstance(viewport2["cold_nodes"], list)

        # ── Step 15: Supersedes (mutation B) ──
        old_dec, new_dec = cortex.graph.supersede(
            old_id=decision.id,
            new_data={"text": "Using RS256 with 4096-bit keys", "status": "active"},
        )
        assert old_dec is not None
        assert new_dec is not None
        assert old_dec.id == decision.id
        assert new_dec.id != decision.id

        # ── Step 16: Check stale ──
        old_check = cortex.db.get_node(decision.id)
        assert old_check is not None
        assert old_check.status.value == "stale"

        # ── Step 17: Walk ──
        walk_path = cortex.graph.walk(start_id=fact.id, steps=3)
        assert isinstance(walk_path, list)

        # ── Step 18: Traverse ──
        traversal = cortex.graph.traverse(start_id=task.id, depth=3)
        assert isinstance(traversal, list)

        # ── Step 19: Navigation history ──
        history = cortex.desktop.get_history("test_project")
        assert len(history) > 0

        # ── Step 20: Update node (mutation A) ──
        updated = cortex.graph.update_node(
            node_id=fact.id,
            data={"text": "JWT tokens expire after 1 hour, using RS256"},
        )
        assert updated is not None
        assert "1 hour" in updated.data["text"]

        # ── Step 21: Delete node ──
        deleted = cortex.graph.delete_node(fileref.id)
        assert deleted is True
        assert cortex.graph.get_node(fileref.id) is None

    def test_error_handling(self, cortex):
        """Error paths: nonexistent node, decompose failure."""
        # Getting nonexistent node
        assert cortex.graph.get_node("no-such-id") is None

        # Deleting nonexistent node
        assert cortex.graph.delete_node("no-such-id") is False

        # Decompose nonexistent task
        with pytest.raises(ValueError, match="not found"):
            cortex.graph.decompose("no-such-id", [{"title": "x"}])

        # Supersede nonexistent
        old, new = cortex.graph.supersede("no-such-id", new_data={"text": "x"})
        assert old is None
        assert new is None

    def test_desktop_workflow(self, cortex):
        """Desktop operations: open, branch, history."""
        viewport = cortex.desktop.open("workflow_test")
        session_id = viewport["session"]["id"]

        # Branch
        cortex.desktop.branch(session_id, "workflow_test", {"reason": "test"})

        # History
        history = cortex.desktop.get_history("workflow_test")
        assert len(history) >= 2  # open + branch

        # Subgraph
        subgraph = cortex.desktop.subgraph(session_id)
        assert "node" in subgraph
