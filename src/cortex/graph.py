"""Graph Manager — high-level graph operations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from .config import config
from .db import DatabaseManager
from .models import (
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
from .vector import VectorManager


class GraphManager:
    """Graph management: creation, navigation, mutation, traversal."""

    def __init__(self, db: DatabaseManager, vector: VectorManager):
        self.db = db
        self.vector = vector

    # ──────────────────────────────────────────────
    # Session initialization
    # ──────────────────────────────────────────────

    def init_session(self, workspace_id: str) -> Node:
        """Create a session root node."""
        existing = self.db.get_session_root(workspace_id)
        if existing:
            return existing

        now = datetime.now(timezone.utc).isoformat()
        session = Node(
            type=NodeType.SESSION,
            workspace_id=workspace_id,
            data={"title": workspace_id, "created": now},
            created_at=now,
            updated_at=now,
        )
        return self.db.create_node(session)

    # ──────────────────────────────────────────────
    # Node creation
    # ──────────────────────────────────────────────

    def add_node(
        self,
        parent_id: Optional[str],
        node_type: NodeType | str,
        data: dict[str, Any],
        workspace_id: str,
    ) -> Node:
        """Add a node to the graph."""
        if isinstance(node_type, str):
            node_type = NodeType(node_type)

        now = datetime.now(timezone.utc).isoformat()
        node = Node(
            type=node_type,
            workspace_id=workspace_id,
            parent_id=parent_id,
            data=data,
            created_at=now,
            updated_at=now,
        )
        node = self.db.create_node(node)

        # Relation contains to parent
        if parent_id:
            self.db.create_relation(
                Relation(
                    from_id=parent_id,
                    to_id=node.id,
                    type=RelationType.CONTAINS,
                    created_at=now,
                )
            )

        # Index in Qdrant if the type is vectorizable
        text = data.get("text") or data.get("title", "")
        if text and self.vector.should_vectorize(node_type):
            layer = self.vector.get_layer_for_type(node_type)
            self.vector.index_node(
                node_id=node.id,
                text=text,
                metadata={
                    "workspace_id": workspace_id,
                    "node_type": node_type.value,
                    "layer": layer,
                    "tags": data.get("tags", []),
                    "status": "active",
                    "created_at": now,
                },
            )

        return node

    # ──────────────────────────────────────────────
    # Node retrieval
    # ──────────────────────────────────────────────

    def get_node(self, node_id: str) -> Optional[Node]:
        """Get a node by ID."""
        return self.db.get_node(node_id)

    def get_subgraph(self, node_id: str, depth: int = 2) -> dict[str, Any]:
        """Subgraph around a node with relations."""
        node, children, relations = self.db.get_subgraph(node_id, depth)
        return {
            "node": node.model_dump() if node else None,
            "children": [c.model_dump() for c in children],
            "relations": [r.model_dump() for r in relations],
        }

    # ──────────────────────────────────────────────
    # Graph navigation
    # ──────────────────────────────────────────────

    def traverse(
        self, start_id: str, relation_type: Optional[str] = None, depth: int = 3
    ) -> list[dict[str, Any]]:
        """Traverse the graph from a node following relations (recursive CTE)."""
        if relation_type:
            where_clause = "WHERE n.id = ? AND r.type = ?"
            params: tuple = (start_id, relation_type, depth)
        else:
            where_clause = "WHERE n.id = ?"
            params = (start_id, depth)

        rows = self.db.execute(
            f"""WITH RECURSIVE walk(id, from_id, to_id, rtype, lvl) AS (
                SELECT n.id, r.from_id, r.to_id, r.type, 1
                FROM nodes n
                LEFT JOIN relations r ON r.from_id = n.id OR r.to_id = n.id
                {where_clause}
                UNION ALL
                SELECT n.id, r.from_id, r.to_id, r.type, w.lvl + 1
                FROM nodes n
                JOIN relations r ON r.from_id = n.id OR r.to_id = n.id
                JOIN walk w ON (r.from_id = w.to_id OR r.to_id = w.from_id)
                WHERE w.lvl < ?
            )
            SELECT DISTINCT id, from_id, to_id, rtype, lvl FROM walk ORDER BY lvl""",
            params,
        )

        results = []
        for row in rows:
            results.append({
                "node_id": row["id"],
                "from_id": row["from_id"],
                "to_id": row["to_id"],
                "relation_type": row["rtype"],
                "level": row["lvl"],
            })

        return results

    def walk(
        self, start_id: str, relation_types: Optional[list[str]] = None, steps: int = 5
    ) -> list[dict[str, Any]]:
        """Walk along a reasoning chain (sequel_to, derives_from)."""
        if relation_types is None:
            relation_types = config.walk_relation_types

        types_placeholder = ",".join("?" for _ in relation_types)

        # Backward walk (from start_id backward along sequel_to)
        rows = self.db.execute(
            f"""WITH RECURSIVE walk(id, from_id, to_id, rtype, lvl) AS (
                SELECT n.id, NULL, NULL, NULL, 0
                FROM nodes n WHERE n.id = ?
                UNION ALL
                SELECT n.id, r.from_id, r.to_id, r.type, w.lvl + 1
                FROM nodes n
                JOIN relations r ON r.to_id = n.id
                JOIN walk w ON r.from_id = w.id
                WHERE r.type IN ({types_placeholder}) AND w.lvl < ?
            )
            SELECT DISTINCT id, from_id, to_id, rtype, lvl FROM walk ORDER BY lvl""",
            (start_id, *relation_types, steps),
        )

        # Forward walk (from start_id forward along sequel_to)
        rows_forward = self.db.execute(
            f"""WITH RECURSIVE walk(id, from_id, to_id, rtype, lvl) AS (
                SELECT n.id, NULL, NULL, NULL, 0
                FROM nodes n WHERE n.id = ?
                UNION ALL
                SELECT n.id, r.from_id, r.to_id, r.type, w.lvl + 1
                FROM nodes n
                JOIN relations r ON r.from_id = n.id
                JOIN walk w ON r.to_id = w.id
                WHERE r.type IN ({types_placeholder}) AND w.lvl < ?
            )
            SELECT DISTINCT id, from_id, to_id, rtype, lvl FROM walk ORDER BY lvl""",
            (start_id, *relation_types, steps),
        )

        results = []
        seen = set()
        for row in list(rows) + list(rows_forward):
            if row["id"] not in seen:
                seen.add(row["id"])
                node = self.db.get_node(row["id"])
                results.append({
                    "node": node.model_dump() if node else None,
                    "from_id": row["from_id"],
                    "to_id": row["to_id"],
                    "relation_type": row["rtype"],
                    "level": row["lvl"],
                })
        return results

    def temporal_walk(
        self,
        workspace_id: str,
        from_time: Optional[str] = None,
        to_time: Optional[str] = None,
        relation_type: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Walk the graph along the time axis.

        Returns nodes ordered by created_at ASC within optional time range.
        If relation_type is specified, filters by node type.
        """
        nodes = self.db.time_range_query(
            workspace_id=workspace_id,
            from_time=from_time,
            to_time=to_time,
            node_type=relation_type,
            limit=limit,
        )
        return [n.model_dump() for n in nodes]

    # ──────────────────────────────────────────────
    # Task decomposition
    # ──────────────────────────────────────────────

    def decompose(
        self, task_id: str, subtasks: list[dict[str, Any]]
    ) -> list[Node]:
        """Decompose a task into subtasks."""
        task = self.db.get_node(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        created_nodes = []
        for sub in subtasks:
            now = datetime.now(timezone.utc).isoformat()
            node = Node(
                type=NodeType.SUBTASK,
                workspace_id=task.workspace_id,
                parent_id=task_id,
                data=sub,
                created_at=now,
                updated_at=now,
            )
            node = self.db.create_node(node)
            self.db.create_relation(
                Relation(
                    from_id=task_id,
                    to_id=node.id,
                    type=RelationType.DECOMPOSES_TO,
                    created_at=now,
                )
            )
            created_nodes.append(node)

        return created_nodes

    # ──────────────────────────────────────────────
    # Mutation
    # ──────────────────────────────────────────────

    def update_node(
        self, node_id: str, data: dict[str, Any]
    ) -> Optional[Node]:
        """Update a node (Strategy A: Update)."""
        old_node = self.db.get_node(node_id)
        if not old_node:
            return None

        updated = self.db.update_node(node_id, data=data)
        if not updated:
            return None

        # If text changed — re-index the vector
        old_text = old_node.data.get("text", "")
        new_text = data.get("text", old_text)
        if old_text != new_text and new_text and self.vector.should_vectorize(old_node.type):
            self.vector.remove_node_vector(node_id)
            self.vector.index_node(
                node_id=node_id,
                text=new_text,
                metadata={
                    "workspace_id": old_node.workspace_id,
                    "node_type": old_node.type.value,
                    "layer": self.vector.get_layer_for_type(old_node.type),
                    "status": "active",
                },
            )

        return updated

    def supersede(
        self, old_id: str, new_data: dict[str, Any]
    ) -> tuple[Optional[Node], Optional[Node]]:
        """Replace a decision (Strategy B: Supersedes)."""
        old_node = self.db.get_node(old_id)
        if not old_node:
            return None, None

        # Mark old as stale
        self.db.update_node(old_id, status=NodeStatus.STALE)

        # Create new node
        now = datetime.now(timezone.utc).isoformat()
        new_node = Node(
            type=old_node.type,
            workspace_id=old_node.workspace_id,
            parent_id=old_node.parent_id,
            data=new_data,
            created_at=now,
            updated_at=now,
        )
        new_node = self.db.create_node(new_node)

        # Relation supersedes
        self.db.create_relation(
            Relation(
                from_id=new_node.id,
                to_id=old_node.id,
                type=RelationType.SUPERSEDES,
                created_at=now,
            )
        )

        # Index new node
        text = new_data.get("text") or new_data.get("title", "")
        if text and self.vector.should_vectorize(old_node.type):
            self.vector.index_node(
                node_id=new_node.id,
                text=text,
                metadata={
                    "workspace_id": old_node.workspace_id,
                    "node_type": old_node.type.value,
                    "layer": self.vector.get_layer_for_type(old_node.type),
                    "status": "active",
                },
            )

        return old_node, new_node

    def stale_cascade(self, parent_id: str) -> list[Node]:
        """Stale cascade: mark child nodes as stale (Strategy C)."""
        children = self.db.get_nodes_by_parent(parent_id)
        stale_nodes = []
        for child in children:
            if child.status == NodeStatus.ACTIVE:
                self.db.update_node(child.id, status=NodeStatus.STALE)
                stale_nodes.append(child)
        return stale_nodes

    # ──────────────────────────────────────────────
    # Graph search
    # ──────────────────────────────────────────────

    def search_graph(
        self, query: str, workspace_id: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Hybrid search: vector search + subgraph expansion.
        Returns {vector_results: [...], graph_subgraphs: [...]}.
        """
        # 1. Vector search
        vector_results = self.vector.search(
            query=query, workspace_id=workspace_id, top_k=5
        )

        # 2. For each result — expand subgraph
        graph_subgraphs = []
        for vr in vector_results:
            node_id = vr["node_id"]
            subgraph = self.get_subgraph(node_id)
            graph_subgraphs.append({
                "vector_result": vr,
                "subgraph": subgraph,
            })

        return {
            "vector_results": vector_results,
            "graph_subgraphs": graph_subgraphs,
        }

    # ──────────────────────────────────────────────
    # Deletion
    # ──────────────────────────────────────────────

    def delete_node(self, node_id: str, cascade: bool = False) -> bool:
        """Delete a node and its vector."""
        node = self.db.get_node(node_id)
        if not node:
            return False

        # Delete vector
        if self.vector.should_vectorize(node.type):
            self.vector.remove_node_vector(node_id)

        # Delete from graph
        return self.db.delete_node(node_id, cascade=cascade)

    def add_relation(
        self,
        from_id: str,
        to_id: str,
        relation_type: RelationType,
        weight: float = 1.0,
    ) -> Relation:
        """Add a relation."""
        relation = Relation(
            from_id=from_id,
            to_id=to_id,
            type=relation_type,
            weight=weight,
        )
        return self.db.create_relation(relation)
