"""Vector Manager — Qdrant integration (API v1.18), indexing and search."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Optional

from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    DatetimeRange,
    FieldCondition,
    Filter,
    MatchValue,
)

from .config import config
from .models import NodeType

logger = logging.getLogger(__name__)

# Neutral name for the search vector (replaces model-specific "fast-bge-small-en")
NAMED_VECTOR = "primary"

# Node types that are vectorized
VECTORIZABLE_TYPES = {
    NodeType.ENTITY, NodeType.FACT, NodeType.DECISION, NodeType.CHUNK,
    NodeType.THOUGHT, NodeType.QUESTION, NodeType.HYPOTHESIS,
    NodeType.ACTION, NodeType.ERROR, NodeType.NOTE,
    NodeType.PATTERN, NodeType.GOAL, NodeType.CONSTRAINT,
}

INITIALIZED_KEY = "_cortex_collection_ready"


class VectorManager:
    """Vector index management in Qdrant."""

    _embedding_model: Any = None  # Lazy singleton for fastembed

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        collection: str | None = None,
    ):
        self.client = QdrantClient(
            host=host or config.qdrant_host,
            port=port or config.qdrant_port,
            timeout=config.qdrant_timeout,
        )
        self.collection = collection or config.collection_name
        self._initialized = False

    def _get_embedding_model(self) -> Any:
        """Lazy singleton for the fastembed TextEmbedding model."""
        if VectorManager._embedding_model is None:
            from fastembed import TextEmbedding
            VectorManager._embedding_model = TextEmbedding(config.embedding_model)
        return VectorManager._embedding_model

    def ensure_collection(self) -> None:
        """
        Create the collection if it does not exist.

        The collection has two vectors of the same dimensionality (384d):
          - "": default vector (for the Qdrant admin UI)
          - "primary": named vector (for query_points search)
        On upsert, the embedding is duplicated into both vectors.
        """
        if self._initialized:
            return
        try:
            cols = self.client.get_collections().collections
            exists = any(c.name == self.collection for c in cols)
            if not exists:
                self._create_collection()
            else:
                # Check: collection has correct vector config for UI + search
                info = self.client.get_collection(self.collection)
                existing_config = getattr(info, 'config', None)
                if existing_config:
                    params = getattr(existing_config, 'params', None)
                    if params:
                        vectors = getattr(params, 'vectors', None)
                        needs_recreate = False

                        if isinstance(vectors, dict):
                            # Named vector config — check for both default and named
                            has_default = "" in vectors
                            has_named = NAMED_VECTOR in vectors
                            if not has_default or not has_named:
                                logger.warning(
                                    f"Qdrant collection has vectors {list(vectors.keys())} "
                                    f"— expected ['', '{NAMED_VECTOR}']. Recreating..."
                                )
                                needs_recreate = True
                        elif vectors is not None:
                            # Single VectorParams — only default exists, no named vector
                            logger.warning(
                                f"Qdrant collection has single default vector only "
                                f"— missing named vector '{NAMED_VECTOR}'. Recreating..."
                            )
                            needs_recreate = True

                        if needs_recreate:
                            self.client.delete_collection(self.collection)
                            self._create_collection()
                            logger.info("Qdrant: collection recreated with correct vector config")
            self._initialized = True
        except Exception as e:
            logger.error(f"Qdrant ensure collection error: {e}")

    def _create_collection(self) -> None:
        """Create the collection with default + named vector."""
        from qdrant_client.http.models import VectorParams, Distance
        self.client.create_collection(
            collection_name=self.collection,
            vectors_config={
                "": VectorParams(size=config.embedding_size, distance=Distance.COSINE),
                NAMED_VECTOR: VectorParams(size=config.embedding_size, distance=Distance.COSINE),
            },
        )

    def get_collection_status(self) -> Optional[str]:
        try:
            info = self.client.get_collection(self.collection)
            return info.status  # type: ignore
        except Exception:
            return None

    def is_ready(self) -> bool:
        try:
            return self.get_collection_status() is not None
        except Exception:
            return False

    def _stable_id(self, node_id: str) -> int:
        """Generate a stable integer ID from a node_id using UUID5."""
        return uuid.uuid5(uuid.NAMESPACE_DNS, node_id).int % (2**63)

    def index_node(self, node_id: str, text: str, metadata: dict[str, Any]) -> bool:
        """
        Index a node in Qdrant.

        Computes the embedding locally via fastembed.
        The embedding is duplicated into the default vector ("") and the
        named vector (primary). Search uses 'primary',
        while the admin UI uses the default vector.
        """
        try:
            model = self._get_embedding_model()
            embedding = list(model.embed(text))[0]

            self.client.upsert(
                collection_name=self.collection,
                points=[{
                    "id": self._stable_id(node_id),
                    "vector": {
                        "": list(embedding),
                        NAMED_VECTOR: list(embedding),
                    },
                    "payload": {
                        "node_id": node_id,
                        "text": text[:500],
                        "workspace_id": metadata.get("workspace_id", ""),
                        "node_type": metadata.get("node_type", ""),
                        "layer": metadata.get("layer", "fact"),
                        "tags": json.dumps(metadata.get("tags", [])),
                        "status": metadata.get("status", "active"),
                        "created_at": metadata.get("created_at", ""),
                    },
                }],
            )
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"Qdrant index error: {e}")
            return False

    def remove_node_vector(self, node_id: str) -> bool:
        """Remove a node's vector from Qdrant."""
        try:
            self.client.delete(
                collection_name=self.collection,
                points_selector=Filter(
                    must=[FieldCondition(key="node_id", match=MatchValue(value=node_id))]
                ),
            )
            return True
        except Exception as e:
            logger.error(f"Qdrant delete error: {e}")
            return False

    def search(
        self,
        query: str,
        top_k: int = 10,
        workspace_id: Optional[str] = None,
        node_type: Optional[str] = None,
        status_filter: Optional[str] = "active",
        time_from: Optional[str] = None,
        time_to: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Semantic search.

        1. Computes the query embedding locally via fastembed
        2. Searches using the named vector primary via query_points
        3. Filters by optional time range (created_at in Qdrant payload)
        """
        filter_conditions = []
        if workspace_id:
            filter_conditions.append(
                FieldCondition(key="workspace_id", match=MatchValue(value=workspace_id))
            )
        if node_type:
            filter_conditions.append(
                FieldCondition(key="node_type", match=MatchValue(value=node_type))
            )
        if status_filter:
            filter_conditions.append(
                FieldCondition(key="status", match=MatchValue(value=status_filter))
            )
        if time_from or time_to:
            range_kwargs = {}
            if time_from:
                range_kwargs["gte"] = time_from
            if time_to:
                range_kwargs["lte"] = time_to
            filter_conditions.append(
                FieldCondition(
                    key="created_at",
                    range=DatetimeRange(**range_kwargs),
                )
            )

        query_filter = Filter(must=filter_conditions) if filter_conditions else None

        try:
            model = self._get_embedding_model()
            embedding = list(model.embed(query))[0]

            results = self.client.query_points(
                collection_name=self.collection,
                query=list(embedding),
                using=NAMED_VECTOR,
                query_filter=query_filter,
                limit=top_k,
            )

            points = []
            if results and hasattr(results, 'points') and results.points:
                points = results.points

            output = []
            for r in points:
                payload = r.payload or {}
                output.append({
                    "node_id": payload.get("node_id", ""),
                    "node_type": payload.get("node_type", "unknown"),
                    "layer": payload.get("layer", "fact"),
                    "text": payload.get("text", ""),
                    "score": r.score,
                    "metadata": payload,
                })
            return output
        except Exception as e:
            logger.error(f"Qdrant search error: {e}")
            return []

    @staticmethod
    def get_layer_for_type(node_type: NodeType) -> str:
        if node_type in {NodeType.ENTITY}:
            return "entity"
        if node_type in {NodeType.CHUNK}:
            return "chunk"
        return "fact"

    @staticmethod
    def should_vectorize(node_type: NodeType) -> bool:
        return node_type in VECTORIZABLE_TYPES
