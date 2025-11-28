"""
Kafka Topics Definition
Kafka Topic 定义

定义系统中所有的消息 Topic
"""
from enum import Enum
from typing import Dict, Any


class MagellanTopics(str, Enum):
    """
    Magellan 系统 Kafka Topics

    命名规范: magellan.{domain}.{action}
    """

    # Agent 相关
    AGENT_REQUEST = "magellan.agent.request"      # Agent 执行请求
    AGENT_RESPONSE = "magellan.agent.response"    # Agent 执行结果

    # LLM 相关
    LLM_REQUEST = "magellan.llm.request"          # LLM 调用请求
    LLM_RESPONSE = "magellan.llm.response"        # LLM 调用响应

    # 工具调用
    TOOL_REQUEST = "magellan.tool.request"        # 工具调用请求
    TOOL_RESPONSE = "magellan.tool.response"      # 工具调用结果

    # 会话事件
    SESSION_EVENTS = "magellan.session.events"    # 会话状态事件流

    # 审计日志
    AUDIT_LOG = "magellan.audit.log"              # 审计日志归档

    # 系统事件
    SYSTEM_HEALTH = "magellan.system.health"      # 系统健康状态
    SYSTEM_ERRORS = "magellan.system.errors"      # 系统错误

    @classmethod
    def get_topic_config(cls, topic: 'MagellanTopics') -> Dict[str, Any]:
        """
        获取 Topic 配置

        Args:
            topic: Topic 枚举

        Returns:
            Topic 配置字典
        """
        configs = {
            cls.AGENT_REQUEST: {
                "partitions": 3,
                "replication_factor": 1,
                "retention_ms": 604800000,  # 7 days
                "cleanup_policy": "delete"
            },
            cls.AGENT_RESPONSE: {
                "partitions": 3,
                "replication_factor": 1,
                "retention_ms": 604800000,
                "cleanup_policy": "delete"
            },
            cls.LLM_REQUEST: {
                "partitions": 5,  # LLM 请求量大，多分区
                "replication_factor": 1,
                "retention_ms": 259200000,  # 3 days
                "cleanup_policy": "delete"
            },
            cls.LLM_RESPONSE: {
                "partitions": 5,
                "replication_factor": 1,
                "retention_ms": 259200000,
                "cleanup_policy": "delete"
            },
            cls.SESSION_EVENTS: {
                "partitions": 3,
                "replication_factor": 1,
                "retention_ms": 604800000,
                "cleanup_policy": "delete"
            },
            cls.AUDIT_LOG: {
                "partitions": 1,
                "replication_factor": 1,
                "retention_ms": 2592000000,  # 30 days - 审计日志保留更久
                "cleanup_policy": "delete"
            },
            cls.SYSTEM_HEALTH: {
                "partitions": 1,
                "replication_factor": 1,
                "retention_ms": 86400000,  # 1 day
                "cleanup_policy": "delete"
            },
            cls.SYSTEM_ERRORS: {
                "partitions": 1,
                "replication_factor": 1,
                "retention_ms": 604800000,
                "cleanup_policy": "delete"
            },
        }

        return configs.get(topic, {
            "partitions": 1,
            "replication_factor": 1,
            "retention_ms": 604800000,
            "cleanup_policy": "delete"
        })

    @classmethod
    def all_topics(cls) -> list:
        """获取所有 Topic 名称"""
        return [t.value for t in cls]


# Topic 分区键策略
def get_partition_key(topic: MagellanTopics, message: dict) -> str:
    """
    根据消息内容获取分区键

    保证同一会话或同一 Agent 的消息路由到同一分区，保持顺序

    Args:
        topic: Topic
        message: 消息内容

    Returns:
        分区键
    """
    if topic in [MagellanTopics.AGENT_REQUEST, MagellanTopics.AGENT_RESPONSE]:
        # Agent 相关消息按 session_id 分区
        return message.get("session_id", "default")

    elif topic in [MagellanTopics.LLM_REQUEST, MagellanTopics.LLM_RESPONSE]:
        # LLM 相关消息按 correlation_id 分区
        return message.get("correlation_id", "default")

    elif topic == MagellanTopics.SESSION_EVENTS:
        # 会话事件按 session_id 分区
        return message.get("session_id", "default")

    elif topic == MagellanTopics.AUDIT_LOG:
        # 审计日志按时间分区（单分区）
        return "audit"

    else:
        # 默认按 message_id 分区
        return message.get("message_id", "default")
