"""
BaseOrchestrator - 所有场景Orchestrator的基类
包含快速判断模式和标准分析模式的核心逻辑
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import WebSocket

from app.models.analysis_models import (
    AnalysisRequest,
    AnalysisSession,
    AnalysisDepth,
    DecisionMode,
    WorkflowStep,
    WorkflowStepTemplate,
    QuickJudgmentResult,
    InvestmentScenario
)
from app.core.agent_registry import registry
from app.core.session_store import SessionStore
# Phase 7: Import Agent Message Service for Kafka integration
from app.messaging import get_agent_service


class BaseOrchestrator(ABC):
    """
    Orchestrator基类
    每个投资场景继承此类并实现特定逻辑
    """

    def __init__(
        self,
        scenario: InvestmentScenario,
        session_id: str,
        request: AnalysisRequest,
        websocket: Optional[WebSocket] = None
    ):
        self.scenario = scenario
        self.session_id = session_id
        self.request = request
        self.websocket = websocket

        # 决策模式 (子类可覆盖)
        self.decision_mode = DecisionMode.HYBRID

        # Phase 2: 使用AgentRegistry替代硬编码的agent_pool
        # IMPORTANT: Initialize registry FIRST before loading workflows
        self.registry = registry  # New: Use AgentRegistry
        self.agent_pool = {}  # Deprecated, kept for backward compatibility
        
        # Initialize SessionStore
        self.session_store = SessionStore()

        # Phase 2: 从AgentRegistry加载workflow配置
        # Convert YAML-based workflow steps to old WorkflowStepTemplate format for backward compatibility
        self.workflow_templates = self._load_workflow_from_registry(
            scenario.value,
            request.config.depth.value
        )

        # 工作流执行状态
        self.workflow: List[WorkflowStep] = []
        self.current_step_index = 0
        self.results: Dict[str, Any] = {}

        # 快速判断结果
        self.quick_judgment: Optional[QuickJudgmentResult] = None

        # Session元数据
        self.start_time = datetime.now()
        self.started_at = self.start_time.isoformat()

    # ============ Phase 2: 新增配置加载方法 ============

    def _load_workflow_from_registry(
        self,
        scenario: str,
        depth: str
    ) -> List[WorkflowStepTemplate]:
        """
        Phase 2: 从AgentRegistry加载workflow配置

        将YAML格式的workflow步骤转换为WorkflowStepTemplate对象
        以保持与现有代码的兼容性

        Args:
            scenario: 场景ID (e.g., 'early-stage-investment')
            depth: 分析深度 ('quick', 'standard', 'comprehensive')

        Returns:
            WorkflowStepTemplate列表
        """
        # 映射depth到mode
        mode = 'quick' if depth == 'quick' else 'standard'

        # 从AgentRegistry获取workflow步骤
        steps = self.registry.get_workflow_steps(scenario, mode)

        if not steps:
            raise ValueError(f"No workflow found for scenario={scenario}, mode={mode}")

        # 转换为WorkflowStepTemplate对象
        templates = []
        for step in steps:
            # Convert depends_on (integers) to strings
            depends_on = step.get('depends_on', [])
            inputs = [str(dep) for dep in depends_on] if depends_on else []

            template = WorkflowStepTemplate(
                id=str(step.get('step_id', '')),
                name=step.get('description', ''),
                required=step.get('required', True),
                agent=step.get('agent_id', ''),
                quick_mode=step.get('agent_params', {}).get('quick_mode', False),
                expected_duration=step.get('estimated_duration', 60),
                inputs=inputs,
                data_sources=step.get('data_sources', []),
                expected_output=step.get('expected_output', []),
                condition=step.get('condition')
            )
            templates.append(template)

        return templates

    # ============ 抽象方法 (子类必须实现) ============

    def _init_agent_pool(self) -> Dict[str, Any]:
        """
        初始化专业Agent池

        Phase 2 NOTE: 此方法已弃用，保留仅为向后兼容
        子类不再需要实现此方法
        Agent现在通过AgentRegistry动态创建

        Returns:
            空字典（向后兼容）
        """
        return {}

    @abstractmethod
    async def _validate_target(self) -> bool:
        """
        验证分析目标是否有效
        例如: 股票代码是否存在、公司是否可查询到
        """
        pass

    @abstractmethod
    async def _synthesize_final_report(self) -> Dict[str, Any]:
        """
        综合所有步骤结果,生成最终报告
        子类必须实现
        """
        pass

    # ============ 核心协调逻辑 ============

    async def orchestrate(self) -> Dict[str, Any]:
        """
        核心协调逻辑 - 主入口
        """
        try:
            # 1. 验证目标
            await self._send_status("initializing", f"正在验证{self.scenario.value}分析目标...")
            if not await self._validate_target():
                raise ValueError("分析目标验证失败")

            # 2. 根据depth选择执行路径
            if self.request.config.depth == AnalysisDepth.QUICK:
                # 快速判断模式
                result = await self._quick_judgment_mode()
                return result
            else:
                # 标准/深度分析模式
                result = await self._standard_analysis_mode()
                return result

        except Exception as e:
            await self._send_error(str(e))
            raise

    # ============ 快速判断模式 ============

    async def _quick_judgment_mode(self) -> Dict[str, Any]:
        """
        快速判断模式 (3-5分钟)
        """
        await self._send_status("quick_mode", "启动快速判断模式...")

        # 构建快速workflow
        self.workflow = self._build_workflow_from_templates(self.workflow_templates)
        await self._send_workflow_start()

        # 执行快速workflow
        for step in self.workflow:
            self.current_step_index = self.workflow.index(step)
            await self._execute_step(step)

        # 生成快速判断结果
        quick_result = await self._synthesize_quick_judgment()

        # 保存session
        await self._save_session(quick_judgment=quick_result)

        # 发送快速判断完成消息
        await self._send_quick_judgment_complete(quick_result)

        return {
            "mode": "quick_judgment",
            "session_id": self.session_id,
            **quick_result
        }

    async def _synthesize_quick_judgment(self) -> Dict[str, Any]:
        """
        综合快速判断结果
        默认实现,子类可覆盖
        """
        # 从results中提取关键信息
        team_score = self.results.get("team_quick_check", {}).get("team_score", 0.5)
        market_score = self.results.get("market_opportunity", {}).get("market_attractiveness", 0.5)
        red_flags = self.results.get("red_flag_scan", {}).get("red_flags", [])

        # 简单的决策逻辑
        overall_score = (team_score + market_score) / 2

        if len(red_flags) > 0:
            recommendation = "PASS"
        elif overall_score >= 0.7:
            recommendation = "BUY"
        elif overall_score >= 0.5:
            recommendation = "FURTHER_DD"
        else:
            recommendation = "PASS"

        return {
            "recommendation": recommendation,
            "confidence": overall_score,
            "judgment_time": self._calculate_elapsed_time(),
            "summary": {
                "verdict": self._generate_quick_verdict(recommendation, overall_score),
                "key_positive": self._extract_positives(),
                "key_concern": self._extract_concerns(),
                "red_flags": red_flags
            },
            "scores": {
                "team": team_score,
                "market": market_score,
                "overall": overall_score
            },
            "next_steps": {
                "recommended_action": "进行标准尽调" if recommendation == "FURTHER_DD" else None,
                "focus_areas": self._suggest_focus_areas() if recommendation == "FURTHER_DD" else []
            }
        }

    def _generate_quick_verdict(self, recommendation: str, score: float) -> str:
        """生成快速判断结论"""
        if recommendation == "BUY":
            return f"综合评分{score:.2f},建议投资"
        elif recommendation == "FURTHER_DD":
            return f"综合评分{score:.2f},建议进行标准尽调"
        else:
            return f"综合评分{score:.2f},建议放弃"

    def _extract_positives(self) -> List[str]:
        """提取积极因素"""
        positives = []
        # 从results中提取,子类可覆盖实现更详细的逻辑
        return positives

    def _extract_concerns(self) -> List[str]:
        """提取关注点"""
        concerns = []
        return concerns

    def _suggest_focus_areas(self) -> List[str]:
        """建议后续关注领域"""
        return ["深入团队背景调查", "市场数据验证", "竞争格局分析"]

    # ============ 标准分析模式 ============

    async def _standard_analysis_mode(self) -> Dict[str, Any]:
        """
        标准/深度分析模式 (30-45分钟 或 1-2小时)
        """
        await self._send_status("standard_mode", "启动标准分析模式...")

        # 构建workflow
        self.workflow = await self._build_workflow()
        await self._send_workflow_start()

        # 执行工作流
        for step in self.workflow:
            self.current_step_index = self.workflow.index(step)
            await self._execute_step(step)

            # 智能模式: 检查是否需要调整后续步骤
            if self.decision_mode == DecisionMode.INTELLIGENT:
                adjusted = await self._maybe_adjust_workflow(step)
                if adjusted:
                    await self._send_workflow_adjusted()

        # 生成最终报告
        await self._send_status("synthesizing", "正在生成分析报告...")
        final_report = await self._synthesize_final_report()

        # 保存结果
        await self._save_session(final_report=final_report)

        # 发送完成消息
        await self._send_complete(final_report)

        return final_report

    async def _build_workflow(self) -> List[WorkflowStep]:
        """
        构建工作流
        根据decision_mode和用户配置决定步骤
        """
        if self.decision_mode == DecisionMode.FIXED:
            # 固定模式: 使用模板workflow
            return self._build_fixed_workflow()

        elif self.decision_mode == DecisionMode.HYBRID:
            # 混合模式: 默认workflow + 条件调整
            workflow = self._build_fixed_workflow()

            # 检查特殊情况并调整
            if await self._is_special_case():
                workflow = await self._adjust_for_special_case(workflow)

            return workflow

        else:
            # 智能模式: 暂时使用固定workflow (未来可用LLM决策)
            return self._build_fixed_workflow()

    def _build_fixed_workflow(self) -> List[WorkflowStep]:
        """
        从模板构建固定workflow
        """
        return self._build_workflow_from_templates(self.workflow_templates)

    def _build_workflow_from_templates(
        self,
        templates: List[WorkflowStepTemplate]
    ) -> List[WorkflowStep]:
        """
        从WorkflowStepTemplate列表构建WorkflowStep列表
        """
        workflow = []
        for template in templates:
            # 检查条件
            if not self._should_execute_step(template):
                continue

            step = WorkflowStep(
                id=template.id,
                name=template.name,
                agent=template.agent,
                status="pending"
            )
            workflow.append(step)

        return workflow

    def _should_execute_step(self, template: WorkflowStepTemplate) -> bool:
        """
        判断步骤是否应该执行
        """
        # 必需步骤总是执行
        if template.required:
            return True

        # 检查条件表达式
        if template.condition:
            try:
                return eval(template.condition, {
                    "config": self.request.config,
                    "target": self.request.target,
                    "results": self.results
                })
            except:
                return False

        return True

    async def _is_special_case(self) -> bool:
        """
        判断是否为特殊情况
        子类可覆盖
        """
        return False

    async def _adjust_for_special_case(
        self,
        workflow: List[WorkflowStep]
    ) -> List[WorkflowStep]:
        """
        调整workflow应对特殊情况
        子类可覆盖
        """
        return workflow

    # ============ 步骤执行 ============

    async def _execute_step(self, step: WorkflowStep):
        """
        执行单个步骤
        """
        # 更新步骤状态
        step.status = "running"
        step.started_at = datetime.now().isoformat()
        await self._send_step_start(step)

        try:
            # 获取对应的模板
            template = self._get_step_template(step.id)

            if step.agent == "orchestrator":
                # Orchestrator自己执行
                result = await self._execute_orchestrator_step(step, template)
            else:
                # 调用专业Agent
                result = await self._execute_agent_step(step, template)

            # 保存结果
            step.result = result
            step.status = "success"
            step.completed_at = datetime.now().isoformat()
            step.progress = 100
            self.results[step.id] = result

            await self._send_step_complete(step)

        except Exception as e:
            step.status = "error"
            step.error = str(e)
            step.completed_at = datetime.now().isoformat()

            await self._send_step_error(step, str(e))
            raise

    def _get_step_template(self, step_id: str) -> Optional[WorkflowStepTemplate]:
        """获取步骤模板"""
        for template in self.workflow_templates:
            if template.id == step_id:
                return template
        return None

    async def _execute_orchestrator_step(
        self,
        step: WorkflowStep,
        template: WorkflowStepTemplate
    ) -> Dict[str, Any]:
        """
        Orchestrator自己执行的步骤 (如综合判断)
        """
        # 默认实现,子类可覆盖
        if step.id == "quick_judgment":
            return await self._synthesize_quick_judgment()
        else:
            return {"status": "completed"}

    async def _execute_agent_step(
        self,
        step: WorkflowStep,
        template: WorkflowStepTemplate
    ) -> Dict[str, Any]:
        """
        执行Agent任务

        Phase 7: 使用AgentMessageService通过Kafka执行Agent
        支持自动降级到直接调用
        """
        # 构建Agent任务
        task = self._build_agent_task(step, template)

        await self._send_agent_event(step, "thinking", f"{step.agent}正在分析...")

        try:
            # Phase 7: 使用AgentMessageService (支持Kafka + 自动降级)
            agent_service = await get_agent_service()

            # 构建配置参数
            config = {
                "quick_mode": template.quick_mode,
                "scenario": self.scenario.value,
                "depth": self.request.config.depth.value,
                "language": getattr(self.request.config, 'language', 'zh')
            }

            # 调用Agent服务
            response = await agent_service.request_analysis(
                agent_id=step.agent,
                inputs=self.request.target,
                session_id=self.session_id,
                config=config,
                trace_id=getattr(self, 'trace_id', None),
                timeout=template.expected_duration or 120
            )

            # 处理响应
            if response.get("status") == "success":
                result = response.get("outputs", {})
                # 记录执行方式 (kafka 或 direct)
                via = response.get("via", "unknown")
                print(f"[BaseOrchestrator] Agent {step.agent} executed via {via}")
                return result
            else:
                # Agent执行失败
                error_msg = response.get("error_message", "Unknown error")
                print(f"[BaseOrchestrator] Agent {step.agent} failed: {error_msg}")
                return {
                    "error": error_msg,
                    "agent": step.agent,
                    "mock": True
                }

        except Exception as e:
            print(f"[BaseOrchestrator] Agent {step.agent} execution failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "error": str(e),
                "agent": step.agent,
                "mock": True  # 标记为降级的mock结果
            }

    def _build_agent_task(
        self,
        step: WorkflowStep,
        template: WorkflowStepTemplate
    ) -> Dict[str, Any]:
        """
        为Agent构建任务描述
        """
        # 收集输入数据
        inputs = {}
        for input_key in template.inputs:
            if input_key == "all_previous":
                inputs = self.results.copy()
            else:
                inputs[input_key] = self.results.get(input_key)

        task = {
            "step_id": step.id,
            "objective": step.name,
            "inputs": inputs,
            "target": self.request.target,
            "config": self.request.config.dict(),
            "data_sources": template.data_sources,
            "quick_mode": template.quick_mode,
            "context": {
                "scenario": self.scenario.value,
                "session_id": self.session_id
            }
        }

        return task

    async def _maybe_adjust_workflow(self, completed_step: WorkflowStep) -> bool:
        """
        智能模式: 根据步骤结果决定是否调整workflow
        """
        # Phase 1暂不实现,返回False
        return False

    # ============ WebSocket消息发送 ============

    async def _send_status(self, status: str, message: str):
        if self.websocket:
            await self.websocket.send_json({
                "type": "status_update",
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "status": status,
                    "message": message
                }
            })

    async def _send_workflow_start(self):
        if self.websocket:
            await self.websocket.send_json({
                "type": "workflow_start",
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "orchestrator": self.__class__.__name__,
                    "scenario": self.scenario.value,
                    "depth": self.request.config.depth.value,
                    "total_steps": len(self.workflow),
                    "steps": [
                        {"id": s.id, "name": s.name, "agent": s.agent}
                        for s in self.workflow
                    ]
                }
            })

    async def _send_step_start(self, step: WorkflowStep):
        if self.websocket:
            await self.websocket.send_json({
                "type": "step_start",
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "step_id": step.id,
                    "step_name": step.name,
                    "step_number": self.current_step_index + 1,
                    "total_steps": len(self.workflow),
                    "agent": step.agent
                }
            })

    async def _send_step_complete(self, step: WorkflowStep):
        if self.websocket:
            await self.websocket.send_json({
                "type": "step_complete",
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "step_id": step.id,
                    "status": "success",
                    "result": step.result if step.result else {},
                    "duration": self._calculate_step_duration(step)
                }
            })

    async def _send_step_error(self, step: WorkflowStep, error: str):
        if self.websocket:
            await self.websocket.send_json({
                "type": "step_error",
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "step_id": step.id,
                    "error": error
                }
            })

    async def _send_agent_event(self, step: WorkflowStep, event_type: str, message: str):
        if self.websocket:
            await self.websocket.send_json({
                "type": "agent_event",
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "step_id": step.id,
                    "agent": step.agent,
                    "event_type": event_type,
                    "message": message
                }
            })

    async def _send_quick_judgment_complete(self, result):
        if self.websocket:
            # 如果是 Pydantic model,转换为字典
            if hasattr(result, 'model_dump'):
                result_dict = result.model_dump()
            elif hasattr(result, 'dict'):
                result_dict = result.dict()
            else:
                result_dict = result

            # 处理枚举类型
            if 'recommendation' in result_dict and hasattr(result_dict['recommendation'], 'value'):
                result_dict['recommendation'] = result_dict['recommendation'].value

            await self.websocket.send_json({
                "type": "quick_judgment_complete",
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "data": result_dict
            })

    async def _send_complete(self, report: Dict[str, Any]):
        if self.websocket:
            await self.websocket.send_json({
                "type": "analysis_complete",
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "status": "success",
                    "report_summary": {
                        "recommendation": report.get("recommendation"),
                        "confidence": report.get("confidence")
                    }
                }
            })

    async def _send_error(self, error: str):
        if self.websocket:
            await self.websocket.send_json({
                "type": "error",
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "error": error
                }
            })

    async def _send_workflow_adjusted(self):
        if self.websocket:
            await self.websocket.send_json({
                "type": "workflow_adjusted",
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "message": "Workflow已调整"
                }
            })

    # ============ 辅助方法 ============

    def _calculate_step_duration(self, step: WorkflowStep) -> Optional[int]:
        """计算步骤执行时长 (秒)"""
        if step.started_at and step.completed_at:
            start = datetime.fromisoformat(step.started_at)
            end = datetime.fromisoformat(step.completed_at)
            return int((end - start).total_seconds())
        return None

    def _calculate_elapsed_time(self) -> str:
        """计算总运行时间"""
        start = datetime.fromisoformat(self.started_at)
        now = datetime.now()
        elapsed = int((now - start).total_seconds())
        minutes = elapsed // 60
        seconds = elapsed % 60
        return f"{minutes}分{seconds}秒"

    async def _save_session(
        self,
        quick_judgment: Optional[Dict[str, Any]] = None,
        final_report: Optional[Dict[str, Any]] = None
    ):
        """
        保存session和report到Redis
        """
        try:
            # Construct session context
            context = {
                "session_id": self.session_id,
                "scenario": self.scenario.value,
                "request": self.request.dict(),
                "status": "completed" if (final_report or quick_judgment) else "running",
                "results": self.results,
                "workflow": [step.dict() for step in self.workflow],
                "started_at": self.started_at,
                "updated_at": datetime.now().isoformat()
            }

            if quick_judgment:
                # Handle Pydantic models in quick_judgment
                if hasattr(quick_judgment, 'dict'):
                    context["quick_judgment"] = quick_judgment.dict()
                elif hasattr(quick_judgment, 'model_dump'):
                     context["quick_judgment"] = quick_judgment.model_dump()
                else:
                    context["quick_judgment"] = quick_judgment
            
            if final_report:
                context["final_report"] = final_report

            # Save session
            self.session_store.save_session(self.session_id, context)

            # If completed (quick or standard), save as a report
            if quick_judgment or final_report:
                # Prepare quick_judgment data for report
                qj_data = {}
                if quick_judgment:
                    if hasattr(quick_judgment, 'dict'):
                        qj_data = quick_judgment.dict()
                    elif hasattr(quick_judgment, 'model_dump'):
                        qj_data = quick_judgment.model_dump()
                    else:
                        qj_data = quick_judgment

                report_data = {
                    "id": self.session_id, # Use session_id as report_id for simplicity
                    "session_id": self.session_id,
                    "project_name": self.request.project_name,
                    "company_name": self.request.target.get("company_name") or self.request.target.get("target_name") or self.request.target.get("ticker") or "Unknown Target",
                    "analysis_type": self.scenario.value,
                    "status": "completed",
                    "created_at": datetime.now().isoformat(),
                    "steps": [step.dict() for step in self.workflow],
                    "preliminary_im": final_report if final_report else {}, # Map final report structure here
                    "quick_judgment": qj_data
                }
                self.session_store.save_report(self.session_id, report_data)
                
        except Exception as e:
            print(f"[BaseOrchestrator] Failed to save session: {e}")
            # Don't raise, just log, to avoid crashing the flow at the very end
