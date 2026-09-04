from __future__ import annotations

from pymilvus import (  # type: ignore[import-untyped]
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)


class MilvusDenseIndex:
    """真实 Milvus 稠密向量索引，按余弦相似度检索。"""

    def __init__(
        self,
        *,
        uri: str = "http://localhost:19530",
        collection_name: str = "dense_vectors",
        dim: int,
    ) -> None:
        connections.connect(alias="default", uri=uri)
        self._collection_name = collection_name
        self._dim = dim
        self._collection = self._ensure_collection()

    def _ensure_collection(self) -> Collection:
        if utility.has_collection(self._collection_name):
            return Collection(self._collection_name)
        fields = [
            FieldSchema(
                name="id",
                dtype=DataType.VARCHAR,
                is_primary=True,
                max_length=512,
            ),
            FieldSchema(
                name="vector",
                dtype=DataType.FLOAT_VECTOR,
                dim=self._dim,
            ),
        ]
        schema = CollectionSchema(fields, description="dense retrieval vectors")
        collection = Collection(self._collection_name, schema)
        collection.create_index(
            "vector",
            {"metric_type": "COSINE", "index_type": "AUTOINDEX", "params": {}},
        )
        return collection

    def add(self, vector_id: str, vector: list[float]) -> None:
        if not vector:
            raise ValueError("vector must not be empty")
        if len(vector) != self._dim:
            raise ValueError(
                f"vector dim mismatch: expected {self._dim}, got {len(vector)}"
            )
        self._collection.insert([[vector_id], [vector]])
        self._collection.flush()

    def search(
        self, query: list[float], top_k: int = 10
    ) -> list[tuple[str, float]]:
        if not query:
            raise ValueError("query must not be empty")
        self._collection.load()
        results = self._collection.search(
            [query],
            "vector",
            {"metric_type": "COSINE", "params": {}},
            limit=top_k,
            output_fields=["id"],
        )
        hits: list[tuple[str, float]] = []
        for hit in results[0]:
            hits.append((str(hit.entity.get("id")), float(hit.distance)))
        return hits
