# backend/services/report_orchestrator/app/core/dd_state_machine.py
"""
State machine for Due Diligence (DD) workflow.
DD 工作流状态机
"""
import asyncio
from typing import Optional, Dict, Any, List
from fastapi import WebSocket
from starlette.websockets import WebSocketState
from datetime import datetime
import os

from ..models.dd_models import (
    DDWorkflowState,
    DDSessionContext,
    DDStep,
    DDWorkflowMessage,
    BPStructuredData,
    TeamAnalysisOutput,
    MarketAnalysisOutput,
    PreliminaryIM,
    CrossCheckResult,
)
from .llm_helper import LLMHelper
from .service_endpoints import get_internal_knowledge_url, get_web_search_url
from app.services.web_search_access import search_web as shared_search_web

# V4: Import AgentEventBus
from .agent_event_bus import get_event_bus


class DDStateMachine:
    """
    State machine managing the DD workflow lifecycle.
    
    States:
    1. INIT -> DOC_PARSE
    2. DOC_PARSE -> TDD (and MDD in parallel)
    3. TDD + MDD -> CROSS_CHECK
    4. CROSS_CHECK -> DD_QUESTIONS
    5. DD_QUESTIONS -> HITL_REVIEW
    6. HITL_REVIEW -> COMPLETED
    
    Error at any state -> ERROR
    """
    
    def __init__(
        self,
        session_id: str,
        company_name: str,
        bp_file_content: Optional[bytes],
        bp_filename: str,
        user_id: str = "default_user",
        # V5: Frontend configuration support
        project_name: Optional[str] = None,
        selected_agents: Optional[List[str]] = None,
        data_sources: Optional[List[str]] = None,
        priority: str = "normal",
        description: Optional[str] = None
    ):
        self.context = DDSessionContext(
            session_id=session_id,
            company_name=company_name,
            user_id=user_id
        )
        self.bp_file_content = bp_file_content
        self.bp_filename = bp_filename
        self.websocket: Optional[WebSocket] = None
        self._websocket_lock = asyncio.Lock()  # V5: Lock for WebSocket send operations

        # V5: Store frontend configuration
        self.project_name = project_name or f"{company_name} DD Analysis"
        self.selected_agents = selected_agents or []
        self.data_sources = data_sources or []
        self.priority = priority
        self.description = description

        # V4: AgentEventBus for real-time updates
        self.event_bus = get_event_bus()

        # Service URLs (prefer environment, fall back to docker-compose internal DNS names)
        self.LLM_GATEWAY_URL = os.getenv("LLM_GATEWAY_URL", "http://llm_gateway:8003")
        # docker-compose uses PUBLIC_DATA_URL to point at external_data_service
        self.EXTERNAL_DATA_URL = os.getenv(
            "PUBLIC_DATA_URL",
            os.getenv("EXTERNAL_DATA_URL", "http://external_data_service:8006"),
        )
        self.WEB_SEARCH_URL = get_web_search_url()
        self.INTERNAL_KNOWLEDGE_URL = get_internal_knowledge_url()
        self.USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user_service:8008")
        self._llm_helper = LLMHelper(llm_gateway_url=self.LLM_GATEWAY_URL, timeout=30)

        # Steps definition (dynamically adjusted based on selected_agents)
        self.steps = self._init_steps()

    def _should_run_step(self, step_id: int) -> bool:
        """
        V5: Determine if a step should run based on selected_agents configuration.

        Agent to Step mapping:
        - team-evaluator -> Step 3 (TDD)
        - market-analyst -> Step 4 (MDD)
        - financial-expert -> Step 1 (BP Parse), Step 4 (MDD)
        - risk-assessor -> Step 5 (Cross-check), Step 6 (Questions)
        - tech-specialist -> Step 4 (MDD)
        - legal-advisor -> Step 6 (Questions)

        Steps 0, 1, 7 always run (Init, BP Parse, HITL Review)
        """
        # If no agents selected, run all steps (default behavior)
        if not self.selected_agents:
            return True

        # Always run these steps
        if step_id in [0, 1, 7]:
            return True

        # Step 2: Preference check (always run if configured)
        if step_id == 2:
            return True

        # Step 3: TDD - requires team-evaluator
        if step_id == 3:
            return 'team-evaluator' in self.selected_agents

        # Step 4: MDD - requires market-analyst, financial-expert, or tech-specialist
        if step_id == 4:
            return any(agent in self.selected_agents for agent in
                      ['market-analyst', 'financial-expert', 'tech-specialist'])

        # Step 5: Cross-check - requires risk-assessor or at least 2 agents
        if step_id == 5:
            return 'risk-assessor' in self.selected_agents or len(self.selected_agents) >= 2

        # Step 6: DD Questions - requires risk-assessor or legal-advisor
        if step_id == 6:
            return any(agent in self.selected_agents for agent in
                      ['risk-assessor', 'legal-advisor'])

        return True

    def _init_steps(self) -> Dict[int, DDStep]:
        """Initialize all workflow steps"""
        return {
            0: DDStep(id=0, title="初始化 DD 工作流", status="pending"),
            1: DDStep(id=1, title="解析商业计划书 (BP)", status="pending", sub_steps=[
                "上传文件到 LLM Gateway",
                "提取结构化数据",
                "验证数据完整性"
            ]),
            2: DDStep(id=2, title="机构偏好匹配检查", status="pending", sub_steps=[
                "获取机构投资偏好",
                "检查行业/阶段匹配度",
                "计算综合匹配评分"
            ]),
            3: DDStep(id=3, title="团队背景调查 (TDD)", status="pending", sub_steps=[
                "查询工商/LinkedIn 数据",
                "网络搜索团队背景",
                "生成团队分析报告"
            ]),
            4: DDStep(id=4, title="市场尽职调查 (MDD)", status="pending", sub_steps=[
                "验证市场规模",
                "搜索竞品信息",
                "查询内部历史项目",
                "生成市场分析报告"
            ]),
            5: DDStep(id=5, title="交叉验证 BP 数据", status="pending", sub_steps=[
                "对比团队信息",
                "验证市场数据",
                "识别不一致之处"
            ]),
            6: DDStep(id=6, title="生成 DD 问题清单", status="pending", sub_steps=[
                "分析薄弱环节",
                "生成专业问题",
                "分类和优先级排序"
            ]),
            7: DDStep(id=7, title="等待人工审核", status="pending", flush=True)
        }
    
    async def run(self, websocket: Optional[WebSocket] = None):
        """
        Execute the complete DD workflow.
        执行完整的 DD 工作流
        """
        self.websocket = websocket

        # V4: Subscribe websocket to event bus
        if self.websocket:
            await self.event_bus.subscribe(self.websocket)

        try:
            print(f"[DD_WORKFLOW] Starting workflow for {self.context.company_name}", flush=True)
            print(f"[DD_WORKFLOW] Selected agents: {self.selected_agents}", flush=True)
            print(f"[DD_WORKFLOW] Data sources: {self.data_sources}", flush=True)

            # Step 0: Initialization
            print(f"[DD_WORKFLOW] Step 0: Init", flush=True)
            await self._transition_to_init()

            # Step 1: Parse BP
            print(f"[DD_WORKFLOW] Step 1: Parse BP", flush=True)
            await self._transition_to_doc_parse()

            # Step 2: Preference Check (V5: conditional)
            if self._should_run_step(2):
                print(f"[DD_WORKFLOW] Step 2: Preference check", flush=True)
                should_continue = await self._transition_to_preference_check()
                if not should_continue:
                    print(f"[DD_WORKFLOW] Preference mismatch, terminating early", flush=True)
                    await self._transition_to_completed()
                    return
            else:
                print(f"[DD_WORKFLOW] Step 2: Skipped (not configured)", flush=True)
                self.steps[2].status = "skipped"

            # Step 3 & 4: TDD and MDD (V5: conditional parallel)
            run_tdd = self._should_run_step(3)
            run_mdd = self._should_run_step(4)

            if run_tdd or run_mdd:
                print(f"[DD_WORKFLOW] Step 3&4: Parallel analysis (TDD={run_tdd}, MDD={run_mdd})", flush=True)
                await self._transition_to_parallel_analysis()
            else:
                print(f"[DD_WORKFLOW] Step 3&4: Skipped (no agents selected)", flush=True)
                self.steps[3].status = "skipped"
                self.steps[4].status = "skipped"

            # Step 5: Cross-check (V5: conditional)
            if self._should_run_step(5):
                print(f"[DD_WORKFLOW] Step 5: Cross-check", flush=True)
                await self._transition_to_cross_check()
            else:
                print(f"[DD_WORKFLOW] Step 5: Skipped (risk-assessor not selected)", flush=True)
                self.steps[5].status = "skipped"

            # Step 6: Generate DD questions (V5: conditional)
            if self._should_run_step(6):
                print(f"[DD_WORKFLOW] Step 6: DD questions", flush=True)
                await self._transition_to_dd_questions()
            else:
                print(f"[DD_WORKFLOW] Step 6: Skipped (no Q&A agents selected)", flush=True)
                self.steps[6].status = "skipped"

            # Step 7: HITL Review
            print(f"[DD_WORKFLOW] Step 7: HITL review", flush=True)
            await self._transition_to_hitl_review()

            # HITL review pauses the workflow - user needs to review the preliminary IM
            # The workflow will resume when user provides feedback (future implementation)
            # For now, HITL review is the final step

            print(f"[DD_WORKFLOW] Workflow paused for HITL review", flush=True)
            
        except Exception as e:
            print(f"[DD_WORKFLOW] ERROR: {e}", flush=True)
            import traceback
            traceback.print_exc()
            await self._transition_to_error(str(e))
    
    async def _transition_to_init(self):
        """Initialize the workflow"""
        self.context.current_state = DDWorkflowState.INIT
        step = self.steps[0]
        step.status = "running"
        step.started_at = datetime.now().isoformat()
        
        await self._send_progress_update(step)
        
        # Simulate initialization
        await asyncio.sleep(0.5)
        
        step.status = "success"
        step.completed_at = datetime.now().isoformat()
        step.result = f"已为 '{self.context.company_name}' 初始化 DD 工作流"
        
        await self._send_progress_update(step)
    
    async def _transition_to_doc_parse(self):
        """Parse BP document or skip if no BP provided"""
        self.context.current_state = DDWorkflowState.DOC_PARSE
        step = self.steps[1]
        step.status = "running"
        step.started_at = datetime.now().isoformat()
        step.progress = 0

        await self._send_progress_update(step)

        # V4: Publish Agent event
        await self.event_bus.publish_started(
            agent_name="BP Parser",
            message=f"开始解析商业计划书"
        )

        try:
            # Check if BP file is provided
            if not self.bp_file_content:
                # No BP file - search for company info online
                step.progress = 30
                step.result = f"未提供 BP 文件，正在搜索 '{self.context.company_name}' 的公开信息..."
                await self._send_progress_update(step)

                # V4: Publish searching event
                await self.event_bus.publish_searching(
                    agent_name="BP Parser",
                    query=f"{self.context.company_name} 公司信息",
                    progress=0.3
                )
                
                print(f"[DEBUG] No BP file, searching for company info online...", flush=True)
                
                # Search for company information
                try:
                    bp_data = await self._search_company_info(self.context.company_name)
                    self.context.bp_data = bp_data
                    
                    step.progress = 100
                    step.status = "success"
                    step.completed_at = datetime.now().isoformat()
                    step.result = f"从公开信息中获取了关于 '{self.context.company_name}' 的基本信息"
                    print(f"[DEBUG] Company search successful!", flush=True)
                except Exception as search_error:
                    print(f"[ERROR] Company search failed: {search_error}", flush=True)
                    # Fallback to minimal data
                    self.context.bp_data = BPStructuredData(
                        company_name=self.context.company_name,
                        product_description="待通过调研确定",
                        current_stage="待确定",
                        target_market="待调研"
                    )
                    step.progress = 100
                    step.status = "success"
                    step.completed_at = datetime.now().isoformat()
                    step.result = f"未找到公开信息，将基于公司名称进行基础分析"
            else:
                # BP file provided - parse it
                print(f"[DEBUG] Parsing BP file: {self.bp_filename}, size: {len(self.bp_file_content)} bytes", flush=True)
                from ..parsers.bp_parser import BPParser
                
                parser = BPParser(self.LLM_GATEWAY_URL)
                
                # Update progress during parsing
                step.progress = 30
                await self._send_progress_update(step)
                
                print(f"[DEBUG] Calling parser.parse_bp...", flush=True)
                # Parse BP
                try:
                    bp_data = await parser.parse_bp(
                        self.bp_file_content, 
                        self.bp_filename,
                        self.context.company_name
                    )
                    print(f"[DEBUG] BP parsing successful!", flush=True)
                except Exception as parse_error:
                    print(f"[DEBUG] BP parsing failed: {parse_error}", flush=True)
                    import traceback
                    traceback.print_exc()
                    raise
                
                self.context.bp_data = bp_data

                # V4: Publish result event
                await self.event_bus.publish_result(
                    agent_name="BP Parser",
                    message=f"提取了 {len(bp_data.team)} 名团队成员和关键业务信息",
                    data={"team_count": len(bp_data.team)}
                )

                step.progress = 100
                step.status = "success"
                step.completed_at = datetime.now().isoformat()
                step.result = f"成功解析 BP，提取了 {len(bp_data.team)} 名团队成员和关键业务信息"

                # V4: Publish completed event
                await self.event_bus.publish_completed(
                    agent_name="BP Parser",
                    message="BP解析完成"
                )
            
        except Exception as e:
            step.status = "error"
            step.error_message = f"BP 解析失败: {str(e)}"
            self.context.errors.append(step.error_message)
            raise
        
        await self._send_progress_update(step)
    
    async def _transition_to_preference_check(self) -> bool:
        """
        Check if project matches institution preferences (Sprint 4)
        检查项目是否匹配机构偏好
        
        Returns:
            bool: True if should continue, False if should terminate early
        """
        self.context.current_state = DDWorkflowState.PREFERENCE_CHECK
        step = self.steps[2]
        step.status = "running"
        step.started_at = datetime.now().isoformat()
        step.progress = 0
        
        await self._send_progress_update(step)
        
        try:
            from ..agents.preference_match_agent import PreferenceMatchAgent
            
            agent = PreferenceMatchAgent(self.USER_SERVICE_URL)
            
            step.progress = 30
            await self._send_progress_update(step)
            
            # Execute preference matching
            match_result = await agent.check_match(
                bp_data=self.context.bp_data,
                user_id=self.context.user_id
            )
            
            # Store result in context
            self.context.preference_match_result = match_result.to_dict()
            
            step.progress = 100
            step.status = "success"
            step.completed_at = datetime.now().isoformat()
            
            if match_result.is_match:
                step.result = f"✅ 匹配度: {match_result.match_score}分 - 继续分析"
                await self._send_progress_update(step)
                return True  # Continue workflow
            else:
                step.result = f"⚠️ 匹配度: {match_result.match_score}分 - 不匹配，提前终止"
                step.error_message = f"不匹配原因: {'; '.join(match_result.mismatch_reasons)}"
                
                # Store mismatch info
                self.context.errors.append(f"项目与机构投资偏好不符 (匹配度 {match_result.match_score}分)")
                self.context.errors.extend(match_result.mismatch_reasons)
                
                await self._send_progress_update(step)
                return False  # Terminate early
        
        except Exception as e:
            step.status = "error"
            step.error_message = f"偏好检查失败: {str(e)}"
            self.context.errors.append(step.error_message)
            
            # On error, default to continue (fail-safe)
            print(f"Warning: Preference check failed, defaulting to continue: {e}", flush=True)
            await self._send_progress_update(step)
            return True
    
    async def _transition_to_parallel_analysis(self):
        """Execute TDD and MDD in parallel (V5: conditional based on selected_agents)"""
        tdd_step = self.steps[3]
        mdd_step = self.steps[4]

        # V5: Check which analyses should run
        run_tdd = self._should_run_step(3)
        run_mdd = self._should_run_step(4)

        tasks = []

        try:
            # Execute TDD if needed
            if run_tdd:
                tdd_step.status = "running"
                tdd_step.started_at = datetime.now().isoformat()
                await self._send_progress_update(tdd_step)
                tdd_task = asyncio.create_task(self._execute_tdd())
                tasks.append(('tdd', tdd_task))
            else:
                tdd_step.status = "skipped"
                tdd_step.result = "未选择团队评估智能体"
                await self._send_progress_update(tdd_step)

            # Execute MDD if needed
            if run_mdd:
                mdd_step.status = "running"
                mdd_step.started_at = datetime.now().isoformat()
                await self._send_progress_update(mdd_step)
                mdd_task = asyncio.create_task(self._execute_mdd())
                tasks.append(('mdd', mdd_task))
            else:
                mdd_step.status = "skipped"
                mdd_step.result = "未选择市场分析智能体"
                await self._send_progress_update(mdd_step)

            # Wait for all running tasks
            if tasks:
                results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)

                # Process results
                for (task_type, _), result in zip(tasks, results):
                    # Check if result is an exception
                    if isinstance(result, Exception):
                        print(f"[DD_WORKFLOW] Task {task_type} failed with exception: {result}")
                        if task_type == 'tdd':
                            tdd_step.status = "error"
                            tdd_step.error_message = str(result)
                            tdd_step.result = "团队分析失败"
                            await self._send_progress_update(tdd_step)
                        elif task_type == 'mdd':
                            mdd_step.status = "error"
                            mdd_step.error_message = str(result)
                            mdd_step.result = "市场分析失败"
                            await self._send_progress_update(mdd_step)
                        continue

                    # Process successful results
                    if task_type == 'tdd':
                        self.context.team_analysis = result
                        tdd_step.status = "success"
                        tdd_step.completed_at = datetime.now().isoformat()
                        tdd_step.result = f"团队分析完成，经验匹配度: {result.experience_match_score}/10"
                        await self._send_progress_update(tdd_step)
                    elif task_type == 'mdd':
                        self.context.market_analysis = result
                        mdd_step.status = "success"
                        mdd_step.completed_at = datetime.now().isoformat()
                        mdd_step.result = "市场分析完成，已验证市场规模和竞争格局"
                        await self._send_progress_update(mdd_step)

        except Exception as e:
            # Mark running steps as error
            if run_tdd:
                tdd_step.status = "error"
                tdd_step.error_message = str(e)
            if run_mdd:
                mdd_step.status = "error"
                mdd_step.error_message = str(e)
            self.context.errors.append(f"并行分析失败: {str(e)}")
            raise
    
    async def _execute_tdd(self) -> TeamAnalysisOutput:
        """Execute Team Due Diligence"""
        # V4: Publish started event
        await self.event_bus.publish_started(
            agent_name="Team Agent",
            message=f"开始团队尽职调查"
        )

        from ..agents.team_analysis_agent import TeamAnalysisAgent

        agent = TeamAnalysisAgent(
            external_data_url=self.EXTERNAL_DATA_URL,
            web_search_url=self.WEB_SEARCH_URL,
            llm_gateway_url=self.LLM_GATEWAY_URL
        )

        # V4: Pass event bus to agent
        agent.event_bus = self.event_bus

        result = await agent.analyze(
            bp_team_info=self.context.bp_data.team,
            company_name=self.context.company_name
        )

        # V4: Publish completed event
        await self.event_bus.publish_completed(
            agent_name="Team Agent",
            message=f"团队分析完成，经验匹配度: {result.experience_match_score}/10"
        )

        return result
    
    async def _execute_mdd(self) -> MarketAnalysisOutput:
        """Execute Market Due Diligence"""
        # V4: Publish started event
        await self.event_bus.publish_started(
            agent_name="Market Agent",
            message=f"开始市场尽职调查"
        )

        from ..agents.market_analysis_agent import MarketAnalysisAgent

        agent = MarketAnalysisAgent(
            web_search_url=self.WEB_SEARCH_URL,
            internal_knowledge_url=self.INTERNAL_KNOWLEDGE_URL,
            llm_gateway_url=self.LLM_GATEWAY_URL
        )

        # V4: Pass event bus to agent
        agent.event_bus = self.event_bus

        result = await agent.analyze(
            bp_market_info={
                "target_market": self.context.bp_data.target_market,
                "market_size_tam": self.context.bp_data.market_size_tam,
                "competitors": self.context.bp_data.competitors,
            },
            company_name=self.context.company_name
        )

        # V4: Publish completed event
        await self.event_bus.publish_completed(
            agent_name="Market Agent",
            message="市场分析完成"
        )

        return result
    
    async def _transition_to_cross_check(self):
        """Cross-check BP data against external sources"""
        self.context.current_state = DDWorkflowState.CROSS_CHECK
        step = self.steps[5]  # Updated from 4 to 5 (Sprint 4)
        step.status = "running"
        step.started_at = datetime.now().isoformat()
        
        await self._send_progress_update(step)
        
        try:
            # Simple cross-checking logic (can be expanded)
            cross_check_results = []
            
            # Check team information
            if self.context.team_analysis and self.context.team_analysis.concerns and len(self.context.team_analysis.concerns) > 0:
                for concern in self.context.team_analysis.concerns:
                    cross_check_results.append(CrossCheckResult(
                        category="Team",
                        bp_claim="团队背景声明",
                        external_data=concern,
                        is_consistent=False,
                        discrepancy_level="Minor",
                        notes="团队分析中发现的潜在问题"
                    ))
            
            # Check market information
            if self.context.market_analysis and self.context.market_analysis.red_flags and len(self.context.market_analysis.red_flags) > 0:
                for red_flag in self.context.market_analysis.red_flags:
                    cross_check_results.append(CrossCheckResult(
                        category="Market",
                        bp_claim="市场规模和增长预期",
                        external_data=red_flag,
                        is_consistent=False,
                        discrepancy_level="Major" if "严重" in red_flag or "重大" in red_flag else "Minor",
                        notes="市场分析中发现的风险"
                    ))
            
            self.context.cross_check_results = cross_check_results
            
            step.status = "success"
            step.completed_at = datetime.now().isoformat()
            step.result = f"交叉验证完成，发现 {len(cross_check_results)} 个需要关注的点"
            
        except Exception as e:
            step.status = "error"
            step.error_message = f"交叉验证失败: {str(e)}"
            self.context.errors.append(step.error_message)
            raise
        
        await self._send_progress_update(step)
    
    async def _transition_to_dd_questions(self):
        """Generate DD question list"""
        self.context.current_state = DDWorkflowState.DD_QUESTIONS
        step = self.steps[6]  # Updated from 5 to 6 (Sprint 4)
        step.status = "running"
        step.started_at = datetime.now().isoformat()
        
        await self._send_progress_update(step)
        
        try:
            from ..agents.risk_agent import RiskAgent
            
            agent = RiskAgent(self.LLM_GATEWAY_URL)
            
            dd_questions = await agent.generate_dd_questions(
                team_analysis=self.context.team_analysis,
                market_analysis=self.context.market_analysis,
                bp_data=self.context.bp_data
            )
            
            self.context.dd_questions = dd_questions
            
            step.status = "success"
            step.completed_at = datetime.now().isoformat()
            step.result = f"已生成 {len(dd_questions)} 个 DD 问题"
            
        except Exception as e:
            step.status = "error"
            step.error_message = f"DD 问题生成失败: {str(e)}"
            self.context.errors.append(step.error_message)
            raise
        
        await self._send_progress_update(step)
    
    async def _transition_to_hitl_review(self):
        """Pause for Human-in-the-Loop review"""
        self.context.current_state = DDWorkflowState.HITL_REVIEW
        step = self.steps[7]  # Updated from 6 to 7 (Sprint 4)
        step.status = "paused"
        step.started_at = datetime.now().isoformat()
        step.result = "✅ 初步尽职调查完成！您现在可以：\n\n1. 📝 查看和编辑投资备忘录\n2. 📄 添加访谈纪要或补充材料\n3. 💬 回答 DD 问题以深化分析\n\n请在 IM 工作台中继续您的工作。"

        # V5: Use ReportSynthesizerAgent to generate the final summary
        try:
            from ..agents.report_synthesizer_agent import ReportSynthesizerAgent
            
            print(f"[DD_WORKFLOW] Calling ReportSynthesizer for final summary...", flush=True)
            
            synthesizer = ReportSynthesizerAgent(quick_mode=False)
            
            # Prepare context for synthesizer
            # Convert Pydantic models to dicts where necessary
            context_data = {
                "scenario": "due-diligence",
                "target": {
                    "company_name": self.context.company_name,
                    "project_name": self.project_name,
                    # Add other target info from bp_data if available
                    **self.context.bp_data.dict()
                },
                "team_analysis": self.context.team_analysis.dict() if self.context.team_analysis else {},
                "market_analysis": self.context.market_analysis.dict() if self.context.market_analysis else {},
                # Add other analyses if available (financial, risk, etc.)
                "risk_assessment": {
                    "red_flags": [r.external_data for r in self.context.cross_check_results if r.discrepancy_level == "Major"] 
                                 + ([q.question for q in self.context.dd_questions] if self.context.dd_questions else [])
                }
            }
            
            # Generate report
            synthesized_report = await synthesizer.synthesize(context_data)
            
            print(f"[DD_WORKFLOW] ReportSynthesizer finished. Recommendation: {synthesized_report.get('overall_recommendation')}", flush=True)
            
            # Update context with synthesized result
            # We need to map the synthesizer output back to PreliminaryIM structure or store it directly
            # For now, we'll enhance the PreliminaryIM with the synthesized summary
            
            # Extract summary from synthesized report
            exec_summary = synthesized_report.get('executive_summary', '')
            financial_highlights = synthesized_report.get('preliminary_im', {}).get('financial_highlights', {})
            
            # Build PreliminaryIM (combining structured data + synthesized text)
            preliminary_im = PreliminaryIM(
                company_name=self.context.company_name,
                bp_structured_data=self.context.bp_data,
                team_section=self.context.team_analysis,
                market_section=self.context.market_analysis,
                cross_check_results=self.context.cross_check_results,
                dd_questions=self.context.dd_questions,
                session_id=self.context.session_id,
                # Add synthesized fields
                investment_highlights=synthesized_report.get('preliminary_im', {}).get('investment_highlights', []),
                investment_recommendation=synthesized_report.get('preliminary_im', {}).get('investment_recommendation', ''),
                key_findings=synthesized_report.get('preliminary_im', {}).get('key_findings', []),
                financial_highlights=financial_highlights,
                final_report=synthesized_report # Store full report for reference
            )
            
            self.context.preliminary_im = preliminary_im.dict()
            
            # Send to frontend for review
            await self._send_hitl_message(step, preliminary_im)

        except Exception as e:
            print(f"[DD_WORKFLOW] Report synthesis failed: {e}", flush=True)
            import traceback
            traceback.print_exc()
            
            # Fallback to basic PreliminaryIM if synthesis fails
            preliminary_im = PreliminaryIM(
                company_name=self.context.company_name,
                bp_structured_data=self.context.bp_data,
                team_section=self.context.team_analysis,
                market_section=self.context.market_analysis,
                cross_check_results=self.context.cross_check_results,
                dd_questions=self.context.dd_questions,
                session_id=self.context.session_id
            )
            await self._send_hitl_message(step, preliminary_im)
    
    async def _transition_to_completed(self):
        """Mark workflow as completed"""
        self.context.current_state = DDWorkflowState.COMPLETED
        
        step = DDStep(
            id=7,
            title="DD 工作流完成",
            status="success",
            result="所有分析步骤已完成，投资备忘录已生成"
        )
        
        await self._send_progress_update(step, final=True)
    
    async def _transition_to_error(self, error_message: str):
        """Handle error state"""
        self.context.current_state = DDWorkflowState.ERROR

        error_step = DDStep(
            id=-1,
            title="工作流错误",
            status="error",
            error_message=error_message
        )

        if self.websocket:
            # Check if WebSocket is still connected before sending
            try:
                if self.websocket.client_state != WebSocketState.CONNECTED:
                    print(f"[DEBUG] WebSocket not connected in error handler (state: {self.websocket.client_state}), skipping error message", flush=True)
                    return
            except Exception as state_check_error:
                print(f"[DEBUG] WebSocket state check failed in error handler: {state_check_error}", flush=True)
                return

            message = DDWorkflowMessage(
                session_id=self.context.session_id,
                status="error",
                current_step=error_step,
                message=f"DD 工作流遇到错误: {error_message}"
            )

            try:
                await self.websocket.send_json(message.dict())
            except Exception as e:
                print(f"[DEBUG] Failed to send error message via WebSocket: {e}", flush=True)
    
    async def _send_progress_update(self, step: DDStep, final: bool = False):
        """Send progress update via WebSocket with lock protection"""
        if not self.websocket:
            return

        # Check if WebSocket is still connected
        try:
            if self.websocket.client_state != WebSocketState.CONNECTED:
                print(f"[DEBUG] WebSocket not connected (state: {self.websocket.client_state}), skipping progress update", flush=True)
                return
        except Exception as state_check_error:
            print(f"[DEBUG] WebSocket state check failed: {state_check_error}", flush=True)
            return

        status = "completed" if final else "in_progress"

        message = DDWorkflowMessage(
            session_id=self.context.session_id,
            status=status,
            current_step=step,
            all_steps=list(self.steps.values())
        )

        # V5: Use lock to prevent race conditions when sending from parallel tasks
        async with self._websocket_lock:
            try:
                await self.websocket.send_json(message.dict())
            except Exception as e:
                print(f"[DEBUG] Failed to send progress update: {e}", flush=True)
    
    async def _send_hitl_message(self, step: DDStep, preliminary_im: PreliminaryIM):
        """Send HITL review message"""
        if not self.websocket:
            print(f"[HITL] No websocket available", flush=True)
            return

        # Check if WebSocket is still connected
        try:
            if self.websocket.client_state != WebSocketState.CONNECTED:
                print(f"[HITL] WebSocket not connected (state: {self.websocket.client_state}), skipping HITL message", flush=True)
                return
        except Exception as state_check_error:
            print(f"[HITL] WebSocket state check failed: {state_check_error}", flush=True)
            return

        print(f"[HITL] Converting preliminary IM to frontend format...", flush=True)
        # Convert PreliminaryIM to frontend-compatible format
        frontend_report = self._convert_im_to_frontend_format(preliminary_im)

        # Build message dict manually to avoid Pydantic validation on preliminary_im
        message_dict = {
            "session_id": self.context.session_id,
            "status": "hitl_required",
            "current_step": step.dict() if step else None,
            "all_steps": [s.dict() for s in self.steps.values()],
            "preliminary_im": frontend_report,  # Already a dict
            "message": "初步投资备忘录已生成，请审核并提供反馈"
        }

        # V5: Use lock to prevent race conditions
        async with self._websocket_lock:
            try:
                print(f"[HITL] Sending HITL message with report for session {self.context.session_id}", flush=True)
                await self.websocket.send_json(message_dict)
                print(f"[HITL] ✅ HITL message sent successfully!", flush=True)
            except Exception as e:
                print(f"[HITL] ❌ Failed to send HITL message: {e}", flush=True)
                import traceback
                traceback.print_exc()
    
    async def _search_company_info(self, company_name: str) -> "BPStructuredData":
        """
        Search for company information online when no BP is provided.
        使用网络搜索获取公司基本信息（当没有 BP 文件时）
        """
        from ..models.dd_models import BPStructuredData, TeamMember
        
        # Search for company basic info
        query = f"{company_name} 公司简介 业务 产品"
        
        try:
            search_results = await shared_search_web(
                self.WEB_SEARCH_URL,
                query=query,
                max_results=5,
                timeout=30.0,
            )

            if search_results:
                # Extract info from search results using LLM.
                # shared_search_web normalizes to title/content/url.
                context = "\n\n".join([
                    f"标题: {r.get('title', '')}\n内容: {r.get('content', '')}\n链接: {r.get('url', '')}"
                    for r in search_results[:5]
                ])

                prompt = f"""根据以下搜索结果，提取关于 "{company_name}" 的基本信息：

{context}

请以 JSON 格式返回：
{{
    "company_name": "公司全称",
    "product_description": "主营产品/业务描述（50-100字）",
    "target_market": "目标市场/行业",
    "current_stage": "发展阶段（种子期/天使轮/A轮/B轮/成熟期等）",
    "founding_year": "成立年份（如果有）",
    "team_size": "团队规模（如果有）",
    "key_members": ["核心团队成员姓名和职位，如果有"]
}}

如果某些信息无法从搜索结果中获取，请填写 "未知" 或 "信息不详"。
只返回 JSON，不要其他说明文字。"""

                company_info = await self._llm_helper.call(prompt=prompt, response_format="json")
                if "error" in company_info:
                    print(f"[ERROR] Failed to extract company info via LLM: {company_info}", flush=True)
                else:
                    # Build team members from key_members if available
                    team_members = []
                    if "key_members" in company_info and company_info["key_members"]:
                        for member_info in company_info["key_members"][:5]:
                            if isinstance(member_info, str):
                                parts = member_info.split()
                                name = parts[0] if parts else "未知"
                                title = " ".join(parts[1:]) if len(parts) > 1 else "管理层"
                            else:
                                name = member_info.get("name", "未知")
                                title = member_info.get("title", "管理层")

                            team_members.append(TeamMember(
                                name=name,
                                title=title,
                                background=f"根据公开信息，{name} 担任 {company_name} 的 {title}"
                            ))

                    return BPStructuredData(
                        company_name=company_info.get("company_name", company_name),
                        product_description=company_info.get("product_description", "信息不详"),
                        target_market=company_info.get("target_market", "信息不详"),
                        current_stage=company_info.get("current_stage", "信息不详"),
                        team=team_members,
                        founding_date=company_info.get("founding_year"),
                    )
        
        except Exception as e:
            print(f"[ERROR] Failed to search company info: {e}", flush=True)
            import traceback
            traceback.print_exc()
        
        # Fallback: minimal data
        return BPStructuredData(
            company_name=company_name,
            product_description="信息不详，需进一步调研",
            current_stage="信息不详",
            target_market="信息不详"
        )
    
    def _convert_im_to_frontend_format(self, preliminary_im: PreliminaryIM) -> Dict[str, Any]:
        """
        Convert PreliminaryIM to frontend-compatible FullReport format.
        将 PreliminaryIM 转换为前端兼容的 FullReport 格式
        """
        # Build report sections
        sections = []
        
        # 1. Executive Summary (基于 BP 数据 + 综合分析)
        bp_data = preliminary_im.bp_structured_data
        
        # Extract synthesized content if available (from V5 update)
        inv_rec = getattr(preliminary_im, 'investment_recommendation', None)
        inv_highlights = getattr(preliminary_im, 'investment_highlights', [])
        key_findings = getattr(preliminary_im, 'key_findings', [])
        
        exec_summary = f"""**公司**: {bp_data.company_name}
**融资**: {bp_data.funding_request or '待定'}
**估值**: {bp_data.current_valuation or '待定'}
**阶段**: {bp_data.current_stage or '待确认'}

**产品描述**: {bp_data.product_description or '详见BP'}

**市场**: {bp_data.target_market or '待确认'}
**市场规模**: {bp_data.market_size_tam or '待核实'}
"""

        # Add synthesized insights if available
        if inv_rec:
            exec_summary += f"\n\n**投资建议**: {inv_rec}"
        
        if inv_highlights:
            highlights_str = "\n".join([f"- {h}" for h in inv_highlights[:3]])
            exec_summary += f"\n\n**投资亮点**:\n{highlights_str}"
            
        if key_findings:
            # Clean up key findings format if they contain category prefixes
            cleaned_findings = []
            for f in key_findings[:3]:
                if isinstance(f, str) and ":" in f:
                    cleaned_findings.append(f.split(":", 1)[1].strip())
                else:
                    cleaned_findings.append(str(f))
            findings_str = "\n".join([f"- {f}" for f in cleaned_findings])
            exec_summary += f"\n\n**关键发现**:\n{findings_str}"

        sections.append({
            "section_title": "执行摘要",
            "content": exec_summary
        })
        
        # 2. Team Analysis
        team_section = preliminary_im.team_section
        if team_section:
            team_strengths = chr(10).join(f'- {s}' for s in team_section.strengths) if team_section.strengths else '- 无'
            team_concerns = chr(10).join(f'- {c}' for c in team_section.concerns) if team_section.concerns else '- 无'
            team_content = f"""{team_section.summary}

**优势**:
{team_strengths}

**担忧**:
{team_concerns}

**经验匹配度**: {team_section.experience_match_score}/10
"""
            sections.append({
                "section_title": "团队分析",
                "content": team_content
            })
        
        # 3. Market Analysis
        market_section = preliminary_im.market_section
        if market_section:
            market_content = f"""{market_section.summary}

**市场规模验证**: {market_section.market_validation}

**增长潜力**: {market_section.growth_potential}

**竞争格局**: {market_section.competitive_landscape}

**市场风险**:
{chr(10).join(f'- {r}' for r in market_section.red_flags) if market_section.red_flags else '暂无'}

**市场机会**:
{chr(10).join(f'- {o}' for o in market_section.opportunities) if market_section.opportunities else '暂无'}
"""
            sections.append({
                "section_title": "市场分析",
                "content": market_content
            })
        
        # 4. Cross-check Results (if any)
        if preliminary_im.cross_check_results:
            cross_check_content = "以下是 BP 数据与外部数据源的交叉验证结果：\n\n"
            for result in preliminary_im.cross_check_results:
                cross_check_content += f"""**{result.category}**:
- BP 声明: {result.bp_claim}
- 外部数据: {result.external_data}
- 一致性: {'✓ 一致' if result.is_consistent else '✗ 不一致'}
- 差异程度: {result.discrepancy_level}
{f'- 备注: {result.notes}' if result.notes else ''}

"""
            sections.append({
                "section_title": "数据交叉验证",
                "content": cross_check_content
            })
        
        # Build frontend-compatible format
        return {
            "company_ticker": bp_data.company_name,
            "report_sections": sections,
            "session_id": preliminary_im.session_id,
            "dd_questions": [q.dict() for q in preliminary_im.dd_questions]
        }
    
    def get_current_context(self) -> DDSessionContext:
        """Get current session context"""
        return self.context
