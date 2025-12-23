"""
Agent Message Service
Agent 消息服务

提供基于消息队列的 Agent 调用接口，支持：
- 异步 Agent 执行
- 执行状态追踪
- 结果消息分发
"""
import asyncio
import logging
import uuid
from typing import Dict, Any, Optional, Callable
from datetime import datetime

from ..messages import AgentRequest, AgentResponse, AuditLogMessage
from ..topics import MagellanTopics
from ..kafka_client import get_kafka_client
from ...core.agents import AgentRegistry, get_agent_registry
from ...core.agents.base.interfaces import AgentInput, AgentConfig

logger = logging.getLogger(__name__)


class AgentMessageService:
    """
    Agent 消息服务

    管理 Agent 执行请求的发送和响应处理
    """

    def __init__(self):
        self._kafka_client = None
        self._agent_registry: Optional[AgentRegistry] = None
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._response_handlers: Dict[str, Callable] = {}

    async def initialize(self):
        """初始化服务"""
        self._kafka_client = get_kafka_client()
        self._agent_registry = get_agent_registry()

        # 订阅 Agent 响应 Topic
        if self._kafka_client.is_available:
            await self._kafka_client.subscribe(
                MagellanTopics.AGENT_RESPONSE,
                "report_orchestrator_agent",
                self._handle_agent_response
            )

            # 同时订阅 Agent 请求（作为执行者）
            await self._kafka_client.subscribe(
                MagellanTopics.AGENT_REQUEST,
                "agent_executor",
                self._execute_agent_request
            )

            logger.info("Agent service subscribed to Kafka")

    async def request_analysis(
        self,
        agent_id: str,
        inputs: Dict[str, Any],
        session_id: str,
        config: Dict[str, Any] = None,
        trace_id: str = None,
        timeout: int = 120
    ) -> Dict[str, Any]:
        """
        请求 Agent 执行分析

        Args:
            agent_id: Agent 标识
            inputs: 输入数据
            session_id: 会话 ID
            config: 配置参数
            trace_id: 追踪 ID
            timeout: 超时时间

        Returns:
            Agent 分析结果
        """
        correlation_id = str(uuid.uuid4())
        trace_id = trace_id or str(uuid.uuid4())

        request = AgentRequest(
            source="report_orchestrator",
            destination=agent_id,
            correlation_id=correlation_id,
            trace_id=trace_id,
            session_id=session_id,
            agent_id=agent_id,
            action="analyze",
            inputs=inputs,
            config=config or {},
            timeout_seconds=timeout
        )

        start_time = datetime.now()

        # bp_parser 必须直接执行，不走 Kafka，因为：
        # 1. PDF 解析使用 Gemini API 需要较长时间
        # 2. PDF 文件较大，Kafka 消息有大小限制
        agents_bypass_kafka = ["bp_parser"]
        
        if agent_id in agents_bypass_kafka:
            logger.info(f"Agent {agent_id} bypasses Kafka, executing directly")
            result = await self._execute_directly(request)
            await self._log_audit(request, result, start_time)
            return result

        # 尝试使用 Kafka
        if self._kafka_client and self._kafka_client.is_available:
            try:
                result = await self._send_via_kafka(request, timeout)
                await self._log_audit(request, result, start_time)
                return result
            except Exception as e:
                logger.warning(f"Kafka Agent call failed, falling back to direct: {e}")

        # 降级到直接调用
        result = await self._execute_directly(request)
        await self._log_audit(request, result, start_time)
        return result

    async def _send_via_kafka(
        self,
        request: AgentRequest,
        timeout: int
    ) -> Dict[str, Any]:
        """通过 Kafka 发送请求"""
        future = asyncio.get_event_loop().create_future()
        self._pending_requests[request.correlation_id] = future

        try:
            await self._kafka_client.send(MagellanTopics.AGENT_REQUEST, request)
            result = await asyncio.wait_for(future, timeout=timeout)
            return result

        except asyncio.TimeoutError:
            logger.error(f"Agent Kafka request timeout: {request.agent_id}")
            return {
                "agent_id": request.agent_id,
                "status": "error",
                "error_message": "Request timeout",
                "correlation_id": request.correlation_id
            }

        finally:
            self._pending_requests.pop(request.correlation_id, None)

    async def _execute_directly(self, request: AgentRequest) -> Dict[str, Any]:
        """直接执行 Agent（降级模式）"""
        try:
            agent = self._agent_registry.create_agent(
                request.agent_id,
                quick_mode=request.config.get("quick_mode", False)
            )

            # Phase 7: 构建标准化 AgentInput
            agent_config = AgentConfig(
                quick_mode=request.config.get("quick_mode", False),
                timeout=request.timeout_seconds or 120
            )

            agent_input = AgentInput(
                session_id=request.session_id,
                agent_id=request.agent_id,
                target=request.inputs if isinstance(request.inputs, dict) else {"data": request.inputs},
                context=request.config.get("context", {}),
                config=agent_config,
                request_id=request.correlation_id
            )

            # 执行分析 - Agent.analyze 期望 (target, context) 两个参数
            result = await agent.analyze(agent_input.target, agent_input.context)

            # 将 AgentOutput 转换为字典 (确保完全序列化 for direct call)
            if hasattr(result, 'model_dump'):
                output_dict = result.model_dump(mode='json')  # Pydantic v2
            elif hasattr(result, 'dict'):
                output_dict = result.dict()  # Pydantic v1
            elif isinstance(result, dict):
                output_dict = result
            else:
                output_dict = {"result": str(result)}

            return {
                "agent_id": request.agent_id,
                "status": "success",
                "outputs": output_dict,
                "correlation_id": request.correlation_id,
                "via": "direct"
            }

        except Exception as e:
            logger.error(f"Direct Agent execution failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "agent_id": request.agent_id,
                "status": "error",
                "error_message": str(e),
                "correlation_id": request.correlation_id
            }

    async def _execute_agent_request(self, message):
        """
        执行 Agent 请求（作为消费者）

        当收到 Agent 请求消息时，执行对应的 Agent 并发送响应
        Phase 7: 使用标准化 AgentInput
        """
        # Phase 7: 从原始 dict 重建 AgentRequest
        if isinstance(message, dict):
            message = AgentRequest(**message)
        elif not hasattr(message, 'agent_id'):
            # 如果是 MagellanMessage，尝试使用 model_dump
            message = AgentRequest(**message.model_dump())

        logger.info(f"Executing Agent request via Kafka: {message.agent_id}")
        start_time = datetime.now()

        try:
            agent = self._agent_registry.create_agent(
                message.agent_id,
                quick_mode=message.config.get("quick_mode", False)
            )

            # Phase 7: 构建标准化 AgentInput
            agent_config = AgentConfig(
                quick_mode=message.config.get("quick_mode", False),
                timeout=message.timeout_seconds or 120
            )

            agent_input = AgentInput(
                session_id=message.session_id,
                agent_id=message.agent_id,
                target=message.inputs if isinstance(message.inputs, dict) else {"data": message.inputs},
                context=message.config.get("context", {}),
                config=agent_config,
                request_id=message.correlation_id
            )

            # 执行分析 - Agent.analyze 期望 (target, context) 两个参数
            result = await agent.analyze(agent_input.target, agent_input.context)

            # 将 AgentOutput 转换为字典 (确保完全序列化 for Kafka)
            if hasattr(result, 'model_dump'):
                output_dict = result.model_dump(mode='json')  # Pydantic v2 - 递归序列化
            elif hasattr(result, 'dict'):
                output_dict = result.dict()  # Pydantic v1
            elif isinstance(result, dict):
                output_dict = result
            else:
                output_dict = {"result": str(result)}

            elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # 发送响应
            response = AgentResponse(
                source=message.agent_id,
                destination=message.source,
                correlation_id=message.correlation_id,
                trace_id=message.trace_id,
                session_id=message.session_id,
                agent_id=message.agent_id,
                status="success",
                outputs=output_dict,
                execution_time_ms=elapsed_ms
            )

            await self._kafka_client.send(MagellanTopics.AGENT_RESPONSE, response)

        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            import traceback
            traceback.print_exc()

            response = AgentResponse(
                source=message.agent_id,
                destination=message.source,
                correlation_id=message.correlation_id,
                trace_id=message.trace_id,
                session_id=message.session_id,
                agent_id=message.agent_id,
                status="error",
                error_message=str(e),
                error_code="EXECUTION_ERROR"
            )

            await self._kafka_client.send(MagellanTopics.AGENT_RESPONSE, response)

    async def _handle_agent_response(self, message):
        """处理 Agent 响应消息"""
        # Phase 7: 处理 dict 或 AgentResponse 类型
        if isinstance(message, dict):
            correlation_id = message.get('correlation_id')
            agent_id = message.get('agent_id')
            status = message.get('status')
            outputs = message.get('outputs')
            execution_time_ms = message.get('execution_time_ms')
            error_message = message.get('error_message')
        else:
            correlation_id = message.correlation_id
            agent_id = message.agent_id
            status = message.status
            outputs = message.outputs
            execution_time_ms = message.execution_time_ms
            error_message = message.error_message

        if correlation_id in self._pending_requests:
            future = self._pending_requests[correlation_id]
            if not future.done():
                future.set_result({
                    "agent_id": agent_id,
                    "status": status,
                    "outputs": outputs,
                    "execution_time_ms": execution_time_ms,
                    "error_message": error_message,
                    "correlation_id": correlation_id,
                    "via": "kafka"
                })

    async def _log_audit(
        self,
        request: AgentRequest,
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
                action="agent_execution",
                actor="system",
                resource_type="agent",
                resource_id=request.agent_id,
                session_id=request.session_id,
                trace_id=request.trace_id,
                details={
                    "correlation_id": request.correlation_id,
                    "agent_id": request.agent_id,
                    "action": request.action,
                    "elapsed_ms": elapsed_ms,
                    "via": result.get("via", "unknown")
                },
                result=result.get("status", "unknown")
            )

            await self._kafka_client.send(MagellanTopics.AUDIT_LOG, audit)

        except Exception as e:
            logger.warning(f"Failed to log audit: {e}")


# 单例
_agent_service: Optional[AgentMessageService] = None


async def get_agent_service() -> AgentMessageService:
    """获取 Agent 服务单例"""
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentMessageService()
        await _agent_service.initialize()
    return _agent_service
