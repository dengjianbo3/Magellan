"""
WorkflowEngine - Workflow执行引擎

职责:
1. 从AgentRegistry加载workflow配置
2. 按照workflow定义的步骤顺序执行agents
3. 管理agent之间的数据传递
4. 处理错误和重试
5. 通过WebSocket报告进度

设计原则:
- 配置驱动: 完全由workflows.yaml驱动
- 解耦合: 不依赖特定的Agent实现
- 可扩展: 支持添加新的执行策略
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import WebSocket

from app.core.agent_registry import registry

logger = logging.getLogger(__name__)


class WorkflowExecutionError(Exception):
    """Workflow执行错误"""
    pass


class WorkflowEngine:
    """
    Workflow执行引擎

    负责orchestrate整个投资分析流程
    """

    def __init__(
        self,
        scenario_id: str,
        mode: str = 'standard',
        websocket: Optional[WebSocket] = None
    ):
        """
        初始化WorkflowEngine

        Args:
            scenario_id: 场景ID (e.g., 'early-stage-investment')
            mode: 执行模式 ('quick' 或 'standard')
            websocket: WebSocket连接用于进度报告
        """
        self.scenario_id = scenario_id
        self.mode = mode
        self.websocket = websocket
        self.registry = registry

        # 执行上下文 - 存储所有agent的输出
        self.context: Dict[str, Any] = {
            'scenario_id': scenario_id,
            'mode': mode,
            'start_time': datetime.now().isoformat(),
        }

        # 执行状态
        self.current_step = 0
        self.total_steps = 0
        self.failed_steps = []

        logger.info(f"🚀 WorkflowEngine initialized: scenario={scenario_id}, mode={mode}")

    async def execute(self, initial_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行整个workflow（支持并行执行）

        Args:
            initial_context: 初始上下文，包含用户输入和目标信息
                {
                    'target': {...},  # 分析目标
                    'user_id': '...',  # 用户ID
                    'bp_file_id': '...',  # BP文件ID (可选)
                }

        Returns:
            执行结果上下文，包含所有agent的输出
            {
                'scenario_id': '...',
                'mode': '...',
                'start_time': '...',
                'end_time': '...',
                'status': 'success'|'failed',
                'team_evaluator_result': {...},
                'market_analyst_result': {...},
                ...
                'final_report': {...}  # 来自report_synthesizer
            }

        Raises:
            WorkflowExecutionError: Workflow执行失败
        """
        import asyncio

        try:
            # 0. 检查缓存 (如果启用)
            target = initial_context.get('target', {})
            if target:
                try:
                    from .session_store import SessionStore
                    session_store = SessionStore()
                    cached_result = session_store.get_cached_analysis(target, self.scenario_id)
                    if cached_result:
                        logger.info(f"💾 Cache hit! Using cached analysis for {self.scenario_id}")
                        cached_result['from_cache'] = True
                        return cached_result
                except Exception as e:
                    logger.warning(f"Cache check failed (continuing without cache): {e}")

            # 1. 验证workflow配置
            if not self.registry.validate_workflow(self.scenario_id, self.mode):
                raise WorkflowExecutionError(
                    f"Invalid workflow: {self.scenario_id} mode={self.mode}"
                )

            # 2. 获取workflow步骤
            steps = self.registry.get_workflow_steps(self.scenario_id, self.mode)
            if not steps:
                raise WorkflowExecutionError(
                    f"No steps found for workflow: {self.scenario_id} mode={self.mode}"
                )

            self.total_steps = len(steps)
            logger.info(f"📋 Workflow has {self.total_steps} steps")

            # 3. 合并初始上下文
            self.context.update(initial_context)

            # 4. 报告开始
            await self._report_workflow_start()

            # 5. 按依赖关系分组执行（并行优化）
            executed_step_ids = set()
            step_map = {step['step_id']: step for step in steps}

            while len(executed_step_ids) < len(steps):
                # 找出可以并行执行的步骤（依赖已满足）
                ready_steps = []
                for step in steps:
                    step_id = step['step_id']
                    if step_id in executed_step_ids:
                        continue
                    
                    depends_on = step.get('depends_on', [])
                    if all(dep_id in executed_step_ids for dep_id in depends_on):
                        ready_steps.append(step)

                if not ready_steps:
                    # 防止死循环
                    remaining = [s['step_id'] for s in steps if s['step_id'] not in executed_step_ids]
                    raise WorkflowExecutionError(f"Deadlock detected! Remaining steps: {remaining}")

                # 并行执行所有就绪的步骤
                if len(ready_steps) > 1:
                    logger.info(f"🚀 Parallel execution: {[s['agent_id'] for s in ready_steps]}")
                
                async def execute_with_tracking(step):
                    """执行单个步骤并跟踪结果"""
                    step_index = steps.index(step) + 1
                    self.current_step = step_index
                    logger.info(f"⚡ Executing step {step_index}/{self.total_steps}: {step['agent_id']}")
                    
                    try:
                        result = await self._execute_step(step)
                        result_key = f"{step['agent_id']}_result"
                        self.context[result_key] = result
                        logger.info(f"✅ Step {step_index} completed: {step['agent_id']}")
                        return (step['step_id'], 'success', result)
                    except Exception as e:
                        self.failed_steps.append({
                            'step_id': step.get('step_id'),
                            'agent_id': step['agent_id'],
                            'error': str(e)
                        })
                        logger.error(f"❌ Step {step_index} failed: {step['agent_id']} - {e}")
                        
                        if step.get('required', True):
                            raise
                        else:
                            logger.warning(f"⚠️  Non-required step failed, continuing...")
                            return (step['step_id'], 'failed', None)

                # 并行执行
                tasks = [execute_with_tracking(step) for step in ready_steps]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # 处理结果
                for result in results:
                    if isinstance(result, Exception):
                        raise WorkflowExecutionError(f"Step execution failed: {result}")
                    step_id, status, _ = result
                    executed_step_ids.add(step_id)

            # 6. 标记完成
            self.context['end_time'] = datetime.now().isoformat()
            self.context['status'] = 'success' if not self.failed_steps else 'partial_success'
            self.context['failed_steps'] = self.failed_steps

            # 7. 报告完成
            await self._report_workflow_complete()

            # 8. 缓存结果 (成功时)
            if self.context['status'] == 'success' and target:
                try:
                    from .session_store import SessionStore
                    session_store = SessionStore()
                    session_store.cache_analysis_result(target, self.scenario_id, self.context)
                    logger.info(f"💾 Cached analysis result for {self.scenario_id}")
                except Exception as e:
                    logger.warning(f"Failed to cache result: {e}")

            logger.info(f"🎉 Workflow execution completed: status={self.context['status']}")

            return self.context

        except Exception as e:
            # 标记失败
            self.context['end_time'] = datetime.now().isoformat()
            self.context['status'] = 'failed'
            self.context['error'] = str(e)

            # 报告失败
            await self._report_workflow_error(str(e))

            logger.error(f"💥 Workflow execution failed: {e}")
            raise WorkflowExecutionError(f"Workflow execution failed: {e}") from e

    async def _execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行单个workflow步骤

        Args:
            step: 步骤配置
                {
                    'step_id': 1,
                    'agent_id': 'team_evaluator',
                    'agent_params': {'quick_mode': True, 'language': 'zh'},
                    'description': '团队评估',
                    'required': True,
                    'depends_on': [...]  # 依赖的步骤ID
                }

        Returns:
            Agent执行结果
        """
        agent_id = step['agent_id']
        agent_params = step.get('agent_params', {})

        # 报告步骤开始
        await self._report_step_start(step)

        try:
            # 1. 创建agent实例
            logger.debug(f"Creating agent: {agent_id} with params {agent_params}")
            agent = self.registry.create_agent(agent_id, **agent_params)

            # 2. 准备agent输入
            agent_input = self._prepare_agent_input(step)

            # 3. 执行agent
            # 注意: 这里假设agent有一个统一的接口方法
            # 实际实现中可能需要根据agent类型调用不同的方法
            if hasattr(agent, 'run'):
                result = await agent.run(agent_input)
            elif hasattr(agent, 'execute'):
                result = await agent.execute(agent_input)
            elif hasattr(agent, 'analyze'):
                result = await agent.analyze(agent_input)
            else:
                # Fallback: 如果是旧的Agent类（同步方法）
                if hasattr(agent, 'process'):
                    result = agent.process(agent_input)
                else:
                    raise ValueError(f"Agent {agent_id} has no recognized execution method")

            # 4. 报告步骤完成
            await self._report_step_complete(step, result)

            return result

        except Exception as e:
            # 报告步骤失败
            await self._report_step_error(step, str(e))
            raise

    def _prepare_agent_input(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """
        准备agent的输入数据

        根据step的depends_on配置，收集依赖步骤的输出

        Args:
            step: 步骤配置

        Returns:
            Agent输入数据
        """
        agent_input = {
            # 基础上下文
            'scenario_id': self.scenario_id,
            'mode': self.mode,
            'target': self.context.get('target', {}),
        }

        # 添加依赖步骤的输出
        depends_on = step.get('depends_on', [])
        if depends_on:
            # depends_on 是步骤ID列表，需要找到对应的agent_id
            workflow_steps = self.registry.get_workflow_steps(self.scenario_id, self.mode)
            for dep_step_id in depends_on:
                # 找到依赖步骤
                dep_step = next(
                    (s for s in workflow_steps if s['step_id'] == dep_step_id),
                    None
                )
                if dep_step:
                    dep_agent_id = dep_step['agent_id']
                    result_key = f"{dep_agent_id}_result"
                    if result_key in self.context:
                        agent_input[result_key] = self.context[result_key]

        # 添加其他上下文数据（如BP文件、用户偏好等）
        for key in ['bp_file_id', 'user_id', 'user_preferences']:
            if key in self.context:
                agent_input[key] = self.context[key]

        return agent_input

    # ============================================
    # WebSocket进度报告
    # ============================================

    async def _report_workflow_start(self):
        """报告workflow开始"""
        if self.websocket:
            await self.websocket.send_json({
                'type': 'workflow_start',
                'scenario_id': self.scenario_id,
                'mode': self.mode,
                'total_steps': self.total_steps,
                'timestamp': datetime.now().isoformat()
            })

    async def _report_step_start(self, step: Dict[str, Any]):
        """报告步骤开始"""
        if self.websocket:
            await self.websocket.send_json({
                'type': 'step_start',
                'step_id': step.get('step_id'),
                'agent_id': step['agent_id'],
                'description': step.get('description', ''),
                'progress': f"{self.current_step}/{self.total_steps}",
                'timestamp': datetime.now().isoformat()
            })

    async def _report_step_complete(self, step: Dict[str, Any], result: Any):
        """报告步骤完成"""
        if self.websocket:
            await self.websocket.send_json({
                'type': 'step_complete',
                'step_id': step.get('step_id'),
                'agent_id': step['agent_id'],
                'progress': f"{self.current_step}/{self.total_steps}",
                'timestamp': datetime.now().isoformat()
                # 注意: 不发送完整result，避免数据过大
            })

    async def _report_step_error(self, step: Dict[str, Any], error: str):
        """报告步骤错误"""
        if self.websocket:
            await self.websocket.send_json({
                'type': 'step_error',
                'step_id': step.get('step_id'),
                'agent_id': step['agent_id'],
                'error': error,
                'timestamp': datetime.now().isoformat()
            })

    async def _report_workflow_complete(self):
        """报告workflow完成"""
        if self.websocket:
            await self.websocket.send_json({
                'type': 'workflow_complete',
                'status': self.context['status'],
                'failed_steps': self.failed_steps,
                'timestamp': datetime.now().isoformat()
            })

    async def _report_workflow_error(self, error: str):
        """报告workflow错误"""
        if self.websocket:
            await self.websocket.send_json({
                'type': 'workflow_error',
                'error': error,
                'timestamp': datetime.now().isoformat()
            })

    # ============================================
    # 便捷方法
    # ============================================

    def get_agent_result(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """获取指定agent的执行结果"""
        return self.context.get(f"{agent_id}_result")

    def get_final_report(self) -> Optional[Dict[str, Any]]:
        """获取最终报告（来自report_synthesizer）"""
        return self.get_agent_result('report_synthesizer')


# ============================================
# 便捷函数
# ============================================

async def execute_workflow(
    scenario_id: str,
    mode: str,
    initial_context: Dict[str, Any],
    websocket: Optional[WebSocket] = None
) -> Dict[str, Any]:
    """
    便捷函数: 执行workflow

    Args:
        scenario_id: 场景ID
        mode: 执行模式
        initial_context: 初始上下文
        websocket: WebSocket连接

    Returns:
        执行结果
    """
    engine = WorkflowEngine(scenario_id, mode, websocket)
    return await engine.execute(initial_context)
