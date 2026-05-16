"""SQLite Database Manager — schema and CRUD for the graph."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

from .config import config
from .models import (
    ArchiveInfo,
    NavHistoryEntry,
    Node,
    NodePreview,
    NodeStatus,
    NodeType,
    Relation,
    RelationType,
)


class DatabaseManager:
    """SQLite management — graph, relations, navigation history."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path or config.db_path)
        self.conn: sqlite3.Connection | None = None

    def connect(self) -> None:
        """Connect to the database and create the schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._create_schema()
        self._migrate_v1_temporal()

    def close(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None

    def _create_schema(self) -> None:
        """Create tables and indexes."""
        with self.conn:  # type: ignore
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS nodes (
                    id          TEXT PRIMARY KEY,
                    type        TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    parent_id   TEXT,
                    data        JSON NOT NULL DEFAULT '{}',
                    status      TEXT DEFAULT 'active',
                    created_at  TEXT NOT NULL,
                    updated_at  TEXT NOT NULL
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS relations (
                    id          TEXT PRIMARY KEY,
                    from_id     TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
                    to_id       TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
                    type        TEXT NOT NULL,
                    weight      REAL DEFAULT 1.0,
                    data        JSON DEFAULT '{}',
                    created_at  TEXT NOT NULL
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS navigation_history (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    workspace_id TEXT NOT NULL,
                    node_id     TEXT NOT NULL,
                    action      TEXT NOT NULL,
                    context     JSON DEFAULT '{}',
                    created_at  TEXT NOT NULL
                )
            """)
            # Indexes
            for idx in [
                "CREATE INDEX IF NOT EXISTS idx_nodes_workspace ON nodes(workspace_id)",
                "CREATE INDEX IF NOT EXISTS idx_nodes_parent ON nodes(parent_id)",
                "CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type)",
                "CREATE INDEX IF NOT EXISTS idx_nodes_status ON nodes(status)",
                "CREATE INDEX IF NOT EXISTS idx_nodes_created ON nodes(workspace_id, created_at)",
                "CREATE INDEX IF NOT EXISTS idx_nodes_updated ON nodes(workspace_id, updated_at)",
                "CREATE INDEX IF NOT EXISTS idx_relations_from ON relations(from_id)",
                "CREATE INDEX IF NOT EXISTS idx_relations_to ON relations(to_id)",
                "CREATE INDEX IF NOT EXISTS idx_relations_type ON relations(type)",
                "CREATE INDEX IF NOT EXISTS idx_nav_workspace ON navigation_history(workspace_id)",
                "CREATE INDEX IF NOT EXISTS idx_nav_created ON navigation_history(workspace_id, created_at)",
            ]:
                self.conn.execute(idx)

    # ──────────────────────────────────────────────
    # Migrations
    # ──────────────────────────────────────────────

    def _migrate_v1_temporal(self) -> None:
        """Add updated_at column to relations if missing."""
        cursor = self.conn.execute("PRAGMA table_info(relations)")  # type: ignore
        cols = {row[1] for row in cursor.fetchall()}
        if "updated_at" not in cols:
            self.conn.execute(  # type: ignore
                "ALTER TABLE relations ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''"
            )
            self.conn.execute(  # type: ignore
                "UPDATE relations SET updated_at = created_at"
            )
            logger.info("Migration v1: added updated_at to relations")

    # ──────────────────────────────────────────────
    # Nodes
    # ──────────────────────────────────────────────

    def create_node(self, node: Node) -> Node:
        """Create a node."""
        with self.conn:  # type: ignore
            self.conn.execute(
                """INSERT INTO nodes (id, type, workspace_id, parent_id, data, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    node.id,
                    node.type.value,
                    node.workspace_id,
                    node.parent_id,
                    json.dumps(node.data, ensure_ascii=False),
                    node.status.value,
                    node.created_at,
                    node.updated_at,
                ),
            )
        return node

    def get_node(self, node_id: str) -> Optional[Node]:
        """Get a node by ID."""
        row = self.conn.execute(  # type: ignore
            "SELECT * FROM nodes WHERE id = ?", (node_id,)
        ).fetchone()
        return self._row_to_node(row) if row else None

    def update_node(
        self,
        node_id: str,
        data: Optional[dict[str, Any]] = None,
        status: Optional[NodeStatus] = None,
    ) -> Optional[Node]:
        """Update a node."""
        now = datetime.now(timezone.utc).isoformat()
        sets = ["updated_at = ?"]
        params: list[Any] = [now]

        if data is not None:
            sets.append("data = ?")
            params.append(json.dumps(data, ensure_ascii=False))
        if status is not None:
            sets.append("status = ?")
            params.append(status.value)

        params.append(node_id)
        with self.conn:  # type: ignore
            self.conn.execute(
                f"UPDATE nodes SET {', '.join(sets)} WHERE id = ?", params
            )
        return self.get_node(node_id)

    def delete_node(self, node_id: str, cascade: bool = False) -> bool:
        """Delete a node."""
        with self.conn:  # type: ignore
            if cascade:
                # Cascade delete by parent_id
                self.conn.execute(
                    "DELETE FROM nodes WHERE id IN ("
                    "  WITH RECURSIVE subtree(id) AS ("
                    "    VALUES(?) UNION ALL SELECT n.id FROM nodes n JOIN subtree s ON n.parent_id = s.id"
                    "  ) SELECT id FROM subtree"
                    ")",
                    (node_id,),
                )
            else:
                self.conn.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
        return True

    def list_nodes(self, workspace_id: str) -> list[Node]:
        """All nodes in a workspace."""
        rows = self.conn.execute(  # type: ignore
            "SELECT * FROM nodes WHERE workspace_id = ? ORDER BY created_at", (workspace_id,)
        ).fetchall()
        return [self._row_to_node(r) for r in rows if r]

    def get_nodes_by_parent(self, parent_id: str) -> list[Node]:
        """Child nodes by parent_id."""
        rows = self.conn.execute(  # type: ignore
            "SELECT * FROM nodes WHERE parent_id = ? ORDER BY created_at", (parent_id,)
        ).fetchall()
        return [self._row_to_node(r) for r in rows if r]

    def get_subgraph(
        self, node_id: str, depth: int = 2
    ) -> tuple[Optional[Node], list[Node], list[Relation]]:
        """Get a node, its children, and all relations around it."""
        node = self.get_node(node_id)
        children = self.get_nodes_by_parent(node_id) if node else []

        # Relations: from and to around the node
        rows = self.conn.execute(  # type: ignore
            "SELECT * FROM relations WHERE from_id = ? OR to_id = ?",
            (node_id, node_id),
        ).fetchall()
        relations = [self._row_to_relation(r) for r in rows]

        return node, children, relations

    def get_cold_nodes(self, workspace_id: str, hot_ids: set[str]) -> list[NodePreview]:
        """Cold nodes: active, not hot, without full text."""
        if hot_ids:
            placeholders = ",".join("?" for _ in hot_ids)
            rows = self.conn.execute(  # type: ignore
                f"""SELECT n.id, n.type, n.data, n.status, n.created_at,
                           (SELECT COUNT(*) FROM nodes c WHERE c.parent_id = n.id) as children_count
                    FROM nodes n
                    WHERE n.workspace_id = ?
                      AND n.status = 'active'
                      AND n.id NOT IN ({placeholders})
                    ORDER BY n.updated_at DESC
                    LIMIT 100""",
                (workspace_id, *hot_ids),
            ).fetchall()
        else:
            rows = self.conn.execute(  # type: ignore
                """SELECT n.id, n.type, n.data, n.status, n.created_at,
                           (SELECT COUNT(*) FROM nodes c WHERE c.parent_id = n.id) as children_count
                    FROM nodes n
                    WHERE n.workspace_id = ?
                      AND n.status = 'active'
                    ORDER BY n.updated_at DESC
                    LIMIT 100""",
                (workspace_id,),
            ).fetchall()

        result = []
        for r in rows:
            raw = r["data"]
            if isinstance(raw, str):
                try:
                    data = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    data = {}
            elif raw is None:
                data = {}
            else:
                data = raw
            title = data.get("title") or str(data.get("text", ""))[:80]
            result.append(NodePreview(
                id=r["id"], type=r["type"], title=title,
                status=r["status"], children_count=r["children_count"],
                created_at=r["created_at"],
            ))
        return result

    def get_archive_info(self, workspace_id: str) -> ArchiveInfo:
        """Information about archived nodes."""
        row = self.conn.execute(  # type: ignore
            """SELECT COUNT(*) as cnt, MIN(updated_at) as oldest
               FROM nodes WHERE workspace_id = ? AND status = 'archived'""",
            (workspace_id,),
        ).fetchone()
        if row and row["cnt"] > 0:
            return ArchiveInfo(available=True, archived_count=row["cnt"], oldest=row["oldest"])
        return ArchiveInfo()

    def archive_stale_nodes(self, workspace_id: str, days_threshold: int | None = None) -> int:
        """Mark stale nodes as archived."""
        threshold = days_threshold if days_threshold is not None else config.archive_days_threshold
        result = self.conn.execute(  # type: ignore
            """UPDATE nodes SET status = 'archived', updated_at = datetime('now')
               WHERE workspace_id = ?
                 AND status = 'active'
                 AND id NOT IN (SELECT node_id FROM navigation_history
                                WHERE workspace_id = ?
                                  AND created_at > datetime('now', ?))
               """,
            (workspace_id, workspace_id, f"-{threshold} days"),
        )
        return result.rowcount  # type: ignore

    def get_session_root(self, workspace_id: str) -> Optional[Node]:
        """Root node of a session."""
        row = self.conn.execute(  # type: ignore
            "SELECT * FROM nodes WHERE workspace_id = ? AND type = 'session' LIMIT 1",
            (workspace_id,),
        ).fetchone()
        return self._row_to_node(row) if row else None

    # ──────────────────────────────────────────────
    # Relations
    # ──────────────────────────────────────────────

    def create_relation(self, relation: Relation) -> Relation:
        """Create a relation."""
        with self.conn:  # type: ignore
            self.conn.execute(
                """INSERT INTO relations (id, from_id, to_id, type, weight, data, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    relation.id,
                    relation.from_id,
                    relation.to_id,
                    relation.type.value,
                    relation.weight,
                    json.dumps(relation.data, ensure_ascii=False),
                    relation.created_at,
                    relation.updated_at,
                ),
            )
        return relation

    def update_relation(
        self, relation_id: str, data: Optional[dict] = None, weight: Optional[float] = None
    ) -> Optional[Relation]:
        """Update a relation — updates updated_at."""
        now = datetime.now(timezone.utc).isoformat()
        sets = ["updated_at = ?"]
        params: list[Any] = [now]
        if data is not None:
            sets.append("data = ?")
            params.append(json.dumps(data, ensure_ascii=False))
        if weight is not None:
            sets.append("weight = ?")
            params.append(weight)
        params.append(relation_id)
        with self.conn:  # type: ignore
            self.conn.execute(
                f"UPDATE relations SET {', '.join(sets)} WHERE id = ?", params
            )
        # Return updated relation
        row = self.conn.execute(  # type: ignore
            "SELECT * FROM relations WHERE id = ?", (relation_id,)
        ).fetchone()
        return self._row_to_relation(row) if row else None

    def delete_relation(self, relation_id: str) -> bool:
        """Delete a relation."""
        with self.conn:  # type: ignore
            self.conn.execute("DELETE FROM relations WHERE id = ?", (relation_id,))
        return True

    def get_relations_for_node(self, node_id: str) -> list[Relation]:
        """All relations for a node."""
        rows = self.conn.execute(  # type: ignore
            "SELECT * FROM relations WHERE from_id = ? OR to_id = ?",
            (node_id, node_id),
        ).fetchall()
        return [self._row_to_relation(r) for r in rows]

    # ──────────────────────────────────────────────
    # Navigation history
    # ──────────────────────────────────────────────

    def add_nav_history(self, entry: NavHistoryEntry) -> None:
        """Add a navigation history record."""
        with self.conn:  # type: ignore
            self.conn.execute(
                """INSERT INTO navigation_history (workspace_id, node_id, action, context, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    entry.workspace_id,
                    entry.node_id,
                    entry.action,
                    json.dumps(entry.context, ensure_ascii=False),
                    entry.created_at,
                ),
            )

    def get_nav_history(
        self, workspace_id: str, limit: int = 20
    ) -> list[NavHistoryEntry]:
        """Latest navigation history records."""
        rows = self.conn.execute(  # type: ignore
            """SELECT * FROM navigation_history
               WHERE workspace_id = ?
               ORDER BY created_at DESC LIMIT ?""",
            (workspace_id, limit),
        ).fetchall()

        result = []
        for r in rows:
            d = dict(r)
            # Parse JSON strings
            if isinstance(d.get("context"), str):
                try:
                    d["context"] = json.loads(d["context"])
                except (json.JSONDecodeError, TypeError):
                    d["context"] = {}
            result.append(NavHistoryEntry(**d))
        return result

    def get_last_focus_nodes(
        self, workspace_id: str, limit: int = 5
    ) -> set[str]:
        """Last N nodes that were focused."""
        rows = self.conn.execute(  # type: ignore
            """SELECT DISTINCT node_id FROM navigation_history
               WHERE workspace_id = ? AND action IN ('focus', 'branch')
               ORDER BY created_at DESC LIMIT ?""",
            (workspace_id, limit),
        ).fetchall()
        return {r["node_id"] for r in rows}

    # ──────────────────────────────────────────────
    # Temporal queries
    # ──────────────────────────────────────────────

    def time_range_query(
        self,
        workspace_id: str,
        from_time: Optional[str] = None,
        to_time: Optional[str] = None,
        node_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[Node]:
        """Query nodes by time range. Filters by created_at."""
        conditions = ["workspace_id = ?"]
        params: list[Any] = [workspace_id]
        if from_time:
            conditions.append("created_at >= ?")
            params.append(from_time)
        if to_time:
            conditions.append("created_at <= ?")
            params.append(to_time)
        if node_type:
            conditions.append("type = ?")
            params.append(node_type)

        rows = self.conn.execute(  # type: ignore
            f"SELECT * FROM nodes WHERE {' AND '.join(conditions)} ORDER BY created_at ASC LIMIT ?",
            (*params, limit),
        ).fetchall()
        return [self._row_to_node(r) for r in rows if r]

    def get_anchor(self, workspace_id: str) -> Optional[tuple[str, str]]:
        """Get deterministic anchor: (node_id, created_at) of last focus."""
        row = self.conn.execute(  # type: ignore
            """SELECT node_id, created_at FROM navigation_history
               WHERE workspace_id = ? AND action = 'focus'
               ORDER BY created_at DESC LIMIT 1""",
            (workspace_id,),
        ).fetchone()
        return (row["node_id"], row["created_at"]) if row else None

    # ──────────────────────────────────────────────
    # SQL — for direct queries from GraphManager
    # ──────────────────────────────────────────────

    def execute(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        """Execute an arbitrary SQL query."""
        return self.conn.execute(sql, params).fetchall()  # type: ignore

    def execute_write(self, sql: str, params: tuple = ()) -> None:
        """Execute a write query."""
        with self.conn:  # type: ignore
            self.conn.execute(sql, params)

    # ──────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────

    @staticmethod
    def _row_to_node(row: sqlite3.Row) -> Optional[Node]:
        if not row:
            return None
        return Node(
            id=row["id"],
            type=NodeType(row["type"]),
            workspace_id=row["workspace_id"],
            parent_id=row["parent_id"],
            data=json.loads(row["data"]) if isinstance(row["data"], str) else row["data"] or {},
            status=NodeStatus(row["status"]) if row["status"] else NodeStatus.ACTIVE,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _row_to_relation(row: sqlite3.Row) -> Optional[Relation]:
        if not row:
            return None
        return Relation(
            id=row["id"],
            from_id=row["from_id"],
            to_id=row["to_id"],
            type=RelationType(row["type"]),
            weight=row["weight"],
            data=json.loads(row["data"]) if isinstance(row["data"], str) else row["data"] or {},
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
