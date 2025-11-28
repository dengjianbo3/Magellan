"""
RAG Service (Retrieval-Augmented Generation)
RAG服务（检索增强生成）

Provides advanced search capabilities with hybrid search, reranking, and context assembly.
提供混合搜索、重排序和上下文组装的高级搜索能力。
"""

from typing import List, Dict, Any, Optional, Tuple
from rank_bm25 import BM25Okapi
import numpy as np
from sentence_transformers import CrossEncoder
import re


class RAGService:
    """Service for advanced retrieval and context assembly"""

    def __init__(self, vector_store_service):
        """
        Initialize RAG service

        Args:
            vector_store_service: Instance of VectorStoreService
        """
        self.vector_store = vector_store_service

        # Initialize cross-encoder for reranking (lightweight multilingual model)
        # This model scores query-document pairs for better relevance
        try:
            self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
            print("[RAGService] ✅ Cross-encoder reranker initialized")
        except Exception as e:
            print(f"[RAGService] ⚠️ Failed to load reranker: {e}. Will use without reranking.")
            self.reranker = None

        # BM25 index cache (will be built on-demand)
        self.bm25_index = None
        self.bm25_documents = []
        self.bm25_doc_ids = []

    def _build_bm25_index(self, documents: List[Dict[str, Any]]) -> None:
        """
        Build BM25 index from documents

        Args:
            documents: List of documents with 'text' and 'id' fields
        """
        if not documents:
            print("[RAGService] No documents to index for BM25")
            return

        # Tokenize documents for BM25
        tokenized_docs = []
        self.bm25_documents = []
        self.bm25_doc_ids = []

        for doc in documents:
            text = doc.get('text', '')
            doc_id = doc.get('id', '')

            # Simple tokenization (split by whitespace and punctuation)
            tokens = self._tokenize(text)

            tokenized_docs.append(tokens)
            self.bm25_documents.append(text)
            self.bm25_doc_ids.append(doc_id)

        # Build BM25 index
        self.bm25_index = BM25Okapi(tokenized_docs)
        print(f"[RAGService] ✅ BM25 index built with {len(documents)} documents")

    def _tokenize(self, text: str) -> List[str]:
        """
        Simple tokenization for BM25

        Args:
            text: Input text

        Returns:
            List of tokens
        """
        # Convert to lowercase and split by whitespace/punctuation
        text = text.lower()
        tokens = re.findall(r'\w+', text)
        return tokens

    def _bm25_search(self, query: str, top_k: int = 100) -> List[Tuple[str, float]]:
        """
        Perform BM25 keyword search

        Args:
            query: Search query
            top_k: Number of top results to return

        Returns:
            List of (doc_id, score) tuples
        """
        if self.bm25_index is None:
            print("[RAGService] BM25 index not built, skipping BM25 search")
            return []

        # Tokenize query
        query_tokens = self._tokenize(query)

        # Get BM25 scores
        scores = self.bm25_index.get_scores(query_tokens)

        # Get top-k results
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # Only include non-zero scores
                doc_id = self.bm25_doc_ids[idx]
                results.append((doc_id, float(scores[idx])))

        print(f"[RAGService] BM25 search found {len(results)} results")
        return results

    def _reciprocal_rank_fusion(
        self,
        vector_results: List[Dict[str, Any]],
        bm25_results: List[Tuple[str, float]],
        k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Combine results from vector search and BM25 using Reciprocal Rank Fusion

        Args:
            vector_results: Results from vector search
            bm25_results: Results from BM25 search
            k: Constant for RRF formula (default 60)

        Returns:
            Fused and ranked results
        """
        # Build score dictionaries
        rrf_scores = {}

        # Add vector search results
        for rank, result in enumerate(vector_results):
            doc_id = result['id']
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (k + rank + 1)

        # Add BM25 results
        for rank, (doc_id, _) in enumerate(bm25_results):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (k + rank + 1)

        # Sort by RRF score
        sorted_doc_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

        # Build result list with original data
        result_map = {r['id']: r for r in vector_results}

        fused_results = []
        for doc_id in sorted_doc_ids:
            if doc_id in result_map:
                result = result_map[doc_id].copy()
                result['rrf_score'] = rrf_scores[doc_id]
                fused_results.append(result)

        print(f"[RAGService] RRF fusion combined {len(fused_results)} unique documents")
        return fused_results

    def _rerank_results(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Rerank results using cross-encoder model

        Args:
            query: Search query
            results: List of search results
            top_k: Number of top results to return after reranking

        Returns:
            Reranked results
        """
        if not self.reranker or not results:
            return results[:top_k]

        try:
            # Prepare query-document pairs
            pairs = [[query, result['text'][:512]] for result in results]  # Limit text length

            # Get cross-encoder scores
            scores = self.reranker.predict(pairs)

            # Add scores to results
            for i, result in enumerate(results):
                result['rerank_score'] = float(scores[i])

            # Sort by rerank score
            reranked = sorted(results, key=lambda x: x['rerank_score'], reverse=True)

            print(f"[RAGService] Reranked {len(results)} results, returning top {top_k}")
            return reranked[:top_k]

        except Exception as e:
            print(f"[RAGService] Error during reranking: {e}. Returning original results.")
            return results[:top_k]

    def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        vector_weight: float = 0.7,
        bm25_weight: float = 0.3,
        use_reranking: bool = True,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining vector search and BM25

        Args:
            query: Search query
            top_k: Number of final results to return
            vector_weight: Weight for vector search (not used in RRF, kept for API compatibility)
            bm25_weight: Weight for BM25 search (not used in RRF, kept for API compatibility)
            use_reranking: Whether to apply reranking
            filter_conditions: Optional metadata filters for vector search

        Returns:
            List of search results with scores
        """
        print(f"[RAGService] Starting hybrid search for query: '{query[:50]}...'")

        # Step 1: Vector search
        vector_results = self.vector_store.search(
            query=query,
            limit=50,  # Get more candidates for fusion
            score_threshold=0.3,  # Lower threshold to get more candidates
            filter_conditions=filter_conditions
        )

        # Step 2: BM25 search (if index exists)
        bm25_results = []
        if self.bm25_index is not None:
            bm25_results = self._bm25_search(query, top_k=50)

        # Step 3: Fusion
        if bm25_results:
            fused_results = self._reciprocal_rank_fusion(vector_results, bm25_results)
        else:
            fused_results = vector_results

        # Step 4: Reranking (optional)
        if use_reranking and len(fused_results) > top_k:
            final_results = self._rerank_results(query, fused_results, top_k=top_k)
        else:
            final_results = fused_results[:top_k]

        print(f"[RAGService] ✅ Hybrid search completed, returning {len(final_results)} results")
        return final_results

    def build_context(
        self,
        query: str,
        top_k: int = 5,
        max_context_length: int = 2000,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build context for RAG by retrieving relevant documents

        Args:
            query: User query
            top_k: Number of documents to retrieve
            max_context_length: Maximum total character length of context
            filter_conditions: Optional metadata filters

        Returns:
            Dictionary with context and source documents
        """
        # Perform hybrid search
        results = self.hybrid_search(
            query=query,
            top_k=top_k,
            use_reranking=True,
            filter_conditions=filter_conditions
        )

        # Build context string
        context_parts = []
        total_length = 0
        sources = []

        for i, result in enumerate(results):
            text = result['text']
            metadata = result.get('metadata', {})

            # Check if adding this would exceed max length
            if total_length + len(text) > max_context_length:
                # Add partial text if there's room
                remaining = max_context_length - total_length
                if remaining > 100:  # Only add if meaningful
                    text = text[:remaining] + "..."
                else:
                    break

            # Add to context
            source_label = metadata.get('title', metadata.get('file_name', f'Document {i+1}'))
            context_parts.append(f"[{source_label}]\n{text}\n")
            total_length += len(text)

            # Track source
            sources.append({
                'id': result['id'],
                'title': source_label,
                'score': result.get('rerank_score', result.get('rrf_score', result.get('score', 0))),
                'metadata': metadata
            })

        context = "\n---\n".join(context_parts)

        return {
            'context': context,
            'sources': sources,
            'query': query,
            'num_sources': len(sources)
        }

    def refresh_bm25_index(self) -> bool:
        """
        Refresh BM25 index from vector store

        Returns:
            True if successful
        """
        try:
            print("[RAGService] Refreshing BM25 index...")

            # Get all documents from vector store
            documents = self.vector_store.list_documents(limit=10000)

            if not documents:
                print("[RAGService] No documents found to index")
                return False

            # Rebuild index
            self._build_bm25_index(documents)
            return True

        except Exception as e:
            print(f"[RAGService] Error refreshing BM25 index: {e}")
            return False

    def get_answer_with_sources(
        self,
        query: str,
        llm_client,
        top_k: int = 5,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get answer from LLM with retrieved context (full RAG pipeline)

        Args:
            query: User query
            llm_client: LLM client instance (from llm_gateway)
            top_k: Number of source documents to retrieve
            filter_conditions: Optional metadata filters

        Returns:
            Dictionary with answer, sources, and context
        """
        # Build context
        rag_context = self.build_context(
            query=query,
            top_k=top_k,
            filter_conditions=filter_conditions
        )

        # Build prompt with context
        prompt = f"""基于以下参考资料回答问题。如果参考资料中没有相关信息，请明确说明。

参考资料：
{rag_context['context']}

问题：{query}

请提供详细且准确的回答，并在回答中引用相关的参考资料。"""

        try:
            # Call LLM (this would integrate with your llm_gateway)
            # For now, return context and prompt for the caller to use
            return {
                'query': query,
                'context': rag_context['context'],
                'sources': rag_context['sources'],
                'prompt': prompt,
                'num_sources': rag_context['num_sources']
            }
        except Exception as e:
            print(f"[RAGService] Error generating answer: {e}")
            return {
                'query': query,
                'context': rag_context['context'],
                'sources': rag_context['sources'],
                'error': str(e),
                'num_sources': rag_context['num_sources']
            }
