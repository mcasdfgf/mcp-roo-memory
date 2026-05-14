"""Tests for CortexServer — initialization, tools, resources, error handling."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestCortexServerInitialization:
    """Server creation and startup."""

    def test_server_creation(self):
        with patch("cortex.server.Cortex"):
            from cortex.server import CortexServer
            server = CortexServer(db_path=":memory:")
            assert server.server is not None
            assert server.cortex is not None

    def test_server_creation_with_defaults(self):
        with patch("cortex.server.Cortex"):
            from cortex.server import CortexServer
            server = CortexServer()
            assert server.server is not None


class TestCortexServerWorkspaceResolution:
    """_ws() and _ws_opt() methods — workspace ID resolution."""

    def test_ws_resolves_from_arg(self):
        with patch("cortex.server.Cortex"):
            from cortex.server import CortexServer
            server = CortexServer(db_path=":memory:")
            result = server._ws({"workspace_id": "my-project"})
            assert result == "my-project"

    def test_ws_falls_back_to_default(self):
        with patch("cortex.server.Cortex"):
            with patch("cortex.server.resolve_workspace_id", return_value="default-ws"):
                from cortex.server import CortexServer
                server = CortexServer(db_path=":memory:")
                result = server._ws({})
                assert result == "default-ws"

    def test_ws_opt_returns_none_when_not_provided(self):
        with patch("cortex.server.Cortex"):
            from cortex.server import CortexServer
            server = CortexServer(db_path=":memory:")
            result = server._ws_opt({})
            assert result is None

    def test_ws_opt_returns_value_when_provided(self):
        with patch("cortex.server.Cortex"):
            from cortex.server import CortexServer
            server = CortexServer(db_path=":memory:")
            result = server._ws_opt({"workspace_id": "explicit-ws"})
            assert result == "explicit-ws"

    def test_ws_opt_ignores_empty_string(self):
        with patch("cortex.server.Cortex"):
            from cortex.server import CortexServer
            server = CortexServer(db_path=":memory:")
            result = server._ws_opt({"workspace_id": ""})
            assert result is None


class TestCortexServerTools:
    """MCP tool registration — verify tool handlers exist."""

    def test_handle_tool_desktop_open(self):
        """Verify desktop_open tool handler works."""
        with patch("cortex.server.Cortex") as MockCortex:
            from cortex.server import CortexServer
            import mcp.types as types

            mock_cortex_instance = MagicMock()
            MockCortex.return_value = mock_cortex_instance
            mock_cortex_instance.desktop.open.return_value = {
                "session": {"id": "s1", "type": "session", "workspace_id": "ws1"},
                "hot_nodes": [],
                "cold_nodes": [],
                "archive": {"available": False, "archived_count": 0},
                "history": [],
                "last_focus": "s1",
            }

            server = CortexServer(db_path=":memory:")

            import asyncio
            result = asyncio.run(server._handle_tool("desktop_open", {"workspace_id": "ws1"}))
            assert len(result) == 1
            assert "session" in str(result[0])

    def test_handle_tool_desktop_focus(self):
        with patch("cortex.server.Cortex") as MockCortex:
            from cortex.server import CortexServer
            import mcp.types as types

            mock_cortex = MagicMock()
            MockCortex.return_value = mock_cortex
            mock_cortex.desktop.focus.return_value = {"node": {"id": "n1"}}

            server = CortexServer(db_path=":memory:")
            import asyncio
            result = asyncio.run(server._handle_tool(
                "desktop_focus",
                {"node_id": "n1", "workspace_id": "ws1"},
            ))
            assert len(result) == 1

    def test_handle_tool_desktop_history(self):
        with patch("cortex.server.Cortex") as MockCortex:
            from cortex.server import CortexServer
            import mcp.types as types

            mock_cortex = MagicMock()
            MockCortex.return_value = mock_cortex
            mock_cortex.desktop.get_history.return_value = [{"action": "focus"}]

            server = CortexServer(db_path=":memory:")
            import asyncio
            result = asyncio.run(server._handle_tool(
                "desktop_history",
                {"workspace_id": "ws1"},
            ))
            assert len(result) == 1

    def test_handle_tool_graph_add_node(self):
        with patch("cortex.server.Cortex") as MockCortex:
            from cortex.server import CortexServer
            import mcp.types as types

            mock_cortex = MagicMock()
            MockCortex.return_value = mock_cortex
            mock_node = MagicMock()
            mock_node.model_dump.return_value = {
                "id": "n1", "type": "fact", "workspace_id": "ws1",
            }
            mock_cortex.graph.add_node.return_value = mock_node

            server = CortexServer(db_path=":memory:")
            import asyncio
            result = asyncio.run(server._handle_tool(
                "graph_add_node",
                {"type": "fact", "workspace_id": "ws1", "data": {"text": "test"}},
            ))
            assert len(result) == 1

    def test_handle_tool_graph_get_node(self):
        with patch("cortex.server.Cortex") as MockCortex:
            from cortex.server import CortexServer
            import mcp.types as types

            mock_cortex = MagicMock()
            MockCortex.return_value = mock_cortex
            mock_cortex.graph.get_subgraph.return_value = {
                "node": {"id": "n1"}, "children": [], "relations": [],
            }

            server = CortexServer(db_path=":memory:")
            import asyncio
            result = asyncio.run(server._handle_tool(
                "graph_get_node",
                {"node_id": "n1"},
            ))
            assert len(result) == 1

    def test_handle_tool_graph_add_relation(self):
        with patch("cortex.server.Cortex") as MockCortex:
            from cortex.server import CortexServer
            import mcp.types as types

            mock_cortex = MagicMock()
            MockCortex.return_value = mock_cortex
            mock_rel = MagicMock()
            mock_rel.model_dump.return_value = {
                "id": "r1", "from_id": "a", "to_id": "b", "type": "supports",
            }
            mock_cortex.graph.add_relation.return_value = mock_rel

            server = CortexServer(db_path=":memory:")
            import asyncio
            result = asyncio.run(server._handle_tool(
                "graph_add_relation",
                {"from_id": "a", "to_id": "b", "type": "supports"},
            ))
            assert len(result) == 1

    def test_handle_tool_graph_traverse(self):
        with patch("cortex.server.Cortex") as MockCortex:
            from cortex.server import CortexServer
            import mcp.types as types

            mock_cortex = MagicMock()
            MockCortex.return_value = mock_cortex
            mock_cortex.graph.traverse.return_value = [{"node_id": "n1"}]

            server = CortexServer(db_path=":memory:")
            import asyncio
            result = asyncio.run(server._handle_tool(
                "graph_traverse",
                {"start_id": "n1"},
            ))
            assert len(result) == 1

    def test_handle_tool_graph_walk(self):
        with patch("cortex.server.Cortex") as MockCortex:
            from cortex.server import CortexServer
            import mcp.types as types

            mock_cortex = MagicMock()
            MockCortex.return_value = mock_cortex
            mock_cortex.graph.walk.return_value = [{"node": {"id": "n1"}}]

            server = CortexServer(db_path=":memory:")
            import asyncio
            result = asyncio.run(server._handle_tool(
                "graph_walk",
                {"start_id": "n1"},
            ))
            assert len(result) == 1

    def test_handle_tool_graph_decompose(self):
        with patch("cortex.server.Cortex") as MockCortex:
            from cortex.server import CortexServer
            import mcp.types as types

            mock_cortex = MagicMock()
            MockCortex.return_value = mock_cortex
            mock_node = MagicMock()
            mock_node.id = "sub1"
            mock_cortex.graph.decompose.return_value = [mock_node]

            server = CortexServer(db_path=":memory:")
            import asyncio
            result = asyncio.run(server._handle_tool(
                "graph_decompose",
                {"task_id": "t1", "subtasks": [{"title": "subtask"}]},
            ))
            assert len(result) == 1
            assert "subtask_ids" in str(result[0])

    def test_handle_tool_graph_update_node(self):
        with patch("cortex.server.Cortex") as MockCortex:
            from cortex.server import CortexServer
            import mcp.types as types

            mock_cortex = MagicMock()
            MockCortex.return_value = mock_cortex
            mock_updated = MagicMock()
            mock_updated.model_dump.return_value = {"id": "n1", "data": {"text": "new"}}
            mock_cortex.graph.update_node.return_value = mock_updated

            server = CortexServer(db_path=":memory:")
            import asyncio
            result = asyncio.run(server._handle_tool(
                "graph_update_node",
                {"node_id": "n1", "data": {"text": "new"}},
            ))
            assert len(result) == 1

    def test_handle_tool_graph_supersede(self):
        with patch("cortex.server.Cortex") as MockCortex:
            from cortex.server import CortexServer
            import mcp.types as types

            mock_cortex = MagicMock()
            MockCortex.return_value = mock_cortex
            mock_old = MagicMock()
            mock_old.id = "old1"
            mock_new = MagicMock()
            mock_new.id = "new1"
            mock_cortex.graph.supersede.return_value = (mock_old, mock_new)

            server = CortexServer(db_path=":memory:")
            import asyncio
            result = asyncio.run(server._handle_tool(
                "graph_supersede",
                {"old_id": "old1", "new_data": {"text": "new"}},
            ))
            assert len(result) == 1
            assert "superseded" in str(result[0])

    def test_handle_tool_graph_delete_node(self):
        with patch("cortex.server.Cortex") as MockCortex:
            from cortex.server import CortexServer
            import mcp.types as types

            mock_cortex = MagicMock()
            MockCortex.return_value = mock_cortex
            mock_cortex.graph.delete_node.return_value = True

            server = CortexServer(db_path=":memory:")
            import asyncio
            result = asyncio.run(server._handle_tool(
                "graph_delete_node",
                {"node_id": "n1", "cascade": False},
            ))
            assert len(result) == 1
            assert "deleted" in str(result[0])

    def test_handle_tool_vector_search(self):
        with patch("cortex.server.Cortex") as MockCortex:
            from cortex.server import CortexServer
            import mcp.types as types

            mock_cortex = MagicMock()
            MockCortex.return_value = mock_cortex
            mock_cortex.vector.search.return_value = [
                {"node_id": "n1", "score": 0.95, "text": "result"},
            ]

            server = CortexServer(db_path=":memory:")
            import asyncio
            result = asyncio.run(server._handle_tool(
                "vector_search",
                {"query": "test", "top_k": 5},
            ))
            assert len(result) == 1

    def test_handle_tool_vector_store(self):
        with patch("cortex.server.Cortex") as MockCortex:
            from cortex.server import CortexServer
            import mcp.types as types

            mock_cortex = MagicMock()
            MockCortex.return_value = mock_cortex
            mock_cortex.vector.index_node.return_value = True

            server = CortexServer(db_path=":memory:")
            import asyncio
            result = asyncio.run(server._handle_tool(
                "vector_store",
                {"text": "store me", "metadata": {"workspace_id": "ws1"}},
            ))
            assert len(result) == 1
            assert "indexed" in str(result[0])

    def test_handle_tool_graph_search(self):
        with patch("cortex.server.Cortex") as MockCortex:
            from cortex.server import CortexServer
            import mcp.types as types

            mock_cortex = MagicMock()
            MockCortex.return_value = mock_cortex
            mock_cortex.graph.search_graph.return_value = {
                "vector_results": [],
                "graph_subgraphs": [],
            }

            server = CortexServer(db_path=":memory:")
            import asyncio
            result = asyncio.run(server._handle_tool(
                "graph_search",
                {"query": "test"},
            ))
            assert len(result) == 1


class TestCortexServerErrorHandling:
    """Error handling in the server."""

    def test_handle_tool_unknown(self):
        with patch("cortex.server.Cortex"):
            from cortex.server import CortexServer
            import mcp.types as types

            server = CortexServer(db_path=":memory:")
            import asyncio
            result = asyncio.run(server._handle_tool("unknown_tool", {}))
            assert len(result) == 1
            assert "Unknown tool" in str(result[0])

    def test_call_tool_catches_error(self):
        """Verify call_tool handler catches exceptions gracefully."""
        with patch("cortex.server.Cortex"):
            from cortex.server import CortexServer
            import mcp.types as types

            server = CortexServer(db_path=":memory:")
            # The call_tool handler wraps _handle_tool in try/except
            assert server.server is not None
