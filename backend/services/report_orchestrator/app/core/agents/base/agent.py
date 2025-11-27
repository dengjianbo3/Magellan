"""
Agent Base Class
Agent 基类

当前阶段：从 roundtable 模块导入，保持向后兼容
未来阶段：完全迁移到此模块
"""

# 从现有实现导入，保持向后兼容
from app.core.roundtable.agent import Agent

# 导出
__all__ = ["Agent"]
