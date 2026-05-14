"""Shared fixtures for mcp-cortex tests — all external services mocked."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cortex.config import CortexConfig
from cortex.db import DatabaseManager
from cortex.desktop import DesktopManager
from cortex.graph import GraphManager
from cortex.models import (
    Node,
    NodePreview,
    NodeStatus,
    NodeType,
    Relation,
    RelationType,
)
from cortex.vector import VectorManager


# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _patch_config_env():
    """Override config to use safe defaults for testing."""
    with patch.object(CortexConfig, "model_config", {"env_prefix": "CORTEX_", "extra": "ignore"}):
        yield


# ──────────────────────────────────────────────
# Database
# ──────────────────────────────────────────────


@pytest.fixture
def db_manager():
    """DatabaseManager connected to an in-memory SQLite database."""
    mgr = DatabaseManager(":memory:")
    mgr.connect()
    yield mgr
    mgr.close()


# ──────────────────────────────────────────────
# Qdrant mock
# ──────────────────────────────────────────────


class MockQdrantClient:
    """Fake QdrantClient for testing — stores points in a dict."""

    def __init__(self, *args, **kwargs):
        self.collections: dict = {}
        self._points: dict[str, dict] = {}  # collection_name -> {point_id: payload}
        self._collection_configs: dict = {}
        self._next_collection_id = 1

    def get_collections(self):
        class MockCollections:
            def __init__(self, cols):
                self.collections = cols
        items = []
        for name in self.collections:
            c = MagicMock()
            c.name = name
            items.append(c)
        return MockCollections(items)

    def get_collection(self, collection_name: str):
        """Return a fake collection info."""
        info = MagicMock()
        info.status = "green"
        config = MagicMock()
        params = MagicMock()
        params.vectors = {
            "": MagicMock(size=384),
            "primary": MagicMock(size=384),
        }
        config.params = params
        info.config = config
        return info

    def create_collection(self, collection_name: str, **kwargs):
        self.collections[collection_name] = kwargs
        self._points[collection_name] = {}

    def delete_collection(self, collection_name: str):
        self.collections.pop(collection_name, None)
        self._points.pop(collection_name, None)

    def upsert(self, collection_name: str, points: list[dict]):
        if collection_name not in self._points:
            self._points[collection_name] = {}
        for point in points:
            pid = point["id"]
            self._points[collection_name][pid] = point

    def query_points(self, collection_name: str, query, **kwargs):
        class QueryResult:
            def __init__(self, pts):
                self.points = pts
        results = []
        pts = self._points.get(collection_name, {})

        # Extract filters from query_filter if provided
        query_filter = kwargs.get("query_filter", None)
        filter_workspace_id = None
        filter_node_type = None
        if query_filter:
            must = getattr(query_filter, "must", []) or []
            for cond in must:
                key = getattr(cond, "key", None)
                match = getattr(cond, "match", None)
                if match:
                    val = getattr(match, "value", None)
                    if key == "workspace_id":
                        filter_workspace_id = val
                    elif key == "node_type":
                        filter_node_type = val

        for pid, point in pts.items():
            payload = point.get("payload", {})
            # Apply filters
            if filter_workspace_id and payload.get("workspace_id") != filter_workspace_id:
                continue
            if filter_node_type and payload.get("node_type") != filter_node_type:
                continue
            results.append(
                MagicMock(
                    id=pid,
                    score=0.95,
                    payload=payload,
                )
            )
        return QueryResult(results[: kwargs.get("limit", 10)])

    def delete(self, collection_name: str, points_selector, **kwargs):
        """Delete points by filter."""
        if collection_name in self._points:
            # Extract node_id from filter
            must = getattr(points_selector, "must", []) or []
            node_id = None
            for cond in must:
                match = getattr(cond, "match", None)
                if match and getattr(match, "value", None):
                    node_id = match.value
            if node_id:
                to_remove = []
                for pid, point in self._points[collection_name].items():
                    if point.get("payload", {}).get("node_id") == node_id:
                        to_remove.append(pid)
                for pid in to_remove:
                    del self._points[collection_name][pid]


@pytest.fixture
def mock_qdrant_client():
    """Mock QdrantClient instance."""
    return MockQdrantClient()


@pytest.fixture
def mock_embedding_model():
    """Mock for fastembed TextEmbedding — returns fresh iterable per call."""
    model = MagicMock()
    # Use side_effect so each call returns a fresh list
    model.embed.side_effect = lambda *args, **kwargs: iter([[0.1] * 384])
    return model


# ──────────────────────────────────────────────
# Vector manager
# ──────────────────────────────────────────────


@pytest.fixture
def vector_manager(mock_embedding_model):
    """VectorManager with mocked QdrantClient and embedding model."""
    with patch("cortex.vector.QdrantClient", new_callable=lambda: MockQdrantClient):
        with patch("cortex.vector.VectorManager._get_embedding_model", return_value=mock_embedding_model):
            from cortex.vector import VectorManager as VM
            mgr = VM(host="localhost", port=6333, collection="test_cortex")
            # Override client with our mock
            mgr.client = MockQdrantClient()
            mgr._initialized = True
            yield mgr


# ──────────────────────────────────────────────
# Graph manager
# ──────────────────────────────────────────────


@pytest.fixture
def graph_manager(db_manager, vector_manager):
    """GraphManager with real DB and mocked vector."""
    mgr = GraphManager(db=db_manager, vector=vector_manager)
    return mgr


# ──────────────────────────────────────────────
# Desktop manager
# ──────────────────────────────────────────────


@pytest.fixture
def desktop_manager(db_manager, graph_manager):
    """DesktopManager with real DB and mocked graph."""
    mgr = DesktopManager(db=db_manager, graph=graph_manager)
    return mgr


# ──────────────────────────────────────────────
# Cortex (full assembly)
# ──────────────────────────────────────────────


@pytest.fixture
def cortex(db_manager, vector_manager):
    """Full Cortex assembly with real DB and mocked vector."""
    from cortex import Cortex

    cortex = Cortex(db_path=":memory:")
    # Replace DB and vector with our fixtures
    cortex.db = db_manager
    cortex.vector = vector_manager
    cortex.graph = GraphManager(db=db_manager, vector=vector_manager)
    cortex.desktop = DesktopManager(db=db_manager, graph=cortex.graph)
    cortex.db.connect()
    yield cortex


# ──────────────────────────────────────────────
# Sample data helpers
# ──────────────────────────────────────────────


@pytest.fixture
def sample_node(db_manager) -> Node:
    """Create and return a sample node in the database."""
    node = Node(
        type=NodeType.FACT,
        workspace_id="test_workspace",
        data={"text": "Sample fact", "title": "Sample"},
    )
    return db_manager.create_node(node)


@pytest.fixture
def sample_nodes(db_manager) -> dict[str, Node]:
    """Create a small graph: session -> task -> subtask."""
    session = db_manager.create_node(Node(
        type=NodeType.SESSION,
        workspace_id="test_workspace",
        data={"title": "test_workspace"},
    ))
    task = db_manager.create_node(Node(
        type=NodeType.TASK,
        workspace_id="test_workspace",
        parent_id=session.id,
        data={"title": "Test task"},
    ))
    subtask = db_manager.create_node(Node(
        type=NodeType.SUBTASK,
        workspace_id="test_workspace",
        parent_id=task.id,
        data={"title": "Test subtask"},
    ))
    rel1 = db_manager.create_relation(Relation(
        from_id=session.id, to_id=task.id, type=RelationType.CONTAINS,
    ))
    rel2 = db_manager.create_relation(Relation(
        from_id=task.id, to_id=subtask.id, type=RelationType.CONTAINS,
    ))
    return {"session": session, "task": task, "subtask": subtask}
