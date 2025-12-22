"""
Mock LLM Service - 模拟LLM服务

避免真实的LLM API调用，使用预定义响应。
"""

import pytest
import os
from typing import Dict, Any, Optional, Callable
from unittest.mock import AsyncMock, MagicMock


class MockLLMService:
    """Mock LLM Service - 返回预定义响应"""
    
    def __init__(self, response_map: Dict[str, str] = None):
        """
        Args:
            response_map: Agent name -> response mapping
        """
        self.response_map = response_map or {}
        self.call_count = 0
        self.call_history = []
    
    async def call_llm(self, messages: list, agent_name: str = None) -> Dict[str, Any]:
        """模拟LLM调用"""
        self.call_count += 1
        self.call_history.append({
            "agent_name": agent_name,
            "messages": messages,
            "timestamp": self.call_count
        })
        
        # 从messages中提取agent信息
        if not agent_name:
            for msg in messages:
                if msg.get("role") == "system" and "content" in msg:
                    content = msg["content"]
                    if "TechnicalAnalyst" in content or "技术分析" in content:
                        agent_name = "TechnicalAnalyst"
                    elif "MacroEconomist" in content or "宏观经济" in content:
                        agent_name = "MacroEconomist"
                    elif "SentimentAnalyst" in content or "情绪分析" in content:
                        agent_name = "SentimentAnalyst"
                    elif "QuantStrategist" in content or "量化策略" in content:
                        agent_name = "QuantStrategist"
                    elif "RiskAssessor" in content or "风险评估" in content:
                        agent_name = "RiskAssessor"
                    elif "Leader" in content or "主持人" in content:
                        agent_name = "Leader"
                    break
        
        # 获取预定义响应
        response_content = self.response_map.get(agent_name, self._get_default_response(agent_name))
        
        # 返回OpenAI格式
        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": response_content
                    }
                }
            ]
        }
    
    def _get_default_response(self, agent_name: str) -> str:
        """默认响应"""
        defaults = {
            "TechnicalAnalyst": "## 技术分析\n\n技术面评分: 5/10 (中性)\n建议方向: 观望",
            "MacroEconomist": "## 宏观分析\n\n宏观面评分: 5/10 (中性)\n建议方向: 观望",
            "SentimentAnalyst": "## 情绪分析\n\n情绪评分: 5/10 (中性)\n建议方向: 观望",
            "QuantStrategist": "## 量化分析\n\n量化评分: 5/10 (中性)\n建议方向: 观望",
            "RiskAssessor": "## 风险评估\n\n风险评级: 中等\n建议: 谨慎",
            "Leader": "[USE_TOOL: hold(reason=\"市场不明朗，暂时观望\")]",
        }
        return defaults.get(agent_name, "No response")
    
    def set_response(self, agent_name: str, response: str):
        """设置特定Agent的响应"""
        self.response_map[agent_name] = response
    
    def set_responses(self, responses: Dict[str, str]):
        """批量设置响应"""
        self.response_map.update(responses)
    
    def reset(self):
        """重置状态"""
        self.call_count = 0
        self.call_history = []


@pytest.fixture
def mock_llm_service():
    """提供Mock LLM Service"""
    return MockLLMService()


@pytest.fixture
def mock_llm_bullish(all_agents_bullish, leader_decision_long):
    """Mock LLM - 全部看涨"""
    responses = all_agents_bullish.copy()
    responses["Leader"] = leader_decision_long
    return MockLLMService(response_map=responses)


@pytest.fixture
def mock_llm_bearish(all_agents_bearish, leader_decision_short):
    """Mock LLM - 全部看跌"""
    responses = all_agents_bearish.copy()
    responses["Leader"] = leader_decision_short
    return MockLLMService(response_map=responses)


@pytest.fixture
def mock_llm_hold(leader_decision_hold):
    """Mock LLM - 观望"""
    return MockLLMService(response_map={
        "TechnicalAnalyst": "技术面中性",
        "MacroEconomist": "宏观面不确定",
        "SentimentAnalyst": "情绪面观望",
        "QuantStrategist": "量化信号不明",
        "RiskAssessor": "风险偏高",
        "Leader": leader_decision_hold,
    })


@pytest.fixture
def mock_agent_with_llm(mocker, mock_llm_service):
    """Mock Agent的_call_llm方法"""
    async def mock_call_llm(self, messages):
        agent_name = getattr(self, 'name', None) or getattr(self, 'id', None)
        return await mock_llm_service.call_llm(messages, agent_name)
    
    # Patch Agent._call_llm
    mocker.patch(
        "app.core.agents.agent.Agent._call_llm",
        new=mock_call_llm
    )
    
    return mock_llm_service


class MockLLMWithErrors:
    """Mock LLM Service with error scenarios"""
    
    def __init__(self, fail_rate: float = 0.0, fail_on_agent: str = None):
        """
        Args:
            fail_rate: Probability of failure (0.0 - 1.0)
            fail_on_agent: Always fail for this specific agent
        """
        self.fail_rate = fail_rate
        self.fail_on_agent = fail_on_agent
        self.call_count = 0
    
    async def call_llm(self, messages: list, agent_name: str = None) -> Dict[str, Any]:
        """Simulate LLM call with potential failures"""
        self.call_count += 1
        
        import random
        # Simulate failure
        if self.fail_on_agent == agent_name or random.random() < self.fail_rate:
            raise Exception(f"Mock LLM Error for {agent_name}")
        
        # Return minimal response
        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "[USE_TOOL: hold(reason=\"test\")]"
                    }
                }
            ]
        }


@pytest.fixture
def mock_llm_with_failures():
    """Mock LLM that occasionally fails"""
    return MockLLMWithErrors(fail_rate=0.3)


@pytest.fixture
def mock_llm_always_fails():
    """Mock LLM that always fails"""
    return MockLLMWithErrors(fail_rate=1.0)


# ==================== Helper Functions ====================

def create_mock_agent_response(
    direction: str = "hold",
    confidence: int = 50,
    leverage: int = 1,
    use_tool: bool = True
) -> str:
    """创建标准的Agent响应"""
    if direction == "long" and use_tool:
        return f"""## 分析结论

建议方向: 做多
信心度: {confidence}%
建议杠杆: {leverage}倍

[USE_TOOL: open_long(leverage="{leverage}", amount_usdt="2000", tp_percent="5.0", sl_percent="2.0")]
"""
    elif direction == "short" and use_tool:
        return f"""## 分析结论

建议方向: 做空
信心度: {confidence}%
建议杠杆: {leverage}倍

[USE_TOOL: open_short(leverage="{leverage}", amount_usdt="2000", tp_percent="5.0", sl_percent="2.0")]
"""
    else:
        reason = "市场不明朗" if not use_tool else "测试观望"
        return f"""## 分析结论

建议方向: 观望
信心度: {confidence}%

[USE_TOOL: hold(reason="{reason}")]
"""


@pytest.fixture
def agent_response_builder():
    """Agent响应构建器"""
    return create_mock_agent_response


# ==================== 环境控制 ====================

@pytest.fixture
def use_real_llm():
    """检查是否使用真实LLM"""
    return os.getenv("USE_REAL_LLM", "false").lower() == "true"


@pytest.fixture
def auto_mock_llm(mocker, use_real_llm, mock_llm_service):
    """自动Mock LLM（除非明确要求使用真实LLM）"""
    if not use_real_llm:
        # Auto-patch LLM calls
        async def mock_call(self, messages):
            agent_name = getattr(self, 'name', None)
            return await mock_llm_service.call_llm(messages, agent_name)
        
        mocker.patch(
            "app.core.agents.agent.Agent._call_llm",
            new=mock_call
        )
        
        return mock_llm_service
    return None
