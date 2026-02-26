import pytest

from app.core.memory.qmd_store import QmdMemoryStore


@pytest.mark.asyncio
async def test_qmd_query_uses_search_mode_and_n_flag(monkeypatch, tmp_path):
    monkeypatch.setenv("QMD_MEMORY_RETRIEVAL_MODE", "search")

    store = QmdMemoryStore(memory_root=str(tmp_path))
    calls = []

    async def fake_run_qmd(args, allow_failure):
        calls.append((list(args), bool(allow_failure)))
        return {
            "ok": True,
            "stdout": '[{"snippet":"memory hit","score":0.83,"path":"memo.md"}]',
            "stderr": "",
        }

    monkeypatch.setattr(store, "_run_qmd", fake_run_qmd)

    hits = await store._qmd_query("collection_a", "hello", top_k=3)

    assert hits and hits[0].content == "memory hit"
    assert calls, "expected qmd command call"
    cmd = calls[0][0]
    assert cmd[0] == "search"
    assert "--limit" not in cmd
    assert "-n" in cmd


@pytest.mark.asyncio
async def test_qmd_query_falls_back_to_search_when_query_mode_fails(monkeypatch, tmp_path):
    monkeypatch.setenv("QMD_MEMORY_RETRIEVAL_MODE", "query")
    monkeypatch.setenv("QMD_MEMORY_FALLBACK_TO_SEARCH", "true")

    store = QmdMemoryStore(memory_root=str(tmp_path))
    calls = []

    async def fake_run_qmd(args, allow_failure):
        calls.append((list(args), bool(allow_failure)))
        if args[0] == "query":
            return {"ok": False, "stdout": "", "stderr": "model loading failed"}
        return {
            "ok": True,
            "stdout": '[{"snippet":"fallback hit","score":92.0,"path":"memo.md"}]',
            "stderr": "",
        }

    monkeypatch.setattr(store, "_run_qmd", fake_run_qmd)

    hits = await store._qmd_query("collection_b", "world", top_k=2)

    assert len(calls) == 2
    assert calls[0][0][0] == "query"
    assert calls[1][0][0] == "search"
    assert hits and hits[0].score == 0.92
