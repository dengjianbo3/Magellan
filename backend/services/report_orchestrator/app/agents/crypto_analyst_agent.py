"""
Crypto Analyst Agent - 加密项目深度分析Agent
用于另类投资(Alternative Investment)的加密项目深度分析
支持多步骤分析: 项目识别、技术研究、团队调查、代币经济学深度分析
"""
from typing import Dict, Any, List, Optional
import httpx
from pydantic import BaseModel, Field


class ProjectInfo(BaseModel):
    """项目基本信息"""
    project_name: str = Field(..., description="项目名称")
    symbol: str = Field(..., description="代币符号")
    category: str = Field(..., description="项目分类(L1/L2/DeFi/NFT/GameFi等)")
    launch_date: Optional[str] = Field(None, description="上线日期")
    description: str = Field(..., description="项目简介")
    website: Optional[str] = Field(None, description="官网")
    whitepaper: Optional[str] = Field(None, description="白皮书链接")


class TechnicalAnalysis(BaseModel):
    """技术分析"""
    blockchain: str = Field(..., description="所在区块链")
    consensus_mechanism: Optional[str] = Field(None, description="共识机制")
    smart_contract_audited: bool = Field(False, description="是否经过审计")
    audit_firms: List[str] = Field(default_factory=list, description="审计机构")
    code_quality_score: float = Field(..., description="代码质量评分 0-1")
    security_score: float = Field(..., description="安全评分 0-1")
    tech_innovation: str = Field(..., description="技术创新点")
    tech_risks: List[str] = Field(default_factory=list, description="技术风险")


class TeamAnalysis(BaseModel):
    """团队分析"""
    founders: List[str] = Field(default_factory=list, description="创始人")
    team_size: Optional[int] = Field(None, description="团队规模")
    team_background: str = Field(..., description="团队背景评估")
    advisors: List[str] = Field(default_factory=list, description="顾问")
    investors: List[str] = Field(default_factory=list, description="投资机构")
    team_credibility_score: float = Field(..., description="团队可信度评分 0-1")
    team_experience_score: float = Field(..., description="团队经验评分 0-1")


class TokenomicsDeepAnalysis(BaseModel):
    """代币经济学深度分析"""
    total_supply: Optional[float] = Field(None, description="总供应量")
    circulating_supply: Optional[float] = Field(None, description="流通量")
    distribution: Dict[str, float] = Field(default_factory=dict, description="分配比例")
    vesting_schedule: str = Field(..., description="解锁时间表")
    inflation_rate: Optional[float] = Field(None, description="通胀率")
    burn_mechanism: Optional[str] = Field(None, description="销毁机制")
    utility: List[str] = Field(default_factory=list, description="代币用途")
    value_capture: str = Field(..., description="价值捕获机制")
    tokenomics_score: float = Field(..., description="代币经济学评分 0-1")


class CommunityMetrics(BaseModel):
    """社区指标"""
    twitter_followers: Optional[int] = Field(None, description="Twitter粉丝数")
    discord_members: Optional[int] = Field(None, description="Discord成员数")
    telegram_members: Optional[int] = Field(None, description="Telegram成员数")
    github_stars: Optional[int] = Field(None, description="GitHub星数")
    github_commits_30d: Optional[int] = Field(None, description="近30天提交数")
    community_sentiment: str = Field(..., description="社区情绪(positive/neutral/negative)")
    community_activity_score: float = Field(..., description="社区活跃度评分 0-1")


class MarketAnalysis(BaseModel):
    """市场分析"""
    market_cap: Optional[float] = Field(None, description="市值(USD)")
    fully_diluted_valuation: Optional[float] = Field(None, description="完全稀释估值")
    volume_24h: Optional[float] = Field(None, description="24小时交易量")
    price_change_7d: Optional[float] = Field(None, description="7天价格变化(%)")
    price_change_30d: Optional[float] = Field(None, description="30天价格变化(%)")
    ath: Optional[float] = Field(None, description="历史最高价")
    ath_change_percentage: Optional[float] = Field(None, description="距ATH跌幅(%)")
    market_rank: Optional[int] = Field(None, description="市值排名")
    liquidity_score: float = Field(..., description="流动性评分 0-1")


class RiskAssessment(BaseModel):
    """风险评估"""
    smart_contract_risk: str = Field(..., description="智能合约风险")
    regulatory_risk: str = Field(..., description="监管风险")
    market_risk: str = Field(..., description="市场风险")
    team_risk: str = Field(..., description="团队风险")
    technology_risk: str = Field(..., description="技术风险")
    overall_risk_level: str = Field(..., description="总体风险等级(LOW/MEDIUM/HIGH/CRITICAL)")
    risk_score: float = Field(..., description="风险评分 0-1 (越低越好)")


class CryptoAnalysisResult(BaseModel):
    """加密项目分析结果"""
    project_info: ProjectInfo
    technical_analysis: TechnicalAnalysis
    team_analysis: TeamAnalysis
    tokenomics: TokenomicsDeepAnalysis
    community_metrics: CommunityMetrics
    market_analysis: MarketAnalysis
    risk_assessment: RiskAssessment

    overall_score: float = Field(..., description="综合评分 0-1")
    investment_recommendation: str = Field(..., description="投资建议")
    key_strengths: List[str] = Field(default_factory=list, description="关键优势")
    key_weaknesses: List[str] = Field(default_factory=list, description="关键弱点")
    summary: str = Field(..., description="总结")


class CryptoAnalystAgent:
    """加密项目深度分析Agent - 用于另类投资Standard/Comprehensive模式"""

    def __init__(
        self,
        web_search_url: str = "http://web_search_service:8010",
        llm_gateway_url: str = "http://llm_gateway:8003"
    ):
        self.web_search_url = web_search_url
        self.llm_gateway_url = llm_gateway_url

    async def analyze(
        self,
        target: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> CryptoAnalysisResult:
        """
        执行加密项目深度分析

        Args:
            target: 分析目标,包含:
                - project_name: 项目名称 (可选,如果没有则通过symbol识别)
                - symbol: 代币符号 (如: BTC, ETH, UNI)
                - contract_address: 合约地址 (可选)
                - chain: 区块链 (可选,默认ethereum)
            context: 上下文数据 (quick模式的初步分析结果等)

        Returns:
            CryptoAnalysisResult: 完整的加密项目分析结果
        """
        try:
            # Step 1: 项目识别和基本信息收集
            project_info = await self._identify_project(target)

            # Step 2: 并行执行多维度分析
            import asyncio
            technical_task = self._analyze_technology(target, project_info)
            team_task = self._analyze_team(target, project_info)
            tokenomics_task = self._analyze_tokenomics_deep(target, project_info)
            community_task = self._analyze_community(target, project_info)
            market_task = self._analyze_market(target, project_info)

            technical, team, tokenomics, community, market = await asyncio.gather(
                technical_task,
                team_task,
                tokenomics_task,
                community_task,
                market_task,
                return_exceptions=True
            )

            # 处理异常
            if isinstance(technical, Exception):
                print(f"[CryptoAnalystAgent] Technical analysis failed: {technical}")
                technical = self._fallback_technical()
            if isinstance(team, Exception):
                print(f"[CryptoAnalystAgent] Team analysis failed: {team}")
                team = self._fallback_team()
            if isinstance(tokenomics, Exception):
                print(f"[CryptoAnalystAgent] Tokenomics analysis failed: {tokenomics}")
                tokenomics = self._fallback_tokenomics()
            if isinstance(community, Exception):
                print(f"[CryptoAnalystAgent] Community analysis failed: {community}")
                community = self._fallback_community()
            if isinstance(market, Exception):
                print(f"[CryptoAnalystAgent] Market analysis failed: {market}")
                market = self._fallback_market()

            # Step 3: 风险评估
            risk_assessment = await self._assess_risks(
                technical, team, tokenomics, community, market
            )

            # Step 4: 综合评分和建议
            overall_score, recommendation, strengths, weaknesses, summary = \
                self._synthesize_analysis(
                    technical, team, tokenomics, community, market, risk_assessment
                )

            # 构建结果
            return CryptoAnalysisResult(
                project_info=project_info,
                technical_analysis=technical,
                team_analysis=team,
                tokenomics=tokenomics,
                community_metrics=community,
                market_analysis=market,
                risk_assessment=risk_assessment,
                overall_score=overall_score,
                investment_recommendation=recommendation,
                key_strengths=strengths,
                key_weaknesses=weaknesses,
                summary=summary
            )

        except Exception as e:
            print(f"[CryptoAnalystAgent] Analysis failed: {e}")
            return self._fallback_result(target)

    async def _identify_project(self, target: Dict[str, Any]) -> ProjectInfo:
        """项目识别和基本信息收集"""
        project_name = target.get('project_name', '')
        symbol = target.get('symbol', '').upper()

        if not project_name and not symbol:
            raise ValueError("必须提供project_name或symbol")

        # 搜索项目信息
        query = f"{symbol} {project_name} crypto project whitepaper" if project_name else f"{symbol} cryptocurrency"
        search_results = await self._web_search(query, max_results=5)

        # 使用LLM提取项目信息
        prompt = f"""你是加密货币项目研究专家。根据以下搜索结果,提取项目基本信息。

**项目代币**: {symbol}
**项目名称**: {project_name or '待识别'}

**搜索结果**:
{self._format_search_results(search_results)}

**任务**: 提取项目基本信息

**输出格式**(严格JSON):
{{
  "project_name": "完整项目名称",
  "symbol": "{symbol}",
  "category": "L1/L2/DeFi/NFT/GameFi/其他",
  "launch_date": "YYYY-MM",
  "description": "150字内项目简介",
  "website": "官网URL",
  "whitepaper": "白皮书URL"
}}
"""

        result = await self._call_llm(prompt)

        return ProjectInfo(
            project_name=result.get('project_name', project_name or symbol),
            symbol=symbol,
            category=result.get('category', 'Unknown'),
            launch_date=result.get('launch_date'),
            description=result.get('description', '待补充'),
            website=result.get('website'),
            whitepaper=result.get('whitepaper')
        )

    async def _analyze_technology(
        self,
        target: Dict[str, Any],
        project_info: ProjectInfo
    ) -> TechnicalAnalysis:
        """技术分析"""
        query = f"{project_info.symbol} {project_info.project_name} technology architecture audit security"
        search_results = await self._web_search(query, max_results=5)

        prompt = f"""你是区块链技术专家。分析项目的技术架构和安全性。

**项目**: {project_info.project_name} ({project_info.symbol})
**分类**: {project_info.category}

**搜索结果**:
{self._format_search_results(search_results)}

**任务**: 技术分析

**输出格式**(严格JSON):
{{
  "blockchain": "ethereum/bsc/solana/其他",
  "consensus_mechanism": "PoS/PoW/DPoS/其他",
  "smart_contract_audited": true/false,
  "audit_firms": ["CertiK", "SlowMist"],
  "code_quality_score": 0.8,
  "security_score": 0.75,
  "tech_innovation": "技术创新点描述",
  "tech_risks": ["风险1", "风险2"]
}}
"""

        result = await self._call_llm(prompt)

        return TechnicalAnalysis(**result)

    async def _analyze_team(
        self,
        target: Dict[str, Any],
        project_info: ProjectInfo
    ) -> TeamAnalysis:
        """团队分析"""
        query = f"{project_info.project_name} team founders investors"
        search_results = await self._web_search(query, max_results=5)

        prompt = f"""你是投资尽调专家。分析项目团队背景和可信度。

**项目**: {project_info.project_name}

**搜索结果**:
{self._format_search_results(search_results)}

**任务**: 团队尽调

**输出格式**(严格JSON):
{{
  "founders": ["创始人1", "创始人2"],
  "team_size": 50,
  "team_background": "团队背景评估(100字内)",
  "advisors": ["顾问1"],
  "investors": ["a16z", "Coinbase Ventures"],
  "team_credibility_score": 0.8,
  "team_experience_score": 0.75
}}
"""

        result = await self._call_llm(prompt)

        return TeamAnalysis(**result)

    async def _analyze_tokenomics_deep(
        self,
        target: Dict[str, Any],
        project_info: ProjectInfo
    ) -> TokenomicsDeepAnalysis:
        """代币经济学深度分析"""
        query = f"{project_info.symbol} tokenomics distribution vesting"
        search_results = await self._web_search(query, max_results=5)

        prompt = f"""你是代币经济学专家。深度分析代币经济模型。

**项目**: {project_info.project_name} ({project_info.symbol})

**搜索结果**:
{self._format_search_results(search_results)}

**任务**: 代币经济学深度分析

**输出格式**(严格JSON):
{{
  "total_supply": 1000000000.0,
  "circulating_supply": 500000000.0,
  "distribution": {{"team": 0.15, "investors": 0.2, "community": 0.65}},
  "vesting_schedule": "团队4年线性解锁,投资人2年解锁",
  "inflation_rate": 0.03,
  "burn_mechanism": "交易手续费50%销毁",
  "utility": ["治理", "质押", "手续费支付"],
  "value_capture": "价值捕获机制描述",
  "tokenomics_score": 0.75
}}
"""

        result = await self._call_llm(prompt)

        return TokenomicsDeepAnalysis(**result)

    async def _analyze_community(
        self,
        target: Dict[str, Any],
        project_info: ProjectInfo
    ) -> CommunityMetrics:
        """社区分析"""
        # Mock实现 - 实际应该调用Twitter API, Discord API等
        query = f"{project_info.symbol} community social media"
        search_results = await self._web_search(query, max_results=3)

        prompt = f"""基于搜索结果,评估项目社区活跃度。

**项目**: {project_info.project_name}

**搜索结果**:
{self._format_search_results(search_results)}

**输出格式**(严格JSON):
{{
  "twitter_followers": 100000,
  "discord_members": 50000,
  "telegram_members": 30000,
  "github_stars": 5000,
  "github_commits_30d": 200,
  "community_sentiment": "positive/neutral/negative",
  "community_activity_score": 0.75
}}
"""

        result = await self._call_llm(prompt)

        return CommunityMetrics(**result)

    async def _analyze_market(
        self,
        target: Dict[str, Any],
        project_info: ProjectInfo
    ) -> MarketAnalysis:
        """市场分析"""
        # Mock实现 - 实际应该调用CoinGecko/CoinMarketCap API
        query = f"{project_info.symbol} price market cap volume"
        search_results = await self._web_search(query, max_results=3)

        prompt = f"""基于搜索结果,分析市场数据。

**项目**: {project_info.symbol}

**搜索结果**:
{self._format_search_results(search_results)}

**输出格式**(严格JSON):
{{
  "market_cap": 1000000000.0,
  "fully_diluted_valuation": 2000000000.0,
  "volume_24h": 50000000.0,
  "price_change_7d": 5.2,
  "price_change_30d": -10.5,
  "ath": 100.0,
  "ath_change_percentage": -60.0,
  "market_rank": 50,
  "liquidity_score": 0.8
}}
"""

        result = await self._call_llm(prompt)

        return MarketAnalysis(**result)

    async def _assess_risks(
        self,
        technical: TechnicalAnalysis,
        team: TeamAnalysis,
        tokenomics: TokenomicsDeepAnalysis,
        community: CommunityMetrics,
        market: MarketAnalysis
    ) -> RiskAssessment:
        """综合风险评估"""
        # 基于各模块评分计算风险
        tech_risk_score = 1 - technical.security_score
        team_risk_score = 1 - team.team_credibility_score
        tokenomics_risk_score = 1 - tokenomics.tokenomics_score
        market_risk_score = 1 - market.liquidity_score

        overall_risk_score = (
            tech_risk_score * 0.3 +
            team_risk_score * 0.25 +
            tokenomics_risk_score * 0.25 +
            market_risk_score * 0.20
        )

        # 确定风险等级
        if overall_risk_score >= 0.7:
            risk_level = "CRITICAL"
        elif overall_risk_score >= 0.5:
            risk_level = "HIGH"
        elif overall_risk_score >= 0.3:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return RiskAssessment(
            smart_contract_risk="LOW" if technical.smart_contract_audited else "HIGH",
            regulatory_risk="HIGH",  # 加密货币监管风险普遍较高
            market_risk="HIGH" if market_risk_score > 0.5 else "MEDIUM",
            team_risk="LOW" if team.team_credibility_score > 0.7 else "MEDIUM",
            technology_risk="LOW" if technical.security_score > 0.7 else "MEDIUM",
            overall_risk_level=risk_level,
            risk_score=overall_risk_score
        )

    def _synthesize_analysis(
        self,
        technical: TechnicalAnalysis,
        team: TeamAnalysis,
        tokenomics: TokenomicsDeepAnalysis,
        community: CommunityMetrics,
        market: MarketAnalysis,
        risk: RiskAssessment
    ) -> tuple:
        """综合分析,生成评分和建议"""
        # 加权计算总分
        overall_score = (
            technical.security_score * 0.25 +
            team.team_credibility_score * 0.20 +
            tokenomics.tokenomics_score * 0.25 +
            community.community_activity_score * 0.15 +
            market.liquidity_score * 0.15
        )

        # 根据评分和风险确定建议
        if overall_score >= 0.80 and risk.overall_risk_level in ["LOW", "MEDIUM"]:
            recommendation = "STRONG_BUY"
        elif overall_score >= 0.70 and risk.overall_risk_level != "CRITICAL":
            recommendation = "BUY"
        elif overall_score >= 0.60:
            recommendation = "HOLD"
        elif overall_score >= 0.50:
            recommendation = "FURTHER_DD"
        else:
            recommendation = "PASS"

        # 识别优势和劣势
        strengths = []
        weaknesses = []

        if technical.security_score >= 0.75:
            strengths.append("技术安全性高")
        elif technical.security_score < 0.5:
            weaknesses.append("技术安全性存疑")

        if team.team_credibility_score >= 0.75:
            strengths.append("团队背景优秀")
        elif team.team_credibility_score < 0.5:
            weaknesses.append("团队可信度不足")

        if tokenomics.tokenomics_score >= 0.75:
            strengths.append("代币经济学设计合理")
        elif tokenomics.tokenomics_score < 0.5:
            weaknesses.append("代币经济学存在问题")

        if community.community_activity_score >= 0.75:
            strengths.append("社区活跃度高")
        elif community.community_activity_score < 0.5:
            weaknesses.append("社区活跃度低")

        if market.liquidity_score >= 0.75:
            strengths.append("市场流动性好")
        elif market.liquidity_score < 0.5:
            weaknesses.append("市场流动性不足")

        summary = f"综合评分{overall_score:.2f},风险等级{risk.overall_risk_level}。{recommendation}。"

        return overall_score, recommendation, strengths, weaknesses, summary

    async def _web_search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """网络搜索"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.web_search_url}/search",
                    json={"query": query, "max_results": max_results}
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("results", [])
        except Exception as e:
            print(f"[CryptoAnalystAgent] Web search failed: {e}")

        return []

    async def _call_llm(self, prompt: str) -> Dict[str, Any]:
        """调用LLM"""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.llm_gateway_url}/chat",
                    json={
                        "messages": [{"role": "user", "content": prompt}],
                        "response_format": "json",
                        "temperature": 0.3
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("content", {})
        except Exception as e:
            print(f"[CryptoAnalystAgent] LLM call failed: {e}")

        return {"error": "LLM调用失败"}

    def _format_search_results(self, results: List[Dict[str, Any]]) -> str:
        """格式化搜索结果"""
        if not results:
            return "无搜索结果"

        formatted = []
        for i, r in enumerate(results[:5], 1):
            formatted.append(f"{i}. {r.get('title', 'N/A')}\n   {r.get('content', '')[:200]}...")

        return "\n\n".join(formatted)

    def _fallback_technical(self) -> TechnicalAnalysis:
        """技术分析Fallback"""
        return TechnicalAnalysis(
            blockchain="unknown",
            code_quality_score=0.5,
            security_score=0.5,
            tech_innovation="数据不足",
            tech_risks=["分析失败,数据不足"]
        )

    def _fallback_team(self) -> TeamAnalysis:
        """团队分析Fallback"""
        return TeamAnalysis(
            team_background="数据不足",
            team_credibility_score=0.5,
            team_experience_score=0.5
        )

    def _fallback_tokenomics(self) -> TokenomicsDeepAnalysis:
        """代币经济学Fallback"""
        return TokenomicsDeepAnalysis(
            vesting_schedule="未知",
            value_capture="数据不足",
            tokenomics_score=0.5
        )

    def _fallback_community(self) -> CommunityMetrics:
        """社区分析Fallback"""
        return CommunityMetrics(
            community_sentiment="neutral",
            community_activity_score=0.5
        )

    def _fallback_market(self) -> MarketAnalysis:
        """市场分析Fallback"""
        return MarketAnalysis(
            liquidity_score=0.5
        )

    def _fallback_result(self, target: Dict[str, Any]) -> CryptoAnalysisResult:
        """完整Fallback结果"""
        symbol = target.get('symbol', 'UNKNOWN').upper()

        return CryptoAnalysisResult(
            project_info=ProjectInfo(
                project_name=target.get('project_name', symbol),
                symbol=symbol,
                category="Unknown",
                description="分析失败,数据不足"
            ),
            technical_analysis=self._fallback_technical(),
            team_analysis=self._fallback_team(),
            tokenomics=self._fallback_tokenomics(),
            community_metrics=self._fallback_community(),
            market_analysis=self._fallback_market(),
            risk_assessment=RiskAssessment(
                smart_contract_risk="UNKNOWN",
                regulatory_risk="HIGH",
                market_risk="HIGH",
                team_risk="UNKNOWN",
                technology_risk="UNKNOWN",
                overall_risk_level="HIGH",
                risk_score=0.7
            ),
            overall_score=0.5,
            investment_recommendation="PASS",
            key_strengths=[],
            key_weaknesses=["分析失败,数据不足"],
            summary="自动分析失败,需要人工复核"
        )
