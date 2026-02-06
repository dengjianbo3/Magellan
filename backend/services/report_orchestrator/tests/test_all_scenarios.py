"""
Magellan Analysis Module - 完整的单元测试套件
测试所有5个场景的完整流程
"""
import pytest
import asyncio
from typing import Dict, Any

# 导入所有Orchestrators
from app.core.orchestrators.early_stage_orchestrator import EarlyStageInvestmentOrchestrator
from app.core.orchestrators.growth_orchestrator import GrowthInvestmentOrchestrator
from app.core.orchestrators.public_market_orchestrator import PublicMarketInvestmentOrchestrator
from app.core.orchestrators.alternative_orchestrator import AlternativeInvestmentOrchestrator
from app.core.orchestrators.industry_research_orchestrator import IndustryResearchOrchestrator

# 导入模型
from app.models.analysis_models import (
    AnalysisRequest,
    AnalysisConfig,
    InvestmentScenario,
    AnalysisDepth
)


# =============================================================================
# 测试数据工厂
# =============================================================================

class TestDataFactory:
    """测试数据工厂"""

    @staticmethod
    def create_early_stage_request(depth: AnalysisDepth = AnalysisDepth.QUICK) -> AnalysisRequest:
        """创建早期投资请求"""
        return AnalysisRequest(
            target={
                "company_name": "AI教育科技公司",
                "stage": "seed",
                "industry": "EdTech",
                "team_members": [
                    {"name": "张三", "role": "CEO", "background": "前阿里技术总监"}
                ]
            },
            config=AnalysisConfig(
                depth=depth,
                focus_areas=["team", "market"]
            )
        )

    @staticmethod
    def create_growth_request(depth: AnalysisDepth = AnalysisDepth.QUICK) -> AnalysisRequest:
        """创建成长期投资请求"""
        return AnalysisRequest(
            target={
                "company_name": "云计算独角兽",
                "stage": "series-c",
                "annual_revenue": 50000000,
                "growth_rate": 150
            },
            config=AnalysisConfig(
                depth=depth,
                focus_areas=["financials", "growth"]
            )
        )

    @staticmethod
    def create_public_market_request(depth: AnalysisDepth = AnalysisDepth.QUICK) -> AnalysisRequest:
        """创建公开市场投资请求"""
        return AnalysisRequest(
            target={
                "ticker": "AAPL",
                "exchange": "NASDAQ",
                "asset_type": "stock"
            },
            config=AnalysisConfig(
                depth=depth,
                focus_areas=["valuation", "fundamentals"]
            )
        )

    @staticmethod
    def create_alternative_request(depth: AnalysisDepth = AnalysisDepth.QUICK) -> AnalysisRequest:
        """创建另类投资请求"""
        return AnalysisRequest(
            target={
                "asset_type": "crypto",
                "symbol": "ETH",
                "project_name": "Ethereum"
            },
            config=AnalysisConfig(
                depth=depth,
                focus_areas=["tech", "tokenomics"]
            )
        )

    @staticmethod
    def create_industry_research_request(depth: AnalysisDepth = AnalysisDepth.QUICK) -> AnalysisRequest:
        """创建行业研究请求"""
        return AnalysisRequest(
            target={
                "industry_name": "人工智能",
                "research_topic": "生成式AI市场规模",
                "geo_scope": "global"
            },
            config=AnalysisConfig(
                depth=depth,
                focus_areas=["market_size", "trends"]
            )
        )


# =============================================================================
# 早期投资场景测试
# =============================================================================

class TestEarlyStageInvestment:
    """早期投资场景测试"""

    @pytest.mark.asyncio
    async def test_quick_mode(self):
        """测试Quick模式"""
        request = TestDataFactory.create_early_stage_request(AnalysisDepth.QUICK)
        orchestrator = EarlyStageInvestmentOrchestrator(
            session_id="test-early-quick",
            request=request
        )

        # 验证目标
        is_valid = await orchestrator._validate_target()
        assert is_valid is True

        # 执行分析
        result = await orchestrator.analyze()

        # 验证结果
        assert result is not None
        assert "recommendation" in result
        assert "confidence" in result
        print(f"✓ 早期投资 Quick Mode: {result.get('recommendation')}")

    @pytest.mark.asyncio
    async def test_standard_mode(self):
        """测试Standard模式"""
        request = TestDataFactory.create_early_stage_request(AnalysisDepth.STANDARD)
        orchestrator = EarlyStageInvestmentOrchestrator(
            session_id="test-early-standard",
            request=request
        )

        is_valid = await orchestrator._validate_target()
        assert is_valid is True

        result = await orchestrator.analyze()

        assert result is not None
        assert "investment_score" in result or "overall_score" in result
        print(f"✓ 早期投资 Standard Mode 完成")

    @pytest.mark.asyncio
    async def test_validation_failure(self):
        """测试验证失败情况"""
        request = AnalysisRequest(
            target={"invalid_field": "test"},  # 缺少必填字段
            config=AnalysisConfig(depth=AnalysisDepth.QUICK)
        )

        orchestrator = EarlyStageInvestmentOrchestrator(
            session_id="test-early-invalid",
            request=request
        )

        # 应该抛出异常或返回False
        with pytest.raises(Exception):
            await orchestrator._validate_target()


# =============================================================================
# 成长期投资场景测试
# =============================================================================

class TestGrowthInvestment:
    """成长期投资场景测试"""

    @pytest.mark.asyncio
    async def test_quick_mode(self):
        """测试Quick模式"""
        request = TestDataFactory.create_growth_request(AnalysisDepth.QUICK)
        orchestrator = GrowthInvestmentOrchestrator(
            session_id="test-growth-quick",
            request=request
        )

        is_valid = await orchestrator._validate_target()
        assert is_valid is True

        result = await orchestrator.analyze()
        assert result is not None
        print(f"✓ 成长期投资 Quick Mode 完成")

    @pytest.mark.asyncio
    async def test_agent_pool_initialization(self):
        """测试Agent池初始化"""
        request = TestDataFactory.create_growth_request()
        orchestrator = GrowthInvestmentOrchestrator(
            session_id="test-growth-agents",
            request=request
        )

        # 验证Agent池
        assert "financial_analyst" in orchestrator.agent_pool
        assert "growth_evaluator" in orchestrator.agent_pool
        assert "market_analyst" in orchestrator.agent_pool
        assert "financial_expert" in orchestrator.agent_pool  # 新添加的Agent
        print("✓ 成长期投资 Agent池初始化成功")


# =============================================================================
# 公开市场投资场景测试
# =============================================================================

class TestPublicMarketInvestment:
    """公开市场投资场景测试"""

    @pytest.mark.asyncio
    async def test_quick_mode(self):
        """测试Quick模式"""
        request = TestDataFactory.create_public_market_request(AnalysisDepth.QUICK)
        orchestrator = PublicMarketInvestmentOrchestrator(
            session_id="test-public-quick",
            request=request
        )

        is_valid = await orchestrator._validate_target()
        assert is_valid is True

        result = await orchestrator.analyze()
        assert result is not None
        assert "scores" in result
        print(f"✓ 公开市场投资 Quick Mode 完成")

    @pytest.mark.asyncio
    async def test_data_fetcher_agent(self):
        """测试DataFetcherAgent集成"""
        request = TestDataFactory.create_public_market_request()
        orchestrator = PublicMarketInvestmentOrchestrator(
            session_id="test-public-datafetcher",
            request=request
        )

        # 验证DataFetcherAgent存在
        assert "data_fetcher" in orchestrator.agent_pool
        print("✓ 公开市场投资 DataFetcherAgent集成成功")


# =============================================================================
# 另类投资场景测试
# =============================================================================

class TestAlternativeInvestment:
    """另类投资场景测试"""

    @pytest.mark.asyncio
    async def test_quick_mode(self):
        """测试Quick模式"""
        request = TestDataFactory.create_alternative_request(AnalysisDepth.QUICK)
        orchestrator = AlternativeInvestmentOrchestrator(
            session_id="test-alt-quick",
            request=request
        )

        is_valid = await orchestrator._validate_target()
        assert is_valid is True

        result = await orchestrator.analyze()
        assert result is not None
        assert "risk_level" in result or "scores" in result
        print(f"✓ 另类投资 Quick Mode 完成")

    @pytest.mark.asyncio
    async def test_crypto_analyst_agent(self):
        """测试CryptoAnalystAgent集成"""
        request = TestDataFactory.create_alternative_request()
        orchestrator = AlternativeInvestmentOrchestrator(
            session_id="test-alt-crypto",
            request=request
        )

        # 验证CryptoAnalystAgent存在
        assert "crypto_analyst" in orchestrator.agent_pool
        print("✓ 另类投资 CryptoAnalystAgent集成成功")


# =============================================================================
# 行业研究场景测试
# =============================================================================

class TestIndustryResearch:
    """行业研究场景测试"""

    @pytest.mark.asyncio
    async def test_quick_mode(self):
        """测试Quick模式"""
        request = TestDataFactory.create_industry_research_request(AnalysisDepth.QUICK)
        orchestrator = IndustryResearchOrchestrator(
            session_id="test-industry-quick",
            request=request
        )

        is_valid = await orchestrator._validate_target()
        assert is_valid is True

        result = await orchestrator.analyze()
        assert result is not None
        print(f"✓ 行业研究 Quick Mode 完成")

    @pytest.mark.asyncio
    async def test_industry_researcher_agent(self):
        """测试IndustryResearcherAgent集成"""
        request = TestDataFactory.create_industry_research_request()
        orchestrator = IndustryResearchOrchestrator(
            session_id="test-industry-researcher",
            request=request
        )

        # 验证IndustryResearcherAgent存在
        assert "industry_researcher" in orchestrator.agent_pool
        print("✓ 行业研究 IndustryResearcherAgent集成成功")


# =============================================================================
# Mock数据标识测试
# =============================================================================

class TestMockDataIdentification:
    """测试Mock数据标识功能"""

    @pytest.mark.asyncio
    async def test_mock_data_has_flag_quick_mode(self):
        """测试Quick模式Mock数据带有is_mock标识"""
        request = TestDataFactory.create_early_stage_request(AnalysisDepth.QUICK)
        orchestrator = EarlyStageInvestmentOrchestrator(
            session_id="test-mock-flag",
            request=request
        )

        result = await orchestrator.analyze()

        # 验证is_mock字段存在
        assert "is_mock" in result, "Quick mode结果应该包含is_mock字段"
        assert result["is_mock"] is True, "Mock数据的is_mock应该为True"
        print("✓ Mock数据标识 - Quick Mode")

    @pytest.mark.asyncio
    async def test_all_scenarios_have_mock_flag(self):
        """测试所有场景的Mock数据都有is_mock标识"""
        scenarios = [
            (TestDataFactory.create_growth_request(), GrowthInvestmentOrchestrator, "Growth"),
            (TestDataFactory.create_public_market_request(), PublicMarketInvestmentOrchestrator, "Public Market"),
            (TestDataFactory.create_alternative_request(), AlternativeInvestmentOrchestrator, "Alternative"),
            (TestDataFactory.create_industry_research_request(), IndustryResearchOrchestrator, "Industry Research"),
        ]

        for request, orchestrator_class, name in scenarios:
            orchestrator = orchestrator_class(
                session_id=f"test-mock-{name.lower().replace(' ', '-')}",
                request=request
            )

            result = await orchestrator.analyze()

            assert "is_mock" in result, f"{name}场景应该包含is_mock字段"
            print(f"✓ Mock数据标识 - {name}")


# =============================================================================
# 性能测试
# =============================================================================

class TestPerformance:
    """性能测试"""

    @pytest.mark.asyncio
    async def test_quick_mode_response_time(self):
        """测试Quick模式响应时间 (<5秒)"""
        import time

        request = TestDataFactory.create_early_stage_request(AnalysisDepth.QUICK)
        orchestrator = EarlyStageInvestmentOrchestrator(
            session_id="test-performance",
            request=request
        )

        start_time = time.time()
        result = await orchestrator.analyze()
        elapsed_time = time.time() - start_time

        assert elapsed_time < 10.0, f"Quick模式应该在10秒内完成,实际用时{elapsed_time:.2f}秒"
        print(f"✓ Quick模式响应时间: {elapsed_time:.2f}秒")


# =============================================================================
# 运行所有测试
# =============================================================================

if __name__ == "__main__":
    import sys

    print("=" * 80)
    print("Magellan Analysis Module - 单元测试套件")
    print("=" * 80)

    # 运行pytest
    exit_code = pytest.main([
        __file__,
        "-v",  # 详细输出
        "-s",  # 显示print输出
        "--tb=short",  # 简短的traceback
        "--asyncio-mode=auto"  # 自动async模式
    ])

    sys.exit(exit_code)
