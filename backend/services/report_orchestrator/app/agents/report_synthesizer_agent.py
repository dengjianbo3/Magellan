"""
Report Synthesizer Agent
报告综合Agent - 分析模块专用

职责:
- 综合所有原子Agent的分析结果
- 生成结构化的投资分析报告
- 形成明确的投资建议和决策依据
- 识别关键风险和机会

注: 这个Agent只用于分析模块workflow的最后一步
     圆桌会议使用leader agent
"""

from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class ReportSynthesizerAgent:
    """
    报告综合Agent - 分析模块的总结者

    作用: 将所有原子Agent的输出整合为最终投资报告
    使用场景: 分析模块workflow的最后一步
    """

    def __init__(self, quick_mode: bool = False):
        """
        初始化报告综合Agent

        Args:
            quick_mode: 是否为快速模式
                       - True: 简化报告, 只包含核心结论
                       - False: 完整报告, 包含详细分析
        """
        self.quick_mode = quick_mode
        self.agent_id = "report_synthesizer"
        self.agent_name = "报告综合Agent"

    async def analyze(self, target: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        兼容BaseOrchestrator的analyze()接口

        Args:
            target: 分析目标
            context: 完整上下文，包含所有Agent的结果

        Returns:
            综合分析报告
        """
        # 如果context没有提供，使用target作为context
        if context is None:
            context = {'target': target}

        # 调用synthesize方法
        return await self.synthesize(context)

    async def synthesize(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        综合分析报告

        Args:
            context: 包含所有之前Agent的输出
                {
                    'scenario': 'early-stage-investment',
                    'target': {...},
                    'config': {...},
                    'team_analysis': {...},  # from team_evaluator
                    'market_analysis': {...},  # from market_analyst
                    'financial_analysis': {...},  # from financial_expert
                    'risk_assessment': {...},  # from risk_assessor
                    'tech_assessment': {...},  # from tech_specialist (optional)
                    'legal_assessment': {...}  # from legal_advisor (optional)
                }

        Returns:
            {
                'report_id': 'uuid',
                'scenario': 'early-stage-investment',
                'overall_recommendation': 'invest|observe|reject',
                'investment_score': 0-100,
                'confidence_level': 'high|medium|low',
                'key_findings': [...],
                'strengths': [...],
                'weaknesses': [...],
                'opportunities': [...],
                'threats': [...],
                'detailed_sections': {...},
                'next_steps': [...]
            }
        """
        logger.info(f"[ReportSynthesizer] 开始综合报告 (quick_mode={self.quick_mode})")

        try:
            if self.quick_mode:
                return await self._quick_synthesis(context)
            else:
                return await self._full_synthesis(context)

        except Exception as e:
            logger.error(f"[ReportSynthesizer] 报告综合失败: {e}")
            raise

    async def _quick_synthesis(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        快速综合 - 30秒内输出核心结论
        """
        logger.info("[ReportSynthesizer] 快速模式综合")

        # 提取关键分数
        scores = self._extract_scores(context)

        # 计算综合评分
        overall_score = self._calculate_overall_score(scores)

        # 生成建议
        recommendation = self._generate_recommendation(overall_score, context)

        # 识别关键发现
        key_findings = self._extract_key_findings_quick(context)

        return {
            'report_id': self._generate_report_id(),
            'scenario': context.get('scenario', 'unknown'),
            'mode': 'quick',
            'overall_recommendation': recommendation['action'],
            'investment_score': overall_score,
            'confidence_level': recommendation['confidence'],
            'key_findings': key_findings,
            'scores_breakdown': scores,
            'summary': self._generate_quick_summary(context, overall_score),
            'next_steps': recommendation['next_steps']
        }

    async def _full_synthesis(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        完整综合 - 生成详细分析报告
        """
        logger.info("[ReportSynthesizer] 完整模式综合")

        # 提取关键分数
        scores = self._extract_scores(context)

        # 计算综合评分
        overall_score = self._calculate_overall_score(scores)

        # 生成建议
        recommendation = self._generate_recommendation(overall_score, context)

        # SWOT分析
        swot = self._generate_swot(context)

        # 详细发现
        detailed_findings = self._extract_detailed_findings(context)

        # 风险与机会
        risks_opportunities = self._extract_risks_and_opportunities(context)

        # 生成详细章节
        detailed_sections = self._generate_detailed_sections(context)

        return {
            'report_id': self._generate_report_id(),
            'scenario': context.get('scenario', 'unknown'),
            'mode': 'full',
            'overall_recommendation': recommendation['action'],
            'investment_score': overall_score,
            'confidence_level': recommendation['confidence'],

            # 核心发现
            'executive_summary': self._generate_executive_summary(context, overall_score, swot),
            'key_findings': detailed_findings,

            # SWOT分析
            'strengths': swot['strengths'],
            'weaknesses': swot['weaknesses'],
            'opportunities': swot['opportunities'],
            'threats': swot['threats'],

            # 分数详情
            'scores_breakdown': scores,

            # 风险与机会
            'critical_risks': risks_opportunities['critical_risks'],
            'key_opportunities': risks_opportunities['key_opportunities'],

            # 详细章节
            'detailed_sections': detailed_sections,

            # 行动建议
            'next_steps': recommendation['next_steps'],
            'investment_thesis': recommendation['thesis']
        }

    def _extract_scores(self, context: Dict[str, Any]) -> Dict[str, float]:
        """从各Agent输出中提取评分"""
        scores = {}

        # 团队评分
        if 'team_analysis' in context:
            scores['team'] = context['team_analysis'].get('team_score', 0)

        # 市场评分
        if 'market_analysis' in context:
            market_data = context['market_analysis']
            # 根据市场规模和增长率计算分数
            scores['market'] = self._calculate_market_score(market_data)

        # 财务评分
        if 'financial_analysis' in context:
            scores['financial'] = context['financial_analysis'].get('financial_health_score', 0)

        # 技术评分
        if 'tech_assessment' in context:
            scores['tech'] = context['tech_assessment'].get('tech_score', 0)

        # 风险评分 (反向: 风险越高分数越低)
        if 'risk_assessment' in context:
            risk_score = context['risk_assessment'].get('risk_score', 50)
            scores['risk'] = 100 - risk_score  # 反转分数

        # 法律评分
        if 'legal_assessment' in context:
            legal_risk = context['legal_assessment'].get('legal_risk_score', 50)
            scores['legal'] = 100 - legal_risk  # 反转分数

        return scores

    def _calculate_market_score(self, market_data: Dict[str, Any]) -> float:
        """根据市场数据计算市场评分"""
        # 简化版: 基于增长率
        growth_rate = market_data.get('growth_rate', 0)

        if growth_rate > 50:
            return 90
        elif growth_rate > 30:
            return 80
        elif growth_rate > 20:
            return 70
        elif growth_rate > 10:
            return 60
        else:
            return 50

    def _calculate_overall_score(self, scores: Dict[str, float]) -> float:
        """
        计算综合评分

        根据场景不同,权重也不同:
        - 早期投资: 团队60%, 市场30%, 其他10%
        - 成长期: 财务40%, 市场30%, 团队20%, 其他10%
        - 公开市场: 财务60%, 市场30%, 其他10%
        """
        if not scores:
            return 50.0

        # 简化版: 平均分
        total = sum(scores.values())
        count = len(scores)

        return round(total / count, 1) if count > 0 else 50.0

    def _generate_recommendation(
        self,
        overall_score: float,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成投资建议"""

        # 提取关键风险
        critical_risks = []
        if 'risk_assessment' in context:
            risk_data = context['risk_assessment']
            red_flags = risk_data.get('red_flags', [])
            critical_risks = [flag for flag in red_flags if flag.get('severity') == '高']

        # 决策逻辑
        if len(critical_risks) > 0:
            # 有严重红旗 → 不推荐
            return {
                'action': 'reject',
                'confidence': 'high',
                'reason': f"发现{len(critical_risks)}个高严重性风险",
                'next_steps': [
                    '详细调查红旗问题',
                    '与创始人沟通核实',
                    '等待问题解决后重新评估'
                ],
                'thesis': None
            }

        elif overall_score >= 75:
            # 高分 → 推荐投资
            return {
                'action': 'invest',
                'confidence': 'high',
                'reason': f"综合评分{overall_score}分,各维度表现优秀",
                'next_steps': [
                    '进入投资委员会审议',
                    '准备Term Sheet',
                    '开展法律和财务尽调',
                    '协商投资条款'
                ],
                'thesis': self._generate_investment_thesis(context, overall_score)
            }

        elif overall_score >= 60:
            # 中等分数 → 持续观察
            return {
                'action': 'observe',
                'confidence': 'medium',
                'reason': f"综合评分{overall_score}分,部分维度需改进",
                'next_steps': [
                    '识别需要改进的关键领域',
                    '与团队沟通改进计划',
                    '设定里程碑跟踪进展',
                    '3-6个月后重新评估'
                ],
                'thesis': None
            }

        else:
            # 低分 → 不推荐
            return {
                'action': 'reject',
                'confidence': 'high',
                'reason': f"综合评分{overall_score}分,不符合投资标准",
                'next_steps': [
                    '与创始人反馈评估结果',
                    '说明不投资的核心原因',
                    '建议团队改进方向'
                ],
                'thesis': None
            }

    def _generate_investment_thesis(
        self,
        context: Dict[str, Any],
        score: float
    ) -> str:
        """生成投资逻辑"""

        # 提取关键优势
        strengths = []

        if 'team_analysis' in context:
            team = context['team_analysis']
            if team.get('team_score', 0) >= 80:
                strengths.append("团队经验丰富且互补性强")

        if 'market_analysis' in context:
            market = context['market_analysis']
            if market.get('growth_rate', 0) >= 20:
                strengths.append(f"市场高速增长({market.get('growth_rate')}% CAGR)")

        if 'financial_analysis' in context:
            financial = context['financial_analysis']
            unit_econ = financial.get('unit_economics', {})
            if unit_econ.get('ltv_cac_ratio', 0) >= 3:
                strengths.append("单位经济模型健康")

        thesis = "我们看好这个项目因为:\n"
        for i, strength in enumerate(strengths, 1):
            thesis += f"{i}. {strength}\n"

        return thesis

    def _generate_swot(self, context: Dict[str, Any]) -> Dict[str, List[str]]:
        """生成SWOT分析"""

        swot = {
            'strengths': [],
            'weaknesses': [],
            'opportunities': [],
            'threats': []
        }

        # Strengths (从各Agent提取)
        if 'team_analysis' in context:
            team_strengths = context['team_analysis'].get('key_strengths', [])
            swot['strengths'].extend(team_strengths)

        if 'financial_analysis' in context:
            financial = context['financial_analysis']
            if financial.get('financial_health_score', 0) >= 70:
                swot['strengths'].append("财务健康度良好")

        # Weaknesses
        if 'team_analysis' in context:
            team_risks = context['team_analysis'].get('key_risks', [])
            swot['weaknesses'].extend(team_risks)

        if 'financial_analysis' in context:
            financial = context['financial_analysis']
            metrics = financial.get('key_metrics', {})
            if metrics.get('cash_runway_months', 0) < 12:
                swot['weaknesses'].append("现金流较紧张,跑道不足12个月")

        # Opportunities
        if 'market_analysis' in context:
            market_opps = context['market_analysis'].get('opportunities', [])
            swot['opportunities'].extend(market_opps)

        # Threats
        if 'risk_assessment' in context:
            risks = context['risk_assessment'].get('red_flags', [])
            swot['threats'].extend([r.get('description', '') for r in risks])

        return swot

    def _extract_key_findings_quick(self, context: Dict[str, Any]) -> List[str]:
        """快速模式: 提取5个最关键发现"""
        findings = []

        # 1. 团队发现
        if 'team_analysis' in context:
            team = context['team_analysis']
            findings.append(f"团队评分: {team.get('team_score', 'N/A')}/100")

        # 2. 市场发现
        if 'market_analysis' in context:
            market = context['market_analysis']
            growth = market.get('growth_rate', 0)
            findings.append(f"市场增速: {growth}% CAGR")

        # 3. 财务发现
        if 'financial_analysis' in context:
            financial = context['financial_analysis']
            findings.append(f"财务健康度: {financial.get('financial_health_score', 'N/A')}/100")

        # 4. 风险发现
        if 'risk_assessment' in context:
            risk = context['risk_assessment']
            red_flags_count = len(risk.get('red_flags', []))
            findings.append(f"识别到{red_flags_count}个红旗风险")

        # 5. 技术发现 (如果有)
        if 'tech_assessment' in context:
            tech = context['tech_assessment']
            findings.append(f"技术评分: {tech.get('tech_score', 'N/A')}/100")

        return findings[:5]  # 最多5个

    def _extract_detailed_findings(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """完整模式: 提取详细发现"""
        findings = []

        # 从每个Agent提取关键发现
        agent_outputs = [
            ('team_analysis', '团队分析'),
            ('market_analysis', '市场分析'),
            ('financial_analysis', '财务分析'),
            ('tech_assessment', '技术评估'),
            ('risk_assessment', '风险评估'),
            ('legal_assessment', '法律评估')
        ]

        for agent_key, agent_name in agent_outputs:
            if agent_key in context:
                agent_data = context[agent_key]

                # 提取该Agent的关键发现
                finding = {
                    'category': agent_name,
                    'score': agent_data.get(f"{agent_key.split('_')[0]}_score", 'N/A'),
                    'key_points': self._extract_key_points_from_agent(agent_data),
                    'concerns': self._extract_concerns_from_agent(agent_data)
                }

                findings.append(finding)

        return findings

    def _extract_key_points_from_agent(self, agent_data: Dict[str, Any]) -> List[str]:
        """从Agent输出中提取关键点"""
        key_points = []

        # 通用字段
        if 'key_strengths' in agent_data:
            key_points.extend(agent_data['key_strengths'])

        if 'highlights' in agent_data:
            key_points.extend(agent_data['highlights'])

        return key_points[:3]  # 最多3个关键点

    def _extract_concerns_from_agent(self, agent_data: Dict[str, Any]) -> List[str]:
        """从Agent输出中提取关注点"""
        concerns = []

        # 通用字段
        if 'key_risks' in agent_data:
            concerns.extend(agent_data['key_risks'])

        if 'concerns' in agent_data:
            concerns.extend(agent_data['concerns'])

        if 'red_flags' in agent_data:
            concerns.extend([flag.get('description', '') for flag in agent_data['red_flags']])

        return concerns[:3]  # 最多3个关注点

    def _extract_risks_and_opportunities(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """提取关键风险和机会"""

        risks = []
        opportunities = []

        # 从风险评估中提取
        if 'risk_assessment' in context:
            risk_data = context['risk_assessment']
            risks.extend(risk_data.get('red_flags', []))

        # 从市场分析中提取机会
        if 'market_analysis' in context:
            market_data = context['market_analysis']
            opportunities.extend(market_data.get('opportunities', []))

        # 从财务分析中提取机会
        if 'financial_analysis' in context:
            financial_data = context['financial_analysis']
            if 'opportunities' in financial_data:
                opportunities.extend(financial_data['opportunities'])

        return {
            'critical_risks': risks[:5],  # 前5个风险
            'key_opportunities': opportunities[:5]  # 前5个机会
        }

    def _generate_detailed_sections(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """生成报告的详细章节"""

        sections = {}

        # 1. 项目概览
        sections['overview'] = self._generate_overview_section(context)

        # 2. 团队分析
        if 'team_analysis' in context:
            sections['team'] = context['team_analysis']

        # 3. 市场分析
        if 'market_analysis' in context:
            sections['market'] = context['market_analysis']

        # 4. 财务分析
        if 'financial_analysis' in context:
            sections['financial'] = context['financial_analysis']

        # 5. 技术评估
        if 'tech_assessment' in context:
            sections['technology'] = context['tech_assessment']

        # 6. 风险评估
        if 'risk_assessment' in context:
            sections['risk'] = context['risk_assessment']

        # 7. 法律评估
        if 'legal_assessment' in context:
            sections['legal'] = context['legal_assessment']

        return sections

    def _generate_overview_section(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """生成项目概览章节"""

        target = context.get('target', {})

        return {
            'scenario': context.get('scenario', 'unknown'),
            'target_name': target.get('company_name', 'N/A'),
            'industry': target.get('industry', 'N/A'),
            'stage': target.get('stage', 'N/A'),
            'analysis_date': self._get_current_date(),
            'analysis_mode': 'quick' if self.quick_mode else 'full'
        }

    def _generate_quick_summary(
        self,
        context: Dict[str, Any],
        overall_score: float
    ) -> str:
        """生成快速摘要"""

        target_name = context.get('target', {}).get('company_name', '该项目')

        summary = f"{target_name}综合评分{overall_score}分。"

        # 添加关键优势
        if overall_score >= 75:
            summary += "整体表现优秀,建议深入尽调。"
        elif overall_score >= 60:
            summary += "整体表现中等,建议持续观察。"
        else:
            summary += "整体表现较弱,不建议投资。"

        return summary

    def _generate_executive_summary(
        self,
        context: Dict[str, Any],
        overall_score: float,
        swot: Dict[str, List[str]]
    ) -> str:
        """生成执行摘要"""

        target_name = context.get('target', {}).get('company_name', '该项目')

        summary = f"""
# 执行摘要

{target_name}综合评分{overall_score}分。

## 核心优势
{self._format_list(swot['strengths'][:3])}

## 关键风险
{self._format_list(swot['threats'][:3])}

## 投资建议
"""

        if overall_score >= 75:
            summary += "**推荐投资**: 项目各维度表现优秀,符合投资标准。"
        elif overall_score >= 60:
            summary += "**持续观察**: 项目有潜力但需改进,建议跟踪进展。"
        else:
            summary += "**不推荐**: 项目不符合当前投资标准。"

        return summary

    def _format_list(self, items: List[str]) -> str:
        """格式化列表"""
        if not items:
            return "- (无)"

        return "\n".join([f"- {item}" for item in items])

    def _generate_report_id(self) -> str:
        """生成报告ID"""
        import uuid
        return str(uuid.uuid4())

    def _get_current_date(self) -> str:
        """获取当前日期"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d")


# 便捷函数
async def synthesize_report(
    context: Dict[str, Any],
    quick_mode: bool = False
) -> Dict[str, Any]:
    """
    快速调用报告综合功能

    Args:
        context: 包含所有Agent输出的上下文
        quick_mode: 是否快速模式

    Returns:
        综合报告
    """
    synthesizer = ReportSynthesizerAgent(quick_mode=quick_mode)
    return await synthesizer.synthesize(context)
