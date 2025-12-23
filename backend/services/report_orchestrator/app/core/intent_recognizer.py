"""
Intent Recognition System for V4
意图识别系统

Hybrid approach:
1. Keyword matching (<10ms)
2. Regex pattern matching (<20ms)
3. LLM classification (~300ms) as fallback

Target accuracy: 85%+
"""
import re
from typing import Dict, List, Tuple
from enum import Enum
from pydantic import BaseModel
import httpx


class IntentType(str, Enum):
    """User intent types"""
    DD_ANALYSIS = "dd_analysis"           # 完整投资尽调
    QUICK_OVERVIEW = "quick_overview"      # 快速概览
    FREE_CHAT = "free_chat"                # 自由对话
    UPLOAD_BP = "upload_bp"                # 上传BP
    ASK_QUESTION = "ask_question"          # 提问
    UNKNOWN = "unknown"                     # 未知意图


class Intent(BaseModel):
    """Recognized intent"""
    type: IntentType
    confidence: float  # 0.0 - 1.0
    extracted_entities: Dict[str, str] = {}  # e.g., {"company_name": "水杉智算"}
    raw_input: str


class IntentRecognizer:
    """
    Hybrid intent recognizer
    混合意图识别器
    """

    # Intent patterns definition
    INTENT_PATTERNS = {
        IntentType.DD_ANALYSIS: {
            "keywords": [
                "分析", "尽调", "DD", "投资", "调研",
                "尽职调查", "投资分析", "深度分析"
            ],
            "patterns": [
                r".*分析.*公司",
                r".*尽调.*",
                r".*投资.*建议",
                r".*DD.*分析",
                r".*调研.*项目",
                r".*评估.*公司"
            ]
        },
        IntentType.QUICK_OVERVIEW: {
            "keywords": [
                "快速", "简单", "概览", "简介",
                "了解一下", "看看", "查询"
            ],
            "patterns": [
                r".*快速.*了解",
                r".*简单.*介绍",
                r".*概览.*",
                r".*怎么样",
                r".*了解一下",
                r"简单.*看看"
            ]
        },
        IntentType.FREE_CHAT: {
            "keywords": [
                "聊聊", "问", "请问", "咨询",
                "什么是", "如何", "为什么"
            ],
            "patterns": [
                r"^聊.*",
                r"^问.*",
                r".*是什么",
                r".*如何.*",
                r".*为什么.*",
                r".*怎么.*"
            ]
        },
        IntentType.UPLOAD_BP: {
            "keywords": [
                "上传", "BP", "商业计划书",
                "文件", "附件"
            ],
            "patterns": [
                r".*上传.*BP",
                r".*BP.*文件",
                r".*商业计划书"
            ]
        },
        IntentType.ASK_QUESTION: {
            "keywords": [
                "?", "？", "吗", "呢",
                "多少", "哪些", "哪个"
            ],
            "patterns": [
                r".*[?？]$",
                r".*吗$",
                r".*呢$",
                r"^多少.*",
                r"^哪些.*",
                r"^哪个.*"
            ]
        }
    }

    def __init__(self, llm_gateway_url: str = "http://llm_gateway:8003"):
        self.llm_gateway_url = llm_gateway_url

    async def recognize(self, user_input: str) -> Intent:
        """
        Recognize user intent using hybrid approach
        识别用户意图（混合方案）

        Args:
            user_input: User's text input

        Returns:
            Intent object with type, confidence, and extracted entities
        """
        user_input = user_input.strip()

        # Special rule: If input is short and looks like a company name,
        # treat as DD_ANALYSIS (most common user intent)
        if len(user_input) <= 15 and len(user_input) >= 2:
            # Check if it's likely a company name (no special keywords)
            has_action_keyword = any(
                kw in user_input.lower()
                for kw in ['什么', '如何', '为什么', '?', '？', '聊', '问']
            )
            if not has_action_keyword:
                # Likely a company name - default to DD_ANALYSIS
                return self._build_intent(
                    intent_type=IntentType.DD_ANALYSIS,
                    confidence=0.75,
                    raw_input=user_input
                )

        # Stage 1: Fast keyword matching
        keyword_result = self._match_keywords(user_input)
        if keyword_result[1] >= 0.8:  # High confidence from keywords
            return self._build_intent(
                intent_type=keyword_result[0],
                confidence=keyword_result[1],
                raw_input=user_input
            )

        # Stage 2: Regex pattern matching
        regex_result = self._match_patterns(user_input)
        if regex_result[1] >= 0.7:  # Medium-high confidence from patterns
            return self._build_intent(
                intent_type=regex_result[0],
                confidence=regex_result[1],
                raw_input=user_input
            )

        # Stage 3: LLM classification (fallback)
        llm_result = await self._llm_classify(user_input)
        return self._build_intent(
            intent_type=llm_result[0],
            confidence=llm_result[1],
            raw_input=user_input
        )

    def _match_keywords(self, text: str) -> Tuple[IntentType, float]:
        """
        Fast keyword matching
        快速关键词匹配
        """
        text_lower = text.lower()
        scores = {}

        for intent_type, config in self.INTENT_PATTERNS.items():
            keywords = config.get("keywords", [])
            if not keywords:
                continue

            # Count keyword matches
            matches = sum(1 for kw in keywords if kw.lower() in text_lower)
            if matches > 0:
                # Confidence based on match count
                confidence = min(matches / len(keywords) * 1.5, 1.0)
                scores[intent_type] = confidence

        if scores:
            best_intent = max(scores.items(), key=lambda x: x[1])
            return best_intent[0], best_intent[1]

        return IntentType.UNKNOWN, 0.0

    def _match_patterns(self, text: str) -> Tuple[IntentType, float]:
        """
        Regex pattern matching
        正则模式匹配
        """
        for intent_type, config in self.INTENT_PATTERNS.items():
            patterns = config.get("patterns", [])

            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    # Pattern match gives 0.7-0.9 confidence
                    return intent_type, 0.8

        return IntentType.UNKNOWN, 0.0

    async def _llm_classify(self, text: str) -> Tuple[IntentType, float]:
        """
        LLM-based intent classification (fallback)
        基于LLM的意图分类（兜底方案）
        """
        try:
            prompt = f"""作为AI投研助手，请分析用户的意图并分类。

用户输入: "{text}"

请从以下意图中选择最匹配的一个：
1. dd_analysis - 用户想要完整的投资尽职调查分析
2. quick_overview - 用户只想快速了解概况
3. free_chat - 用户想要自由对话或提问
4. upload_bp - 用户想要上传BP文件
5. ask_question - 用户在提问

请只返回意图类型（如 "dd_analysis"），不要其他内容。"""

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.llm_gateway_url}/chat",
                    json={
                        "history": [
                            {"role": "user", "parts": [prompt]}
                        ]
                    }
                )

                if response.status_code == 200:
                    content = response.json().get("content", "").strip().lower()

                    # Parse LLM response
                    for intent_type in IntentType:
                        if intent_type.value in content:
                            return intent_type, 0.85  # LLM classification confidence

        except Exception as e:
            print(f"[IntentRecognizer] LLM classification failed: {e}")

        # Default to free_chat if uncertain
        return IntentType.FREE_CHAT, 0.5

    def _build_intent(
        self,
        intent_type: IntentType,
        confidence: float,
        raw_input: str
    ) -> Intent:
        """
        Build Intent object with entity extraction
        构建Intent对象并提取实体
        """
        entities = self._extract_entities(raw_input, intent_type)

        return Intent(
            type=intent_type,
            confidence=confidence,
            extracted_entities=entities,
            raw_input=raw_input
        )

    def _extract_entities(self, text: str, intent_type: IntentType) -> Dict[str, str]:
        """
        Extract entities from text based on intent
        根据意图从文本中提取实体
        """
        entities = {}

        # Extract company name for DD/overview intents
        if intent_type in [IntentType.DD_ANALYSIS, IntentType.QUICK_OVERVIEW]:
            # Simple heuristic: extract quoted strings or capitalized words
            # Example: "分析水杉智算" -> company_name: "水杉智算"

            # Remove intent keywords
            cleaned = re.sub(r'(分析|尽调|DD|投资|调研|快速|了解|概览)', '', text)
            cleaned = cleaned.strip()

            if cleaned:
                entities["company_name"] = cleaned

        return entities


class ConversationManager:
    """
    Manages conversation flow and intent-based routing
    管理对话流程和基于意图的路由
    """

    def __init__(self, intent_recognizer: IntentRecognizer):
        self.recognizer = intent_recognizer

    async def process_message(self, user_input: str) -> Dict:
        """
        Process user message and return response with intent
        处理用户消息并返回包含意图的响应

        Returns:
            {
                "intent": Intent object,
                "response_type": "confirm_intent" | "direct_action",
                "options": [...]  # For confirm_intent
            }
        """
        # Recognize intent
        intent = await self.recognizer.recognize(user_input)

        # Build response based on intent
        if intent.confidence < 0.6:
            # Low confidence - ask for clarification
            return {
                "intent": intent,
                "response_type": "clarify",
                "message": "抱歉，我不太确定您的意图。您可以选择以下服务：",
                "options": self._build_service_options()
            }

        elif intent.type == IntentType.DD_ANALYSIS:
            # High confidence DD analysis - confirm before starting
            company_name = intent.extracted_entities.get("company_name", "该公司")

            return {
                "intent": intent,
                "response_type": "confirm_intent",
                "message": f"我理解您想了解「{company_name}」。我可以为您提供：",
                "options": [
                    {
                        "id": "full_dd",
                        "title": "📊 完整投资尽调分析",
                        "description": "全面的团队、市场、风险分析（3-5分钟）",
                        "action": "start_dd_analysis"
                    },
                    {
                        "id": "quick",
                        "title": "⚡ 快速概览",
                        "description": "基础信息和快速评估（30秒）",
                        "action": "quick_overview"
                    },
                    {
                        "id": "chat",
                        "title": "💬 自由对话",
                        "description": "通过对话深入了解特定方面",
                        "action": "free_chat"
                    }
                ],
                "suggested_action": "full_dd",  # Default suggestion
                "file_upload_hint": "💡 上传BP文件可获得更精准的分析"
            }

        elif intent.type == IntentType.QUICK_OVERVIEW:
            # Quick overview - also show options for user to choose
            company_name = intent.extracted_entities.get("company_name", "该公司")

            return {
                "intent": intent,
                "response_type": "confirm_intent",
                "message": f"我理解您想了解「{company_name}」。我可以为您提供：",
                "options": [
                    {
                        "id": "full_dd",
                        "title": "📊 完整投资尽调分析",
                        "description": "全面的团队、市场、风险分析（3-5分钟）",
                        "action": "start_dd_analysis"
                    },
                    {
                        "id": "quick",
                        "title": "⚡ 快速概览",
                        "description": "基础信息和快速评估（30秒）",
                        "action": "quick_overview"
                    },
                    {
                        "id": "chat",
                        "title": "💬 自由对话",
                        "description": "通过对话深入了解特定方面",
                        "action": "free_chat"
                    }
                ],
                "suggested_action": "quick",  # Default to quick for this intent
                "file_upload_hint": "💡 上传BP文件可获得更精准的分析"
            }

        elif intent.type == IntentType.FREE_CHAT:
            # Free chat mode
            return {
                "intent": intent,
                "response_type": "chat_mode",
                "message": "好的，我会尽力回答您的问题。请问有什么我可以帮助您的？"
            }

        else:
            # Other intents
            return {
                "intent": intent,
                "response_type": "info",
                "message": "我理解了。还有什么我可以帮助您的吗？",
                "options": self._build_service_options()
            }

    def _build_service_options(self) -> List[Dict]:
        """Build standard service option list"""
        return [
            {
                "id": "full_dd",
                "title": "📊 完整投资尽调",
                "description": "全面分析团队、市场、风险",
                "action": "start_dd_analysis"
            },
            {
                "id": "quick",
                "title": "⚡ 快速概览",
                "description": "30秒了解基本情况",
                "action": "quick_overview"
            },
            {
                "id": "chat",
                "title": "💬 自由对话",
                "description": "提问和深入讨论",
                "action": "free_chat"
            }
        ]
