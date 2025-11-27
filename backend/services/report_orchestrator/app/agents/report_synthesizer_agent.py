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
import httpx
import json
import re

logger = logging.getLogger(__name__)


class ReportSynthesizerAgent:
    """
    报告综合Agent - 分析模块的总结者

    作用: 将所有原子Agent的输出整合为最终投资报告
    使用场景: 分析模块workflow的最后一步
    """

    def __init__(self, quick_mode: bool = False, llm_gateway_url: str = "http://llm_gateway:8003"):
        """
        初始化报告综合Agent

        Args:
            quick_mode: 是否为快速模式
                       - True: 简化报告, 只包含核心结论
                       - False: 完整报告, 包含详细分析
            llm_gateway_url: LLM Gateway服务地址
        """
        self.quick_mode = quick_mode
        self.agent_id = "report_synthesizer"
        self.agent_name = "报告综合Agent"
        self.llm_gateway_url = llm_gateway_url

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
        
        # 生成基础结构
        company_info = self._generate_company_info(context)
        sections = self._generate_detailed_sections(context)

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
            'next_steps': recommendation['next_steps'],
            
            # Frontend Compatibility Fields
            'sections': sections,
            'company_info': company_info,
            'team_section': {'summary': sections.get('team', {}).get('summary', '快速评估完成')},
            'market_section': {'summary': sections.get('market', {}).get('summary', '快速评估完成')}
        }

    async def _full_synthesis(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        完整综合 - 生成详细分析报告
        """
        logger.info("[ReportSynthesizer] 完整模式综合")

        # 🚀 核心改进：调用LLM生成真实的分析报告
        llm_report = await self._call_llm_for_synthesis(context)

        # 如果LLM成功生成报告，使用LLM的结果
        if llm_report:
            logger.info("[ReportSynthesizer] ✅ 使用LLM生成的报告")

            # 生成公司信息和ID
            company_info = self._generate_company_info(context)
            report_id = self._generate_report_id()

            # 从LLM报告中提取数据，并补充必要的字段
            detailed_analysis = llm_report.get('detailed_analysis', {})

            # 将detailed_analysis转换为sections格式
            sections = {}
            if 'market' in detailed_analysis:
                sections['market'] = {'summary': detailed_analysis['market']}
            if 'technology' in detailed_analysis:
                sections['technology'] = {'summary': detailed_analysis['technology']}
            if 'financial' in detailed_analysis:
                sections['financial'] = {'summary': detailed_analysis['financial']}
            if 'team' in detailed_analysis:
                sections['team'] = {'summary': detailed_analysis['team']}
            if 'risk' in detailed_analysis:
                sections['risk'] = {'summary': detailed_analysis['risk']}

            # 构建完整报告
            return {
                'report_id': report_id,
                'scenario': context.get('scenario', 'unknown'),
                'mode': 'full',
                'company_name': company_info['name'],

                # LLM生成的核心内容
                'overall_recommendation': llm_report.get('overall_recommendation', 'observe'),
                'investment_score': llm_report.get('investment_score', 50),
                'confidence_level': llm_report.get('confidence_level', 'medium'),
                'executive_summary': llm_report.get('executive_summary', ''),
                'key_findings': llm_report.get('key_findings', []),
                'strengths': llm_report.get('strengths', []),
                'weaknesses': llm_report.get('weaknesses', []),
                'opportunities': llm_report.get('opportunities', []),
                'threats': llm_report.get('threats', []),
                'critical_risks': llm_report.get('critical_risks', []),
                'key_opportunities': llm_report.get('key_opportunities', []),
                'investment_thesis': llm_report.get('investment_thesis', ''),
                'next_steps': llm_report.get('next_steps', []),

                # 详细章节
                'sections': sections,
                'detailed_sections': sections,

                # Frontend兼容性字段
                'company_info': company_info,
                'team_section': sections.get('team', {'summary': '团队分析'}),
                'market_section': sections.get('market', {'summary': '市场分析'}),
                'market_analysis': sections.get('market', {}),
                'team_analysis': sections.get('team', {}),

                # 评分细分（从LLM的key_findings中提取）
                'scores_breakdown': self._extract_scores_from_llm_report(llm_report),

                # PDF/Word导出数据
                'preliminary_im': {
                    "investment_recommendation": llm_report.get('investment_thesis', 'N/A'),
                    "key_findings": [f.get('category', '') + ": " + "; ".join(f.get('key_points', [])) for f in llm_report.get('key_findings', [])],
                    "investment_highlights": llm_report.get('strengths', []),
                    "financial_highlights": {
                        "Overall Score": f"{llm_report.get('investment_score', 0)}/100"
                    },
                    "financial_analysis": detailed_analysis.get('financial', '财务分析'),
                    "risks": llm_report.get('critical_risks', []),
                    "final_recommendation": llm_report.get('overall_recommendation', 'observe'),
                    "next_steps": llm_report.get('next_steps', [])
                },

                'dd_questions': []
            }

        # Fallback: 如果LLM失败，使用原来的逻辑
        logger.warning("[ReportSynthesizer] ⚠️ LLM生成失败，使用Fallback逻辑")

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
        sections = self._generate_detailed_sections(context)
        
        # 生成公司信息 (Frontend compat)
        company_info = self._generate_company_info(context)

        # Construct Preliminary IM for Exporters (PDF/Word)
        preliminary_im = {
            "investment_recommendation": recommendation.get('reason', 'N/A'),
            "key_findings": [f['category'] + ": " + "; ".join(f['key_points']) for f in detailed_findings],
            "investment_highlights": swot['strengths'],
            "financial_highlights": {
                "Financial Score": f"{scores.get('financial', 0)}/100",
                "Market Score": f"{scores.get('market', 0)}/100", 
                "Overall Score": f"{overall_score}/100"
            },
            "financial_analysis": sections.get('financial', {}).get('summary', '详见财务分析章节'),
            "risks": risks_opportunities['critical_risks'],
            "final_recommendation": recommendation.get('action', 'N/A'),
            "next_steps": recommendation.get('next_steps', [])
        }

        return {
            'report_id': self._generate_report_id(),
            'scenario': context.get('scenario', 'unknown'),
            'mode': 'full',
            'overall_recommendation': recommendation['action'],
            'investment_score': overall_score,
            'confidence_level': recommendation['confidence'],
            'company_name': company_info['name'], # Required for cover page

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

            # 详细章节 (Renamed to sections for generic view)
            'sections': sections,
            'detailed_sections': sections, # Keep legacy key just in case

            # Data for Exporters (PDF/Word)
            'preliminary_im': preliminary_im,
            'market_analysis': sections.get('market', {}),
            'team_analysis': sections.get('team', {}),

            # Frontend Specific Mapping (For DD View)
            'company_info': company_info,
            'team_section': self._extract_section_summary(sections, 'team'),
            'market_section': self._extract_section_summary(sections, 'market'),
            'dd_questions': [], # Placeholder

            # 行动建议
            'next_steps': recommendation['next_steps'],
            'investment_thesis': recommendation['thesis']
        }

    # ================= Smart Data Extraction Helper Methods =================

    def _find_data_in_context(self, context: Dict[str, Any], keys: List[str]) -> Optional[Dict[str, Any]]:
        """
        Helper to find a dictionary in context that contains specific keys.
        This handles the mismatch between step IDs and expected data types.
        """
        # Iterate through all values in context
        for value in context.values():
            if isinstance(value, dict):
                # 1. Check top-level keys
                if any(k in value for k in keys):
                    return value
                
                # 2. Check inside 'analysis' wrapper if present
                if "analysis" in value and isinstance(value["analysis"], dict):
                    inner = value["analysis"]
                    if any(k in inner for k in keys):
                        return inner
        return None

    def _find_team_analysis(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self._find_data_in_context(context, ['team_score', 'founder_assessment', 'team_structure', 'key_members_background'])

    def _find_market_analysis(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self._find_data_in_context(context, ['market_size', 'market_size_estimate', 'growth_rate', 'market_validation', 'competitive_landscape', 'market_attractiveness'])

    def _find_financial_analysis(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self._find_data_in_context(context, ['financial_score', 'financial_health_score', 'revenue_model', 'unit_economics', 'valuation', 'detailed_financials', 'fundamentals_score'])

    def _find_risk_assessment(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self._find_data_in_context(context, ['risk_score', 'red_flags', 'risk_matrix', 'critical_issues', 'risk_factors'])

    def _find_tech_assessment(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self._find_data_in_context(context, ['tech_score', 'architecture_assessment', 'tech_foundation_check'])

    def _find_legal_assessment(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self._find_data_in_context(context, ['legal_score', 'compliance_status', 'legal_risks'])

    # ================= Extraction Logic =================
    
    def _generate_company_info(self, context: Dict[str, Any]) -> Dict[str, str]:
        """Generate standardized company info for frontend"""
        target = context.get('target', {})
        if not target:
             target = context.get('inputs', {}).get('target', {})
             
        # Try various keys for name
        name = (target.get('company_name') or 
                target.get('target_name') or 
                target.get('industry_name') or 
                target.get('topic') or 
                'Unknown Target')
                
        industry = target.get('industry') or target.get('industry_name') or 'N/A'
        stage = target.get('stage', 'N/A')
        
        return {
            "name": name,
            "industry": industry,
            "stage": stage
        }

    def _extract_section_summary(self, sections: Dict[str, Any], section_key: str) -> Dict[str, str]:
        """Extract summary from a section for frontend display"""
        section = sections.get(section_key, {})
        summary = section.get('summary')
        if not summary:
             # Try to synthesize a summary from key points
             strengths = section.get('key_strengths', [])
             if strengths:
                 summary = "; ".join(strengths[:2])
             else:
                 summary = f"{section_key} analysis completed."
        return {"summary": summary}

    def _extract_scores_from_llm_report(self, llm_report: Dict[str, Any]) -> Dict[str, float]:
        """从LLM生成的报告中提取各维度评分"""
        scores = {}
        key_findings = llm_report.get('key_findings', [])

        for finding in key_findings:
            category = finding.get('category', '').lower()
            score = finding.get('score')

            if score is not None and isinstance(score, (int, float)):
                if '市场' in category or 'market' in category:
                    scores['market'] = float(score)
                elif '财务' in category or 'financial' in category:
                    scores['financial'] = float(score)
                elif '技术' in category or 'tech' in category:
                    scores['tech'] = float(score)
                elif '团队' in category or 'team' in category:
                    scores['team'] = float(score)
                elif '风险' in category or 'risk' in category:
                    scores['risk'] = float(score)

        return scores

    def _extract_scores(self, context: Dict[str, Any]) -> Dict[str, float]:
        """从各Agent输出中提取评分"""
        scores = {}

        team_data = self._find_team_analysis(context)
        if team_data:
            scores['team'] = team_data.get('team_score', 0)

        market_data = self._find_market_analysis(context)
        if market_data:
            # Use explicit score if available, else calc
            scores['market'] = market_data.get('market_score', self._calculate_market_score(market_data))

        fin_data = self._find_financial_analysis(context)
        if fin_data:
            scores['financial'] = fin_data.get('financial_score') or fin_data.get('financial_health_score') or fin_data.get('fundamentals_score', 0)

        tech_data = self._find_tech_assessment(context)
        if tech_data:
            scores['tech'] = tech_data.get('tech_score', 0)

        risk_data = self._find_risk_assessment(context)
        if risk_data:
            risk_score = risk_data.get('risk_score', 50)
            scores['risk'] = risk_score # risk_score is usually 0-100 where 100 is safe

        return scores

    def _calculate_market_score(self, market_data: Dict[str, Any]) -> float:
        """根据市场数据计算市场评分"""
        # 简化版: 基于增长率或吸引力
        if 'market_attractiveness' in market_data:
             return float(market_data['market_attractiveness']) * 100 if market_data['market_attractiveness'] <= 1 else market_data['market_attractiveness']
             
        growth_rate = market_data.get('growth_rate', 0)
        if isinstance(growth_rate, (int, float)):
            if growth_rate > 50: return 90
            elif growth_rate > 30: return 80
            elif growth_rate > 20: return 70
            elif growth_rate > 10: return 60
        return 50

    def _calculate_overall_score(self, scores: Dict[str, float]) -> float:
        """计算综合评分"""
        if not scores:
            return 50.0
        total = sum(scores.values())
        count = len(scores)
        return round(total / count, 1) if count > 0 else 50.0

    def _generate_recommendation(self, overall_score: float, context: Dict[str, Any]) -> Dict[str, Any]:
        """生成投资建议"""
        critical_risks = []
        risk_data = self._find_risk_assessment(context)
        if risk_data:
            red_flags = risk_data.get('red_flags', [])
            critical_risks = [flag for flag in red_flags if isinstance(flag, dict) and flag.get('severity') == '高']
            if not critical_risks and isinstance(red_flags, list) and len(red_flags) > 0 and isinstance(red_flags[0], str):
                 # Handle string red flags
                 pass 

        if len(critical_risks) > 0:
            return {
                'action': 'reject',
                'confidence': 'high',
                'reason': f"发现{len(critical_risks)}个高严重性风险",
                'next_steps': ['详细调查红旗问题', '与创始人沟通核实', '等待问题解决后重新评估'],
                'thesis': None
            }
        elif overall_score >= 75:
            return {
                'action': 'invest',
                'confidence': 'high',
                'reason': f"综合评分{overall_score}分,各维度表现优秀",
                'next_steps': ['进入投资委员会审议', '准备Term Sheet', '开展法律和财务尽调', '协商投资条款'],
                'thesis': self._generate_investment_thesis(context, overall_score)
            }
        elif overall_score >= 60:
            return {
                'action': 'observe',
                'confidence': 'medium',
                'reason': f"综合评分{overall_score}分,部分维度需改进",
                'next_steps': ['识别需要改进的关键领域', '与团队沟通改进计划', '设定里程碑跟踪进展', '3-6个月后重新评估'],
                'thesis': None
            }
        else:
            return {
                'action': 'reject',
                'confidence': 'high',
                'reason': f"综合评分{overall_score}分,不符合投资标准",
                'next_steps': ['与创始人反馈评估结果', '说明不投资的核心原因', '建议团队改进方向'],
                'thesis': None
            }

    def _generate_investment_thesis(self, context: Dict[str, Any], score: float) -> str:
        """生成投资逻辑"""
        strengths = []
        
        team = self._find_team_analysis(context)
        if team and team.get('team_score', 0) >= 80:
            strengths.append("团队经验丰富且互补性强")

        market = self._find_market_analysis(context)
        if market:
             growth = market.get('growth_rate', 0)
             if isinstance(growth, (int, float)) and growth >= 20:
                 strengths.append(f"市场高速增长({growth}% CAGR)")

        fin = self._find_financial_analysis(context)
        if fin:
             unit_econ = fin.get('unit_economics', {})
             if isinstance(unit_econ, dict) and unit_econ.get('ltv_cac_ratio', 0) >= 3:
                strengths.append("单位经济模型健康")

        thesis = "我们看好这个项目因为:\n"
        for i, strength in enumerate(strengths, 1):
            thesis += f"{i}. {strength}\n"
        return thesis

    def _generate_swot(self, context: Dict[str, Any]) -> Dict[str, List[str]]:
        """生成SWOT分析"""
        swot = {'strengths': [], 'weaknesses': [], 'opportunities': [], 'threats': []}

        team = self._find_team_analysis(context)
        if team:
            swot['strengths'].extend(team.get('key_strengths', []))
            swot['weaknesses'].extend(team.get('key_risks', [])) # Team risks are weaknesses

        fin = self._find_financial_analysis(context)
        if fin and (fin.get('financial_score') or fin.get('financial_health_score') or 0) >= 70:
            swot['strengths'].append("财务健康度良好")
        if fin:
             metrics = fin.get('key_metrics', {}) or {}
             if metrics.get('cash_runway_months', 12) < 12:
                 swot['weaknesses'].append("现金流较紧张")

        market = self._find_market_analysis(context)
        if market:
            swot['opportunities'].extend(market.get('opportunities', []))

        risk = self._find_risk_assessment(context)
        if risk:
             for r in risk.get('red_flags', []):
                 if isinstance(r, dict): swot['threats'].append(r.get('description', ''))
                 elif isinstance(r, str): swot['threats'].append(r)

        return swot

    def _extract_key_findings_quick(self, context: Dict[str, Any]) -> List[str]:
        """快速模式: 提取5个最关键发现"""
        findings = []
        
        team = self._find_team_analysis(context)
        if team: findings.append(f"团队评分: {team.get('team_score', 'N/A')}/100")

        market = self._find_market_analysis(context)
        if market: findings.append(f"市场增速: {market.get('growth_rate', 'N/A')}% CAGR")

        fin = self._find_financial_analysis(context)
        if fin: findings.append(f"财务评分: {fin.get('financial_score', fin.get('financial_health_score', 'N/A'))}/100")

        risk = self._find_risk_assessment(context)
        if risk: findings.append(f"识别到{len(risk.get('red_flags', []))}个红旗风险")

        return findings[:5]

    def _extract_detailed_findings(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """完整模式: 提取详细发现"""
        findings = []
        
        # Map category to helper function and name
        categories = [
            (self._find_team_analysis, '团队分析'),
            (self._find_market_analysis, '市场分析'),
            (self._find_financial_analysis, '财务分析'),
            (self._find_tech_assessment, '技术评估'),
            (self._find_risk_assessment, '风险评估'),
            (self._find_legal_assessment, '法律评估')
        ]

        for finder, name in categories:
            data = finder(context)
            if data:
                # Try to find a score
                score = None
                for k in data.keys():
                    if 'score' in k: 
                        score = data[k]
                        break
                
                finding = {
                    'category': name,
                    'score': score or 'N/A',
                    'key_points': self._extract_key_points_from_agent(data),
                    'concerns': self._extract_concerns_from_agent(data)
                }
                findings.append(finding)

        return findings

    def _extract_key_points_from_agent(self, agent_data: Dict[str, Any]) -> List[str]:
        """从Agent输出中提取关键点"""
        key_points = []
        if 'key_strengths' in agent_data: key_points.extend(agent_data['key_strengths'])
        if 'highlights' in agent_data: key_points.extend(agent_data['highlights'])
        if 'summary' in agent_data: key_points.append(agent_data['summary'][:50] + "...")
        return key_points[:3]

    def _extract_concerns_from_agent(self, agent_data: Dict[str, Any]) -> List[str]:
        """从Agent输出中提取关注点"""
        concerns = []
        if 'key_risks' in agent_data: concerns.extend(agent_data['key_risks'])
        if 'concerns' in agent_data: concerns.extend(agent_data['concerns'])
        if 'red_flags' in agent_data:
             for flag in agent_data['red_flags']:
                 if isinstance(flag, dict): concerns.append(flag.get('description', ''))
                 else: concerns.append(str(flag))
        return concerns[:3]

    def _extract_risks_and_opportunities(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """提取关键风险和机会"""
        risks = []
        opportunities = []

        risk = self._find_risk_assessment(context)
        if risk: risks.extend(risk.get('red_flags', []))

        market = self._find_market_analysis(context)
        if market: opportunities.extend(market.get('opportunities', []))

        fin = self._find_financial_analysis(context)
        if fin and 'opportunities' in fin: opportunities.extend(fin['opportunities'])

        return {
            'critical_risks': risks[:5],
            'key_opportunities': opportunities[:5]
        }

    def _generate_detailed_sections(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """生成报告的详细章节"""
        sections = {}
        sections['overview'] = self._generate_overview_section(context)
        
        team = self._find_team_analysis(context)
        if team: sections['team'] = team
        
        market = self._find_market_analysis(context)
        if market: sections['market'] = market
        
        fin = self._find_financial_analysis(context)
        if fin: sections['financial'] = fin
        
        tech = self._find_tech_assessment(context)
        if tech: sections['technology'] = tech
        
        risk = self._find_risk_assessment(context)
        if risk: sections['risk'] = risk
        
        legal = self._find_legal_assessment(context)
        if legal: sections['legal'] = legal
        
        return sections

    def _generate_overview_section(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """生成项目概览章节"""
        target = context.get('target', {})
        # If target is not directly in context (it might be in inputs), try to find it
        if not target:
             target = context.get('inputs', {}).get('target', {})

        return {
            'scenario': context.get('scenario', 'unknown'),
            'target_name': target.get('company_name', 'N/A'),
            'industry': target.get('industry', 'N/A'),
            'stage': target.get('stage', 'N/A'),
            'analysis_date': self._get_current_date(),
            'analysis_mode': 'quick' if self.quick_mode else 'full'
        }

    def _generate_quick_summary(self, context: Dict[str, Any], overall_score: float) -> str:
        target_name = context.get('target', {}).get('company_name', '该项目')
        summary = f"{target_name}综合评分{overall_score}分。"
        if overall_score >= 75: summary += "整体表现优秀,建议深入尽调。"
        elif overall_score >= 60: summary += "整体表现中等,建议持续观察。"
        else: summary += "整体表现较弱,不建议投资。"
        return summary

    def _generate_executive_summary(self, context: Dict[str, Any], overall_score: float, swot: Dict[str, List[str]]) -> str:
        target_name = context.get('target', {}).get('company_name', '该项目')
        summary = f"# 执行摘要\n\n{target_name}综合评分{overall_score}分。\n\n## 核心优势\n{self._format_list(swot['strengths'][:3])}\n\n## 关键风险\n{self._format_list(swot['threats'][:3])}\n\n## 投资建议\n"
        if overall_score >= 75: summary += "**推荐投资**: 项目各维度表现优秀,符合投资标准。"
        elif overall_score >= 60: summary += "**持续观察**: 项目有潜力但需改进,建议跟踪进展。"
        else: summary += "**不推荐**: 项目不符合当前投资标准。"
        return summary

    def _format_list(self, items: List[str]) -> str:
        if not items: return "- (无)"
        return "\n".join([f"- {item}" for item in items])

    def _generate_report_id(self) -> str:
        import uuid
        return str(uuid.uuid4())

    def _get_current_date(self) -> str:
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d")

    async def _call_llm_for_synthesis(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用LLM来综合分析所有Agent的输出并生成结构化报告

        这是核心方法：让LLM读取所有Agent的Markdown输出，提取关键信息，
        生成结构化的投资分析报告
        """
        logger.info("[ReportSynthesizer] 🤖 调用LLM生成综合报告")

        # 收集所有Agent的输出
        agent_outputs = []
        for key, value in context.items():
            if isinstance(value, dict):
                if 'summary' in value or 'raw_output' in value or 'analysis' in value:
                    agent_outputs.append(f"### {key}分析结果:\n{value.get('summary', value.get('raw_output', value.get('analysis', '')))}\n")

        combined_analysis = "\n\n".join(agent_outputs)

        target_info = context.get('target', {})
        scenario = context.get('scenario', 'unknown')
        company_name = (target_info.get('company_name') or
                       target_info.get('target_name') or
                       target_info.get('industry_name') or
                       '分析目标')

        # 构建提示词
        prompt = f"""你是一位资深投资分析师，负责综合多位专家的分析结果，生成结构化的投资分析报告。

## 分析场景: {scenario}
## 分析目标: {company_name}

## 各专家分析结果:
{combined_analysis}

## 任务要求:
请基于以上专家分析，生成一份结构化的投资分析报告。报告必须包含以下内容（请严格按照JSON格式输出）：

```json
{{
  "investment_score": <综合评分 0-100>,
  "overall_recommendation": "<invest/observe/reject>",
  "confidence_level": "<high/medium/low>",

  "executive_summary": "<执行摘要，2-3段文字>",

  "key_findings": [
    {{
      "category": "<分类名称>",
      "score": <评分>,
      "key_points": ["<要点1>", "<要点2>"],
      "concerns": ["<关注点1>", "<关注点2>"]
    }}
  ],

  "strengths": ["<优势1>", "<优势2>", "<优势3>"],
  "weaknesses": ["<劣势1>", "<劣势2>"],
  "opportunities": ["<机会1>", "<机会2>"],
  "threats": ["<威胁1>", "<威胁2>"],

  "critical_risks": ["<关键风险1>", "<关键风险2>"],
  "key_opportunities": ["<关键机会1>", "<关键机会2>"],

  "investment_thesis": "<投资逻辑，为什么投资这个项目，2-3段文字>",

  "next_steps": ["<下一步1>", "<下一步2>", "<下一步3>"],

  "detailed_analysis": {{
    "market": "<市场分析总结，2-3段>",
    "technology": "<技术分析总结，2-3段>",
    "financial": "<财务分析总结，2-3段>",
    "team": "<团队分析总结，如有>",
    "risk": "<风险分析总结>"
  }}
}}
```

**重要提示**:
1. 必须输出有效的JSON格式，不要有额外的文字说明
2. 所有评分必须是数字 (0-100)
3. recommendation必须是: invest, observe, 或 reject 之一
4. 要深入分析，不要泛泛而谈
5. 基于专家的具体分析内容，提取关键信息
6. 如果某个领域的分析缺失，请在该字段中说明"该领域未进行详细分析"

请开始生成报告:"""

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.llm_gateway_url}/chat",
                    json={
                        "history": [
                            {
                                "role": "user",
                                "parts": [prompt]
                            }
                        ]
                    }
                )
                response.raise_for_status()
                result = response.json()

                # 提取LLM生成的内容
                content = result.get("content", "")
                logger.info(f"[ReportSynthesizer] ✅ LLM返回内容长度: {len(content)}")

                # 解析JSON（LLM可能会返回被```json包裹的内容）
                json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    json_str = content

                # 尝试解析JSON
                try:
                    llm_report = json.loads(json_str)
                    logger.info(f"[ReportSynthesizer] ✅ 成功解析LLM生成的JSON报告")
                    return llm_report
                except json.JSONDecodeError as e:
                    logger.error(f"[ReportSynthesizer] ❌ JSON解析失败: {e}")
                    logger.error(f"[ReportSynthesizer] 原始内容: {content[:500]}")
                    # 返回None，让调用者使用fallback
                    return None

        except Exception as e:
            logger.error(f"[ReportSynthesizer] ❌ LLM调用失败: {e}")
            return None

async def synthesize_report(context: Dict[str, Any], quick_mode: bool = False) -> Dict[str, Any]:
    synthesizer = ReportSynthesizerAgent(quick_mode=quick_mode)
    return await synthesizer.synthesize(context)
