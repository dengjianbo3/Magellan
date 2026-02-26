import asyncio
import time

import pytest

from app.core.orchestrators.base_orchestrator import BaseOrchestrator
from app.models.analysis_models import WorkflowStep, WorkflowStepTemplate


class _DummyOrchestrator(BaseOrchestrator):
    async def _validate_target(self) -> bool:  # pragma: no cover - not used in this unit test
        return True

    async def _synthesize_final_report(self):  # pragma: no cover - not used in this unit test
        return {}


@pytest.mark.asyncio
async def test_execute_workflow_dag_runs_independent_steps_in_parallel():
    orch = _DummyOrchestrator.__new__(_DummyOrchestrator)
    orch.workflow_templates = [
        WorkflowStepTemplate(id="a", name="A", agent="x", inputs=[]),
        WorkflowStepTemplate(id="b", name="B", agent="x", inputs=[]),
        WorkflowStepTemplate(id="c", name="C", agent="x", inputs=["a", "b"]),
    ]
    orch.workflow = [
        WorkflowStep(id="a", name="A", agent="x"),
        WorkflowStep(id="b", name="B", agent="x"),
        WorkflowStep(id="c", name="C", agent="x"),
    ]

    executed = []

    async def _fake_execute(step):
        if step.id in {"a", "b"}:
            await asyncio.sleep(0.05)
        executed.append(step.id)

    orch._execute_step = _fake_execute  # type: ignore[attr-defined]

    start = time.perf_counter()
    await BaseOrchestrator._execute_workflow_dag(orch)
    elapsed = time.perf_counter() - start

    assert elapsed < 0.09  # a + b should run together (not ~0.10 sequential)
    assert executed[-1] == "c"
    assert set(executed[:2]) == {"a", "b"}


@pytest.mark.asyncio
async def test_execute_workflow_dag_blocks_downstream_on_failed_dependency():
    orch = _DummyOrchestrator.__new__(_DummyOrchestrator)
    orch.workflow_templates = [
        WorkflowStepTemplate(id="a", name="A", agent="x", inputs=[]),
        WorkflowStepTemplate(id="b", name="B", agent="x", inputs=[]),
        WorkflowStepTemplate(id="c", name="C", agent="x", inputs=["a", "b"]),
    ]
    orch.workflow = [
        WorkflowStep(id="a", name="A", agent="x"),
        WorkflowStep(id="b", name="B", agent="x"),
        WorkflowStep(id="c", name="C", agent="x"),
    ]

    async def _fake_execute(step):
        if step.id == "a":
            raise RuntimeError("boom")
        return None

    orch._execute_step = _fake_execute  # type: ignore[attr-defined]

    with pytest.raises(RuntimeError):
        await BaseOrchestrator._execute_workflow_dag(orch)

    blocked = next(s for s in orch.workflow if s.id == "c")
    assert blocked.status == "error"
    assert "Dependency failed" in (blocked.error or "")
