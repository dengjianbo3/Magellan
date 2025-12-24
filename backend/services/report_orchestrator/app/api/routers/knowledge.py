"""
Knowledge Base Router
知识库管理路由

提供文档上传、搜索、RAG 等功能
"""

import os
import shutil
import tempfile
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends

logger = logging.getLogger(__name__)

router = APIRouter()

# Global references - will be set from main.py
_vector_store = None
_rag_service = None


def set_vector_store(store):
    """Set the vector store reference"""
    global _vector_store
    _vector_store = store


def set_rag_service(service):
    """Set the RAG service reference"""
    global _rag_service
    _rag_service = service


def get_vector_store():
    """Get vector store dependency"""
    if _vector_store is None:
        raise HTTPException(status_code=503, detail="Vector store not available")
    return _vector_store


def get_rag_service():
    """Get RAG service dependency"""
    if _rag_service is None:
        raise HTTPException(status_code=503, detail="RAG service not available")
    return _rag_service


@router.post("/upload", tags=["Knowledge Base"])
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    store=Depends(get_vector_store)
):
    """
    Upload a document to the knowledge base

    Supports: PDF, DOCX, TXT
    """
    # Import here to avoid circular imports
    from ...services.document_parser import DocumentParser

    # Validate file type
    allowed_extensions = ['.pdf', '.docx', '.doc', '.txt']
    file_ext = os.path.splitext(file.filename)[1].lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )

    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            shutil.copyfileobj(file.file, temp_file)
            temp_path = temp_file.name

        # Parse document
        parsed_doc = DocumentParser.parse_document(temp_path)

        # Clean up temp file
        os.unlink(temp_path)

        if not parsed_doc['success']:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to parse document: {parsed_doc['metadata'].get('error', 'Unknown error')}"
            )

        text = parsed_doc['text']
        if not text.strip():
            raise HTTPException(status_code=400, detail="Document contains no extractable text")

        # Chunk text for better retrieval
        chunks = DocumentParser.chunk_text(text, chunk_size=500, chunk_overlap=50)

        # Prepare metadata
        base_metadata = {
            "title": title or file.filename,
            "filename": file.filename,
            "category": category or "general",
            "file_type": file_ext[1:],  # Remove dot
            **parsed_doc['metadata']
        }

        # Add chunks to vector store
        doc_ids = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = base_metadata.copy()
            chunk_metadata['chunk_index'] = i
            chunk_metadata['total_chunks'] = len(chunks)

            doc_id = store.add_document(
                text=chunk,
                metadata=chunk_metadata
            )
            doc_ids.append(doc_id)

        logger.info(f"Uploaded document: {file.filename}, {len(chunks)} chunks")

        return {
            "success": True,
            "document_ids": doc_ids,
            "num_chunks": len(chunks),
            "metadata": base_metadata
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload document: {str(e)}")


@router.get("/documents", tags=["Knowledge Base"])
async def list_documents(
    limit: int = 20,
    offset: int = 0,
    category: Optional[str] = None,
    store=Depends(get_vector_store)
):
    """
    List documents in the knowledge base
    """
    try:
        filter_conditions = {}
        if category:
            filter_conditions['category'] = category

        documents = store.list_documents(
            limit=limit,
            offset=offset,
            filter_conditions=filter_conditions
        )

        # Get collection info
        collection_info = store.get_collection_info()

        return {
            "documents": documents,
            "total_vectors": collection_info.get("vectors_count", 0),
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")


@router.get("/search", tags=["Knowledge Base"])
async def search_knowledge_base(
    query: str,
    limit: int = 10,
    category: Optional[str] = None,
    store=Depends(get_vector_store)
):
    """
    Search the knowledge base using semantic search
    """
    if not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        filter_conditions = {}
        if category:
            filter_conditions['category'] = category

        results = store.search(
            query=query,
            limit=limit,
            score_threshold=0.3,  # Minimum similarity score
            filter_conditions=filter_conditions
        )

        logger.info(f"Search query: '{query}', found {len(results)} results")

        return {
            "query": query,
            "results": results,
            "count": len(results)
        }

    except Exception as e:
        logger.error(f"Error searching knowledge base: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.delete("/documents/{doc_id}", tags=["Knowledge Base"])
async def delete_document(doc_id: str, store=Depends(get_vector_store)):
    """
    Delete a document from the knowledge base
    """
    try:
        success = store.delete_document(doc_id)

        if success:
            logger.info(f"Deleted document: {doc_id}")
            return {"success": True, "message": "Document deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Document not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")


@router.get("/stats", tags=["Knowledge Base"])
async def get_knowledge_base_stats(store=Depends(get_vector_store)):
    """
    Get knowledge base statistics
    """
    try:
        collection_info = store.get_collection_info()

        return {
            "collection_name": collection_info.get("collection_name", ""),
            "total_vectors": collection_info.get("vectors_count", 0),
            "total_documents": collection_info.get("points_count", 0),
            "status": collection_info.get("status", "unknown")
        }

    except Exception as e:
        logger.error(f"Error getting knowledge base stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.get("/hybrid-search", tags=["Knowledge Base"])
async def hybrid_search(
    query: str,
    top_k: int = 10,
    use_reranking: bool = True,
    category: Optional[str] = None,
    rag=Depends(get_rag_service)
):
    """
    Perform hybrid search combining vector search and BM25 keyword search

    Args:
        query: Search query
        top_k: Number of results to return
        use_reranking: Whether to apply cross-encoder reranking
        category: Optional category filter

    Returns:
        Search results with relevance scores
    """
    if not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        filter_conditions = {}
        if category:
            filter_conditions['category'] = category

        results = rag.hybrid_search(
            query=query,
            top_k=top_k,
            use_reranking=use_reranking,
            filter_conditions=filter_conditions
        )

        logger.info(f"Hybrid search query: '{query}', found {len(results)} results")

        return {
            "query": query,
            "results": results,
            "count": len(results),
            "search_type": "hybrid" + (" + reranking" if use_reranking else "")
        }

    except Exception as e:
        logger.error(f"Error in hybrid search: {e}")
        raise HTTPException(status_code=500, detail=f"Hybrid search failed: {str(e)}")


@router.get("/rag-context", tags=["Knowledge Base"])
async def get_rag_context(
    query: str,
    top_k: int = 5,
    max_context_length: int = 2000,
    category: Optional[str] = None,
    rag=Depends(get_rag_service)
):
    """
    Build RAG context for a query by retrieving relevant documents

    Args:
        query: User query
        top_k: Number of source documents to retrieve
        max_context_length: Maximum total character length of context
        category: Optional category filter

    Returns:
        Assembled context with source documents
    """
    if not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        filter_conditions = {}
        if category:
            filter_conditions['category'] = category

        context_data = rag.build_context(
            query=query,
            top_k=top_k,
            max_context_length=max_context_length,
            filter_conditions=filter_conditions
        )

        logger.info(f"RAG context built for query: '{query}', {context_data['num_sources']} sources")

        return context_data

    except Exception as e:
        logger.error(f"Error building RAG context: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to build context: {str(e)}")


@router.post("/rag-answer", tags=["Knowledge Base"])
async def get_rag_answer(request: dict, rag=Depends(get_rag_service)):
    """
    Get an LLM answer using RAG (Retrieval-Augmented Generation)

    Request body:
        query: User question
        top_k: Number of source documents (default: 5)
        category: Optional category filter

    Returns:
        Answer with sources and context
    """
    query = request.get("query", "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        top_k = request.get("top_k", 5)
        category = request.get("category")

        filter_conditions = {}
        if category:
            filter_conditions['category'] = category

        # Build context with RAG
        rag_result = rag.get_answer_with_sources(
            query=query,
            llm_client=None,  # Not using LLM integration yet
            top_k=top_k,
            filter_conditions=filter_conditions
        )

        logger.info(f"RAG answer generated for query: '{query}'")

        return {
            "query": rag_result['query'],
            "context": rag_result['context'],
            "sources": rag_result['sources'],
            "prompt": rag_result['prompt'],
            "num_sources": rag_result['num_sources'],
            "note": "LLM integration pending - returning context and prompt for now"
        }

    except Exception as e:
        logger.error(f"Error generating RAG answer: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate answer: {str(e)}")


@router.post("/refresh-index", tags=["Knowledge Base"])
async def refresh_bm25_index(rag=Depends(get_rag_service)):
    """
    Refresh the BM25 index for hybrid search

    This should be called after uploading new documents to enable BM25 search
    """
    try:
        success = rag.refresh_bm25_index()

        if success:
            logger.info("BM25 index refreshed successfully")
            return {
                "success": True,
                "message": "BM25 index refreshed successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to refresh index")

    except Exception as e:
        logger.error(f"Error refreshing BM25 index: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh index: {str(e)}")
