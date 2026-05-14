"""Tests for Cortex factory assembly — start, stop, is_ready."""

from __future__ import annotations

from unittest.mock import patch

from cortex import Cortex
from cortex.graph import GraphManager
from cortex.desktop import DesktopManager


class TestCortexAssembly:
    """Cortex factory assembly — start, stop, is_ready."""

    def test_create_cortex(self):
        cortex = Cortex(db_path=":memory:")
        assert cortex.db is not None
        assert cortex.vector is not None
        assert cortex.graph is not None
        assert cortex.desktop is not None
        assert not cortex.is_ready

    def test_start_stop(self, db_manager, vector_manager):
        cortex = Cortex(db_path=":memory:")
        cortex.db = db_manager
        cortex.vector = vector_manager
        cortex.graph = GraphManager(db=db_manager, vector=vector_manager)
        cortex.desktop = DesktopManager(db=db_manager, graph=cortex.graph)

        cortex.start()
        assert cortex.db.conn is not None

        cortex.stop()
        assert cortex.db.conn is None

    def test_is_ready_true(self, db_manager, vector_manager):
        with patch.object(vector_manager, "is_ready", return_value=True):
            cortex = Cortex(db_path=":memory:")
            cortex.db = db_manager
            cortex.vector = vector_manager
            cortex.db.connect()
            assert cortex.is_ready

    def test_is_ready_false_db_not_connected(self, vector_manager):
        cortex = Cortex(db_path=":memory:")
        cortex.vector = vector_manager
        cortex.vector._initialized = True
        assert not cortex.is_ready

    def test_is_ready_false_vector_not_ready(self, db_manager, monkeypatch):
        cortex = Cortex(db_path=":memory:")
        cortex.db = db_manager
        cortex.db.connect()
        # Mock vector.is_ready() to return False
        monkeypatch.setattr(cortex.vector, "is_ready", lambda: False)
        assert not cortex.is_ready
