"""Tests for cortex.__main__ — CLI argument parsing and server startup."""

from __future__ import annotations

import os
from unittest.mock import patch, MagicMock


class TestMainArgparse:
    """Argument parsing for python -m cortex."""

    def test_main_sets_workspace_env(self):
        """--workspace flag sets CORTEX_WORKSPACE_ID env var."""
        with patch("cortex.__main__.asyncio.run") as mock_run:
            with patch("cortex.__main__.argparse.ArgumentParser.parse_known_args") as mock_parse:
                mock_parse.return_value = (MagicMock(workspace_id="researcher"), [])
                from cortex.__main__ import main
                main()
                assert os.environ.get("CORTEX_WORKSPACE_ID") == "researcher"

    def test_main_no_workspace_flag(self):
        """Without --workspace, CORTEX_WORKSPACE_ID is not set."""
        # Save previous value
        prev = os.environ.pop("CORTEX_WORKSPACE_ID", None)
        with patch("cortex.__main__.asyncio.run") as mock_run:
            with patch("cortex.__main__.argparse.ArgumentParser.parse_known_args") as mock_parse:
                mock_parse.return_value = (MagicMock(workspace_id=None), [])
                from cortex.__main__ import main
                main()
                assert "CORTEX_WORKSPACE_ID" not in os.environ or os.environ["CORTEX_WORKSPACE_ID"] == ""
        # Restore
        if prev is not None:
            os.environ["CORTEX_WORKSPACE_ID"] = prev
