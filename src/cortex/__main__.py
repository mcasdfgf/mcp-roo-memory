"""Entry point для запуска MCP-сервера mcp-cortex через stdio.

Usage:
    python -m src.cortex                         # workspace = CWD basename / default
    python -m src.cortex --workspace researcher   # workspace = researcher
    python -m src.cortex -w ai-pulse              # workspace = ai-pulse
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from mcp.server.stdio import stdio_server

from .server import CortexServer


def main() -> None:
    parser = argparse.ArgumentParser(description="Cortex MCP Server — fractal graph memory")
    parser.add_argument(
        "--workspace", "-w",
        dest="workspace_id",
        default=None,
        help="Project workspace ID (sets CORTEX_WORKSPACE_ID). "
             "Each project should have its own ID to isolate memory. "
             "Omit to use CWD basename or 'default'.",
    )
    args, _ = parser.parse_known_args()

    # Set CORTEX_WORKSPACE_ID so resolve_workspace_id() picks it up
    if args.workspace_id:
        os.environ["CORTEX_WORKSPACE_ID"] = args.workspace_id

    asyncio.run(_run_server(args.workspace_id))


async def _run_server(workspace_id: str | None) -> None:
    server = CortexServer()
    server.cortex.start()

    ws_display = workspace_id or os.environ.get("CORTEX_WORKSPACE_ID") or "auto"
    print(f"🧠 Cortex MCP Server started  workspace={ws_display}", file=sys.stderr)
    print("   Graph: SQLite (cortex.db)", file=sys.stderr)
    print("   Vector: Qdrant (cortex_memory)", file=sys.stderr)
    print("   Ready for MCP connections", file=sys.stderr)

    init_opts = server.get_initialization_options()

    async with stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            init_opts,
            raise_exceptions=False,
        )


if __name__ == "__main__":
    main()
