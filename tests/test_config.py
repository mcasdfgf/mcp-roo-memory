"""Tests for CortexConfig — defaults, env overrides, field types."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from cortex.config import CortexConfig


class TestCortexConfigDefaults:
    """Default values for all configuration fields."""

    def test_db_path_default(self):
        config = CortexConfig()
        assert config.db_path == "cortex.db"

    def test_qdrant_defaults(self):
        config = CortexConfig()
        assert config.qdrant_host == "localhost"
        assert config.qdrant_port == 6333
        assert config.qdrant_timeout == 30

    def test_collection_name_default(self):
        config = CortexConfig()
        assert config.collection_name == "cortex_memory"

    def test_embedding_defaults(self):
        config = CortexConfig()
        assert config.embedding_model == "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        assert config.embedding_size == 384

    def test_desktop_defaults(self):
        config = CortexConfig()
        assert config.archive_days_threshold == 7
        assert config.desktop_hot_limit == 5
        assert config.desktop_history_limit == 10

    def test_walk_relation_types_default(self):
        config = CortexConfig()
        assert config.walk_relation_types == ["sequel_to", "derives_from", "leads_to"]


class TestCortexConfigEnvOverride:
    """Override configuration via environment variables with CORTEX_ prefix."""

    def test_db_path_override(self):
        with patch.dict(os.environ, {"CORTEX_DB_PATH": "/tmp/test.db"}, clear=False):
            config = CortexConfig()
            assert config.db_path == "/tmp/test.db"

    def test_qdrant_host_override(self):
        with patch.dict(os.environ, {"CORTEX_QDRANT_HOST": "qdrant.example.com"}, clear=False):
            config = CortexConfig()
            assert config.qdrant_host == "qdrant.example.com"

    def test_qdrant_port_override(self):
        with patch.dict(os.environ, {"CORTEX_QDRANT_PORT": "7333"}, clear=False):
            config = CortexConfig()
            assert config.qdrant_port == 7333

    def test_collection_name_override(self):
        with patch.dict(os.environ, {"CORTEX_COLLECTION_NAME": "my_memory"}, clear=False):
            config = CortexConfig()
            assert config.collection_name == "my_memory"

    def test_embedding_model_override(self):
        with patch.dict(os.environ, {"CORTEX_EMBEDDING_MODEL": "BAAI/bge-large-en-v1.5"}, clear=False):
            config = CortexConfig()
            assert config.embedding_model == "BAAI/bge-large-en-v1.5"

    def test_archive_days_override(self):
        with patch.dict(os.environ, {"CORTEX_ARCHIVE_DAYS_THRESHOLD": "30"}, clear=False):
            config = CortexConfig()
            assert config.archive_days_threshold == 30

    def test_desktop_hot_limit_override(self):
        with patch.dict(os.environ, {"CORTEX_DESKTOP_HOT_LIMIT": "10"}, clear=False):
            config = CortexConfig()
            assert config.desktop_hot_limit == 10


class TestResolveWorkspaceId:
    """resolve_workspace_id() — resolution chain tests."""

    def test_explicit_arg(self):
        with patch.dict(os.environ, {}, clear=True):
            from cortex.config import resolve_workspace_id
            result = resolve_workspace_id(explicit="my-project")
            assert result == "my-project"

    def test_env_var(self):
        with patch.dict(os.environ, {"CORTEX_WORKSPACE_ID": "from-env"}, clear=True):
            from cortex.config import resolve_workspace_id
            result = resolve_workspace_id(explicit=None)
            assert result == "from-env"

    def test_env_var_takes_precedence_over_explicit_empty(self):
        with patch.dict(os.environ, {"CORTEX_WORKSPACE_ID": "env-ws"}, clear=True):
            from cortex.config import resolve_workspace_id
            result = resolve_workspace_id(explicit="")
            assert result == "env-ws"

    def test_cwd_basename(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("cortex.config.Path.cwd", return_value=Path("/projects/my-project")):
                from cortex.config import resolve_workspace_id
                result = resolve_workspace_id(explicit=None)
                assert result == "my-project"

    def test_fallback_default(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("cortex.config.Path.cwd", return_value=Path("/")):
                from cortex.config import resolve_workspace_id
                result = resolve_workspace_id(explicit=None)
                assert result == "default"

    def test_explicit_overrides_env(self):
        with patch.dict(os.environ, {"CORTEX_WORKSPACE_ID": "env-ws"}, clear=True):
            from cortex.config import resolve_workspace_id
            result = resolve_workspace_id(explicit="explicit-ws")
            assert result == "explicit-ws"


class TestCortexConfigEnvOverrideExtra:
    """Additional env overrides not covered by main env test class."""

    def test_desktop_history_limit(self):
        with patch.dict(os.environ, {"CORTEX_DESKTOP_HISTORY_LIMIT": "25"}, clear=False):
            config = CortexConfig()
            assert config.desktop_history_limit == 25

    def test_qdrant_timeout(self):
        with patch.dict(os.environ, {"CORTEX_QDRANT_TIMEOUT": "60"}, clear=False):
            config = CortexConfig()
            assert config.qdrant_timeout == 60

    def test_workspace_id_empty_by_default(self):
        config = CortexConfig()
        assert config.workspace_id == ""


class TestCortexConfigFieldTypes:
    """Ensure fields have the correct Python types."""

    def test_db_path_is_str(self):
        assert isinstance(CortexConfig().db_path, str)

    def test_qdrant_port_is_int(self):
        assert isinstance(CortexConfig().qdrant_port, int)

    def test_qdrant_timeout_is_int(self):
        assert isinstance(CortexConfig().qdrant_timeout, int)

    def test_embedding_size_is_int(self):
        assert isinstance(CortexConfig().embedding_size, int)

    def test_archive_days_is_int(self):
        assert isinstance(CortexConfig().archive_days_threshold, int)

    def test_desktop_hot_limit_is_int(self):
        assert isinstance(CortexConfig().desktop_hot_limit, int)

    def test_walk_types_is_list(self):
        assert isinstance(CortexConfig().walk_relation_types, list)
