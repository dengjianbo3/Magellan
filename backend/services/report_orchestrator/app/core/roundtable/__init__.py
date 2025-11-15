"""
MAIA: Multi-Agent Interaction Architecture for Magellan
基于MAIA框架的多智能体圆桌讨论模块

Inspired by the roundtable discussion design in Crypilot.
"""

from .message import Message, MessageType
from .tool import Tool
from .agent import Agent
from .message_bus import MessageBus
from .meeting import Meeting

__all__ = [
    'Message',
    'MessageType',
    'Tool',
    'Agent',
    'MessageBus',
    'Meeting',
]
