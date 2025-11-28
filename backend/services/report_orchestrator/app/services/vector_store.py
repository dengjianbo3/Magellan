"""
Vector Store Service using Qdrant
向量存储服务（使用Qdrant）

Provides vector database operations for knowledge base management.
提供知识库管理的向量数据库操作。
"""

from typing import List, Dict, Optional, Any
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer
import uuid
from datetime import datetime


class VectorStoreService:
    """Service for managing documents in Qdrant vector database"""

    def __init__(self, qdrant_url: str = "http://qdrant:6333", collection_name: str = "knowledge_base"):
        """
        Initialize vector store service

        Args:
            qdrant_url: URL of Qdrant server
            collection_name: Name of the collection to use
        """
        self.client = QdrantClient(url=qdrant_url)
        self.collection_name = collection_name

        # Initialize embedding model
        # Using a lightweight multilingual model for Chinese + English support
        self.embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        self.vector_size = 384  # Dimension of the model

        # Create collection if it doesn't exist
        self._ensure_collection_exists()

    def _ensure_collection_exists(self):
        """Create collection if it doesn't exist"""
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE)
                )
                print(f"[VectorStore] Created collection: {self.collection_name}")
            else:
                print(f"[VectorStore] Collection already exists: {self.collection_name}")
        except Exception as e:
            print(f"[VectorStore] Error ensuring collection exists: {e}")
            raise

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
        embedding = self.embedding_model.encode(text).tolist()

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

        for doc in documents:
            text = doc.get('text', '')
            metadata = doc.get('metadata', {})
            doc_id = doc.get('doc_id', str(uuid.uuid4()))

            # Generate embedding
            embedding = self.embedding_model.encode(text).tolist()

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
            doc_ids.append(doc_id)

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
        query_embedding = self.embedding_model.encode(query).tolist()

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

        # Search
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=query_filter
        )

        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                "id": result.id,
                "score": result.score,
                "text": result.payload.get("text", ""),
                "metadata": {k: v for k, v in result.payload.items() if k not in ["text", "doc_id"]}
            })

        print(f"[VectorStore] Found {len(formatted_results)} results for query")
        return formatted_results

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
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        List documents with pagination

        Args:
            limit: Maximum number of documents to return
            offset: Number of documents to skip
            filter_conditions: Optional metadata filters

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

        # Scroll through documents
        try:
            result, _ = self.client.scroll(
                collection_name=self.collection_name,
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False,
                scroll_filter=query_filter
            )

            documents = []
            for point in result:
                documents.append({
                    "id": point.id,
                    "text": point.payload.get("text", "")[:200] + "...",  # Preview only
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
        return self.embedding_model.encode(text).tolist()
