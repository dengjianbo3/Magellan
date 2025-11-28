# backend/services/report_orchestrator/app/agents/preference_match_agent.py
"""
Preference Match Agent for Institution Preference Checking
偏好匹配 Agent，用于机构投资偏好检查
"""
import httpx
from typing import List, Dict, Any
from ..models.dd_models import BPStructuredData


class InstitutionPreference:
    """机构投资偏好（简化版，与 user_service 保持一致）"""
    def __init__(self, data: Dict[str, Any]):
        self.user_id = data.get("user_id")
        self.investment_thesis = data.get("investment_thesis", [])
        self.preferred_stages = data.get("preferred_stages", [])
        self.focus_industries = data.get("focus_industries", [])
        self.excluded_industries = data.get("excluded_industries", [])
        self.geography_preference = data.get("geography_preference", [])
        self.investment_range = data.get("investment_range")
        self.min_team_size = data.get("min_team_size")
        self.require_revenue = data.get("require_revenue")
        self.require_product = data.get("require_product")


class PreferenceMatchResult:
    """偏好匹配结果"""
    def __init__(
        self,
        is_match: bool,
        match_score: float,
        matched_criteria: List[str],
        mismatched_criteria: List[str],
        recommendation: str,
        mismatch_reasons: List[str]
    ):
        self.is_match = is_match
        self.match_score = match_score
        self.matched_criteria = matched_criteria
        self.mismatched_criteria = mismatched_criteria
        self.recommendation = recommendation
        self.mismatch_reasons = mismatch_reasons
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_match": self.is_match,
            "match_score": self.match_score,
            "matched_criteria": self.matched_criteria,
            "mismatched_criteria": self.mismatched_criteria,
            "recommendation": self.recommendation,
            "mismatch_reasons": self.mismatch_reasons
        }


class PreferenceMatchAgent:
    """Agent for checking project-institution preference match"""
    
    def __init__(self, user_service_url: str):
        self.user_service_url = user_service_url
    
    async def check_match(
        self,
        bp_data: BPStructuredData,
        user_id: str
    ) -> PreferenceMatchResult:
        """
        检查项目与机构偏好的匹配度
        
        Args:
            bp_data: BP 结构化数据
            user_id: 机构/用户ID
        
        Returns:
            PreferenceMatchResult 匹配结果
        """
        # 1. 获取机构偏好
        preferences = await self._fetch_preferences(user_id)
        
        if not preferences:
            # 如果没有设置偏好，默认通过
            return PreferenceMatchResult(
                is_match=True,
                match_score=100.0,
                matched_criteria=["未设置机构偏好，默认通过"],
                mismatched_criteria=[],
                recommendation="继续分析",
                mismatch_reasons=[]
            )
        
        # 2. 执行匹配检查
        matched = []
        mismatched = []
        reasons = []
        
        # 检查各维度
        industry_score = self._check_industry(bp_data, preferences, matched, mismatched, reasons)
        stage_score = self._check_stage(bp_data, preferences, matched, mismatched, reasons)
        geography_score = self._check_geography(bp_data, preferences, matched, mismatched, reasons)
        amount_score = self._check_investment_amount(bp_data, preferences, matched, mismatched, reasons)
        team_score = self._check_team_size(bp_data, preferences, matched, mismatched, reasons)
        revenue_score = self._check_revenue(bp_data, preferences, matched, mismatched, reasons)
        product_score = self._check_product(bp_data, preferences, matched, mismatched, reasons)
        
        # 3. 计算综合匹配度（加权平均）
        weights = {
            "industry": 0.3,
            "stage": 0.2,
            "geography": 0.1,
            "amount": 0.15,
            "team": 0.1,
            "revenue": 0.075,
            "product": 0.075
        }
        
        total_score = (
            industry_score * weights["industry"] +
            stage_score * weights["stage"] +
            geography_score * weights["geography"] +
            amount_score * weights["amount"] +
            team_score * weights["team"] +
            revenue_score * weights["revenue"] +
            product_score * weights["product"]
        )
        
        # 4. 判断是否匹配（阈值 60 分）
        is_match = total_score >= 60.0
        recommendation = "继续分析" if is_match else "不建议继续"
        
        return PreferenceMatchResult(
            is_match=is_match,
            match_score=round(total_score, 2),
            matched_criteria=matched,
            mismatched_criteria=mismatched,
            recommendation=recommendation,
            mismatch_reasons=reasons
        )
    
    async def _fetch_preferences(self, user_id: str) -> InstitutionPreference:
        """从 user_service 获取机构偏好"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{self.user_service_url}/api/v1/preferences/{user_id}")
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") and data.get("preference"):
                        return InstitutionPreference(data["preference"])
                
                return None
            
            except Exception as e:
                print(f"Warning: Failed to fetch preferences: {e}")
                return None
    
    def _check_industry(
        self,
        bp_data: BPStructuredData,
        preferences: InstitutionPreference,
        matched: List[str],
        mismatched: List[str],
        reasons: List[str]
    ) -> float:
        """检查行业匹配"""
        if not preferences.focus_industries and not preferences.excluded_industries:
            return 100.0  # 未设置行业偏好，满分
        
        target_market = bp_data.target_market.lower() if bp_data.target_market else ""
        
        # 如果 BP 中没有提供行业信息，给予中等分数
        if not target_market:
            return 50.0
        
        # 检查排除行业（优先级最高）
        for excluded in preferences.excluded_industries:
            if excluded.lower() in target_market:
                mismatched.append(f"行业: {bp_data.target_market}")
                reasons.append(f"项目所属行业 '{bp_data.target_market}' 在机构排除列表中")
                return 0.0
        
        # 检查关注行业
        if preferences.focus_industries:
            for focus in preferences.focus_industries:
                if focus.lower() in target_market:
                    matched.append(f"行业: {bp_data.target_market}")
                    return 100.0
            
            # 未匹配关注行业
            mismatched.append(f"行业: {bp_data.target_market}")
            reasons.append(f"项目行业 '{bp_data.target_market}' 不在机构关注列表中")
            return 0.0
        
        return 100.0
    
    def _check_stage(
        self,
        bp_data: BPStructuredData,
        preferences: InstitutionPreference,
        matched: List[str],
        mismatched: List[str],
        reasons: List[str]
    ) -> float:
        """检查融资阶段匹配"""
        if not preferences.preferred_stages:
            return 100.0
        
        current_stage = bp_data.current_stage.lower() if bp_data.current_stage else ""
        
        for stage in preferences.preferred_stages:
            if stage.lower() in current_stage:
                matched.append(f"阶段: {bp_data.current_stage}")
                return 100.0
        
        mismatched.append(f"阶段: {bp_data.current_stage}")
        reasons.append(f"项目阶段 '{bp_data.current_stage}' 不在机构偏好阶段中")
        return 30.0  # 部分分数，因为阶段不是绝对硬性条件
    
    def _check_geography(
        self,
        bp_data: BPStructuredData,
        preferences: InstitutionPreference,
        matched: List[str],
        mismatched: List[str],
        reasons: List[str]
    ) -> float:
        """检查地域偏好"""
        if not preferences.geography_preference:
            return 100.0
        
        # 简化：从 company_name 或其他字段推断地域（实际应该有专门的地域字段）
        # 这里暂时给予中等分数
        return 70.0
    
    def _check_investment_amount(
        self,
        bp_data: BPStructuredData,
        preferences: InstitutionPreference,
        matched: List[str],
        mismatched: List[str],
        reasons: List[str]
    ) -> float:
        """检查投资金额区间"""
        if not preferences.investment_range:
            return 100.0
        
        if not bp_data.funding_request:
            return 70.0  # 未提供融资金额，给予中等分数
        
        # 尝试从字符串中提取数字（简化处理）
        try:
            import re
            numbers = re.findall(r'\d+', bp_data.funding_request)
            if numbers:
                amount = float(numbers[0])
                
                min_amt = preferences.investment_range.get("min_amount", 0)
                max_amt = preferences.investment_range.get("max_amount", float('inf'))
                
                if min_amt <= amount <= max_amt:
                    matched.append(f"融资金额: {bp_data.funding_request}")
                    return 100.0
                else:
                    mismatched.append(f"融资金额: {bp_data.funding_request}")
                    reasons.append(f"融资金额不在机构投资区间 ({min_amt}-{max_amt}万元)")
                    return 20.0
        except Exception:
            pass
        
        return 70.0
    
    def _check_team_size(
        self,
        bp_data: BPStructuredData,
        preferences: InstitutionPreference,
        matched: List[str],
        mismatched: List[str],
        reasons: List[str]
    ) -> float:
        """检查团队规模"""
        if preferences.min_team_size is None:
            return 100.0
        
        team_size = len(bp_data.team) if bp_data.team else 0
        
        if team_size >= preferences.min_team_size:
            matched.append(f"团队规模: {team_size}人")
            return 100.0
        else:
            mismatched.append(f"团队规模: {team_size}人")
            reasons.append(f"团队规模 ({team_size}人) 小于机构要求 ({preferences.min_team_size}人)")
            return 40.0
    
    def _check_revenue(
        self,
        bp_data: BPStructuredData,
        preferences: InstitutionPreference,
        matched: List[str],
        mismatched: List[str],
        reasons: List[str]
    ) -> float:
        """检查是否有收入"""
        if preferences.require_revenue is None:
            return 100.0
        
        has_revenue = bool(bp_data.financial_projections and len(bp_data.financial_projections) > 0)
        
        if preferences.require_revenue:
            if has_revenue:
                matched.append("已有收入/财务数据")
                return 100.0
            else:
                mismatched.append("无收入数据")
                reasons.append("机构要求项目已有收入，但 BP 未提供财务数据")
                return 0.0
        
        return 100.0
    
    def _check_product(
        self,
        bp_data: BPStructuredData,
        preferences: InstitutionPreference,
        matched: List[str],
        mismatched: List[str],
        reasons: List[str]
    ) -> float:
        """检查产品是否上线"""
        if preferences.require_product is None:
            return 100.0
        
        has_product = bool(bp_data.product_name or bp_data.product_description)
        
        if preferences.require_product:
            if has_product:
                matched.append(f"产品: {bp_data.product_name}")
                return 100.0
            else:
                mismatched.append("产品未明确")
                reasons.append("机构要求产品已上线，但 BP 未提供产品信息")
                return 0.0
        
        return 100.0
