"""
Message: The basic unit of communication between agents
消息: Agent之间通信的基本单位
"""
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime


class MessageType(str, Enum):
    """消息类型"""
    BROADCAST = "broadcast"  # 广播消息（发送给所有Agent）
    DIRECT = "direct"       # 直接消息（一对一）
    PRIVATE = "private"     # 私聊消息（不公开）
    QUESTION = "question"   # 提问
    RESPONSE = "response"   # 回复
    AGREEMENT = "agreement" # 赞同
    DISAGREEMENT = "disagreement"  # 反对
    THINKING = "thinking"   # 思考过程分享


class Message(BaseModel):
    """
    消息对象

    代表Agent之间传递的单个消息单元
    """
    sender: str                          # 发送者Agent的名称
    recipient: str                       # 接收者Agent的名称（"ALL"表示广播）
    content: str                         # 消息内容
    message_type: MessageType = MessageType.BROADCAST  # 消息类型
    metadata: Optional[Dict[str, Any]] = None  # 附加元数据
    timestamp: str = None                # 时间戳

    # 用于追踪对话关系
    reply_to: Optional[str] = None       # 回复的消息ID
    message_id: Optional[str] = None     # 消息ID

    def __init__(self, **data):
        if 'timestamp' not in data or data['timestamp'] is None:
            data['timestamp'] = datetime.now().isoformat()
        if 'message_id' not in data or data['message_id'] is None:
            # 生成唯一ID
            import uuid
            data['message_id'] = str(uuid.uuid4())
        super().__init__(**data)

    def is_broadcast(self) -> bool:
        """是否为广播消息"""
        return self.recipient == "ALL" or self.message_type == MessageType.BROADCAST

    def is_private(self) -> bool:
        """是否为私聊消息"""
        return self.message_type == MessageType.PRIVATE

    def is_question(self) -> bool:
        """是否为提问"""
        return self.message_type == MessageType.QUESTION

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "sender": self.sender,
            "recipient": self.recipient,
            "content": self.content,
            "message_type": self.message_type,
            "metadata": self.metadata or {},
            "timestamp": self.timestamp,
            "reply_to": self.reply_to,
            "message_id": self.message_id,
        }
