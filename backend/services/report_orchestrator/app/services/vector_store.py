"""
Vector Store Service using Qdrant
向量存储服务（使用Qdrant）

Provides vector database operations for knowledge base management.
提供知识库管理的向量数据库操作。
"""

import math
import os
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any

from google import genai
from google.genai import types
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue


class VectorStoreService:
    """Service for managing documents in Qdrant vector database"""

    def __init__(
        self,
        qdrant_url: str = "http://qdrant:6333",
        collection_name: str = "knowledge_base",
    ):
        """
        Initialize vector store service

        Args:
            qdrant_url: URL of Qdrant server
            collection_name: Name of the collection to use
        """
        self.client = QdrantClient(url=qdrant_url)
        self.collection_name = collection_name

        # Gemini embeddings configuration (remote API, no local model download)
        self.embedding_model = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
        self.vector_size = int(os.getenv("GEMINI_EMBEDDING_DIMENSION", "768"))
        self.document_task_type = os.getenv("GEMINI_EMBEDDING_TASK_DOCUMENT", "RETRIEVAL_DOCUMENT")
        self.query_task_type = os.getenv("GEMINI_EMBEDDING_TASK_QUERY", "RETRIEVAL_QUERY")
        self.auto_recreate_on_dim_mismatch = os.getenv("QDRANT_AUTO_RECREATE_COLLECTION", "true").lower() == "true"

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY is required for Gemini embeddings")
        self.genai_client = genai.Client(api_key=api_key)

        # Create collection if it doesn't exist
        self._ensure_collection_exists()

    def _extract_vector_size(self, collection_info: Any) -> Optional[int]:
        """Try to read vector size from Qdrant collection config."""
        try:
            vectors_cfg = collection_info.config.params.vectors
            if hasattr(vectors_cfg, "size"):
                return int(vectors_cfg.size)
            if isinstance(vectors_cfg, dict):
                # Named vectors mode
                for _, cfg in vectors_cfg.items():
                    if hasattr(cfg, "size"):
                        return int(cfg.size)
            return None
        except Exception:
            return None

    def _create_collection(self):
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
        )

    def _ensure_collection_exists(self):
        """Create collection if it doesn't exist"""
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.collection_name not in collection_names:
                self._create_collection()
                print(f"[VectorStore] Created collection: {self.collection_name}")
            else:
                info = self.client.get_collection(collection_name=self.collection_name)
                existing_size = self._extract_vector_size(info)
                if existing_size is not None and existing_size != self.vector_size:
                    msg = (
                        f"[VectorStore] Collection '{self.collection_name}' dim mismatch: "
                        f"existing={existing_size}, expected={self.vector_size}"
                    )
                    if self.auto_recreate_on_dim_mismatch:
                        print(f"{msg}. Recreating collection...")
                        self.client.delete_collection(collection_name=self.collection_name)
                        self._create_collection()
                        print(f"[VectorStore] Recreated collection: {self.collection_name}")
                    else:
                        raise RuntimeError(
                            f"{msg}. Set QDRANT_AUTO_RECREATE_COLLECTION=true or manually migrate the collection."
                        )
                else:
                    print(f"[VectorStore] Collection already exists: {self.collection_name}")
        except Exception as e:
            print(f"[VectorStore] Error ensuring collection exists: {e}")
            raise

    def _normalize_vector(self, values: List[float]) -> List[float]:
        # Gemini docs recommend normalization for non-3072 dimensions.
        # Normalizing always is safe for cosine search and keeps behavior stable.
        norm = math.sqrt(sum(v * v for v in values))
        if norm <= 0:
            return values
        return [v / norm for v in values]

    def _fit_dimension(self, values: List[float]) -> List[float]:
        if len(values) == self.vector_size:
            return values
        if len(values) > self.vector_size:
            return values[: self.vector_size]
        return values + [0.0] * (self.vector_size - len(values))

    def _embed_contents(self, contents: List[str], task_type: str) -> List[List[float]]:
        cleaned_contents = [(c if c and c.strip() else " ") for c in contents]
        try:
            config = types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=self.vector_size,
            )
            response = self.genai_client.models.embed_content(
                model=self.embedding_model,
                contents=cleaned_contents,
                config=config,
            )
        except TypeError:
            # Backward compatibility with older google-genai SDKs.
            config = types.EmbedContentConfig(task_type=task_type)
            response = self.genai_client.models.embed_content(
                model=self.embedding_model,
                contents=cleaned_contents,
                config=config,
            )

        vectors: List[List[float]] = []
        embedding_items = getattr(response, "embeddings", None) or []
        if not embedding_items:
            single = getattr(response, "embedding", None)
            if single is not None:
                embedding_items = [single]

        for embedding_obj in embedding_items:
            raw_values = list(embedding_obj.values)
            fitted = self._fit_dimension(raw_values)
            vectors.append(self._normalize_vector(fitted))

        if len(vectors) != len(cleaned_contents):
            raise RuntimeError(
                f"Gemini embedding count mismatch: expected {len(cleaned_contents)}, got {len(vectors)}"
            )
        return vectors

    def _embed_text(self, text: str, task_type: str) -> List[float]:
        return self._embed_contents([text], task_type=task_type)[0]

    def add_document(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        doc_id: Optional[str] = None
    ) -> str:
        """
        Add a document to the vector store

        Args:
            text: Document text content
            metadata: Optional metadata (title, source, date, etc.)
            doc_id: Optional document ID (will be generated if not provided)

        Returns:
            Document ID
        """
        if not doc_id:
            doc_id = str(uuid.uuid4())

        # Generate embedding
        embedding = self._embed_text(text, task_type=self.document_task_type)

        # Prepare payload
        payload = metadata or {}
        payload.update({
            "text": text,
            "created_at": datetime.now().isoformat(),
            "doc_id": doc_id
        })

        # Upload point
        point = PointStruct(
            id=doc_id,
            vector=embedding,
            payload=payload
        )

        self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )

        print(f"[VectorStore] Added document: {doc_id}")
        return doc_id

    def add_documents_batch(
        self,
        documents: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Add multiple documents in batch

        Args:
            documents: List of documents, each with 'text' and optional 'metadata' and 'doc_id'

        Returns:
            List of document IDs
        """
        points = []
        doc_ids = []
        texts = []
        metadata_list = []

        for doc in documents:
            text = doc.get('text', '')
            metadata = doc.get('metadata', {})
            doc_id = doc.get('doc_id', str(uuid.uuid4()))
            texts.append(text)
            metadata_list.append(metadata)
            doc_ids.append(doc_id)

        embeddings = self._embed_contents(texts, task_type=self.document_task_type)

        for i, text in enumerate(texts):
            metadata = metadata_list[i]
            doc_id = doc_ids[i]
            embedding = embeddings[i]

            # Prepare payload
            payload = metadata.copy()
            payload.update({
                "text": text,
                "created_at": datetime.now().isoformat(),
                "doc_id": doc_id
            })

            points.append(PointStruct(
                id=doc_id,
                vector=embedding,
                payload=payload
            ))

        # Batch upload
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )

        print(f"[VectorStore] Added {len(points)} documents in batch")
        return doc_ids

    def search(
        self,
        query: str,
        limit: int = 10,
        score_threshold: float = 0.5,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents

        Args:
            query: Search query text
            limit: Maximum number of results
            score_threshold: Minimum similarity score (0-1)
            filter_conditions: Optional metadata filters

        Returns:
            List of search results with scores and metadata
        """
        # Generate query embedding
        query_embedding = self._embed_text(query, task_type=self.query_task_type)

        # Prepare filter if provided
        query_filter = None
        if filter_conditions:
            conditions = []
            for key, value in filter_conditions.items():
                conditions.append(FieldCondition(
                    key=key,
                    match=MatchValue(value=value)
                ))
            if conditions:
                query_filter = Filter(must=conditions)

        # Search (compatible with old/new qdrant-client)
        results = self._query_points_compat(
            query_embedding=query_embedding,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=query_filter,
        )

        # Format results
        formatted_results = []
        for result in results:
            payload = result.get("payload", {}) if isinstance(result, dict) else (result.payload or {})
            row_id = result.get("id") if isinstance(result, dict) else result.id
            row_score = result.get("score", 0.0) if isinstance(result, dict) else result.score
            formatted_results.append({
                "id": row_id,
                "score": row_score,
                "text": payload.get("text", ""),
                "metadata": {k: v for k, v in payload.items() if k not in ["text", "doc_id"]},
            })

        print(f"[VectorStore] Found {len(formatted_results)} results for query")
        return formatted_results

    def _query_points_compat(
        self,
        query_embedding: List[float],
        limit: int,
        score_threshold: float,
        query_filter: Optional[Filter],
    ) -> List[Any]:
        if hasattr(self.client, "query_points"):
            try:
                response = self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_embedding,
                    limit=limit,
                    score_threshold=score_threshold,
                    query_filter=query_filter,
                )
            except TypeError:
                response = self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_embedding,
                    limit=limit,
                    score_threshold=score_threshold,
                    filter=query_filter,
                )
            return self._extract_rows(response)

        if hasattr(self.client, "search"):
            return self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=query_filter,
            )

        raise RuntimeError("Qdrant client does not support query_points/search APIs")

    @staticmethod
    def _extract_rows(response: Any) -> List[Any]:
        if response is None:
            return []
        if isinstance(response, list):
            return response
        points = getattr(response, "points", None)
        if points is not None:
            return list(points)
        result = getattr(response, "result", None)
        if result is None:
            return []
        if isinstance(result, list):
            return result
        result_points = getattr(result, "points", None)
        if result_points is not None:
            return list(result_points)
        return []

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific document by ID

        Args:
            doc_id: Document ID

        Returns:
            Document data or None if not found
        """
        try:
            result = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[doc_id]
            )

            if result:
                point = result[0]
                return {
                    "id": point.id,
                    "text": point.payload.get("text", ""),
                    "metadata": {k: v for k, v in point.payload.items() if k not in ["text", "doc_id"]}
                }
            return None
        except Exception as e:
            print(f"[VectorStore] Error retrieving document {doc_id}: {e}")
            return None

    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document by ID

        Args:
            doc_id: Document ID

        Returns:
            True if successful
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[doc_id]
            )
            print(f"[VectorStore] Deleted document: {doc_id}")
            return True
        except Exception as e:
            print(f"[VectorStore] Error deleting document {doc_id}: {e}")
            return False

    def list_documents(
        self,
        limit: int = 100,
        offset: int = 0,
        filter_conditions: Optional[Dict[str, Any]] = None,
        include_full_text: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List documents with pagination

        Args:
            limit: Maximum number of documents to return
            offset: Number of documents to skip
            filter_conditions: Optional metadata filters
            include_full_text: Whether to return full text (for indexing/export)

        Returns:
            List of documents
        """
        # Prepare filter if provided
        query_filter = None
        if filter_conditions:
            conditions = []
            for key, value in filter_conditions.items():
                conditions.append(FieldCondition(
                    key=key,
                    match=MatchValue(value=value)
                ))
            if conditions:
                query_filter = Filter(must=conditions)

        if limit <= 0:
            return []
        if offset < 0:
            offset = 0

        # Scroll through documents. Qdrant's scroll offset is point-id based, not integer skip.
        # Implement stable skip+take pagination in application layer.
        try:
            batch_size = max(64, min(512, offset + limit))
            remaining_skip = offset
            remaining_take = limit
            page_offset = None
            result = []

            while remaining_take > 0:
                page_points, next_page_offset = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=batch_size,
                    offset=page_offset,
                    with_payload=True,
                    with_vectors=False,
                    scroll_filter=query_filter
                )
                if not page_points:
                    break

                start_idx = min(remaining_skip, len(page_points))
                remaining_skip -= start_idx

                if start_idx < len(page_points):
                    for point in page_points[start_idx:]:
                        result.append(point)
                        remaining_take -= 1
                        if remaining_take <= 0:
                            break

                if next_page_offset is None:
                    break
                page_offset = next_page_offset

            documents = []
            for point in result:
                raw_text = point.payload.get("text", "")
                preview_text = raw_text if len(raw_text) <= 200 else (raw_text[:200] + "...")
                documents.append({
                    "id": point.id,
                    "text": raw_text if include_full_text else preview_text,
                    "metadata": {k: v for k, v in point.payload.items() if k not in ["text", "doc_id"]}
                })

            return documents
        except Exception as e:
            print(f"[VectorStore] Error listing documents: {e}")
            return []

    def get_collection_info(self) -> Dict[str, Any]:
        """
        Get collection statistics

        Returns:
            Collection information
        """
        try:
            info = self.client.get_collection(collection_name=self.collection_name)
            return {
                "collection_name": self.collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status
            }
        except Exception as e:
            print(f"[VectorStore] Error getting collection info: {e}")
            return {}

    def encode_text(self, text: str) -> List[float]:
        """
        Generate embedding for text (useful for external use)

        Args:
            text: Input text

        Returns:
            Embedding vector
        """
        return self._embed_text(text, task_type=self.document_task_type)
