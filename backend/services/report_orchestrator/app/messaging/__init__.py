"""
Magellan Messaging Module
消息队列模块

提供基于 Kafka 的异步消息通信能力，支持：
- 服务间解耦通信
- 消息持久化和重放
- 分布式事务追踪
- 审计日志记录
"""

from .messages import (
    MagellanMessage,
    MessageType,
    AgentRequest,
    AgentResponse,
    LLMRequest,
    LLMResponse,
    SessionEvent,
)
from .topics import MagellanTopics
from .kafka_client import KafkaClient, get_kafka_client, init_kafka, close_kafka

# 消息服务
from .services import (
    LLMMessageService,
    get_llm_service,
    AgentMessageService,
    get_agent_service,
    SessionEventPublisher,
    get_session_publisher,
)

__all__ = [
    # 消息模型
    "MagellanMessage",
    "MessageType",
    "AgentRequest",
    "AgentResponse",
    "LLMRequest",
    "LLMResponse",
    "SessionEvent",

    # Topic 定义
    "MagellanTopics",

    # Kafka 客户端
    "KafkaClient",
    "get_kafka_client",
    "init_kafka",
    "close_kafka",

    # 消息服务
    "LLMMessageService",
    "get_llm_service",
    "AgentMessageService",
    "get_agent_service",
    "SessionEventPublisher",
    "get_session_publisher",
]
