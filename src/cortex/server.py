"""MCP server for mcp-cortex — tools and resources."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import mcp.types as types
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions

from . import Cortex
from .config import config, resolve_workspace_id
from .models import NodeType, RelationType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cortex-server")


class CortexServer:
    """MCP server for fractal graph memory."""

    def __init__(
        self,
        db_path: str | Path | None = None,
        qdrant_host: str | None = None,
        qdrant_port: int | None = None,
    ):
        self.cortex = Cortex(
            db_path=db_path or config.db_path,
            qdrant_host=qdrant_host or config.qdrant_host,
            qdrant_port=qdrant_port or config.qdrant_port,
        )
        self.server = Server("cortex")

        # Register tools and resources
        self._register_tools()
        self._register_resources()

    # ── helpers ────────────────────────────────────

    def _ws(self, args: dict[str, Any]) -> str:
        """Resolve workspace_id from call args, env, or CWD.

        For WRITE tools (add_node, desktop_open, etc.), resolves to the
        caller's project workspace. For SEARCH tools, use _ws_opt() instead.
        """
        return resolve_workspace_id(args.get("workspace_id"))

    def _ws_opt(self, args: dict[str, Any]) -> str | None:
        """Resolve workspace_id ONLY if explicitly provided.

        For SEARCH tools — None means "search across ALL workspaces",
        while an explicit value narrows to one project.
        """
        raw = args.get("workspace_id")
        if raw and raw.strip():
            return raw.strip()
        return None

    def _register_tools(self) -> None:
        """Register all MCP tools."""

        @self.server.list_tools()
        async def list_tools() -> list[types.Tool]:
            return [
                # ── Desktop (Session / Workspace) ──
                types.Tool(
                    name="desktop_open",
                    description="Open a workspace session and return its Desktop Viewport (Hot/Cold/Archive tiers). "
                                "Use at the START of every task to initialize or resume a session. "
                                "Returns: session root, hot nodes (current focus + direct relations), "
                                "cold nodes (other active nodes, titles only), archive info (old nodes, search only). "
                                "Hot=3-10 nodes always in context, Cold=10-100 by focus/search, Archive=100+ by vector_search only.\n\n"
                                "Without workspace_id, opens YOUR PROJECT's workspace (from CORTEX_WORKSPACE_ID / --workspace). "
                                "To see another project's viewport, pass its workspace_id explicitly.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workspace_id": {"type": "string", "description": "Optional. Omit to open your project's workspace. Set to open another project."},
                        },
                    },
                ),
                types.Tool(
                    name="desktop_focus",
                    description="Focus on a specific node — expand its subgraph with all relations and child nodes. "
                                "Use when you need to explore context around a specific task, fact, or decision. "
                                "Also logs this focus to navigation history for Hot/Cold tier calculations.\n\n"
                                "workspace_id is OPTIONAL.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node_id": {"type": "string", "description": "ID of the node to focus on"},
                            "workspace_id": {"type": "string", "description": "Optional. Falls back to env/CWD folder name / 'default'"},
                        },
                        "required": ["node_id"],
                    },
                ),
                types.Tool(
                    name="desktop_history",
                    description="Get navigation history for a workspace session. "
                                "Use to understand what was recently worked on or to restore context.\n\n"
                                "workspace_id is OPTIONAL.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workspace_id": {"type": "string", "description": "Optional. Falls back to env/CWD folder name / 'default'"},
                            "limit": {"type": "integer", "default": 20},
                        },
                    },
                ),
                # ── Graph (Knowledge) ──
                types.Tool(
                    name="graph_add_node",
                    description="Add a node to the knowledge graph. Supports 13 types (entity, fact, decision, thought, "
                                "chunk, question, hypothesis, action, error, note, pattern, goal, constraint — all vectorized; "
                                "session, task, subtask, fileref — graph only). "
                                "Text in data.text or data.title is automatically indexed into Qdrant vector search for "
                                "vectorizable types. For fileref nodes, pass path in data.path.\n\n"
                                "workspace_id is OPTIONAL.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "parent_id": {"type": "string", "description": "Parent node ID (can be null for roots under session)"},
                            "type": {
                                "type": "string",
                                "enum": [t.value for t in NodeType],
                                "description": "Node type: entity|fact|decision|chunk|thought|question|hypothesis|action|error|note|pattern|goal|constraint|session|task|subtask|fileref",
                            },
                            "workspace_id": {"type": "string", "description": "Optional. Falls back to env/CWD folder name / 'default'"},
                            "data": {
                                "type": "object",
                                "description": "JSON data: text/title/content for semantic content, path/filetype/description for fileref, plus tags array and any custom metadata",
                            },
                        },
                        "required": ["type", "data"],
                    },
                ),
                types.Tool(
                    name="graph_get_node",
                    description="Get a node with its relations and child nodes. "
                                "Use to inspect a node's full context: what it contains, what it relates to, what references it.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node_id": {"type": "string"},
                            "depth": {"type": "integer", "default": 2, "description": "Recursion depth for children"},
                        },
                        "required": ["node_id"],
                    },
                ),
                types.Tool(
                    name="graph_add_relation",
                    description="Create a relation between two nodes. Supports 22 relation types: "
                                "Hierarchical (contains, decomposes_to, belongs_to), "
                                "Semantic (derives_from, supports, contradicts, related_to, questions, answers), "
                                "Index (indexes Entity->Fileref, extracted_from Fact/Chunk->Fileref, references, implements, relates_to_file), "
                                "Chronological (sequel_to, supersedes, leads_to, resolves, triggers), "
                                "Dependency (depends_on, blocks, constrained_by).",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "from_id": {"type": "string", "description": "Source node ID"},
                            "to_id": {"type": "string", "description": "Target node ID"},
                            "type": {
                                "type": "string",
                                "enum": [r.value for r in RelationType],
                                "description": "Relation type (22 types available)",
                            },
                            "weight": {"type": "number", "default": 1.0, "description": "Relation strength 0.0-1.0"},
                        },
                        "required": ["from_id", "to_id", "type"],
                    },
                ),
                types.Tool(
                    name="graph_traverse",
                    description="Traverse the graph starting from a node, following relations. "
                                "Optionally filter by relation type. Uses recursive CTE up to specified depth. "
                                "Use to discover how nodes are connected in the graph.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "start_id": {"type": "string"},
                            "relation": {"type": "string", "description": "Optional: filter by relation type (e.g., 'contains', 'depends_on')"},
                            "depth": {"type": "integer", "default": 3},
                        },
                        "required": ["start_id"],
                    },
                ),
                types.Tool(
                    name="graph_walk",
                    description="Walk along a reasoning chain following sequel_to, derives_from, and leads_to relations. "
                                "Use to reconstruct the chain of thought: how one thought led to another, "
                                "what decisions were derived from what facts. Returns nodes in chronological order.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "start_id": {"type": "string", "description": "Starting node ID (typically a thought or fact)"},
                            "steps": {"type": "integer", "default": 5},
                        },
                        "required": ["start_id"],
                    },
                ),
                types.Tool(
                    name="graph_decompose",
                    description="Decompose a task node into subtasks. Creates subtask nodes and adds decomposes_to relations. "
                                "Use for planning and breaking down complex tasks into manageable pieces.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string", "description": "Parent task node ID"},
                            "subtasks": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "title": {"type": "string"},
                                        "description": {"type": "string"},
                                    },
                                },
                            },
                        },
                        "required": ["task_id", "subtasks"],
                    },
                ),
                types.Tool(
                    name="graph_update_node",
                    description="Update a node's data in-place (Strategy A: Update). "
                                "If data.text changes, the Qdrant vector is automatically re-indexed. "
                                "Use for small corrections and improvements. For major decision changes, use graph_supersede instead.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node_id": {"type": "string"},
                            "data": {"type": "object", "description": "New JSON data (merged with existing)"},
                        },
                        "required": ["node_id", "data"],
                    },
                ),
                types.Tool(
                    name="graph_supersede",
                    description="Supersede an old node with a new one (Strategy B: Supersedes). "
                                "Marks old node as stale, creates a new node with supersedes relation. "
                                "Use when a decision or fact fundamentally changes — preserves history of why previous decision was made. "
                                "The old node remains searchable but is marked stale and deprioritized in results.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "old_id": {"type": "string", "description": "ID of the node to supersede (will become stale)"},
                            "new_data": {"type": "object", "description": "New JSON data for the replacement node"},
                        },
                        "required": ["old_id", "new_data"],
                    },
                ),
                types.Tool(
                    name="graph_delete_node",
                    description="Delete a node and its vector from Qdrant. "
                                "With cascade=true, also deletes all child nodes (subtree). "
                                "Use with caution — prefer graph_supersede (stale) for history preservation.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node_id": {"type": "string"},
                            "cascade": {"type": "boolean", "default": False, "description": "Cascade delete all child nodes"},
                        },
                        "required": ["node_id"],
                    },
                ),
                # ── Vector (Semantic Search) ──
                types.Tool(
                    name="vector_search",
                    description="Semantic vector search across all indexed layers (Entity + Chunk + Fact). "
                                "Use to FIND RELEVANT KNOWLEDGE by meaning. Returns nodes sorted by relevance score. "
                                "Then use graph_get_node or desktop_focus to expand the context. "
                                "This is the PRIMARY entry point for the regression search pattern: "
                                "1. vector_search (meaning) -> 2. graph_get_node (context) -> 3. read files (specifics).\n\n"
                                "CROSS-PROJECT: without workspace_id, searches ALL workspaces. "
                                "Add workspace_id to narrow to one project.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Natural language search query"},
                            "workspace_id": {"type": "string", "description": "Optional. Omit to search ALL projects (cross-project). Set to narrow to one project."},
                            "top_k": {"type": "integer", "default": 10},
                        },
                        "required": ["query"],
                    },
                ),
                types.Tool(
                    name="vector_store",
                    description="Store text with automatic vectorization into Qdrant. "
                                "Use for quick ad-hoc storage of facts without creating a full graph node. "
                                "For structured knowledge, prefer graph_add_node which creates both a graph node and a vector.\n\n"
                                "workspace_id in metadata is OPTIONAL.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "metadata": {
                                "type": "object",
                                "properties": {
                                    "workspace_id": {"type": "string", "description": "Optional. Falls back to env/CWD folder name / 'default'"},
                                    "node_type": {"type": "string", "default": "note"},
                                    "tags": {"type": "array", "items": {"type": "string"}},
                                },
                            },
                        },
                        "required": ["text", "metadata"],
                    },
                ),
                # ── Hybrid Search ──
                types.Tool(
                    name="graph_search",
                    description="Hybrid search: vector search + expanded subgraphs. "
                                "Does vector_search first, then expands each result's subgraph. "
                                "Returns both vector results and their graph contexts. "
                                "Use when you need deep context around search results — faster than "
                                "calling vector_search then graph_get_node for each result manually.\n\n"
                                "CROSS-PROJECT: without workspace_id, searches ALL workspaces. "
                                "Add workspace_id to narrow to one project.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "workspace_id": {"type": "string", "description": "Optional. Omit to search ALL projects (cross-project). Set to narrow to one project."},
                        },
                        "required": ["query"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(
            name: str, arguments: dict[str, Any]
        ) -> list[types.TextContent | types.ResourceContent]:
            try:
                return await self._handle_tool(name, arguments)
            except Exception as e:
                logger.error(f"Tool {name} error: {e}", exc_info=True)
                return [types.TextContent(type="text", text=f"Error: {e!s}")]

    async def _handle_tool(
        self, name: str, args: dict[str, Any]
    ) -> list[types.TextContent | types.ResourceContent]:
        """Handle a tool call."""
        result = None
        ws = self._ws(args)          # WRITE: resolve to caller's project
        ws_opt = self._ws_opt(args)  # SEARCH: None = all workspaces

        if name == "desktop_open":
            result = self.cortex.desktop.open(ws)

        elif name == "desktop_focus":
            result = self.cortex.desktop.focus(args["node_id"], ws)

        elif name == "desktop_history":
            result = self.cortex.desktop.get_history(ws, args.get("limit", 20))

        elif name == "graph_add_node":
            parent = args.get("parent_id")
            node_type = NodeType(args["type"])
            result = self.cortex.graph.add_node(
                parent_id=parent,
                node_type=node_type,
                data=args["data"],
                workspace_id=ws,
            )
            result = result.model_dump()

        elif name == "graph_get_node":
            result = self.cortex.graph.get_subgraph(
                args["node_id"], args.get("depth", 2)
            )

        elif name == "graph_add_relation":
            raw_weight = args.get("weight", 1.0)
            # MCP client may send weight as string; always coerce to float
            try:
                weight = float(raw_weight)
            except (TypeError, ValueError):
                weight = 1.0
            rel = self.cortex.graph.add_relation(
                from_id=args["from_id"],
                to_id=args["to_id"],
                relation_type=RelationType(args["type"]),
                weight=weight,
            )
            result = rel.model_dump()

        elif name == "graph_traverse":
            result = self.cortex.graph.traverse(
                start_id=args["start_id"],
                relation_type=args.get("relation"),
                depth=args.get("depth", 3),
            )

        elif name == "graph_walk":
            result = self.cortex.graph.walk(
                start_id=args["start_id"],
                steps=args.get("steps", 5),
            )

        elif name == "graph_decompose":
            nodes = self.cortex.graph.decompose(
                task_id=args["task_id"],
                subtasks=args["subtasks"],
            )
            result = {"subtask_ids": [n.id for n in nodes]}

        elif name == "graph_update_node":
            updated = self.cortex.graph.update_node(
                node_id=args["node_id"],
                data=args["data"],
            )
            result = updated.model_dump() if updated else None

        elif name == "graph_supersede":
            old_node, new_node = self.cortex.graph.supersede(
                old_id=args["old_id"],
                new_data=args["new_data"],
            )
            result = {
                "old_id": old_node.id if old_node else None,
                "new_id": new_node.id if new_node else None,
                "status": "superseded",
            }

        elif name == "graph_delete_node":
            deleted = self.cortex.graph.delete_node(
                node_id=args["node_id"],
                cascade=args.get("cascade", False),
            )
            result = {"deleted": deleted}

        elif name == "vector_search":
            # ws_opt=None → cross-project search (all workspaces)
            result = self.cortex.vector.search(
                query=args["query"],
                workspace_id=ws_opt,
                top_k=args.get("top_k", 10),
            )

        elif name == "vector_store":
            meta = args["metadata"]
            meta["workspace_id"] = ws
            result = self.cortex.vector.index_node(
                node_id=meta.get("node_id", "direct"),
                text=args["text"],
                metadata=meta,
            )
            result = {"indexed": result}

        elif name == "graph_search":
            # ws_opt=None → cross-project search
            result = self.cortex.graph.search_graph(
                query=args["query"],
                workspace_id=ws_opt,
            )

        if result is None:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

        # Serialize — always use json.dumps for valid JSON output
        import json as _json
        return [types.TextContent(type="text", text=_json.dumps(result, ensure_ascii=False, default=str))]

    def _register_resources(self) -> None:
        """Register MCP resources."""

        @self.server.list_resources()
        async def list_resources() -> list[types.Resource]:
            return [
                types.Resource(
                    uri="cortex://graph/{workspace_id}",
                    name="Graph",
                    description="Full session graph",
                    mimeType="application/json",
                ),
                types.Resource(
                    uri="cortex://node/{node_id}",
                    name="Node",
                    description="Specific node with context",
                    mimeType="application/json",
                ),
                types.Resource(
                    uri="cortex://desktop/{workspace_id}",
                    name="Desktop",
                    description="Current desktop viewport",
                    mimeType="application/json",
                ),
                types.Resource(
                    uri="cortex://search/{query}",
                    name="Search",
                    description="Search results",
                    mimeType="application/json",
                ),
            ]

        @self.server.read_resource()
        async def read_resource(uri: str) -> list[types.ResourceContent]:
            path = uri.replace("cortex://", "")
            default_ws = resolve_workspace_id()

            if path.startswith("graph/"):
                ws_id = path.split("/", 1)[1]
                result = self.cortex.desktop.open(ws_id)

            elif path.startswith("node/"):
                node_id = path.split("/", 1)[1]
                result = self.cortex.graph.get_subgraph(node_id)

            elif path.startswith("desktop/"):
                ws_id = path.split("/", 1)[1]
                result = self.cortex.desktop.open(ws_id)

            elif path.startswith("search/"):
                query = path.split("/", 1)[1]
                result = self.cortex.graph.search_graph(query)

            else:
                return [
                    types.ResourceContent(
                        uri=uri,
                        mimeType="application/json",
                        text=f"Unknown resource: {uri}",
                    )
                ]

            return [
                types.ResourceContent(
                    uri=uri,
                    mimeType="application/json",
                    text=str(result),
                )
            ]

    async def run(self, transport: str = "stdio") -> None:
        """Run the MCP server."""
        self.cortex.start()
        logger.info("Cortex started: DB connected, Qdrant collection ready")

        async with self.server.run() as server:
            await server

    def get_initialization_options(self) -> InitializationOptions:
        """MCP initialization options."""
        return InitializationOptions(
            server_name="cortex",
            server_version="0.1.0",
            capabilities=self.server.get_capabilities(
                notification_options=NotificationOptions(),
                experimental_capabilities={},
            ),
        )
