"""
Analysis orchestrator integration tests aligned with current V2 contracts.
"""

from time import perf_counter
from typing import Any, Callable, Dict, Tuple, Type

import pytest

from app.core.orchestrators.alternative_orchestrator import AlternativeInvestmentOrchestrator
from app.core.orchestrators.base_orchestrator import BaseOrchestrator
from app.core.orchestrators.early_stage_orchestrator import EarlyStageInvestmentOrchestrator
from app.core.orchestrators.growth_orchestrator import GrowthInvestmentOrchestrator
from app.core.orchestrators.industry_research_orchestrator import IndustryResearchOrchestrator
from app.core.orchestrators.public_market_orchestrator import PublicMarketInvestmentOrchestrator
from app.models.analysis_models import (
    AnalysisConfig,
    AnalysisDepth,
    AnalysisRequest,
    InvestmentScenario,
)


class _DummySessionStore:
    def save_session(self, *args, **kwargs):
        return True

    def save_report(self, *args, **kwargs):
        return True


@pytest.fixture(autouse=True)
def _mock_orchestrator_dependencies(monkeypatch):
    """Keep tests deterministic and independent from Redis/Kafka/LLM services."""

    async def _fake_execute_agent_step(self, step, template):
        return {"step_id": step.id, "is_mock": True, "score": 0.8}

    async def _fake_save_session(self, *args, **kwargs):
        return None

    async def _fake_synthesize_report(context, quick_mode=False):
        return {
            "overall_recommendation": "observe",
            "confidence_level": "medium",
            "investment_score": 0.72,
            "scores_breakdown": {
                "team": 0.7,
                "market": 0.74,
                "financial": 0.71,
                "tech": 0.69,
            },
            "summary": "mock synthesis",
            "key_findings": ["mock-finding-1", "mock-finding-2"],
            "next_steps": ["continue dd", "focus on risks"],
            "is_mock": True,
            "quick_mode": quick_mode,
        }

    monkeypatch.setattr(
        "app.core.orchestrators.base_orchestrator.SessionStore",
        _DummySessionStore,
    )
    monkeypatch.setattr(BaseOrchestrator, "_execute_agent_step", _fake_execute_agent_step)
    monkeypatch.setattr(BaseOrchestrator, "_save_session", _fake_save_session)
    monkeypatch.setattr(
        "app.agents.report_synthesizer_agent.synthesize_report",
        _fake_synthesize_report,
    )


class TestDataFactory:
    @staticmethod
    def _create_request(
        project_name: str,
        scenario: InvestmentScenario,
        target: Dict[str, Any],
        depth: AnalysisDepth = AnalysisDepth.QUICK,
    ) -> AnalysisRequest:
        return AnalysisRequest(
            project_name=project_name,
            scenario=scenario,
            target=target,
            config=AnalysisConfig(depth=depth),
            user_id="test_user",
        )

    @staticmethod
    def create_early_stage_request(depth: AnalysisDepth = AnalysisDepth.QUICK) -> AnalysisRequest:
        return TestDataFactory._create_request(
            project_name="AI教育科技公司",
            scenario=InvestmentScenario.EARLY_STAGE,
            target={
                "company_name": "AI教育科技公司",
                "stage": "seed",
                "industry": "EdTech",
            },
            depth=depth,
        )

    @staticmethod
    def create_growth_request(depth: AnalysisDepth = AnalysisDepth.QUICK) -> AnalysisRequest:
        return TestDataFactory._create_request(
            project_name="云计算独角兽",
            scenario=InvestmentScenario.GROWTH,
            target={
                "company_name": "云计算独角兽",
                "stage": "series-c",
                "annual_revenue": 50000000,
                "growth_rate": 150,
            },
            depth=depth,
        )

    @staticmethod
    def create_public_market_request(depth: AnalysisDepth = AnalysisDepth.QUICK) -> AnalysisRequest:
        return TestDataFactory._create_request(
            project_name="AAPL investment",
            scenario=InvestmentScenario.PUBLIC_MARKET,
            target={"ticker": "AAPL", "exchange": "NASDAQ", "asset_type": "stock"},
            depth=depth,
        )

    @staticmethod
    def create_alternative_request(depth: AnalysisDepth = AnalysisDepth.QUICK) -> AnalysisRequest:
        return TestDataFactory._create_request(
            project_name="Ethereum",
            scenario=InvestmentScenario.ALTERNATIVE,
            target={"asset_type": "crypto", "symbol": "ETH", "project_name": "Ethereum"},
            depth=depth,
        )

    @staticmethod
    def create_industry_research_request(depth: AnalysisDepth = AnalysisDepth.QUICK) -> AnalysisRequest:
        return TestDataFactory._create_request(
            project_name="生成式AI行业",
            scenario=InvestmentScenario.INDUSTRY_RESEARCH,
            target={
                "industry_name": "人工智能",
                "research_topic": "生成式AI市场规模",
                "geo_scope": "global",
            },
            depth=depth,
        )


def _assert_quick_result(result: Dict[str, Any]):
    assert result["mode"] == "quick_judgment"
    assert "recommendation" in result
    assert "confidence" in result
    assert "summary" in result


class TestEarlyStageInvestment:
    @pytest.mark.asyncio
    async def test_quick_mode(self):
        request = TestDataFactory.create_early_stage_request(AnalysisDepth.QUICK)
        orchestrator = EarlyStageInvestmentOrchestrator(
            session_id="test-early-quick",
            request=request,
        )

        assert await orchestrator._validate_target() is True
        result = await orchestrator.orchestrate()
        _assert_quick_result(result)

    @pytest.mark.asyncio
    async def test_standard_mode(self):
        request = TestDataFactory.create_early_stage_request(AnalysisDepth.STANDARD)
        orchestrator = EarlyStageInvestmentOrchestrator(
            session_id="test-early-standard",
            request=request,
        )

        result = await orchestrator.orchestrate()
        assert result["overall_recommendation"] == "observe"
        assert result["is_mock"] is True

    def test_validation_failure(self):
        invalid_request = AnalysisRequest(
            project_name="invalid",
            scenario=InvestmentScenario.EARLY_STAGE,
            target={"invalid_field": "test"},
            config=AnalysisConfig(depth=AnalysisDepth.QUICK),
            user_id="test_user",
        )

        with pytest.raises(Exception):
            EarlyStageInvestmentOrchestrator(
                session_id="test-early-invalid",
                request=invalid_request,
            )


class TestAllScenariosQuickMode:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "request_factory,orchestrator_class",
        [
            (TestDataFactory.create_growth_request, GrowthInvestmentOrchestrator),
            (TestDataFactory.create_public_market_request, PublicMarketInvestmentOrchestrator),
            (TestDataFactory.create_alternative_request, AlternativeInvestmentOrchestrator),
            (TestDataFactory.create_industry_research_request, IndustryResearchOrchestrator),
        ],
    )
    async def test_quick_mode(
        self,
        request_factory: Callable[[AnalysisDepth], AnalysisRequest],
        orchestrator_class: Type[BaseOrchestrator],
    ):
        request = request_factory(AnalysisDepth.QUICK)
        orchestrator = orchestrator_class(
            session_id=f"test-{request.scenario.value}",
            request=request,
        )

        assert await orchestrator._validate_target() is True
        assert len(orchestrator.workflow_templates) > 0

        result = await orchestrator.orchestrate()
        _assert_quick_result(result)

        assert all(v.get("is_mock") is True for v in orchestrator.results.values())


class TestPerformance:
    @pytest.mark.asyncio
    async def test_quick_mode_response_time(self):
        request = TestDataFactory.create_early_stage_request(AnalysisDepth.QUICK)
        orchestrator = EarlyStageInvestmentOrchestrator(
            session_id="test-performance",
            request=request,
        )

        started = perf_counter()
        result = await orchestrator.orchestrate()
        elapsed = perf_counter() - started

        _assert_quick_result(result)
        assert elapsed < 5.0, f"Quick mode should finish quickly under mocks, got {elapsed:.2f}s"
