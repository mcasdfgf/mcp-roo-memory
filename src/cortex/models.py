"""Data models for mcp-cortex — nodes, relations, types."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Node types
# ──────────────────────────────────────────────


class NodeType(str, Enum):
    """13 node types for the mcp-cortex graph."""

    # Vectorized (Qdrant)
    ENTITY = "entity"
    FACT = "fact"
    DECISION = "decision"
    CHUNK = "chunk"
    THOUGHT = "thought"
    QUESTION = "question"
    HYPOTHESIS = "hypothesis"
    ACTION = "action"
    ERROR = "error"
    NOTE = "note"
    PATTERN = "pattern"
    GOAL = "goal"
    CONSTRAINT = "constraint"

    # Graph only (SQLite)
    SESSION = "session"
    TASK = "task"
    SUBTASK = "subtask"
    FILEREF = "fileref"


# ──────────────────────────────────────────────
# Relation types
# ──────────────────────────────────────────────


class RelationType(str, Enum):
    """22 relation types for the mcp-cortex graph."""

    # Hierarchical
    CONTAINS = "contains"
    DECOMPOSES_TO = "decomposes_to"
    BELONGS_TO = "belongs_to"

    # Semantic
    DERIVES_FROM = "derives_from"
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    RELATED_TO = "related_to"
    QUESTIONS = "questions"
    ANSWERS = "answers"

    # Index
    INDEXES = "indexes"
    EXTRACTED_FROM = "extracted_from"
    REFERENCES = "references"
    IMPLEMENTS = "implements"
    RELATES_TO_FILE = "relates_to_file"

    # Chronological
    SEQUEL_TO = "sequel_to"
    SUPERSEDES = "supersedes"
    LEADS_TO = "leads_to"
    RESOLVES = "resolves"
    TRIGGERS = "triggers"

    # Dependency
    DEPENDS_ON = "depends_on"
    BLOCKS = "blocks"
    CONSTRAINED_BY = "constrained_by"


# ──────────────────────────────────────────────
# Node statuses
# ──────────────────────────────────────────────


class NodeStatus(str, Enum):
    ACTIVE = "active"
    STALE = "stale"
    ARCHIVED = "archived"


# ──────────────────────────────────────────────
# Pydantic models
# ──────────────────────────────────────────────


class Node(BaseModel):
    """A graph node."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: NodeType
    workspace_id: str
    parent_id: Optional[str] = None
    data: dict[str, Any] = Field(default_factory=dict)
    status: NodeStatus = NodeStatus.ACTIVE
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class Relation(BaseModel):
    """A graph edge."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    from_id: str
    to_id: str
    type: RelationType
    weight: float = 1.0
    data: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class NavHistoryEntry(BaseModel):
    """A navigation history record."""

    workspace_id: str
    node_id: str
    action: str  # focus|branch|traverse|search|open
    context: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class Viewport(BaseModel):
    """Desktop Viewport — what the Roo agent sees."""

    session: Optional[Node] = None
    hot_nodes: list[Node] = Field(default_factory=list)
    cold_nodes: list[NodePreview] = Field(default_factory=list)
    archive: ArchiveInfo = Field(default_factory=lambda: ArchiveInfo())
    last_focus: Optional[str] = None
    history: list[NavHistoryEntry] = Field(default_factory=list)


class NodePreview(BaseModel):
    """Short node info (for Cold tier)."""

    id: str
    type: str
    title: str = ""
    status: str = "active"
    children_count: int = 0
    created_at: str = ""


class ArchiveInfo(BaseModel):
    """Information about archived nodes."""

    available: bool = False
    archived_count: int = 0
    oldest: Optional[str] = None
