"""
Agent Interfaces
Agent 标准化接口定义

定义所有 Agent 的统一输入输出格式，确保:
1. 所有 Agent 可以互相协作
2. 结果可序列化和持久化
3. 支持消息队列传输
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class AgentConfig(BaseModel):
    """Agent 运行配置"""
    quick_mode: bool = False          # 快速模式（简化输出）
    max_tokens: int = 4096            # 最大输出 token
    temperature: float = 0.7          # 生成温度
    timeout: int = 120                # 超时时间（秒）
    retry_count: int = 3              # 重试次数
    parallel_tools: bool = True       # 是否并行执行工具


class AgentInput(BaseModel):
    """Agent 标准输入"""
    session_id: str                           # 会话ID
    agent_id: str                             # Agent标识
    target: Dict[str, Any]                    # 分析目标数据
    context: Dict[str, Any] = Field(default_factory=dict)  # 上下文（前序Agent结果）
    config: AgentConfig = Field(default_factory=AgentConfig)  # 配置

    # 元数据
    request_id: Optional[str] = None          # 请求追踪ID
    timestamp: datetime = Field(default_factory=datetime.now)


class AgentOutputStatus(str, Enum):
    """Agent 输出状态"""
    SUCCESS = "success"
    PARTIAL = "partial"    # 部分成功（某些工具失败）
    ERROR = "error"


class AgentOutput(BaseModel):
    """Agent 标准输出"""
    agent_id: str                             # Agent标识
    status: AgentOutputStatus                 # 执行状态

    # 分析结果
    score: Optional[float] = None             # 0-100 评分
    analysis: Dict[str, Any] = Field(default_factory=dict)  # 结构化分析结果
    key_findings: List[str] = Field(default_factory=list)   # 关键发现
    risks: List[str] = Field(default_factory=list)          # 风险点
    recommendations: List[str] = Field(default_factory=list) # 建议

    # 原始输出（用于展示）
    raw_output: Optional[str] = None

    # 执行元数据
    metadata: Dict[str, Any] = Field(default_factory=dict)  # 元数据
    execution_time_ms: Optional[int] = None   # 执行时间
    tokens_used: Optional[int] = None         # Token消耗
    tools_called: List[str] = Field(default_factory=list)   # 调用的工具列表

    # 错误信息（当status为error时）
    error_message: Optional[str] = None
    error_code: Optional[str] = None


class AtomicAgent(ABC):
    """
    原子 Agent 抽象基类

    所有原子 Agent 必须继承此类并实现 analyze 方法。
    原子 Agent 是系统的基本分析单元，不同场景通过组合原子 Agent 实现。
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.quick_mode = self.config.get('quick_mode', False)

    @property
    @abstractmethod
    def agent_id(self) -> str:
        """Agent 唯一标识（如 'team_evaluator', 'market_analyst'）"""
        pass

    @property
    @abstractmethod
    def name(self) -> Dict[str, str]:
        """Agent 名称（多语言）"""
        pass

    @property
    @abstractmethod
    def description(self) -> Dict[str, str]:
        """Agent 描述（多语言）"""
        pass

    @abstractmethod
    async def analyze(self, input: AgentInput) -> AgentOutput:
        """
        执行分析 - 所有 Agent 必须实现此方法

        Args:
            input: 标准化输入

        Returns:
            标准化输出
        """
        pass

    def supports_quick_mode(self) -> bool:
        """是否支持快速模式"""
        return True

    def get_capabilities(self) -> List[str]:
        """获取Agent能力列表"""
        return []

    def get_tools(self) -> List[str]:
        """获取Agent使用的工具列表"""
        return []
