"""
LLM Message Service
LLM 消息服务

提供统一的 LLM 调用接口，支持：
- Kafka 消息队列通信
- HTTP 降级（Kafka 不可用时）
- 请求追踪和审计
"""
import asyncio
import logging
import os
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx

from ..messages import LLMRequest, AuditLogMessage
from ..topics import MagellanTopics
from ..kafka_client import get_kafka_client

# Import timeout configurations
from ...core.config_timeouts import HTTP_CLIENT_TIMEOUT

logger = logging.getLogger(__name__)

# 配置
LLM_GATEWAY_URL = os.getenv("LLM_GATEWAY_URL", "http://llm_gateway:8003")
# 使用统一的超时配置,但允许环境变量覆盖
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", str(HTTP_CLIENT_TIMEOUT)))


class LLMMessageService:
    """
    LLM 消息服务

    统一的 LLM 调用接口，优先使用 Kafka，降级到 HTTP
    """

    def __init__(self):
        self._kafka_client = None
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._http_client: Optional[httpx.AsyncClient] = None

    async def initialize(self):
        """初始化服务"""
        self._kafka_client = get_kafka_client()
        self._http_client = httpx.AsyncClient(timeout=LLM_TIMEOUT)

        # 订阅 LLM 响应 Topic
        if self._kafka_client.is_available:
            await self._kafka_client.subscribe(
                MagellanTopics.LLM_RESPONSE,
                "report_orchestrator_llm",
                self._handle_llm_response
            )
            logger.info("LLM service subscribed to Kafka")

    async def close(self):
        """关闭服务"""
        if self._http_client:
            await self._http_client.aclose()

    async def chat(
        self,
        messages: List[Dict[str, str]],
        session_id: str = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        model: str = "default",
        trace_id: str = None
    ) -> Dict[str, Any]:
        """
        发送聊天请求

        Args:
            messages: 对话历史
            session_id: 会话 ID
            temperature: 生成温度
            max_tokens: 最大 token
            model: 模型名称
            trace_id: 追踪 ID

        Returns:
            LLM 响应
        """
        correlation_id = str(uuid.uuid4())
        trace_id = trace_id or str(uuid.uuid4())

        # 创建请求消息
        request = LLMRequest(
            source="report_orchestrator",
            destination="llm_gateway",
            correlation_id=correlation_id,
            trace_id=trace_id,
            session_id=session_id,
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        start_time = datetime.now()

        # 尝试使用 Kafka
        if self._kafka_client and self._kafka_client.is_available:
            try:
                result = await self._send_via_kafka(request)
                await self._log_audit(request, result, start_time)
                return result
            except Exception as e:
                logger.warning(f"Kafka LLM call failed, falling back to HTTP: {e}")

        # 降级到 HTTP
        result = await self._send_via_http(request)
        await self._log_audit(request, result, start_time)
        return result

    async def _send_via_kafka(self, request: LLMRequest) -> Dict[str, Any]:
        """通过 Kafka 发送请求"""
        # 创建 Future 等待响应
        future = asyncio.get_event_loop().create_future()
        self._pending_requests[request.correlation_id] = future

        try:
            # 发送请求
            await self._kafka_client.send(MagellanTopics.LLM_REQUEST, request)

            # 等待响应（超时）
            result = await asyncio.wait_for(future, timeout=LLM_TIMEOUT)
            return result

        except asyncio.TimeoutError:
            logger.error(f"LLM Kafka request timeout: {request.correlation_id}")
            raise

        finally:
            # 清理
            self._pending_requests.pop(request.correlation_id, None)

    async def _send_via_http(self, request: LLMRequest) -> Dict[str, Any]:
        """通过 HTTP 发送请求（降级）"""
        # 转换消息格式为 LLM Gateway 期望的格式
        history = []
        for msg in request.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # 转换 role: system/user/assistant -> user/model
            if role == "system" or role == "user":
                history.append({"role": "user", "parts": [content]})
            elif role == "assistant":
                history.append({"role": "model", "parts": [content]})

        try:
            response = await self._http_client.post(
                f"{LLM_GATEWAY_URL}/chat",
                json={
                    "history": history,
                    "temperature": request.temperature
                }
            )
            response.raise_for_status()
            result = response.json()

            return {
                "content": result.get("content", ""),
                "model": request.model,
                "correlation_id": request.correlation_id,
                "via": "http"
            }

        except Exception as e:
            logger.error(f"HTTP LLM call failed: {e}")
            raise

    async def _handle_llm_response(self, message):
        """处理 LLM 响应消息"""
        correlation_id = message.correlation_id

        if correlation_id in self._pending_requests:
            future = self._pending_requests[correlation_id]
            if not future.done():
                future.set_result({
                    "content": message.content,
                    "model": message.model,
                    "usage": message.usage,
                    "correlation_id": correlation_id,
                    "via": "kafka"
                })

    async def _log_audit(
        self,
        request: LLMRequest,
        result: Dict[str, Any],
        start_time: datetime
    ):
        """记录审计日志"""
        if not self._kafka_client or not self._kafka_client.is_available:
            return

        try:
            elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            audit = AuditLogMessage(
                source="report_orchestrator",
                destination="audit",
                action="llm_call",
                actor="system",
                resource_type="llm",
                resource_id=request.model,
                session_id=request.session_id,
                trace_id=request.trace_id,
                details={
                    "correlation_id": request.correlation_id,
                    "model": request.model,
                    "messages_count": len(request.messages),
                    "temperature": request.temperature,
                    "elapsed_ms": elapsed_ms,
                    "via": result.get("via", "unknown")
                },
                result="success" if "content" in result else "error"
            )

            await self._kafka_client.send(MagellanTopics.AUDIT_LOG, audit)

        except Exception as e:
            logger.warning(f"Failed to log audit: {e}")


# 单例
_llm_service: Optional[LLMMessageService] = None


async def get_llm_service() -> LLMMessageService:
    """获取 LLM 服务单例"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMMessageService()
        await _llm_service.initialize()
    return _llm_service
