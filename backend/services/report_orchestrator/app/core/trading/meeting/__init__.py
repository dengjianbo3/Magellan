"""
Meeting Package

Modular implementation of TradingMeeting functionality.
Replaces the monolithic trading_meeting.py with focused, testable modules.
"""

from .runner import MeetingRunner
from .config import MeetingConfig

__all__ = [
    "MeetingRunner",
    "MeetingConfig",
]
