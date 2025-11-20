"""
Agent Registry
Agent和Workflow配置加载器

职责:
1. 从agents.yaml和workflows.yaml加载配置
2. 提供查询Agent和Workflow的接口
3. 根据配置动态创建Agent实例
4. 支持热重载配置

设计原则:
- 配置驱动: 所有Agent和Workflow通过YAML配置
- 懒加载: Agent实例按需创建
- 单例模式: 全局唯一的Registry实例
"""

import yaml
import os
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import importlib

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Agent注册表
    管理所有Agent和Workflow配置
    """

    _instance = None  # 单例实例

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化Registry"""
        if self._initialized:
            return

        self._initialized = True
        self.agents_config = {}
        self.workflows_config = {}
        self.agent_instances = {}  # 缓存Agent实例

        # 配置文件路径
        config_dir = Path(__file__).parent.parent.parent / "config"
        self.agents_config_path = config_dir / "agents.yaml"
        self.workflows_config_path = config_dir / "workflows.yaml"

        # 加载配置
        self._load_configs()

    def _load_configs(self):
        """加载配置文件"""
        try:
            # 加载agents.yaml
            if self.agents_config_path.exists():
                with open(self.agents_config_path, 'r', encoding='utf-8') as f:
                    agents_data = yaml.safe_load(f)
                    self.agents_config = {
                        agent['agent_id']: agent
                        for agent in agents_data.get('agents', [])
                    }
                logger.info(f"✅ Loaded {len(self.agents_config)} agents from agents.yaml")
            else:
                logger.warning(f"⚠️  agents.yaml not found at {self.agents_config_path}")

            # 加载workflows.yaml
            if self.workflows_config_path.exists():
                with open(self.workflows_config_path, 'r', encoding='utf-8') as f:
                    workflows_data = yaml.safe_load(f)
                    self.workflows_config = workflows_data.get('workflows', {})
                logger.info(f"✅ Loaded {len(self.workflows_config)} workflows from workflows.yaml")
            else:
                logger.warning(f"⚠️  workflows.yaml not found at {self.workflows_config_path}")

        except Exception as e:
            logger.error(f"❌ Error loading configs: {e}")
            raise

    def reload_configs(self):
        """重新加载配置 (支持热重载)"""
        logger.info("🔄 Reloading agent and workflow configs...")
        self.agent_instances.clear()  # 清空缓存
        self._load_configs()

    # ============================================
    # Agent相关接口
    # ============================================

    def get_agent_config(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        获取Agent配置

        Args:
            agent_id: Agent ID (e.g., 'team_evaluator')

        Returns:
            Agent配置字典，如果不存在返回None
        """
        return self.agents_config.get(agent_id)

    def list_agents(self, agent_type: Optional[str] = None, scope: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出所有Agent

        Args:
            agent_type: 过滤Agent类型 ('atomic', 'special')
            scope: 过滤使用范围 ('roundtable', 'analysis')

        Returns:
            Agent配置列表
        """
        agents = list(self.agents_config.values())

        # 按类型过滤
        if agent_type:
            agents = [a for a in agents if a.get('type') == agent_type]

        # 按scope过滤
        if scope:
            agents = [a for a in agents if scope in a.get('scope', [])]

        return agents

    def get_atomic_agents(self) -> List[Dict[str, Any]]:
        """获取所有原子Agent"""
        return self.list_agents(agent_type='atomic')

    def create_agent(self, agent_id: str, **kwargs) -> Any:
        """
        创建Agent实例

        Args:
            agent_id: Agent ID
            **kwargs: Agent参数 (e.g., language='zh', quick_mode=True)

        Returns:
            Agent实例

        Raises:
            ValueError: Agent不存在
            ImportError: 无法导入Agent类
        """
        # 生成缓存key
        cache_key = f"{agent_id}_{hash(frozenset(kwargs.items()))}"

        # 检查缓存
        if cache_key in self.agent_instances:
            logger.debug(f"♻️  Using cached agent instance: {agent_id}")
            return self.agent_instances[cache_key]

        # 获取配置
        config = self.get_agent_config(agent_id)
        if not config:
            raise ValueError(f"Agent '{agent_id}' not found in registry")

        # 获取类路径
        class_path = config.get('class_path')
        if not class_path:
            raise ValueError(f"Agent '{agent_id}' has no class_path defined")

        try:
            # 动态导入
            # class_path 格式: "module.path.function_name"
            module_path, function_name = class_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            create_function = getattr(module, function_name)

            # 创建Agent实例
            agent = create_function(**kwargs)
            logger.info(f"✅ Created agent instance: {agent_id} with params {kwargs}")

            # 缓存实例
            self.agent_instances[cache_key] = agent

            return agent

        except ImportError as e:
            logger.error(f"❌ Failed to import agent '{agent_id}': {e}")
            raise ImportError(f"Cannot import agent '{agent_id}' from '{class_path}': {e}")
        except Exception as e:
            logger.error(f"❌ Failed to create agent '{agent_id}': {e}")
            raise

    # ============================================
    # Workflow相关接口
    # ============================================

    def get_workflow_config(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        """
        获取Workflow配置

        Args:
            scenario_id: 场景ID (e.g., 'early-stage-investment')

        Returns:
            Workflow配置字典，如果不存在返回None
        """
        return self.workflows_config.get(scenario_id)

    def get_workflow_steps(self, scenario_id: str, mode: str = 'standard') -> Optional[List[Dict[str, Any]]]:
        """
        获取Workflow的执行步骤

        Args:
            scenario_id: 场景ID
            mode: 执行模式 ('quick' 或 'standard')

        Returns:
            步骤列表，如果不存在返回None
        """
        workflow = self.get_workflow_config(scenario_id)
        if not workflow:
            return None

        modes = workflow.get('modes', {})
        mode_config = modes.get(mode, {})

        return mode_config.get('steps', [])

    def list_workflows(self) -> List[str]:
        """
        列出所有Workflow场景ID

        Returns:
            场景ID列表
        """
        return list(self.workflows_config.keys())

    def get_workflow_estimated_duration(self, scenario_id: str, mode: str = 'standard') -> Optional[int]:
        """
        获取Workflow预计执行时长

        Args:
            scenario_id: 场景ID
            mode: 执行模式

        Returns:
            预计时长（秒），如果不存在返回None
        """
        workflow = self.get_workflow_config(scenario_id)
        if not workflow:
            return None

        modes = workflow.get('modes', {})
        mode_config = modes.get(mode, {})

        return mode_config.get('estimated_duration')

    def validate_workflow(self, scenario_id: str, mode: str = 'standard') -> bool:
        """
        验证Workflow配置是否合法

        Args:
            scenario_id: 场景ID
            mode: 执行模式

        Returns:
            是否合法
        """
        steps = self.get_workflow_steps(scenario_id, mode)
        if not steps:
            logger.error(f"Workflow '{scenario_id}' mode '{mode}' has no steps")
            return False

        # 验证每个步骤的agent是否存在
        for step in steps:
            agent_id = step.get('agent_id')
            if not agent_id:
                logger.error(f"Step {step.get('step_id')} has no agent_id")
                return False

            if not self.get_agent_config(agent_id):
                logger.error(f"Agent '{agent_id}' not found in registry")
                return False

        logger.info(f"✅ Workflow '{scenario_id}' mode '{mode}' validation passed")
        return True

    # ============================================
    # 工具方法
    # ============================================

    def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        获取Agent的摘要信息

        Args:
            agent_id: Agent ID

        Returns:
            摘要信息字典
        """
        config = self.get_agent_config(agent_id)
        if not config:
            return None

        return {
            'agent_id': config.get('agent_id'),
            'type': config.get('type'),
            'scope': config.get('scope'),
            'name': config.get('name'),
            'description': config.get('description'),
            'quick_mode_support': config.get('quick_mode_support'),
            'estimated_duration': config.get('estimated_duration')
        }

    def get_workflow_info(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        """
        获取Workflow的摘要信息

        Args:
            scenario_id: 场景ID

        Returns:
            摘要信息字典
        """
        config = self.get_workflow_config(scenario_id)
        if not config:
            return None

        return {
            'scenario_id': config.get('scenario_id'),
            'name': config.get('name'),
            'description': config.get('description'),
            'modes': list(config.get('modes', {}).keys()),
            'quick_duration': self.get_workflow_estimated_duration(scenario_id, 'quick'),
            'standard_duration': self.get_workflow_estimated_duration(scenario_id, 'standard')
        }

    def __repr__(self):
        return (
            f"<AgentRegistry: "
            f"{len(self.agents_config)} agents, "
            f"{len(self.workflows_config)} workflows>"
        )


# ============================================
# 全局单例实例
# ============================================

# 全局Registry实例
registry = AgentRegistry()


# ============================================
# 便捷访问函数
# ============================================

def get_registry() -> AgentRegistry:
    """获取全局Registry实例"""
    return registry


def get_agent(agent_id: str, **kwargs) -> Any:
    """
    便捷函数: 创建Agent实例

    Args:
        agent_id: Agent ID
        **kwargs: Agent参数

    Returns:
        Agent实例
    """
    return registry.create_agent(agent_id, **kwargs)


def get_workflow(scenario_id: str, mode: str = 'standard') -> Optional[List[Dict[str, Any]]]:
    """
    便捷函数: 获取Workflow步骤

    Args:
        scenario_id: 场景ID
        mode: 执行模式

    Returns:
        步骤列表
    """
    return registry.get_workflow_steps(scenario_id, mode)


# ============================================
# 初始化时自动加载配置
# ============================================

logger.info("🚀 AgentRegistry initialized")
logger.info(f"📁 Agents config: {registry.agents_config_path}")
logger.info(f"📁 Workflows config: {registry.workflows_config_path}")
logger.info(f"✅ Registry: {registry}")
