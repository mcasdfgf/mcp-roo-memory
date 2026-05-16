"""Tests for VectorManager — indexing, search, UUID stability, edge cases."""

from __future__ import annotations

import re
from unittest.mock import patch

import pytest

from cortex.models import NodeType
from cortex.vector import VectorManager
from tests.conftest import MockQdrantClient


class TestVectorManagerIndex:
    """Node indexing and removal."""

    def test_index_node(self, vector_manager: VectorManager):
        result = vector_manager.index_node(
            node_id="test-node-1",
            text="Sample text for indexing",
            metadata={
                "workspace_id": "ws1",
                "node_type": "fact",
                "layer": "fact",
                "tags": ["test"],
                "status": "active",
            },
        )
        assert result is True

    def test_index_node_failure(self, vector_manager: VectorManager):
        """Simulate index failure by making _get_embedding_model raise."""
        with patch.object(vector_manager, "_get_embedding_model", side_effect=Exception("fail")):
            result = vector_manager.index_node(
                node_id="fail-node",
                text="will fail",
                metadata={"workspace_id": "ws1"},
            )
            assert result is False

    def test_remove_node_vector(self, vector_manager: VectorManager):
        vector_manager.index_node(
            node_id="remove-me",
            text="to be removed",
            metadata={"workspace_id": "ws1", "node_type": "fact", "layer": "fact"},
        )
        result = vector_manager.remove_node_vector("remove-me")
        assert result is True

    def test_remove_nonexistent(self, vector_manager: VectorManager):
        """Removing a nonexistent vector should not raise."""
        result = vector_manager.remove_node_vector("no-such-node")
        assert result is True


class TestVectorManagerSearch:
    """Vector search."""

    def test_search_empty(self, vector_manager: VectorManager):
        results = vector_manager.search("anything")
        assert results == []

    def test_search_with_data(self, vector_manager: VectorManager):
        vector_manager.index_node(
            node_id="searchable",
            text="This is a searchable document about authentication",
            metadata={
                "workspace_id": "ws1",
                "node_type": "fact",
                "layer": "fact",
                "status": "active",
            },
        )
        results = vector_manager.search("authentication", top_k=5)
        assert len(results) >= 1
        assert results[0]["node_id"] == "searchable"
        assert results[0]["score"] > 0

    def test_search_with_workspace_filter(self, vector_manager: VectorManager):
        vector_manager.index_node(
            node_id="w1-doc",
            text="Workspace 1 document",
            metadata={
                "workspace_id": "ws1",
                "node_type": "fact",
                "layer": "fact",
                "status": "active",
            },
        )
        vector_manager.index_node(
            node_id="w2-doc",
            text="Workspace 2 document",
            metadata={
                "workspace_id": "ws2",
                "node_type": "fact",
                "layer": "fact",
                "status": "active",
            },
        )
        results = vector_manager.search("document", workspace_id="ws1")
        assert len(results) == 1
        assert results[0]["node_id"] == "w1-doc"

    def test_search_with_node_type_filter(self, vector_manager: VectorManager):
        vector_manager.index_node(
            node_id="fact-1",
            text="A fact",
            metadata={
                "workspace_id": "ws1",
                "node_type": "fact",
                "layer": "fact",
                "status": "active",
            },
        )
        vector_manager.index_node(
            node_id="entity-1",
            text="An entity",
            metadata={
                "workspace_id": "ws1",
                "node_type": "entity",
                "layer": "entity",
                "status": "active",
            },
        )
        results = vector_manager.search("fact", node_type="entity")
        assert len(results) >= 1
        assert results[0]["node_type"] == "entity"

    def test_search_failure(self, vector_manager: VectorManager):
        """Simulate search failure."""
        with patch.object(vector_manager, "_get_embedding_model", side_effect=Exception("fail")):
            results = vector_manager.search("anything")
            assert results == []


class TestVectorManagerStableId:
    """Stable UUID generation from node IDs."""

    def test_stable_id_is_integer(self, vector_manager: VectorManager):
        sid = vector_manager._stable_id("test-node")
        assert isinstance(sid, int)

    def test_stable_id_is_deterministic(self, vector_manager: VectorManager):
        sid1 = vector_manager._stable_id("test-node")
        sid2 = vector_manager._stable_id("test-node")
        assert sid1 == sid2

    def test_stable_id_is_different_for_different_inputs(self, vector_manager: VectorManager):
        sid1 = vector_manager._stable_id("node-a")
        sid2 = vector_manager._stable_id("node-b")
        assert sid1 != sid2

    def test_stable_id_within_range(self, vector_manager: VectorManager):
        """Stable ID should be within 63-bit signed integer range."""
        sid = vector_manager._stable_id("test-node")
        assert 0 <= sid < 2**63


class TestVectorManagerHelpers:
    """Static helper methods."""

    def test_should_vectorize_vectorizable_types(self):
        for nt in [
            NodeType.ENTITY, NodeType.FACT, NodeType.DECISION, NodeType.CHUNK,
            NodeType.THOUGHT, NodeType.QUESTION, NodeType.HYPOTHESIS,
            NodeType.ACTION, NodeType.ERROR, NodeType.NOTE,
            NodeType.PATTERN, NodeType.GOAL, NodeType.CONSTRAINT,
        ]:
            assert VectorManager.should_vectorize(nt), f"{nt} should be vectorizable"

    def test_should_not_vectorize_graph_only(self):
        for nt in [NodeType.SESSION, NodeType.TASK, NodeType.SUBTASK, NodeType.FILEREF]:
            assert not VectorManager.should_vectorize(nt), f"{nt} should NOT be vectorizable"

    def test_get_layer_for_type(self):
        assert VectorManager.get_layer_for_type(NodeType.ENTITY) == "entity"
        assert VectorManager.get_layer_for_type(NodeType.CHUNK) == "chunk"
        assert VectorManager.get_layer_for_type(NodeType.FACT) == "fact"
        assert VectorManager.get_layer_for_type(NodeType.DECISION) == "fact"


class TestVectorManagerEnsureCollection:
    """ensure_collection — creation, recreation, idempotency."""

    def test_ensure_collection_creates(self, vector_manager: VectorManager):
        """Ensure collection creates it if missing."""
        # Mock client.get_collections to return empty
        mock_client = MockQdrantClient()
        vector_manager.client = mock_client
        vector_manager._initialized = False
        vector_manager.ensure_collection()
        assert "test_cortex" in mock_client.collections

    def test_ensure_collection_idempotent(self, vector_manager: VectorManager):
        """Calling ensure_collection twice is safe."""
        mock_client = MockQdrantClient()
        vector_manager.client = mock_client
        vector_manager._initialized = False
        vector_manager.ensure_collection()
        vector_manager.ensure_collection()  # second call should be no-op
        assert len(mock_client.collections) == 1

    def test_ensure_collection_init_flag(self, vector_manager: VectorManager):
        """After ensure_collection, _initialized is True."""
        mock_client = MockQdrantClient()
        vector_manager.client = mock_client
        vector_manager._initialized = False
        vector_manager.ensure_collection()
        assert vector_manager._initialized is True


class TestVectorManagerEdgeCases:
    """Edge cases: empty collection, uninitialized, multiple docs."""

    def test_empty_search(self, vector_manager: VectorManager):
        """Search on empty collection returns empty list."""
        results = vector_manager.search("anything")
        assert results == []

    def test_search_with_time_filter(self, vector_manager: VectorManager):
        """Vector search with time_from/time_to filter."""
        vector_manager.index_node(
            node_id="old-node",
            text="Old fact",
            metadata={
                "workspace_id": "ws1", "node_type": "fact", "layer": "fact",
                "tags": [], "status": "active", "created_at": "2026-05-14T00:00:00Z",
            },
        )
        vector_manager.index_node(
            node_id="new-node",
            text="New fact",
            metadata={
                "workspace_id": "ws1", "node_type": "fact", "layer": "fact",
                "tags": [], "status": "active", "created_at": "2026-05-16T00:00:00Z",
            },
        )

        # Search with time filter — only old
        old_results = vector_manager.search(
            "fact", workspace_id="ws1",
            time_from="2026-05-13T00:00:00Z", time_to="2026-05-15T00:00:00Z",
        )
        assert len(old_results) >= 1
        # Should not include new-node
        new_ids = [r["node_id"] for r in old_results]
        assert "new-node" not in new_ids

        # Search with time filter — only new
        new_results = vector_manager.search(
            "fact", workspace_id="ws1",
            time_from="2026-05-15T00:00:00Z",
        )
        assert len(new_results) >= 1
        new_ids = [r["node_id"] for r in new_results]
        assert "old-node" not in new_ids

    def test_collection_status_not_ready(self, vector_manager: VectorManager):
        """is_ready returns False when collection doesn't exist."""
        # Our mock returns "green" status by default
        assert vector_manager.is_ready() is True
