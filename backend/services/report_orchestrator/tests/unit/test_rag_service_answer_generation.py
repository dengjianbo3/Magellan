import pytest

from app.services.rag_service import RAGService


class _FakeVectorStore:
    def search(self, query, limit=10, score_threshold=0.5, filter_conditions=None):
        return [
            {
                "id": "doc-1",
                "score": 0.9,
                "text": "This is a sample context document.",
                "metadata": {"title": "Doc One"},
            }
        ]


class _GoodLLM:
    async def call(self, prompt: str, response_format: str = "text"):
        assert response_format == "text"
        return {"content": "这是基于知识库的回答。"}


class _BadLLM:
    async def call(self, prompt: str, response_format: str = "text"):
        return {}


@pytest.mark.asyncio
async def test_get_answer_with_sources_returns_answer():
    rag = RAGService(vector_store_service=_FakeVectorStore())

    result = await rag.get_answer_with_sources(
        query="请总结文档内容",
        llm_client=_GoodLLM(),
        top_k=1,
    )

    assert result["query"] == "请总结文档内容"
    assert result["answer"] == "这是基于知识库的回答。"
    assert result["num_sources"] == 1
    assert isinstance(result["sources"], list)
    assert "参考资料" in result["prompt"]


@pytest.mark.asyncio
async def test_get_answer_with_sources_returns_error_when_llm_invalid():
    rag = RAGService(vector_store_service=_FakeVectorStore())

    result = await rag.get_answer_with_sources(
        query="请总结文档内容",
        llm_client=_BadLLM(),
        top_k=1,
    )

    assert result["query"] == "请总结文档内容"
    assert "error" in result
    assert result["num_sources"] == 1
