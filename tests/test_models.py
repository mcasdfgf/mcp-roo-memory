"""Tests for Pydantic data models — Node, Relation, Viewport, enums."""

from __future__ import annotations

from cortex.models import (
    ArchiveInfo,
    NavHistoryEntry,
    Node,
    NodePreview,
    NodeStatus,
    NodeType,
    Relation,
    RelationType,
    Viewport,
)


class TestNodeType:
    """All 17 node types are defined."""

    def test_vectorized_types(self):
        assert NodeType.ENTITY == "entity"
        assert NodeType.FACT == "fact"
        assert NodeType.DECISION == "decision"
        assert NodeType.CHUNK == "chunk"
        assert NodeType.THOUGHT == "thought"
        assert NodeType.QUESTION == "question"
        assert NodeType.HYPOTHESIS == "hypothesis"
        assert NodeType.ACTION == "action"
        assert NodeType.ERROR == "error"
        assert NodeType.NOTE == "note"
        assert NodeType.PATTERN == "pattern"
        assert NodeType.GOAL == "goal"
        assert NodeType.CONSTRAINT == "constraint"

    def test_graph_only_types(self):
        assert NodeType.SESSION == "session"
        assert NodeType.TASK == "task"
        assert NodeType.SUBTASK == "subtask"
        assert NodeType.FILEREF == "fileref"

    def test_total_count(self):
        assert len(list(NodeType)) == 17


class TestRelationType:
    """All 22 relation types are defined."""

    def test_hierarchical(self):
        assert RelationType.CONTAINS == "contains"
        assert RelationType.DECOMPOSES_TO == "decomposes_to"
        assert RelationType.BELONGS_TO == "belongs_to"

    def test_semantic(self):
        assert RelationType.DERIVES_FROM == "derives_from"
        assert RelationType.SUPPORTS == "supports"
        assert RelationType.CONTRADICTS == "contradicts"
        assert RelationType.RELATED_TO == "related_to"
        assert RelationType.QUESTIONS == "questions"
        assert RelationType.ANSWERS == "answers"

    def test_index(self):
        assert RelationType.INDEXES == "indexes"
        assert RelationType.EXTRACTED_FROM == "extracted_from"
        assert RelationType.REFERENCES == "references"
        assert RelationType.IMPLEMENTS == "implements"
        assert RelationType.RELATES_TO_FILE == "relates_to_file"

    def test_chronological(self):
        assert RelationType.SEQUEL_TO == "sequel_to"
        assert RelationType.SUPERSEDES == "supersedes"
        assert RelationType.LEADS_TO == "leads_to"
        assert RelationType.RESOLVES == "resolves"
        assert RelationType.TRIGGERS == "triggers"

    def test_dependency(self):
        assert RelationType.DEPENDS_ON == "depends_on"
        assert RelationType.BLOCKS == "blocks"
        assert RelationType.CONSTRAINED_BY == "constrained_by"

    def test_total_count(self):
        assert len(list(RelationType)) == 22


class TestNodeStatus:
    """All 3 node statuses are defined."""

    def test_statuses(self):
        assert NodeStatus.ACTIVE == "active"
        assert NodeStatus.STALE == "stale"
        assert NodeStatus.ARCHIVED == "archived"

    def test_total_count(self):
        assert len(list(NodeStatus)) == 3


class TestNode:
    """Node model: creation, serialization, deserialization."""

    def test_create_minimal(self):
        node = Node(type=NodeType.FACT, workspace_id="ws1")
        assert node.type == NodeType.FACT
        assert node.workspace_id == "ws1"
        assert node.id is not None
        assert node.status == NodeStatus.ACTIVE
        assert node.data == {}
        assert node.parent_id is None

    def test_create_with_all_fields(self):
        node = Node(
            id="test-id-123",
            type=NodeType.DECISION,
            workspace_id="ws1",
            parent_id="parent-123",
            data={"text": "Important decision"},
            status=NodeStatus.STALE,
        )
        assert node.id == "test-id-123"
        assert node.type == NodeType.DECISION
        assert node.parent_id == "parent-123"
        assert node.data["text"] == "Important decision"
        assert node.status == NodeStatus.STALE

    def test_serialization(self):
        node = Node(type=NodeType.FACT, workspace_id="ws1", data={"text": "hello"})
        dumped = node.model_dump()
        assert dumped["type"] == "fact"
        assert dumped["workspace_id"] == "ws1"
        assert dumped["data"]["text"] == "hello"
        assert "id" in dumped
        assert "created_at" in dumped

    def test_deserialization(self):
        original = Node(type=NodeType.FACT, workspace_id="ws1", data={"text": "hello"})
        data = original.model_dump()
        restored = Node(**data)
        assert restored.id == original.id
        assert restored.type == original.type
        assert restored.data == original.data
        assert restored.status == original.status


class TestRelation:
    """Relation model: creation, validation."""

    def test_create_minimal(self):
        rel = Relation(from_id="a", to_id="b", type=RelationType.CONTAINS)
        assert rel.from_id == "a"
        assert rel.to_id == "b"
        assert rel.type == RelationType.CONTAINS
        assert rel.weight == 1.0
        assert rel.id is not None
        assert rel.data == {}

    def test_create_with_weight(self):
        rel = Relation(from_id="a", to_id="b", type=RelationType.SUPPORTS, weight=0.8)
        assert rel.weight == 0.8

    def test_serialization(self):
        rel = Relation(from_id="a", to_id="b", type=RelationType.DEPENDS_ON)
        dumped = rel.model_dump()
        assert dumped["from_id"] == "a"
        assert dumped["to_id"] == "b"
        assert dumped["type"] == "depends_on"


class TestNodePreview:
    """NodePreview model."""

    def test_create(self):
        preview = NodePreview(id="123", type="fact", title="Hello")
        assert preview.id == "123"
        assert preview.type == "fact"
        assert preview.title == "Hello"
        assert preview.status == "active"
        assert preview.children_count == 0

    def test_serialization(self):
        preview = NodePreview(id="123", type="task", title="Task", status="stale", children_count=3)
        dumped = preview.model_dump()
        assert dumped["children_count"] == 3
        assert dumped["status"] == "stale"


class TestViewport:
    """Viewport model."""

    def test_create_empty(self):
        vp = Viewport()
        assert vp.session is None
        assert vp.hot_nodes == []
        assert vp.cold_nodes == []
        assert vp.archive is not None
        assert vp.last_focus is None
        assert vp.history == []

    def test_create_with_data(self):
        session = Node(type=NodeType.SESSION, workspace_id="ws1")
        hot = [Node(type=NodeType.FACT, workspace_id="ws1")]
        cold = [NodePreview(id="cold-1", type="fact", title="Cold")]
        vp = Viewport(session=session, hot_nodes=hot, cold_nodes=cold, last_focus="focus-1")
        assert vp.session is not None
        assert len(vp.hot_nodes) == 1
        assert len(vp.cold_nodes) == 1
        assert vp.last_focus == "focus-1"


class TestRelationTemporal:
    """Relation temporal fields."""

    def test_relation_updated_at_defaults_to_now(self):
        rel = Relation(from_id="a", to_id="b", type=RelationType.SUPPORTS)
        assert rel.updated_at is not None
        assert rel.updated_at >= rel.created_at

    def test_relation_updated_at_explicit(self):
        rel = Relation(from_id="a", to_id="b", type=RelationType.SUPPORTS, updated_at="2026-05-16T00:00:00Z")
        assert rel.updated_at == "2026-05-16T00:00:00Z"


class TestNavHistoryEntry:
    """NavHistoryEntry model."""

    def test_create(self):
        entry = NavHistoryEntry(workspace_id="ws1", node_id="n1", action="focus")
        assert entry.workspace_id == "ws1"
        assert entry.node_id == "n1"
        assert entry.action == "focus"
        assert entry.context == {}


class TestArchiveInfo:
    """ArchiveInfo model."""

    def test_default(self):
        info = ArchiveInfo()
        assert info.available is False
        assert info.archived_count == 0
        assert info.oldest is None

    def test_with_data(self):
        info = ArchiveInfo(available=True, archived_count=5, oldest="2024-01-01")
        assert info.available is True
        assert info.archived_count == 5
        assert info.oldest == "2024-01-01"
