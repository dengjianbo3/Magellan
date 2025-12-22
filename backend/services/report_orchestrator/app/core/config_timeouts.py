"""
Timeout configurations for Trading system

考虑到实际情况：
- 单个Agent可能需要20-30秒（包括工具调用和LLM思考）
- 5个Agent并发，最慢的可能需要40-60秒
- Meeting可能有3-4轮讨论，总共需要2-5分钟
"""

# ==================== LLM相关超时 ====================

# 单个LLM API调用超时
LLM_REQUEST_TIMEOUT = 180  # 3分钟 - 适配thinking模式和tool calling
LLM_CONNECTION_TIMEOUT = 30  # 连接建立超时

# LLM Gateway HTTP超时
LLM_GATEWAY_TIMEOUT = 200  # 比REQUEST_TIMEOUT稍长，留出缓冲

# ==================== Agent执行超时 ====================

# 单个Agent的单次action超时
# 包括：LLM调用 + 工具执行 + 结果处理
AGENT_ACTION_TIMEOUT = 240  # 4分钟 - 考虑复杂的工具链调用

# Agent整体执行超时（包含多次重试）
AGENT_TOTAL_TIMEOUT = 360  # 6分钟

# Tool调用超时
TOOL_EXECUTION_TIMEOUT = 60  # 1分钟 - 单个工具执行

# ==================== Meeting相关超时 ====================

# 单轮Meeting超时
MEETING_TURN_TIMEOUT = 300  # 5分钟 - 5个Agent并发执行
MEETING_SINGLE_AGENT_TIMEOUT = 240  # 4分钟 - 单个Agent在一轮中的超时

# 整个Meeting总超时
MEETING_TOTAL_TIMEOUT = 900  # 15分钟 - 3-4轮讨论
MEETING_MAX_DURATION = 900  # 与TOTAL_TIMEOUT保持一致

# ==================== HTTP Client超时 ====================

# HTTP客户端超时配置
HTTP_CLIENT_TIMEOUT = 240  # 4分钟 - 总超时
HTTP_CLIENT_CONNECT_TIMEOUT = 30  # 连接超时
HTTP_CLIENT_READ_TIMEOUT = 200  # 读取超时

# ==================== Trading特定超时 ====================

# Trading分析总超时（从trigger到完成）
TRADING_ANALYSIS_TIMEOUT = 1200  # 20分钟 - 完整的分析周期

# Trading信号生成超时
TRADING_SIGNAL_TIMEOUT = 600  # 10分钟

# Trading执行超时（下单、查询等）
TRADING_EXECUTION_TIMEOUT = 30  # 30秒

# ==================== 重试配置 ====================

# LLM调用重试
LLM_MAX_RETRIES = 3
LLM_RETRY_DELAY = 5  # 秒
LLM_RETRY_BACKOFF = 2  # 指数退避倍数

# Agent重试
AGENT_MAX_RETRIES = 2
AGENT_RETRY_DELAY = 10

# ==================== 根据模型调整超时 ====================

MODEL_TIMEOUT_MULTIPLIERS = {
    "gemini-2.0-flash-thinking-exp": 2.0,  # thinking模式需要更多时间
    "gemini-2.0-flash-exp": 1.5,
    "gemini-2.5-flash-lite": 1.0,  # 基准
    "gemini-1.5-flash": 1.0,
    "deepseek-chat": 1.5,
    "deepseek-reasoner": 2.0,
}

def get_model_timeout(base_timeout: int, model_name: str) -> int:
    """
    根据模型名称调整超时时间

    Args:
        base_timeout: 基础超时时间（秒）
        model_name: 模型名称

    Returns:
        调整后的超时时间
    """
    multiplier = MODEL_TIMEOUT_MULTIPLIERS.get(model_name, 1.0)
    return int(base_timeout * multiplier)


# ==================== 环境变量覆盖 ====================

import os

# 允许通过环境变量覆盖
LLM_REQUEST_TIMEOUT = int(os.getenv("LLM_REQUEST_TIMEOUT", LLM_REQUEST_TIMEOUT))
AGENT_ACTION_TIMEOUT = int(os.getenv("AGENT_ACTION_TIMEOUT", AGENT_ACTION_TIMEOUT))
MEETING_TURN_TIMEOUT = int(os.getenv("MEETING_TURN_TIMEOUT", MEETING_TURN_TIMEOUT))
MEETING_TOTAL_TIMEOUT = int(os.getenv("MEETING_TOTAL_TIMEOUT", MEETING_TOTAL_TIMEOUT))
HTTP_CLIENT_TIMEOUT = int(os.getenv("HTTP_CLIENT_TIMEOUT", HTTP_CLIENT_TIMEOUT))

# ==================== 日志配置 ====================

# 是否打印超时警告
ENABLE_TIMEOUT_WARNINGS = True
TIMEOUT_WARNING_THRESHOLD = 0.8  # 达到超时时间的80%时发出警告

def log_timeout_warning(operation: str, elapsed: float, timeout: float):
    """记录超时警告"""
    if ENABLE_TIMEOUT_WARNINGS and elapsed > timeout * TIMEOUT_WARNING_THRESHOLD:
        import logging
        logger = logging.getLogger(__name__)
        percentage = (elapsed / timeout) * 100
        logger.warning(
            f"[Timeout Warning] {operation} took {elapsed:.1f}s "
            f"({percentage:.1f}% of {timeout}s timeout)"
        )
