"""
Message Models
消息模型定义

定义系统中所有消息的标准格式，确保：
1. 消息可序列化（JSON）
2. 支持消息追踪和审计
3. 与 Kafka 兼容
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from enum import Enum
import uuid


class MessageType(str, Enum):
    """消息类型"""
    REQUEST = "request"       # 请求消息
    RESPONSE = "response"     # 响应消息
    EVENT = "event"           # 事件消息
    ERROR = "error"           # 错误消息
    HEARTBEAT = "heartbeat"   # 心跳消息


class MessagePriority(str, Enum):
    """消息优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class MagellanMessage(BaseModel):
    """
    Magellan 标准消息格式

    所有消息的基类，包含：
    - 消息元数据（ID、时间戳、版本）
    - 消息路由（源、目标、回复地址）
    - 追踪信息（会话、用户、trace）
    """
    # 消息元数据
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))  # 关联ID，用于追踪请求链
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = "1.0"

    # 消息路由
    source: str                           # 发送方服务/组件
    destination: str                      # 目标服务/组件
    reply_to: Optional[str] = None        # 回复 Topic

    # 消息内容
    message_type: MessageType
    priority: MessagePriority = MessagePriority.NORMAL
    payload: Dict[str, Any] = Field(default_factory=dict)

    # 追踪信息
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))  # 分布式追踪ID

    # 过期时间
    ttl_seconds: Optional[int] = None     # Time to live

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def to_json(self) -> str:
        """序列化为 JSON 字符串"""
        return self.model_dump_json()

    @classmethod
    def from_json(cls, json_str: str) -> 'MagellanMessage':
        """从 JSON 字符串反序列化"""
        return cls.model_validate_json(json_str)


class AgentRequest(MagellanMessage):
    """
    Agent 执行请求消息

    发送给 Agent 执行分析任务
    """
    agent_id: str                         # 目标 Agent ID
    action: str = "analyze"               # 操作类型 (analyze, synthesize, etc.)
    inputs: Dict[str, Any] = Field(default_factory=dict)  # 输入数据
    config: Dict[str, Any] = Field(default_factory=dict)  # 配置参数
    timeout_seconds: int = 120            # 超时时间

    def __init__(self, **data):
        if 'message_type' not in data:
            data['message_type'] = MessageType.REQUEST
        super().__init__(**data)


class AgentResponse(MagellanMessage):
    """
    Agent 执行响应消息

    Agent 执行完成后返回的结果
    """
    agent_id: str                         # Agent ID
    status: str = "success"               # 状态 (success/error/partial)
    outputs: Dict[str, Any] = Field(default_factory=dict)  # 输出结果

    # 执行指标
    execution_time_ms: Optional[int] = None
    tokens_used: Optional[int] = None
    tools_called: List[str] = Field(default_factory=list)

    # 错误信息
    error_code: Optional[str] = None
    error_message: Optional[str] = None

    def __init__(self, **data):
        if 'message_type' not in data:
            data['message_type'] = MessageType.RESPONSE
        super().__init__(**data)


class LLMRequest(MagellanMessage):
    """
    LLM 调用请求消息

    发送给 LLM Gateway 的请求
    """
    model: str = "default"                # 模型名称
    messages: List[Dict[str, str]] = Field(default_factory=list)  # 对话历史
    temperature: float = 0.7
    max_tokens: int = 4096
    stream: bool = False                  # 是否流式返回

    def __init__(self, **data):
        if 'message_type' not in data:
            data['message_type'] = MessageType.REQUEST
        super().__init__(**data)


class LLMResponse(MagellanMessage):
    """
    LLM 调用响应消息

    LLM Gateway 返回的结果
    """
    content: str = ""                     # 生成的内容
    model: str = ""                       # 实际使用的模型
    usage: Dict[str, int] = Field(default_factory=dict)  # Token 使用统计
    finish_reason: str = ""               # 结束原因

    def __init__(self, **data):
        if 'message_type' not in data:
            data['message_type'] = MessageType.RESPONSE
        super().__init__(**data)


class SessionEvent(MagellanMessage):
    """
    会话事件消息

    用于广播会话状态变化
    """
    event_type: str                       # 事件类型
    event_data: Dict[str, Any] = Field(default_factory=dict)

    # 会话状态
    session_status: Optional[str] = None  # active/completed/error
    progress: Optional[float] = None      # 进度 0-100

    def __init__(self, **data):
        if 'message_type' not in data:
            data['message_type'] = MessageType.EVENT
        super().__init__(**data)


class AuditLogMessage(MagellanMessage):
    """
    审计日志消息

    记录系统操作，用于追踪和合规
    """
    action: str                           # 操作类型
    actor: str                            # 执行者
    resource_type: str                    # 资源类型
    resource_id: str                      # 资源ID
    details: Dict[str, Any] = Field(default_factory=dict)
    result: str = "success"               # 结果 (success/failure)

    def __init__(self, **data):
        if 'message_type' not in data:
            data['message_type'] = MessageType.EVENT
        super().__init__(**data)
