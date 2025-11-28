# backend/services/report_orchestrator/app/agents/exit_agent.py
"""
退出分析 Agent
分析 IPO、并购等退出路径
"""
import httpx
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class IPOAnalysis(BaseModel):
    """IPO 分析"""
    feasibility: str = Field(..., description="可行性评估（高/中/低）")
    estimated_timeline: str = Field(..., description="预计时间")
    requirements: List[str] = Field(..., description="前置条件")
    target_board: Optional[str] = Field(None, description="目标板块")

class ExitAnalysis(BaseModel):
    """退出分析结果"""
    primary_path: str = Field(..., description="主要退出路径")
    ipo_analysis: IPOAnalysis
    ma_opportunities: List[str] = Field(..., description="并购机会")
    exit_risks: List[str] = Field(..., description="退出风险")
    analysis_text: str = Field(..., description="详细分析文本")

class ExitAgent:
    """退出分析 Agent"""
    
    def __init__(
        self,
        web_search_url: str = "http://web_search_service:8003",
        llm_gateway_url: str = "http://llm_gateway:8001"
    ):
        self.web_search_url = web_search_url
        self.llm_gateway_url = llm_gateway_url
    
    async def analyze_exit_paths(
        self,
        bp_data: Dict[str, Any],
        market_analysis: str,
        valuation_analysis: Any
    ) -> ExitAnalysis:
        """
        分析退出路径
        
        Args:
            bp_data: BP 结构化数据
            market_analysis: 市场分析结果
            valuation_analysis: 估值分析结果
        
        Returns:
            ExitAnalysis: 退出分析结果
        """
        try:
            # 1. 搜索行业退出案例
            exit_data = await self._search_exit_cases(bp_data)
            
            # 2. 构建分析 Prompt
            prompt = self._build_exit_prompt(
                bp_data,
                market_analysis,
                valuation_analysis,
                exit_data
            )
            
            # 3. 调用 LLM 分析
            llm_response = await self._call_llm(prompt)
            
            # 4. 解析 LLM 响应
            analysis = self._parse_llm_response(llm_response, bp_data)
            
            return analysis
        
        except Exception as e:
            print(f"Error in exit analysis: {e}")
            return self._create_fallback_analysis(bp_data)
    
    async def _search_exit_cases(self, bp_data: Dict[str, Any]) -> str:
        """搜索行业退出案例"""
        try:
            target_market = bp_data.get("target_market", "科技")
            
            query = f"{target_market} IPO 并购 退出案例 科创板 创业板"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.web_search_url}/search",
                    json={"query": query, "max_results": 5}
                )
                
                if response.status_code == 200:
                    results = response.json().get("results", [])
                    search_text = "\n\n".join([
                        f"案例: {r.get('title', '')}\n{r.get('content', '')[:300]}"
                        for r in results[:3]
                    ])
                    return search_text
                else:
                    return "无法获取退出案例数据"
        
        except Exception as e:
            print(f"Error searching exit cases: {e}")
            return "搜索失败"
    
    def _build_exit_prompt(
        self,
        bp_data: Dict[str, Any],
        market_analysis: str,
        valuation_analysis: Any,
        exit_data: str
    ) -> str:
        """构建退出分析 Prompt"""
        company_name = bp_data.get("company_name", "目标公司")
        target_market = bp_data.get("target_market", "未知市场")
        current_stage = bp_data.get("current_stage", "早期")
        
        prompt = f"""你是一位专业的投资退出分析师。

**项目信息**:
- 公司名称: {company_name}
- 目标市场: {target_market}
- 当前阶段: {current_stage}

**市场分析摘要**:
{market_analysis[:400]}

**行业退出案例**:
{exit_data[:800]}

**任务**: 请分析该项目的退出路径，输出 JSON 格式：

{{
  "primary_path": "主要退出路径（IPO/并购/其他）",
  "ipo_analysis": {{
    "feasibility": "可行性（高/中/低）",
    "estimated_timeline": "预计时间（如：5-7年）",
    "requirements": [
      "前置条件1（如：营收达到5亿）",
      "前置条件2",
      "前置条件3"
    ],
    "target_board": "目标板块（如：科创板、创业板）"
  }},
  "ma_opportunities": [
    "潜在买家1（行业巨头或战略投资者）",
    "潜在买家2",
    "潜在买家3"
  ],
  "exit_risks": [
    "退出风险1",
    "退出风险2",
    "退出风险3"
  ],
  "analysis_text": "详细的退出分析，包括：\\n### 主要退出路径\\n\\n### IPO 路径分析\\n\\n### 并购机会\\n\\n### 退出时间窗口\\n\\n### 风险提示\\n\\n（用 Markdown 格式，400-600字）"
}}

**要求**:
1. 退出路径要现实可行
2. IPO 分析要考虑中国资本市场特点（科创板、创业板、北交所等）
3. 并购机会要具体（行业内的潜在买家）
4. 风险提示要全面（监管、市场、时间窗口等）
5. analysis_text 要结构清晰

请只输出 JSON，不要包含其他文字。
"""
        return prompt
    
    async def _call_llm(self, prompt: str) -> str:
        """调用 LLM Gateway"""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.llm_gateway_url}/generate",
                    json={"prompt": prompt}
                )
                
                if response.status_code == 200:
                    return response.json().get("text", "")
                else:
                    raise Exception(f"LLM returned {response.status_code}")
        
        except Exception as e:
            print(f"Error calling LLM: {e}")
            raise
    
    def _parse_llm_response(self, response: str, bp_data: Dict[str, Any]) -> ExitAnalysis:
        """解析 LLM 响应"""
        import json
        import re
        
        try:
            cleaned = re.sub(r'```json\s*|\s*```', '', response.strip())
            data = json.loads(cleaned)
            
            return ExitAnalysis(
                primary_path=data.get("primary_path", "IPO"),
                ipo_analysis=IPOAnalysis(**data.get("ipo_analysis", {})),
                ma_opportunities=data.get("ma_opportunities", []),
                exit_risks=data.get("exit_risks", []),
                analysis_text=data.get("analysis_text", "")
            )
        
        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            return self._create_fallback_analysis(bp_data)
    
    def _create_fallback_analysis(self, bp_data: Dict[str, Any]) -> ExitAnalysis:
        """创建后备分析结果"""
        target_market = bp_data.get("target_market", "科技")
        
        return ExitAnalysis(
            primary_path="IPO",
            ipo_analysis=IPOAnalysis(
                feasibility="中等",
                estimated_timeline="5-7年",
                requirements=[
                    "营收达到 5 亿元以上",
                    "连续 3 年盈利或符合科创板标准",
                    "完善公司治理结构"
                ],
                target_board="科创板或创业板"
            ),
            ma_opportunities=[
                f"{target_market}行业龙头企业",
                "战略投资者",
                "产业基金"
            ],
            exit_risks=[
                "IPO 窗口期不确定",
                "监管政策变化",
                "市场环境波动"
            ],
            analysis_text=f"""### 主要退出路径

基于当前阶段和{target_market}行业特点，**IPO** 是最可能的退出路径。

### IPO 路径分析

- **可行性**: 中等
- **时间窗口**: 5-7 年
- **目标板块**: 科创板或创业板

**前置条件**:
1. 营收达到 5 亿元以上
2. 连续 3 年盈利或符合科创板标准
3. 完善公司治理结构

### 并购机会

潜在买家包括：
- {target_market}行业龙头企业
- 战略投资者
- 产业基金

### 风险提示

⚠️ **退出风险**:
- IPO 窗口期不确定，需密切关注资本市场环境
- 监管政策变化可能影响上市进程
- 市场环境波动影响估值
"""
        )
