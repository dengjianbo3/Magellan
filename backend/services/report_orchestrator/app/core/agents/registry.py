"""
Agent Registry
Agent 注册中心

提供统一的 Agent 创建和管理接口
"""
import yaml
import logging
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Agent 注册中心

    功能:
    1. 从 agents.yaml 加载配置
    2. 根据 agent_id 创建 Agent 实例
    3. 管理 Agent 生命周期
    """

    _instance: Optional['AgentRegistry'] = None
    _config: Dict[str, Any] = {}
    _factory_map: Dict[str, Callable] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._load_config()
        self._register_factories()

    def _load_config(self):
        """加载 agents.yaml 配置"""
        config_path = Path(__file__).parent.parent.parent.parent / "config" / "agents.yaml"

        if not config_path.exists():
            logger.warning(f"agents.yaml not found at {config_path}")
            return

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
            logger.info(f"Loaded {len(self._config.get('agents', []))} agents from config")
        except Exception as e:
            logger.error(f"Failed to load agents.yaml: {e}")

    def _register_factories(self):
        """注册 Agent 工厂函数"""
        # 原子 Agent 工厂
        from .atomic import (
            create_team_evaluator,
            create_market_analyst,
            create_financial_expert,
            create_risk_assessor,
            create_tech_specialist,
            create_legal_advisor,
            create_technical_analyst,
            create_bp_parser,  # Added bp_parser
        )

        # 特殊 Agent 工厂
        from .special import create_leader, create_report_synthesizer

        self._factory_map = {
            # 原子 Agent
            "team_evaluator": create_team_evaluator,
            "market_analyst": create_market_analyst,
            "financial_expert": create_financial_expert,
            "risk_assessor": create_risk_assessor,
            "tech_specialist": create_tech_specialist,
            "legal_advisor": create_legal_advisor,
            "technical_analyst": create_technical_analyst,
            "bp_parser": create_bp_parser,  # Added bp_parser

            # 特殊 Agent
            "leader": create_leader,
            "report_synthesizer": create_report_synthesizer,
        }

        logger.info(f"Registered {len(self._factory_map)} agent factories")

    def get_agent_config(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        获取 Agent 配置

        Args:
            agent_id: Agent 标识

        Returns:
            Agent 配置字典，如果不存在返回 None
        """
        agents = self._config.get('agents', [])
        for agent in agents:
            if agent.get('agent_id') == agent_id:
                return agent
        return None

    def create_agent(
        self,
        agent_id: str,
        language: str = "zh",
        quick_mode: bool = False,
        **kwargs
    ) -> Any:
        """
        创建 Agent 实例

        Args:
            agent_id: Agent 标识
            language: 输出语言 ("zh" 中文, "en" 英文)
            quick_mode: 是否快速模式
            **kwargs: 其他参数

        Returns:
            Agent 实例
        """
        factory = self._factory_map.get(agent_id)

        if not factory:
            raise ValueError(f"Unknown agent_id: {agent_id}")

        # 获取配置
        config = self.get_agent_config(agent_id)

        # 创建 Agent - 使用正确的参数签名
        return factory(
            language=language,
            quick_mode=quick_mode
        )

    def list_agents(self, type_filter: str = None, scope_filter: str = None) -> List[Dict[str, Any]]:
        """
        列出所有 Agent

        Args:
            type_filter: 类型过滤 ('atomic' 或 'special')
            scope_filter: 范围过滤 ('roundtable' 或 'analysis')

        Returns:
            Agent 配置列表
        """
        agents = self._config.get('agents', [])

        if type_filter:
            agents = [a for a in agents if a.get('type') == type_filter]

        if scope_filter:
            agents = [a for a in agents if scope_filter in a.get('scope', [])]

        return agents

    def list_atomic_agents(self) -> List[Dict[str, Any]]:
        """列出所有原子 Agent"""
        return self.list_agents(type_filter='atomic')

    def list_special_agents(self) -> List[Dict[str, Any]]:
        """列出所有特殊 Agent"""
        return self.list_agents(type_filter='special')

    def get_agents_for_scenario(self, scenario: str) -> List[str]:
        """
        获取某个场景需要的 Agent ID 列表

        Args:
            scenario: 场景名称 (如 'early_stage', 'growth', 'public_market')

        Returns:
            Agent ID 列表
        """
        # 场景到 Agent 的映射
        scenario_agents = {
            "early_stage": ["team_evaluator", "market_analyst", "financial_expert", "risk_assessor"],
            "growth": ["market_analyst", "financial_expert", "team_evaluator", "tech_specialist", "risk_assessor"],
            "public_market": ["financial_expert", "market_analyst", "risk_assessor"],
            "alternative": ["market_analyst", "financial_expert", "legal_advisor", "risk_assessor", "technical_analyst"],
            "industry_research": ["market_analyst", "tech_specialist", "financial_expert"],
            "roundtable": ["leader", "team_evaluator", "market_analyst", "financial_expert", "risk_assessor", "tech_specialist", "legal_advisor"],
        }

        return scenario_agents.get(scenario, [])


# 单例访问
def get_agent_registry() -> AgentRegistry:
    """获取 AgentRegistry 单例"""
    return AgentRegistry()
