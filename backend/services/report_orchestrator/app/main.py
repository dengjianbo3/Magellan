# backend/services/report_orchestrator/app/main.py
import httpx
import asyncio
import json
import re
import os
import base64
import uuid
import time
import hashlib
from collections import OrderedDict
from copy import deepcopy
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Set

# V2 models (keep for backward compatibility)
from .models.dd_models import (
    DDSessionContext,
)

# V3: Import state machine
from .core.dd_state_machine import DDStateMachine

# V4: Import intent recognition and conversation management
from .core.intent_recognizer import IntentRecognizer, ConversationManager

# V5: Import Redis session store
from .core.session_store import SessionStore
from .core.auth import CurrentUser, get_current_user, resolve_user_from_token

# Phase 4: Import API routers
from .api.routers import health_router, reports_router
from .api.routers.agents import router as agents_router
from .api.routers.knowledge import router as knowledge_router, set_vector_store, set_rag_service
from .api.routers.roundtable import (
    router as roundtable_router,
    set_active_meetings,
    set_llm_gateway_url,
    set_roundtable_sessions,
)
from .api.routers.files import router as files_router
from .api.routers.analysis import router as analysis_router, set_analysis_runtime_starter
from .api.routers.export import router as export_router, set_get_report_func
from .api.routers.dd_workflow import router as dd_workflow_router, set_session_funcs
from .api.routers.monitoring import router as monitoring_router
from .api.routers.trading_mode import router as trading_mode_router
from .api.trading_routes import router as trading_router
from .middleware import RequestLoggingMiddleware, CachingMiddleware

# Phase 4: Import storage services
from .services.storage import init_report_storage

# Phase 2: Prometheus metrics
from prometheus_fastapi_instrumentator import Instrumentator

# Phase 2: Structured logging
from .core.logging_config import configure_logging, get_logger

# Phase 2: Knowledge Base services
from .services.vector_store import VectorStoreService
from .services.rag_service import RAGService
from .core.memory import format_memory_hits, get_memory_store
from .core.memory.governance import compact_text, make_provenance_metadata, should_persist_memory
from .core.model_policy import resolve_model_for_role
from .core.orchestration_templates import get_orchestration_templates
from .core.skills import build_skill_instruction_context
from .core.expert_chat import (
    build_execution_stages,
    extract_specialist_response,
    format_shared_evidence_context,
)
from .core.metrics import (
    record_cache_event,
    record_llm_context_usage,
    record_route_decision,
)
from .core.observability.metrics_snapshot import MetricsSnapshotCache

# Configure logging (JSON in production, console in development)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
JSON_LOGS = os.getenv("JSON_LOGS", "false").lower() == "true"
configure_logging(log_level=LOG_LEVEL, json_logs=JSON_LOGS)
logger = get_logger(__name__)
atomic_memory_store = get_memory_store()
ATOMIC_MEMORY_TOP_K = max(1, int(os.getenv("ATOMIC_MEMORY_TOP_K", "3")))

# --- Service Discovery (prefer env, fall back to docker-compose internal DNS names) ---
# docker-compose uses PUBLIC_DATA_URL to point at external_data_service
EXTERNAL_DATA_URL = os.getenv("PUBLIC_DATA_URL", os.getenv("EXTERNAL_DATA_URL", "http://external_data_service:8006"))
LLM_GATEWAY_URL = os.getenv("LLM_GATEWAY_URL", "http://llm_gateway:8003")
FILE_SERVICE_URL = os.getenv("FILE_SERVICE_URL", "http://file_service:8001")

# --- Check Standalone Mode ---
STANDALONE_MODE = os.getenv("STANDALONE_MODE", "false").lower() == "true"

# Expert chat defaults
ORCHESTRATION_TEMPLATES = get_orchestration_templates()
_EXPERT_CHAT_TEMPLATE = ORCHESTRATION_TEMPLATES.get("expert_chat", {})
_ROUNDTABLE_TEMPLATE = ORCHESTRATION_TEMPLATES.get("roundtable", {})

EXPERT_CHAT_PROVIDER = os.getenv("EXPERT_CHAT_PROVIDER", "gemini")
EXPERT_CHAT_MAX_HISTORY = int(os.getenv("EXPERT_CHAT_MAX_HISTORY", str(_EXPERT_CHAT_TEMPLATE.get("max_history", 24))))
EXPERT_CHAT_MAX_ATTACHMENTS = int(os.getenv("EXPERT_CHAT_MAX_ATTACHMENTS", str(_EXPERT_CHAT_TEMPLATE.get("max_attachments", 3))))
EXPERT_CHAT_MAX_ATTACHMENT_BYTES = int(
    os.getenv(
        "EXPERT_CHAT_MAX_ATTACHMENT_BYTES",
        str(_EXPERT_CHAT_TEMPLATE.get("max_attachment_bytes", 6 * 1024 * 1024)),
    )
)
EXPERT_CHAT_LEADER_FOLLOWUP_AFTER_DELEGATION = os.getenv(
    "EXPERT_CHAT_LEADER_FOLLOWUP_AFTER_DELEGATION",
    str(_EXPERT_CHAT_TEMPLATE.get("leader_followup_after_delegation", False)).lower(),
).lower() == "true"
EXPERT_CHAT_AGENT_TURN_TIMEOUT_SECONDS = int(
    os.getenv(
        "EXPERT_CHAT_AGENT_TURN_TIMEOUT_SECONDS",
        str(_EXPERT_CHAT_TEMPLATE.get("turn_timeout_seconds", 600)),
    )
)
EXPERT_CHAT_ROUTE_CACHE_ENABLED = os.getenv("EXPERT_CHAT_ROUTE_CACHE_ENABLED", "true").lower() == "true"
EXPERT_CHAT_ROUTE_CACHE_TTL_SECONDS = max(5, int(os.getenv("EXPERT_CHAT_ROUTE_CACHE_TTL_SECONDS", "30")))
EXPERT_CHAT_ROUTE_CACHE_MAX_ENTRIES = max(32, int(os.getenv("EXPERT_CHAT_ROUTE_CACHE_MAX_ENTRIES", "512")))
EXPERT_CHAT_MAX_PARALLEL_SPECIALISTS = max(
    1, int(os.getenv("EXPERT_CHAT_MAX_PARALLEL_SPECIALISTS", "2"))
)
EXPERT_CHAT_MEMORY_ASYNC_WRITE = os.getenv("EXPERT_CHAT_MEMORY_ASYNC_WRITE", "true").lower() == "true"
EXPERT_CHAT_MEMORY_WRITE_CONCURRENCY = max(
    1, int(os.getenv("EXPERT_CHAT_MEMORY_WRITE_CONCURRENCY", "4"))
)

# In-memory chat sessions (PoC scope)
active_chat_sessions: Dict[str, Dict[str, Any]] = {}
_leader_route_cache: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
_leader_route_cache_lock = asyncio.Lock()
_expert_chat_memory_write_sem = asyncio.Semaphore(EXPERT_CHAT_MEMORY_WRITE_CONCURRENCY)
_expert_chat_memory_tasks: Set[asyncio.Task] = set()

# --- Lifespan Handler for Kafka ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Startup: Initialize Kafka messaging (skip in standalone mode)
    if not STANDALONE_MODE:
        try:
            from .messaging import init_kafka, get_session_publisher, get_agent_service, get_llm_service
            await init_kafka()
            # Initialize session event publisher for WebSocket integration
            await get_session_publisher()
            # Phase 7: Initialize Agent and LLM message services
            agent_service = await get_agent_service()
            llm_service = await get_llm_service()
            logger.info("Kafka messaging initialized successfully (Agent + LLM services ready)")
        except Exception as e:
            logger.warning(f"Kafka initialization failed (will use HTTP fallback): {e}")
    else:
        logger.info("[STANDALONE] Skipping Kafka initialization")

    # Auto-start trading in standalone mode
    if STANDALONE_MODE:
        logger.info("STANDALONE_MODE detected, auto-starting trading system...")
        asyncio.create_task(_auto_start_trading())

    yield

    # Shutdown: Close Kafka connections (skip in standalone mode)
    if not STANDALONE_MODE:
        try:
            from .messaging import close_kafka
            await close_kafka()
            logger.info("Kafka messaging closed")
        except Exception as e:
            logger.warning(f"Error closing Kafka: {e}")


async def _auto_start_trading():
    """Auto-start trading system after a short delay to ensure all services are ready."""
    await asyncio.sleep(10)  # Wait for services to be ready
    try:
        from app.services.trading_system import get_trading_system
        logger.info("Auto-starting trading system...")
        system = await get_trading_system(user_id="system")
        await system.start()
        logger.info("Trading system auto-started successfully")
    except Exception as e:
        logger.error(f"Failed to auto-start trading system: {e}")


app = FastAPI(
    title="Orchestrator Agent Service",
    description="Manages the multi-agent workflow for generating investment reports (V2) and DD analysis (V3).",
    version="3.0.0",  # Updated for V3
    lifespan=lifespan
)

# --- CORS config ---
def _parse_cors_origins(raw: str):
    mobile_and_local_defaults = [
        "http://localhost",
        "https://localhost",
        "capacitor://localhost",
        "ionic://localhost",
        "http://localhost:5174",
        "http://localhost:8081",
    ]

    raw = (raw or "").strip()
    if not raw:
        return mobile_and_local_defaults
    if raw == "*" or raw.lower() == "all":
        return ["*"]
    parts = []
    if raw.startswith("["):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                parts = [str(p).strip() for p in parsed if str(p).strip()]
        except Exception:
            parts = []
    if not parts:
        parts = [p.strip() for p in raw.split(",") if p.strip()]

    for origin in mobile_and_local_defaults:
        if origin not in parts:
            parts.append(origin)
    return parts

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(
        os.getenv("CORS_ALLOW_ORIGINS") or os.getenv("CORS_ORIGINS", "")
    ),
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Response caching middleware (added after logging so cache hits are logged)
app.add_middleware(CachingMiddleware)

# Global storage for active meeting instances (for Human-in-the-Loop support)
active_meetings: Dict[str, Any] = {}
roundtable_sessions: Dict[str, Dict[str, Any]] = {}

# Phase 4: Initialize Roundtable Router dependencies
set_active_meetings(active_meetings)
set_roundtable_sessions(roundtable_sessions)
set_llm_gateway_url(LLM_GATEWAY_URL)
print("[main.py] ✅ Roundtable Router initialized")

# Phase 2: Initialize Prometheus metrics
Instrumentator().instrument(app)

# `/metrics` snapshot cache: avoid recomputing full exposition on every scrape under high load.
METRICS_SNAPSHOT_TTL_SECONDS = max(0.1, float(os.getenv("METRICS_SNAPSHOT_TTL_SECONDS", "2.0")))
_metrics_snapshot_cache = MetricsSnapshotCache(ttl_seconds=METRICS_SNAPSHOT_TTL_SECONDS)


@app.get("/metrics", include_in_schema=False, tags=["System (Phase 2)"])
async def metrics_snapshot() -> Response:
    return await _metrics_snapshot_cache.response()

# Phase 4: Include API Routers (新架构 - 完整迁移)
app.include_router(health_router, tags=["Health"])
app.include_router(reports_router, prefix="/api/reports", tags=["Reports"])
app.include_router(agents_router, prefix="/api/agents", tags=["Agents"])
app.include_router(knowledge_router, prefix="/api/knowledge", tags=["Knowledge Base"])
app.include_router(roundtable_router, prefix="/api/roundtable", tags=["Roundtable"])
app.include_router(files_router, prefix="/api", tags=["File Upload"])
app.include_router(analysis_router, prefix="/api/v2/analysis", tags=["Analysis V2"])
app.include_router(export_router, prefix="/api/reports", tags=["Report Export"])
app.include_router(dd_workflow_router, prefix="/api/dd", tags=["DD Workflow"])
app.include_router(monitoring_router, prefix="/api/errors", tags=["Monitoring"])
app.include_router(trading_router, tags=["Auto Trading"])
app.include_router(trading_mode_router, tags=["Trading Mode"])

# --- Pydantic Models ---
class AnalysisRequest(BaseModel):
    ticker: str

class ContinueRequest(BaseModel):
    session_id: str
    selected_ticker: str

class Step(BaseModel):
    id: int
    title: str
    status: str # 'running', 'success', 'error', 'paused'
    result: str | None = None
    options: List[Dict[str, Any]] | None = None # For HITL

class ReportSection(BaseModel):
    section_title: str
    content: str

class FinancialChartData(BaseModel):
    years: List[int]
    revenues: List[float]
    profits: List[float]

class FullReportResponse(BaseModel):
    company_ticker: str
    report_sections: List[ReportSection]
    financial_chart_data: Optional[FinancialChartData] = None

class InstantFeedbackRequest(BaseModel):
    analysis_context: str
    user_input: str

class InstantFeedbackResponse(BaseModel):
    feedback: str

class AnalysisResponse(BaseModel):
    session_id: str
    status: str # 'in_progress', 'hitl_required', 'completed', 'error', 'hitl_follow_up_required'
    steps: List[Step]
    preliminary_report: Optional[FullReportResponse] = None
    key_questions: Optional[List[str]] = None


# --- Helper Functions ---
async def call_llm_gateway(
    client: httpx.AsyncClient,
    history: List[Dict[str, Any]],
    model: Optional[str] = None,
) -> str:
    safe_model = str(model or "gateway_default")
    prompt_texts: List[str] = []
    for item in history or []:
        if not isinstance(item, dict):
            continue
        parts = item.get("parts")
        if isinstance(parts, list):
            prompt_texts.extend([str(part) for part in parts if part is not None])
        elif item.get("content"):
            prompt_texts.append(str(item.get("content")))

    try:
        payload: Dict[str, Any] = {"history": history}
        if model:
            payload["model"] = model
        response = await client.post(f"{LLM_GATEWAY_URL}/chat", json=payload)
        if response.status_code == 200:
            try:
                parsed = response.json()
                content = str(parsed.get("content", ""))
                record_llm_context_usage(
                    source="legacy_chat",
                    model=safe_model,
                    usage=parsed.get("usage"),
                    prompt_texts=prompt_texts,
                    completion_text=content,
                )
                return content
            except (json.JSONDecodeError, KeyError):
                return '["Error: LLM returned invalid JSON."]'
        else:
            return f'["Error: LLM Gateway returned status code {response.status_code}"]'
    except Exception as e:
        return f'["Error: Could not connect to LLM Gateway: {e}"]'


def _fallback_roundtable_title(topic: str, language: str) -> str:
    topic = (topic or "").strip()
    if not topic:
        return "头脑风暴纪要" if language == "zh" else "Brainstorm Minutes"

    if language == "zh":
        max_len = 22
        return topic if len(topic) <= max_len else (topic[:max_len] + "...")

    words = topic.split()
    if len(words) <= 10:
        return topic
    return " ".join(words[:10]) + "..."


def _clean_llm_title_candidate(raw_text: str) -> str:
    text = (raw_text or "").strip()
    if not text:
        return ""

    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list) and parsed:
                text = str(parsed[0]).strip()
        except Exception:
            pass

    text = text.replace("```", "").strip()
    if "\n" in text:
        text = text.splitlines()[0].strip()

    for prefix in ("title:", "标题：", "标题:"):
        if text.lower().startswith(prefix.lower()):
            text = text[len(prefix):].strip()

    text = text.lstrip("#*- ").strip().strip('"').strip("'")
    text = " ".join(text.split())
    return text


def _prepend_original_topic_to_minutes(meeting_minutes: str, topic: str, language: str) -> str:
    minutes = (meeting_minutes or "").strip()
    source_topic = (topic or "").strip()
    if not source_topic:
        return minutes

    if language == "zh":
        header = "## 原始讨论课题"
        body = (
            f"{header}\n\n{source_topic}\n\n"
            "---\n\n"
        )
    else:
        header = "## Original Discussion Topic"
        body = (
            f"{header}\n\n{source_topic}\n\n"
            "---\n\n"
        )

    if minutes.startswith(header):
        return minutes
    return body + minutes


async def _generate_roundtable_report_title(topic: str, meeting_minutes: str, language: str) -> str:
    fallback = _fallback_roundtable_title(topic, language)
    minutes_preview = (meeting_minutes or "").strip()[:1800]

    if language == "zh":
        prompt = f"""请为这次头脑风暴生成一个简洁专业的报告标题。

要求：
1. 12-22个中文字符，尽量避免超过22个字符
2. 不要换行，不要引号，不要 Markdown，不要序号
3. 不要照搬原始课题的超长句子，要提炼“核心主题”
4. 只输出标题文本

原始课题：
{topic}

会议纪要摘要：
{minutes_preview}
"""
    else:
        prompt = f"""Create a concise and professional report title for this brainstorm session.

Requirements:
1. 5-10 words
2. Single line only, no quotes, no markdown, no numbering
3. Summarize the core theme instead of copying the long raw topic
4. Return title text only

Original topic:
{topic}

Meeting minutes excerpt:
{minutes_preview}
"""

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            candidate = await call_llm_gateway(
                client,
                [{"role": "user", "parts": [prompt]}],
                model=resolve_model_for_role("roundtable_summary"),
            )
        cleaned = _clean_llm_title_candidate(candidate)
        if not cleaned:
            return fallback
        if language == "zh" and len(cleaned) > 30:
            return fallback
        return cleaned
    except Exception as e:
        logger.warning(f"[ROUNDTABLE] Failed to summarize report title, using fallback: {e}")
        return fallback


class WebSocketMessage(BaseModel):
    """Standard message format for WebSocket communication."""
    session_id: str
    status: str
    step: Optional[Step] = None
    preliminary_report: Optional[FullReportResponse] = None
    key_questions: Optional[List[str]] = None

USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user_service:8008")

class UserPersona(BaseModel):
    investment_style: Optional[str] = "Balanced"
    risk_tolerance: Optional[str] = "Medium"


# ============================================================================
# Expert Chat Hub Helpers
# ============================================================================

def _registry_to_chat_id(agent_id: str) -> str:
    return str(agent_id or "").strip().replace("_", "-")


def _build_expert_chat_catalog() -> tuple[Dict[str, Dict[str, Any]], Dict[str, str], Dict[str, str]]:
    from .core.agent_registry import get_registry

    registry = get_registry()
    profiles: Dict[str, Dict[str, Any]] = {}
    registry_ids: Dict[str, str] = {}
    alias_map: Dict[str, str] = {}

    all_agents = registry.list_specialists(scope="roundtable")
    for cfg in all_agents:
        registry_id = str(cfg.get("agent_id") or "").strip()
        if not registry_id:
            continue
        if registry_id in {"bp_parser", "report_synthesizer"}:
            continue

        chat_id = _registry_to_chat_id(registry_id)
        name = cfg.get("name") if isinstance(cfg.get("name"), dict) else {}
        desc = cfg.get("description") if isinstance(cfg.get("description"), dict) else {}
        name_zh = str(name.get("zh") or chat_id)
        name_en = str(name.get("en") or chat_id)
        role_zh = str(desc.get("zh") or "专家")
        role_en = str(desc.get("en") or "Expert")

        aliases = {
            chat_id.lower(),
            registry_id.lower(),
            name_zh.lower(),
            name_en.lower(),
            _registry_to_chat_id(name_en).lower(),
        }
        if registry_id == "leader":
            aliases.update({"host", "主持人", "主理人", "主agent", "leader"})

        profiles[chat_id] = {
            "name_zh": name_zh,
            "name_en": name_en,
            "role_zh": role_zh,
            "role_en": role_en,
            "aliases": sorted([a for a in aliases if a]),
        }
        registry_ids[chat_id] = registry_id

    # Keep leader first, preserve yaml order for others.
    ordered_profiles: Dict[str, Dict[str, Any]] = {}
    if "leader" in profiles:
        ordered_profiles["leader"] = profiles.pop("leader")
    ordered_profiles.update(profiles)

    ordered_registry_ids: Dict[str, str] = {}
    if "leader" in registry_ids:
        ordered_registry_ids["leader"] = registry_ids.pop("leader")
    ordered_registry_ids.update(registry_ids)

    for chat_id, profile in ordered_profiles.items():
        alias_map[chat_id.lower()] = chat_id
        for alias in profile.get("aliases", []):
            alias_map[str(alias).strip().lower()] = chat_id

    return ordered_profiles, ordered_registry_ids, alias_map


EXPERT_CHAT_AGENT_PROFILES, EXPERT_CHAT_AGENT_REGISTRY_IDS, EXPERT_ALIAS_TO_AGENT = _build_expert_chat_catalog()
EXPERT_SPECIALIST_IDS = [k for k in EXPERT_CHAT_AGENT_PROFILES.keys() if k != "leader"]


def _is_zh(language: str) -> bool:
    return str(language or "").lower().startswith("zh")


def _expert_chat_registry_language(language: str) -> str:
    return "zh" if _is_zh(language) else "en"


def _normalize_expert_chat_knowledge_category(category: str) -> str:
    try:
        from .core.roundtable.mcp_tools import normalize_knowledge_category

        normalized = normalize_knowledge_category(category)
        return normalized or "all"
    except Exception:
        raw = str(category or "").strip().lower()
        if raw in {"general", "financial", "market", "legal"}:
            return raw
        return "all"


def _build_expert_chat_pool_signature(
    language: str,
    knowledge_enabled: bool,
    knowledge_category: str,
) -> str:
    return "|".join(
        [
            _expert_chat_registry_language(language),
            "1" if knowledge_enabled else "0",
            _normalize_expert_chat_knowledge_category(knowledge_category),
        ]
    )


def _create_expert_chat_agent_pool(
    language: str,
    knowledge_enabled: bool,
    knowledge_category: str,
    user_id: str = "",
    session_id: str = "",
) -> Dict[str, Any]:
    from .core.agent_registry import get_registry
    from .core.roundtable.mcp_tools import (
        reset_roundtable_knowledge_preferences,
        set_roundtable_knowledge_preferences,
    )

    registry = get_registry()
    registry_language = _expert_chat_registry_language(language)
    normalized_category = _normalize_expert_chat_knowledge_category(knowledge_category)
    category_for_tool = None if normalized_category == "all" else normalized_category

    token = set_roundtable_knowledge_preferences(
        enabled=knowledge_enabled,
        category=category_for_tool,
    )

    pool: Dict[str, Any] = {}
    try:
        for chat_agent_id, registry_agent_id in EXPERT_CHAT_AGENT_REGISTRY_IDS.items():
            try:
                create_kwargs: Dict[str, Any] = {"language": registry_language}
                if registry_agent_id != "leader":
                    create_kwargs["quick_mode"] = False
                agent = registry.create_agent(
                    registry_agent_id,
                    **create_kwargs,
                )
                setattr(agent, "user_id", str(user_id or "anonymous"))
                setattr(agent, "session_id", str(session_id or ""))
                setattr(agent, "atomic_agent_id", chat_agent_id)
                pool[chat_agent_id] = agent
            except Exception as create_error:
                logger.exception(
                    "[ExpertChat] Failed to create agent '%s' from registry id '%s': %s",
                    chat_agent_id,
                    registry_agent_id,
                    create_error,
                )
    finally:
        reset_roundtable_knowledge_preferences(token)

    return pool


def _ensure_expert_chat_agent_pool(
    session_state: Dict[str, Any],
    language: str,
    knowledge_enabled: bool,
    knowledge_category: str,
    user_id: str = "",
    session_id: str = "",
) -> Dict[str, Any]:
    signature = _build_expert_chat_pool_signature(
        language=language,
        knowledge_enabled=knowledge_enabled,
        knowledge_category=knowledge_category,
    )

    existing = session_state.get("agents")
    if isinstance(existing, dict) and session_state.get("agent_pool_signature") == signature:
        for agent_id, agent in existing.items():
            setattr(agent, "user_id", str(user_id or "anonymous"))
            setattr(agent, "session_id", str(session_id or ""))
            setattr(agent, "atomic_agent_id", str(agent_id))
        return existing

    pool = _create_expert_chat_agent_pool(
        language=language,
        knowledge_enabled=knowledge_enabled,
        knowledge_category=knowledge_category,
        user_id=user_id,
        session_id=session_id,
    )
    session_state["agents"] = pool
    session_state["agent_pool_signature"] = signature
    return pool


def _display_agent_name(agent_id: str, language: str) -> str:
    profile = EXPERT_CHAT_AGENT_PROFILES.get(agent_id, {})
    if _is_zh(language):
        return profile.get("name_zh", agent_id)
    return profile.get("name_en", agent_id)


def _build_expert_chat_agents(language: str) -> List[Dict[str, str]]:
    agents: List[Dict[str, str]] = []
    for agent_id, profile in EXPERT_CHAT_AGENT_PROFILES.items():
        agents.append(
            {
                "id": agent_id,
                "name": profile.get("name_zh") if _is_zh(language) else profile.get("name_en"),
                "role": profile.get("role_zh") if _is_zh(language) else profile.get("role_en"),
            }
        )
    return agents


def _extract_mentions(content: str) -> List[str]:
    if not content:
        return []
    candidates = re.findall(r"@([^\s@,，。:：;；!?？]+)", content)
    targets: List[str] = []
    for raw in candidates:
        token = str(raw).strip().lower()
        agent_id = EXPERT_ALIAS_TO_AGENT.get(token)
        if agent_id and agent_id not in targets:
            targets.append(agent_id)
    return targets


def _format_history_window(history: List[Dict[str, Any]], limit: int = 12) -> str:
    window = history[-limit:] if history else []
    if not window:
        return "(empty)"
    lines: List[str] = []
    for msg in window:
        speaker = msg.get("speaker", "Unknown")
        role = str(msg.get("role", "")).lower()
        if role == "assistant":
            # Keep assistant context compact to reduce repeated token replay.
            body = str(msg.get("content_summary") or msg.get("content") or "").strip()[:360]
        else:
            body = str(msg.get("content") or "").strip()[:700]
        if not body:
            continue
        lines.append(f"- [{speaker}] {body}")
    return "\n".join(lines) if lines else "(empty)"


def _rebuild_shared_evidence_board_from_history(
    history: List[Dict[str, Any]],
    max_items: int = 16,
) -> List[Dict[str, Any]]:
    board: List[Dict[str, Any]] = []
    for msg in history[-max_items:]:
        if str(msg.get("role", "")).lower() != "assistant":
            continue
        summary = str(msg.get("content_summary") or "").strip()
        if not summary:
            content = str(msg.get("content") or "").strip().replace("\n", " ")
            summary = compact_text(content, max_chars=220)
        if not summary:
            continue
        board.append(
            {
                "agent_id": str(msg.get("agent_id") or "").strip(),
                "agent_name": str(msg.get("speaker") or msg.get("agent_id") or "Expert").strip(),
                "summary": summary,
                "key_points": [],
                "risks": [],
                "confidence": None,
            }
        )
    return board[-max_items:]


async def _build_expert_chat_memory_context(
    user_id: str,
    agent_id: str,
    user_message: str,
    history: List[Dict[str, Any]],
) -> str:
    query = " ".join(
        [
            str(user_message or "").strip(),
            str(history[-1].get("content", "")) if history else "",
        ]
    ).strip()[:1800]
    if not query:
        return ""
    try:
        agent_hits = await atomic_memory_store.query_agent_memory(
            user_id=str(user_id or "anonymous"),
            agent_id=str(agent_id),
            query=query,
            top_k=ATOMIC_MEMORY_TOP_K,
            collection="episodic",
        )
        shared_hits = await atomic_memory_store.query_shared_evidence(
            user_id=str(user_id or "anonymous"),
            query=query,
            top_k=max(1, ATOMIC_MEMORY_TOP_K - 1),
        )
    except Exception as e:
        logger.warning("[ExpertChat] memory query failed for %s: %s", agent_id, e)
        return ""

    agent_text = format_memory_hits(agent_hits, max_items=ATOMIC_MEMORY_TOP_K, max_chars=1400)
    shared_text = format_memory_hits(shared_hits, max_items=ATOMIC_MEMORY_TOP_K, max_chars=900)
    chunks: List[str] = []
    if agent_text:
        chunks.append(f"## {agent_id} historical memory\n{agent_text}")
    if shared_text:
        chunks.append(f"## Shared evidence memory\n{shared_text}")
    return "\n\n".join(chunks)


async def _persist_expert_chat_memory(
    user_id: str,
    agent_id: str,
    session_id: str,
    user_message: str,
    answer: str,
    delegated_by_leader: bool,
) -> None:
    if not answer:
        return
    content = compact_text(
        (
            f"User message:\n{(user_message or '')[:2000]}\n\n"
            f"Agent response:\n{(answer or '')[:4500]}"
        ),
        max_chars=4200,
    )
    if not should_persist_memory(content):
        return
    metadata = make_provenance_metadata(
        source="expert_chat",
        session_id=session_id,
        agent_id=agent_id,
        extra={"delegated_by_leader": bool(delegated_by_leader)},
    )
    try:
        await atomic_memory_store.add_agent_memory(
            user_id=str(user_id or "anonymous"),
            agent_id=str(agent_id),
            content=content,
            metadata=metadata,
            collection="episodic",
        )
        await atomic_memory_store.add_shared_evidence(
            user_id=str(user_id or "anonymous"),
            content=compact_text(f"[{agent_id}] {(answer or '')[:3000]}", max_chars=2600),
            metadata=metadata,
        )
    except Exception as e:
        logger.warning("[ExpertChat] memory persist failed for %s: %s", agent_id, e)


def _schedule_expert_chat_memory_persist(**kwargs: Any) -> None:
    async def _runner() -> None:
        try:
            async with _expert_chat_memory_write_sem:
                await _persist_expert_chat_memory(**kwargs)
        except Exception as e:
            logger.warning("[ExpertChat] async memory persist task failed: %s", e)

    try:
        task = asyncio.create_task(_runner())
    except RuntimeError:
        # No running event loop: best effort fallback.
        logger.warning("[ExpertChat] no running loop, skip async memory persist scheduling")
        return
    _expert_chat_memory_tasks.add(task)
    task.add_done_callback(lambda t: _expert_chat_memory_tasks.discard(t))


def _parse_json_object(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    stripped = str(text).strip()
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    fenced = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", stripped, re.IGNORECASE)
    if fenced:
        try:
            parsed = json.loads(fenced.group(1))
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

    inline = re.search(r"(\{[\s\S]*\})", stripped)
    if inline:
        try:
            parsed = json.loads(inline.group(1))
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
    return None


def _sanitize_expert_chat_attachments(raw_attachments: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw_attachments, list):
        return []

    attachments: List[Dict[str, Any]] = []
    allowed_mimes = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"}

    for idx, item in enumerate(raw_attachments):
        if len(attachments) >= EXPERT_CHAT_MAX_ATTACHMENTS:
            break
        if not isinstance(item, dict):
            continue

        mime_type = str(item.get("mime_type") or item.get("mimeType") or "").strip().lower()
        if mime_type not in allowed_mimes:
            continue

        raw_data = str(item.get("data_base64") or item.get("dataBase64") or "").strip()
        if not raw_data:
            continue
        if raw_data.startswith("data:") and "," in raw_data:
            raw_data = raw_data.split(",", 1)[1]

        try:
            binary = base64.b64decode(raw_data, validate=True)
        except Exception:
            continue

        if not binary or len(binary) > EXPERT_CHAT_MAX_ATTACHMENT_BYTES:
            continue

        ext = mime_type.split("/")[-1].replace("jpeg", "jpg")
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", str(item.get("name") or f"image_{idx + 1}.{ext}")).strip("._")
        if not safe_name:
            safe_name = f"image_{idx + 1}.{ext}"

        attachments.append(
            {
                "name": safe_name,
                "mime_type": mime_type,
                "size": len(binary),
                "data_base64": base64.b64encode(binary).decode("ascii"),
            }
        )

    return attachments


def _attachments_summary(attachments: List[Dict[str, Any]], language: str) -> str:
    if not attachments:
        return "none"
    if _is_zh(language):
        items = ", ".join(f"{att.get('name')}({att.get('size', 0)} bytes)" for att in attachments)
        return f"已上传图片: {items}"
    items = ", ".join(f"{att.get('name')}({att.get('size', 0)} bytes)" for att in attachments)
    return f"Uploaded images: {items}"


def _flatten_messages_for_file_prompt(messages: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for msg in messages:
        role = str(msg.get("role", "user")).upper()
        content = str(msg.get("content", "")).strip()
        if not content:
            continue
        lines.append(f"{role}: {content[:3000]}")
    return "\n\n".join(lines)[:12000]


async def _build_attachment_context(
    user_message: str,
    attachments: List[Dict[str, Any]],
    language: str,
) -> str:
    if not attachments:
        return ""

    zh = _is_zh(language)
    try:
        prompt = (
            (
                "请基于上传图片提取与用户问题相关的关键信息，聚焦事实、数字、时间和风险提示。"
                "只输出精炼结论，不要重复用户原话。\n\n"
                f"用户问题: {user_message}"
            )
            if zh
            else (
                "Extract key image-grounded facts relevant to the user request. "
                "Focus on concrete facts, numbers, time references, and risk cues. "
                "Return concise findings only.\n\n"
                f"User request: {user_message}"
            )
        )
        return await _llm_chat_completion(
            [
                {"role": "system", "content": "You are an image analysis assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            attachments=attachments,
            model=resolve_model_for_role("attachment_vision"),
        )
    except Exception as e:
        logger.warning(f"[ExpertChat] Failed to build attachment context: {e}")
        return ""


def _build_agent_task_prompt(
    agent_id: str,
    user_message: str,
    history: List[Dict[str, Any]],
    language: str,
    knowledge_enabled: bool,
    knowledge_category: str,
    attachment_summary: str,
    attachment_context: str,
    memory_context: str = "",
    shared_evidence_context: str = "",
    delegated_by_leader: bool = False,
    specialist_outputs: Optional[List[Dict[str, str]]] = None,
) -> str:
    skill_context = build_skill_instruction_context(
        agent_id=agent_id,
        user_message=user_message,
        language=language,
    )
    history_limit = 6 if (shared_evidence_context or skill_context) else 10
    history_text = _format_history_window(history, limit=history_limit)
    normalized_category = _normalize_expert_chat_knowledge_category(knowledge_category)

    specialist_outputs_text = ""
    if specialist_outputs:
        specialist_outputs_text = "\n\n".join(
            f"[{item.get('agent_name')}]\n{item.get('content')}"
            for item in specialist_outputs
            if item.get("content")
        )

    if _is_zh(language):
        prompt = (
            f"最近对话历史:\n{history_text}\n\n"
            f"用户当前问题:\n{user_message}\n\n"
            f"知识检索开关: {'开启' if knowledge_enabled else '关闭'}\n"
            f"知识范围: {normalized_category}\n"
            f"附件摘要: {attachment_summary}\n"
            f"是否为Leader委派: {'是' if delegated_by_leader else '否'}\n"
        )
        if attachment_context:
            prompt += f"\n图片分析上下文:\n{attachment_context}\n"
        if skill_context:
            prompt += f"\n本轮能力卡片:\n{skill_context}\n"
        if memory_context:
            prompt += f"\n历史记忆参考:\n{memory_context}\n"
        if shared_evidence_context:
            prompt += f"\n共享证据板(优先复用，避免重复检索):\n{shared_evidence_context}\n"
        if specialist_outputs_text:
            prompt += f"\n专家阶段输出:\n{specialist_outputs_text}\n"
        prompt += (
            "\n请直接给出专业、可执行、基于证据的回答。"
            "如果信息不足，请明确缺口并给出下一步需要补充的数据。"
        )
        if delegated_by_leader:
            prompt += (
                "\n你是被委派专家。请优先复用共享证据，只有在关键事实缺失时才额外检索。"
                "结论请包含: 核心判断、关键依据、风险与失效条件。"
                "在回答末尾附加 INTERNAL_EVIDENCE_PACKET JSON 块（summary/key_points/risks/confidence），"
                "格式为 [INTERNAL_EVIDENCE_PACKET]{...}[/INTERNAL_EVIDENCE_PACKET]。"
            )
        return prompt

    prompt = (
        f"Recent conversation:\n{history_text}\n\n"
        f"Current user request:\n{user_message}\n\n"
        f"Knowledge retrieval enabled: {knowledge_enabled}\n"
        f"Knowledge scope: {normalized_category}\n"
        f"Attachment summary: {attachment_summary}\n"
        f"Delegated by Leader: {delegated_by_leader}\n"
    )
    if attachment_context:
        prompt += f"\nImage-grounded context:\n{attachment_context}\n"
    if skill_context:
        prompt += f"\nLoaded skill cards:\n{skill_context}\n"
    if memory_context:
        prompt += f"\nHistorical memory context:\n{memory_context}\n"
    if shared_evidence_context:
        prompt += f"\nShared evidence board (reuse first, avoid duplicate retrieval):\n{shared_evidence_context}\n"
    if specialist_outputs_text:
        prompt += f"\nSpecialist outputs:\n{specialist_outputs_text}\n"
    prompt += (
        "\nProvide a professional, evidence-based, and actionable response. "
        "If information is insufficient, clearly state what is missing and the next data needed."
    )
    if delegated_by_leader:
        prompt += (
            "\nYou are a delegated specialist. Reuse shared evidence first and call new tools only for missing critical facts. "
            "Include: thesis, supporting evidence, risk/invalidation. "
            "Append an INTERNAL_EVIDENCE_PACKET JSON block at the end "
            "using [INTERNAL_EVIDENCE_PACKET]{...}[/INTERNAL_EVIDENCE_PACKET] "
            "with fields summary/key_points/risks/confidence."
        )
    return prompt


async def _run_expert_chat_agent_once(agent: Any, prompt: str) -> str:
    from .core.roundtable.message import Message, MessageType
    from .core.roundtable.message_bus import MessageBus

    bus = MessageBus()
    bus.register_agent(agent.name)
    agent.message_bus = bus

    await bus.send(
        Message(
            sender="User",
            recipient=agent.name,
            content=prompt,
            message_type=MessageType.DIRECT,
        )
    )

    outputs = await asyncio.wait_for(
        agent.think_and_act(),
        timeout=EXPERT_CHAT_AGENT_TURN_TIMEOUT_SECONDS,
    )
    text_parts = [
        str(item.content).strip()
        for item in (outputs or [])
        if getattr(item, "content", None)
    ]
    return "\n\n".join([part for part in text_parts if part]).strip()


def _sanitize_resume_history(raw_history: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw_history, list):
        return []

    cleaned: List[Dict[str, Any]] = []
    for item in raw_history[-EXPERT_CHAT_MAX_HISTORY:]:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "")).lower().strip()
        if role not in {"user", "assistant", "system"}:
            continue
        content = str(item.get("content", "")).strip()
        if not content:
            continue

        speaker = str(item.get("speaker") or ("User" if role == "user" else "Assistant")).strip()[:80]
        msg: Dict[str, Any] = {
            "role": role,
            "speaker": speaker,
            "content": content[:8000],
            "timestamp": str(item.get("timestamp") or datetime.utcnow().isoformat()),
        }
        if role == "assistant":
            msg["agent_id"] = str(item.get("agent_id") or "").strip()[:80]
            summary = str(item.get("content_summary") or "").strip()
            if summary:
                msg["content_summary"] = summary[:400]
        cleaned.append(msg)
    return cleaned


def _build_leader_route_cache_key(
    user_message: str,
    history: List[Dict[str, Any]],
    language: str,
    knowledge_enabled: bool,
    knowledge_category: str,
    attachments_summary: str,
) -> str:
    history_window = history[-6:] if isinstance(history, list) else []
    history_snapshot = [
        {
            "role": str(item.get("role", "")),
            "agent_id": str(item.get("agent_id", "")),
            "content": str(item.get("content", ""))[:280],
        }
        for item in history_window
        if isinstance(item, dict)
    ]
    payload = {
        "user_message": str(user_message or "")[:1500],
        "language": str(language or ""),
        "knowledge_enabled": bool(knowledge_enabled),
        "knowledge_category": str(knowledge_category or "all"),
        "attachments_summary": str(attachments_summary or ""),
        "history": history_snapshot,
    }
    digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    return f"leader_route:{digest}"


async def _leader_route_cache_get(cache_key: str) -> Optional[Dict[str, Any]]:
    if not EXPERT_CHAT_ROUTE_CACHE_ENABLED:
        return None
    now = time.time()
    async with _leader_route_cache_lock:
        item = _leader_route_cache.get(cache_key)
        if not item:
            record_cache_event(layer="leader_route", event="miss")
            return None
        if float(item.get("expires_at", 0.0)) <= now:
            _leader_route_cache.pop(cache_key, None)
            record_cache_event(layer="leader_route", event="stale")
            return None
        _leader_route_cache.move_to_end(cache_key)
        record_cache_event(layer="leader_route", event="hit")
        value = item.get("value")
        return deepcopy(value) if isinstance(value, dict) else None


async def _leader_route_cache_set(cache_key: str, decision: Dict[str, Any]) -> None:
    if not EXPERT_CHAT_ROUTE_CACHE_ENABLED:
        return
    if not isinstance(decision, dict):
        return
    payload = {
        "expires_at": time.time() + EXPERT_CHAT_ROUTE_CACHE_TTL_SECONDS,
        "value": deepcopy(decision),
    }
    async with _leader_route_cache_lock:
        _leader_route_cache[cache_key] = payload
        _leader_route_cache.move_to_end(cache_key)
        while len(_leader_route_cache) > EXPERT_CHAT_ROUTE_CACHE_MAX_ENTRIES:
            _leader_route_cache.popitem(last=False)
            record_cache_event(layer="leader_route", event="evict")
    record_cache_event(layer="leader_route", event="store")


async def _llm_chat_completion(
    messages: List[Dict[str, Any]],
    temperature: float = 1.0,
    provider: str = EXPERT_CHAT_PROVIDER,
    attachments: Optional[List[Dict[str, Any]]] = None,
    model: Optional[str] = None,
) -> str:
    sanitized_attachments = _sanitize_expert_chat_attachments(attachments)
    prompt_texts = [str(msg.get("content", "")) for msg in messages if isinstance(msg, dict) and msg.get("content")]

    async with httpx.AsyncClient(timeout=420.0) as client:
        if sanitized_attachments and provider != "gemini":
            note = "The active provider does not support image attachments in this flow. Continue with text only."
            messages = messages + [{"role": "system", "content": note}]
            sanitized_attachments = []

        if not sanitized_attachments:
            payload: Dict[str, Any] = {
                "messages": messages,
                "temperature": temperature,
                "provider": provider,
            }
            if model:
                payload["model"] = model
            response = await client.post(
                f"{LLM_GATEWAY_URL}/v1/chat/completions",
                json=payload,
            )
            if response.status_code != 200:
                detail = response.text[:500]
                raise HTTPException(status_code=502, detail=f"LLM Gateway error ({response.status_code}): {detail}")
            payload = response.json()
            content = (
                payload.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )
            record_llm_context_usage(
                source="expert_chat",
                model=str(model or provider or "default"),
                usage=payload.get("usage"),
                prompt_texts=prompt_texts,
                completion_text=content,
            )
            return content

        prompt_for_file = _flatten_messages_for_file_prompt(messages)
        image_outputs: List[str] = []
        for attachment in sanitized_attachments:
            file_bytes = base64.b64decode(attachment["data_base64"])
            file_resp = await client.post(
                f"{LLM_GATEWAY_URL}/generate_from_file",
                data={"prompt": prompt_for_file},
                files={
                    "file": (
                        attachment["name"],
                        file_bytes,
                        attachment["mime_type"],
                    )
                },
            )
            if file_resp.status_code != 200:
                detail = file_resp.text[:500]
                raise HTTPException(status_code=502, detail=f"File multimodal call failed ({file_resp.status_code}): {detail}")
            file_payload = file_resp.json()
            image_content = str(file_payload.get("content", "")).strip()
            record_llm_context_usage(
                source="expert_chat_file",
                model=str(model or provider or "default"),
                usage=file_payload.get("usage"),
                prompt_texts=[prompt_for_file, f"attachment:{attachment['name']}"],
                completion_text=image_content,
            )
            image_outputs.append(image_content)

        if len(image_outputs) == 1:
            return image_outputs[0]

        merge_request: Dict[str, Any] = {
            "messages": [
                {
                    "role": "system",
                    "content": "Synthesize multiple image analyses into one concise response without repeating points.",
                },
                {
                    "role": "user",
                    "content": (
                        f"Original request context:\n{prompt_for_file}\n\n"
                        + "\n\n".join(
                            f"[Image {idx + 1} Analysis]\n{text}"
                            for idx, text in enumerate(image_outputs)
                        )
                    ),
                },
            ],
            "temperature": 0.7,
            "provider": provider,
        }
        if model:
            merge_request["model"] = model
        merge_response = await client.post(
            f"{LLM_GATEWAY_URL}/v1/chat/completions",
            json=merge_request,
        )
        if merge_response.status_code != 200:
            detail = merge_response.text[:500]
            raise HTTPException(status_code=502, detail=f"LLM merge error ({merge_response.status_code}): {detail}")
        merge_response_payload = merge_response.json()
        merged_content = (
            merge_response_payload.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        record_llm_context_usage(
            source="expert_chat_merge",
            model=str(model or provider or "default"),
            usage=merge_response_payload.get("usage"),
            prompt_texts=[
                str(merge_request.get("messages", [{}])[0].get("content", "")),
                str(merge_request.get("messages", [{}, {}])[1].get("content", "")),
            ],
            completion_text=merged_content,
        )
        return merged_content


async def _leader_plan_route(
    user_message: str,
    history: List[Dict[str, Any]],
    language: str,
    knowledge_enabled: bool,
    knowledge_category: str,
    attachments_summary: str = "none",
) -> Dict[str, Any]:
    route_started_at = time.perf_counter()
    cache_key = _build_leader_route_cache_key(
        user_message=user_message,
        history=history,
        language=language,
        knowledge_enabled=knowledge_enabled,
        knowledge_category=knowledge_category,
        attachments_summary=attachments_summary,
    )
    cached = await _leader_route_cache_get(cache_key)
    if cached:
        cached_need_specialists = bool(cached.get("need_specialists")) and bool(cached.get("specialists"))
        record_route_decision(
            channel="expert_chat",
            mode="delegated" if cached_need_specialists else "leader",
            status="cached",
            latency_seconds=time.perf_counter() - route_started_at,
        )
        return cached

    specialist_desc = ", ".join(
        f"{agent_id}({EXPERT_CHAT_AGENT_PROFILES[agent_id].get('name_zh')})"
        for agent_id in EXPERT_SPECIALIST_IDS
    )
    history_text = _format_history_window(history, limit=10)
    system_prompt = (
        "You are the Leader in a professional expert group chat. "
        "You must decide whether to delegate this turn to specialists.\n"
        "Return STRICT JSON only with keys: need_specialists(boolean), specialists(string[]), leader_reply(string), reason(string).\n"
        "Only choose specialists from this list: "
        f"{', '.join(EXPERT_SPECIALIST_IDS)}."
    )
    user_prompt = (
        f"Language: {'zh-CN' if _is_zh(language) else 'en-US'}\n"
        f"Knowledge enabled: {knowledge_enabled}, category: {knowledge_category or 'all'}\n"
        f"Attachments: {attachments_summary}\n"
        f"Specialists: {specialist_desc}\n\n"
        f"Recent history:\n{history_text}\n\n"
        f"Current user message:\n{user_message}\n"
    )
    try:
        raw = await _llm_chat_completion(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            model=resolve_model_for_role("leader_router"),
        )
        parsed = _parse_json_object(raw)
        if not parsed:
            raise RuntimeError("Leader route plan parsing failed: non-JSON response")
        specialists = [
            sid for sid in parsed.get("specialists", []) if sid in EXPERT_SPECIALIST_IDS
        ]
        need_specialists = bool(parsed.get("need_specialists")) and bool(specialists)
        record_route_decision(
            channel="expert_chat",
            mode="delegated" if need_specialists else "leader",
            status="success",
            latency_seconds=time.perf_counter() - route_started_at,
        )
        decision = {
            "need_specialists": need_specialists,
            "specialists": specialists,
            "leader_reply": str(parsed.get("leader_reply", "")).strip(),
            "reason": str(parsed.get("reason", "")).strip() or "leader_decision",
        }
        await _leader_route_cache_set(cache_key, decision)
        return decision
    except Exception:
        record_route_decision(
            channel="expert_chat",
            mode="leader",
            status="error",
            latency_seconds=time.perf_counter() - route_started_at,
        )
        raise


async def _ask_specialist(
    agent_id: str,
    user_message: str,
    history: List[Dict[str, Any]],
    language: str,
    knowledge_enabled: bool,
    knowledge_category: str,
    user_id: str,
    session_id: str,
    attachments: Optional[List[Dict[str, Any]]] = None,
    attachment_context: str = "",
    shared_evidence_context: str = "",
    session_agents: Optional[Dict[str, Any]] = None,
    delegated_by_leader: bool = False,
) -> Dict[str, Any]:
    attachment_note = _attachments_summary(attachments or [], language)
    specialist_agent = (session_agents or {}).get(agent_id)
    if specialist_agent is None:
        raise RuntimeError(f"ExpertChat specialist agent not initialized: {agent_id}")
    memory_context = await _build_expert_chat_memory_context(
        user_id=user_id,
        agent_id=agent_id,
        user_message=user_message,
        history=history,
    )

    prompt = _build_agent_task_prompt(
        agent_id=agent_id,
        user_message=user_message,
        history=history,
        language=language,
        knowledge_enabled=knowledge_enabled,
        knowledge_category=knowledge_category,
        attachment_summary=attachment_note,
        attachment_context=attachment_context,
        memory_context=memory_context,
        shared_evidence_context=shared_evidence_context,
        delegated_by_leader=delegated_by_leader,
    )
    raw_answer = await _run_expert_chat_agent_once(specialist_agent, prompt)
    if not raw_answer:
        raise RuntimeError(f"ExpertChat specialist agent returned empty output: {agent_id}")
    parsed = extract_specialist_response(
        agent_id=agent_id,
        agent_name=_display_agent_name(agent_id, language),
        raw_content=raw_answer,
        language=language,
    )
    answer = str(parsed.get("content") or raw_answer).strip()
    if not answer:
        answer = raw_answer.strip()
    if EXPERT_CHAT_MEMORY_ASYNC_WRITE:
        _schedule_expert_chat_memory_persist(
            user_id=user_id,
            agent_id=agent_id,
            session_id=session_id,
            user_message=user_message,
            answer=answer,
            delegated_by_leader=delegated_by_leader,
        )
    else:
        await _persist_expert_chat_memory(
            user_id=user_id,
            agent_id=agent_id,
            session_id=session_id,
            user_message=user_message,
            answer=answer,
            delegated_by_leader=delegated_by_leader,
        )
    return {
        "content": answer,
        "summary": str(parsed.get("summary") or "")[:320],
        "evidence_packet": parsed.get("evidence_packet") or {},
    }


async def _leader_direct_reply(
    user_message: str,
    history: List[Dict[str, Any]],
    language: str,
    knowledge_enabled: bool,
    knowledge_category: str,
    user_id: str,
    session_id: str,
    attachments: Optional[List[Dict[str, Any]]] = None,
    attachment_context: str = "",
    session_agents: Optional[Dict[str, Any]] = None,
) -> str:
    attachment_note = _attachments_summary(attachments or [], language)
    leader_agent = (session_agents or {}).get("leader")
    if leader_agent is None:
        raise RuntimeError("ExpertChat leader agent not initialized")
    memory_context = await _build_expert_chat_memory_context(
        user_id=user_id,
        agent_id="leader",
        user_message=user_message,
        history=history,
    )

    prompt = _build_agent_task_prompt(
        agent_id="leader",
        user_message=user_message,
        history=history,
        language=language,
        knowledge_enabled=knowledge_enabled,
        knowledge_category=knowledge_category,
        attachment_summary=attachment_note,
        attachment_context=attachment_context,
        memory_context=memory_context,
        delegated_by_leader=False,
    )
    answer = await _run_expert_chat_agent_once(leader_agent, prompt)
    if not answer:
        raise RuntimeError("ExpertChat leader agent returned empty output")
    if EXPERT_CHAT_MEMORY_ASYNC_WRITE:
        _schedule_expert_chat_memory_persist(
            user_id=user_id,
            agent_id="leader",
            session_id=session_id,
            user_message=user_message,
            answer=answer,
            delegated_by_leader=False,
        )
    else:
        await _persist_expert_chat_memory(
            user_id=user_id,
            agent_id="leader",
            session_id=session_id,
            user_message=user_message,
            answer=answer,
            delegated_by_leader=False,
        )
    return answer


async def _leader_summarize_with_specialists(
    user_message: str,
    specialist_outputs: List[Dict[str, str]],
    history: List[Dict[str, Any]],
    language: str,
    user_id: str,
    session_id: str,
    attachments: Optional[List[Dict[str, Any]]] = None,
    attachment_context: str = "",
    session_agents: Optional[Dict[str, Any]] = None,
) -> str:
    attachment_note = _attachments_summary(attachments or [], language)
    leader_agent = (session_agents or {}).get("leader")
    if leader_agent is None:
        raise RuntimeError("ExpertChat leader agent not initialized for summarize")
    memory_context = await _build_expert_chat_memory_context(
        user_id=user_id,
        agent_id="leader",
        user_message=user_message,
        history=history,
    )

    prompt = _build_agent_task_prompt(
        agent_id="leader",
        user_message=user_message,
        history=history,
        language=language,
        knowledge_enabled=True,
        knowledge_category="all",
        attachment_summary=attachment_note,
        attachment_context=attachment_context,
        memory_context=memory_context,
        delegated_by_leader=False,
        specialist_outputs=specialist_outputs,
    )
    answer = await _run_expert_chat_agent_once(leader_agent, prompt)
    if not answer:
        raise RuntimeError("ExpertChat leader summarize returned empty output")
    if EXPERT_CHAT_MEMORY_ASYNC_WRITE:
        _schedule_expert_chat_memory_persist(
            user_id=user_id,
            agent_id="leader",
            session_id=session_id,
            user_message=user_message,
            answer=answer,
            delegated_by_leader=False,
        )
    else:
        await _persist_expert_chat_memory(
            user_id=user_id,
            agent_id="leader",
            session_id=session_id,
            user_message=user_message,
            answer=answer,
            delegated_by_leader=False,
        )
    return answer

# --- WebSocket Workflow ---
@app.websocket("/ws/start_analysis")
async def websocket_analysis_endpoint(websocket: WebSocket):
    await websocket.accept()
    token = (websocket.query_params.get("token") or "").strip()
    try:
        current_user = await resolve_user_from_token(token)
    except Exception as auth_error:
        logger.warning(f"[Legacy WS] Authentication failed for /ws/start_analysis: {auth_error}")
        await websocket.close(code=1008, reason="Authentication required")
        return
    session_id = ""
    user_persona = UserPersona()
    selected_ticker = ""

    try:
        # 1. Wait for the initial request
        initial_request = await websocket.receive_json()
        ticker = initial_request.get("ticker")
        requested_user_id = initial_request.get("user_id")
        user_id = current_user.id
        if requested_user_id and str(requested_user_id) != str(user_id):
            logger.info(f"[Legacy WS] Ignoring mismatched requested user_id={requested_user_id}; using authenticated user_id={user_id}")

        if not ticker:
            await websocket.close(code=1008, reason="Ticker not provided")
            return

        async with httpx.AsyncClient(timeout=300.0) as client:
            uuid_response = await client.get('https://www.uuidgenerator.net/api/version4')
            session_id = f"session_{ticker}_{uuid_response.text}"

            print("DEBUG: Starting Step 0: Fetch User Persona")
            step0 = Step(id=0, title=f"正在获取用户 '{user_id}' 的投资画像", status="running")
            await websocket.send_json(WebSocketMessage(session_id=session_id, status='in_progress', step=step0).dict())
            print("DEBUG: Sent Step 0 running status")
            try:
                print("DEBUG: Calling user_service")
                persona_resp = await client.get(f"{USER_SERVICE_URL}/users/{user_id}")
                persona_resp.raise_for_status()
                user_persona = UserPersona(**persona_resp.json())
                step0.status = "success"
                step0.result = f"画像已加载：投资风格 '{user_persona.investment_style}', 风险偏好 '{user_persona.risk_tolerance}'."
                print("DEBUG: user_service call successful")
            except Exception as e:
                step0.status = "error"
                step0.result = "无法加载用户画像，将使用默认设置。"
                print(f"DEBUG: user_service call failed: {e}")
            await websocket.send_json(WebSocketMessage(session_id=session_id, status='in_progress', step=step0).dict())
            print("DEBUG: Sent Step 0 final status")

            # --- Step 1: Data Collection & Ambiguity Resolution ---
            print("DEBUG: Starting Step 1: Data Collection")
            step1 = Step(id=1, title=f"正在为 '{ticker}' 获取公开数据", status="running")
            await websocket.send_json(WebSocketMessage(session_id=session_id, status='in_progress', step=step1).dict())
            print("DEBUG: Sent Step 1 running status")
            
            public_data_resp = await client.post(f"{EXTERNAL_DATA_URL}/get_company_info", json={"ticker": ticker})
            print("DEBUG: Called get_company_info")
            public_data_resp.raise_for_status()
            response_data = public_data_resp.json()

            if response_data['status'] == 'multiple_options':
                print("DEBUG: Ambiguity found, pausing for user input")
                step1.status = "paused"
                step1.result = "公司名称存在歧义，请选择正确的公司。"
                step1.options = response_data['data']
                await websocket.send_json(WebSocketMessage(session_id=session_id, status='hitl_required', step=step1).dict())
                
                print("DEBUG: Waiting for user choice...")
                user_choice = await websocket.receive_json()
                selected_ticker = user_choice.get("selected_ticker")
                ticker = selected_ticker
                print(f"DEBUG: User selected {selected_ticker}")

                step1.title = f"正在为 {selected_ticker} 获取已确认的数据"
                step1.status = "running"
                step1.result = f"您选择了 {selected_ticker}。正在继续分析..."
                step1.options = None
                await websocket.send_json(WebSocketMessage(session_id=session_id, status='in_progress', step=step1).dict())

                public_data_resp = await client.post(f"{EXTERNAL_DATA_URL}/get_company_info", json={"ticker": selected_ticker})
                print("DEBUG: Called get_company_info again with confirmed ticker")
            else:
                selected_ticker = ticker

            public_data_resp.raise_for_status()
            public_data = public_data_resp.json()['data']
            step1.status = "success"
            step1.result = f"已成功获取 {public_data.get('company_name', selected_ticker)} 的数据。"
            await websocket.send_json(WebSocketMessage(session_id=session_id, status='in_progress', step=step1).dict())
            print("DEBUG: Sent Step 1 success status")

            # --- Step 2: Initial Analysis with LLM ---
            print("DEBUG: Starting Step 2: Initial Analysis")
            step2 = Step(id=2, title="正在使用 Gemini 生成初步分析", status="running")
            await websocket.send_json(WebSocketMessage(session_id=session_id, status='in_progress', step=step2).dict())
            prompt = f"请根据以下公司数据，为一位投资者撰写一份简洁并引人入胜的中文公司介绍。\n\n数据:\n{public_data}"
            summary = await call_llm_gateway(client, [{"role": "user", "parts": [prompt]}])
            step2.status = "success"
            step2.result = summary
            await websocket.send_json(WebSocketMessage(session_id=session_id, status='in_progress', step=step2).dict())
            print("DEBUG: Sent Step 2 success status")

            # --- Step 3: Fetch Financial Data for Chart ---
            print("DEBUG: Starting Step 3: Fetch Financial Data")
            step3 = Step(id=3, title="正在获取用于图表的财务摘要", status="running")
            await websocket.send_json(WebSocketMessage(session_id=session_id, status='in_progress', step=step3).dict())
            financial_data = None
            try:
                print("DEBUG: Calling get_financial_summary")
                financial_resp = await client.post(f"{EXTERNAL_DATA_URL}/get_financial_summary", json={"ticker": selected_ticker})
                financial_resp.raise_for_status()
                financial_data = financial_resp.json()
                step3.status = "success"
                step3.result = "已成功获取财务摘要。"
                print("DEBUG: get_financial_summary successful")
            except Exception as e:
                step3.status = "error"
                step3.result = f"无法获取财务摘要: {e}"
                print(f"DEBUG: get_financial_summary failed: {e}")
            await websocket.send_json(WebSocketMessage(session_id=session_id, status='in_progress', step=step3).dict())
            print("DEBUG: Sent Step 3 final status")

            # --- Step 4: Generate Key Questions (HITL Node 2) ---
            print("DEBUG: Starting Step 4: Generate Key Questions")
            step4 = Step(id=4, title="正在生成关键追问问题", status="running")
            await websocket.send_json(WebSocketMessage(session_id=session_id, status='in_progress', step=step4).dict())
            prompt = f"""你是一位专业的投资分析师。你的客户的投资风格是 '{user_persona.investment_style}'，风险偏好为 '{user_persona.risk_tolerance}'。
            请根据以下的公司介绍，为这位客户量身定制一个包含3-4个有深度、有批判性的中文追问问题的JSON数组。
            公司介绍: {summary}
            
            关键要求：你的整个回答必须只有纯粹的JSON数组，不包含任何额外的文字、解释或markdown格式。
            """
            questions_str = await call_llm_gateway(client, [{"role": "user", "parts": [prompt]}])
            
            key_questions = []
            try:
                # First, try to parse directly
                key_questions = json.loads(questions_str)
            except json.JSONDecodeError:
                # If direct parsing fails, try to extract from markdown
                match = re.search(r"```json\n(.*)\n```", questions_str, re.DOTALL)
                if match:
                    try:
                        key_questions = json.loads(match.group(1))
                    except json.JSONDecodeError:
                        key_questions = ["错误：无法从LLM返回的Markdown中解析JSON。"]
                else:
                    key_questions = ["错误：LLM返回了无效的、非JSON格式的内容。"]

            # Handle cases where the LLM returns a list of objects with a "question" key
            if key_questions and isinstance(key_questions[0], dict):
                key_questions = [q.get("question", "无效的问题格式") for q in key_questions]
            
            if not key_questions or "错误" in key_questions[0]:
                step4.status = "error"
                step4.result = key_questions[0] if key_questions else "错误：LLM返回了空的问题列表。"
                await websocket.send_json(WebSocketMessage(session_id=session_id, status='error', step=step4).dict())
                return

            step4.status = "success"
            step4.result = "已成功生成用于用户追问的关键问题。"
            await websocket.send_json(WebSocketMessage(session_id=session_id, status='in_progress', step=step4).dict())
            print("DEBUG: Sent Step 4 success status")

            # --- Final HITL Follow-up ---
            print("DEBUG: Preparing final HITL message")
            preliminary_report = FullReportResponse(
                company_ticker=selected_ticker,
                report_sections=[
                    ReportSection(section_title="初步分析", content=summary),
                    ReportSection(section_title="财务分析", content="包含关键财务数据的交互式图表。")
                ],
                financial_chart_data=financial_data
            )
            
            await websocket.send_json(WebSocketMessage(
                session_id=session_id,
                status='hitl_follow_up_required',
                preliminary_report=preliminary_report.dict(),
                key_questions=key_questions
            ).dict())
            print("DEBUG: Sent final HITL message")


    except WebSocketDisconnect:
        print(f"Client disconnected from session {session_id}")
    except Exception as e:
        print(f"An unexpected error occurred in session {session_id}: {e}")
        error_step = Step(id=-1, title="Workflow Error", status="error", result=str(e))
        if websocket.client_state == 1: # OPEN
             await websocket.send_json(WebSocketMessage(session_id=session_id, status='error', step=error_step).dict())
             await websocket.close(code=1011, reason=f"An internal error occurred: {e}")


# NOTE: Deprecated endpoints removed in Phase 4 refactoring:
# - /start_analysis, /continue_analysis (use /ws/start_analysis instead)


@app.post("/get_instant_feedback", response_model=InstantFeedbackResponse, tags=["Agent Workflow"])
async def get_instant_feedback(
    request: InstantFeedbackRequest,
    _: CurrentUser = Depends(get_current_user),
):
    """
    Provides instant feedback on a user's input based on the current analysis context.
    """
    prompt = f"""You are an AI investment analyst assistant. Your user is currently reviewing an investment report summary.
    
    Report Summary:
    ---
    {request.analysis_context}
    ---
    
    The user has just provided the following information or answer to a question:
    ---
    {request.user_input}
    ---
    
    Based on the user's input, provide a concise, insightful feedback. Analyze how this new information strengthens, weakens, or clarifies the points in the original summary. Do not just repeat the information.
    """
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            feedback = await call_llm_gateway(client, [{"role": "user", "parts": [prompt]}])
            return InstantFeedbackResponse(feedback=feedback)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get feedback from LLM Gateway: {e}")


@app.get("/", tags=["Health Check"])
def read_root():
    """Health check endpoint."""
    return {"status": "ok", "service": "Orchestrator Agent", "version": "3.0.0"}


# ============================================================================
# V3: DD Workflow WebSocket Endpoint
# ============================================================================

# V5: Initialize Redis Session Store for persistence
REQUIRE_REDIS = os.getenv("REPORT_ORCH_REQUIRE_REDIS", "false").lower() == "true"
try:
    session_store = SessionStore()  # Uses REDIS_URL from environment
    print("[main.py] ✅ SessionStore initialized successfully")
except Exception as e:
    print(f"[main.py] ❌ Failed to initialize SessionStore: {e}")
    if REQUIRE_REDIS:
        # PoC/hosted environments should fail-fast to avoid silent data loss.
        raise
    print("[main.py] ⚠️  Falling back to in-memory storage")
    session_store = None

# Phase 4: Initialize Storage Services with session_store
report_storage = init_report_storage(session_store)
print("[main.py] ✅ ReportStorage initialized")

# V5: Backward compatibility - keep in-memory storage as fallback
dd_sessions: Dict[str, DDSessionContext] = {}  # Fallback if Redis fails
saved_reports: List[Dict[str, Any]] = []  # Fallback if Redis fails

# Phase 2: Initialize Vector Store for Knowledge Base (skip in standalone mode)
vector_store = None
rag_service = None

if not STANDALONE_MODE:
    try:
        QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
        vector_store = VectorStoreService(qdrant_url=QDRANT_URL)
        print("[main.py] ✅ VectorStore initialized successfully")
    except Exception as e:
        print(f"[main.py] ❌ Failed to initialize VectorStore: {e}")
        print("[main.py] ⚠️  Knowledge base features will be disabled")
        vector_store = None

    # Phase 2: Initialize RAG Service for Advanced Search
    try:
        if vector_store:
            rag_service = RAGService(vector_store_service=vector_store)
            # Build BM25 index on startup
            rag_service.refresh_bm25_index()
            print("[main.py] ✅ RAG Service initialized successfully")
        else:
            rag_service = None
            print("[main.py] ⚠️  RAG Service disabled (VectorStore not available)")
    except Exception as e:
        print(f"[main.py] ❌ Failed to initialize RAG Service: {e}")
        print("[main.py] ⚠️  Advanced search features will be disabled")
        rag_service = None

    # Phase 4: Initialize Knowledge Router dependencies
    if vector_store:
        set_vector_store(vector_store)
        print("[main.py] ✅ Knowledge Router vector_store set")
    if rag_service:
        set_rag_service(rag_service)
        print("[main.py] ✅ Knowledge Router rag_service set")
else:
    print("[main.py] [STANDALONE] Skipping VectorStore/RAG initialization")

# ============================================================================
# V5: Storage Helper Functions (Redis with Fallback)
# ============================================================================

def save_session(session_id: str, context: DDSessionContext) -> bool:
    """Save session to Redis or fallback to in-memory storage."""
    if session_store:
        # Convert DDSessionContext to dict for JSON serialization
        context_dict = context.model_dump() if hasattr(context, 'model_dump') else context.dict()
        return session_store.save_session(session_id, context_dict, ttl_days=30)
    else:
        # Fallback to in-memory
        dd_sessions[session_id] = context
        return True


def get_session(session_id: str, user_id: Optional[str] = None) -> Optional[DDSessionContext]:
    """Get session from Redis or fallback to in-memory storage."""
    if session_store:
        context_dict = session_store.get_session(session_id, user_id=user_id)
        if context_dict:
            return DDSessionContext(**context_dict)
        return None
    else:
        # Fallback to in-memory
        context = dd_sessions.get(session_id)
        if not context:
            return None
        if user_id and str(getattr(context, "user_id", "") or "") != str(user_id):
            return None
        return context


def session_exists(session_id: str) -> bool:
    """Check if session exists."""
    if session_store:
        return session_store.session_exists(session_id)
    else:
        return session_id in dd_sessions


def _save_report_to_store(report_id: str, report_data: Dict[str, Any]) -> bool:
    """Save report to Redis or fallback to in-memory storage."""
    if session_store:
        return session_store.save_report(report_id, report_data, ttl_days=365)
    else:
        # Fallback to in-memory
        saved_reports.append(report_data)
        return True


def _get_report_from_store(report_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get report from Redis or fallback to in-memory storage."""
    if session_store:
        return session_store.get_report(report_id, user_id=user_id)
    else:
        # Fallback to in-memory
        report = next((r for r in saved_reports if r["id"] == report_id), None)
        if not report:
            return None
        if user_id and str(report.get("user_id") or "") != str(user_id):
            return None
        return report


def _get_all_reports_from_store(limit: int = 100) -> List[Dict[str, Any]]:
    """Get all reports from Redis or fallback to in-memory storage."""
    if session_store:
        return session_store.get_all_reports(limit=limit)
    else:
        # Fallback to in-memory
        return saved_reports[:limit]


def _delete_report_from_store(report_id: str, user_id: Optional[str] = None) -> bool:
    """Delete report from Redis or fallback to in-memory storage."""
    if session_store:
        return session_store.delete_report(report_id, user_id=user_id)
    else:
        # Fallback to in-memory
        global saved_reports
        report_index = next(
            (
                i for i, r in enumerate(saved_reports)
                if r["id"] == report_id and (not user_id or str(r.get("user_id") or "") == str(user_id))
            ),
            None,
        )
        if report_index is not None:
            saved_reports.pop(report_index)
            return True
        return False


# Phase 4: Initialize Export and DD Workflow Router dependencies
set_get_report_func(_get_report_from_store)
set_session_funcs(get_session, save_session)
print("[main.py] ✅ Export Router and DD Workflow Router initialized")


@app.websocket("/ws/start_dd_analysis")
async def websocket_dd_analysis_endpoint(websocket: WebSocket):
    """
    V3 WebSocket endpoint for Due Diligence (DD) workflow.
    
    Client sends:
    {
        "company_name": "智算科技",
        "bp_file_base64": "...",  # Base64 encoded file
        "bp_filename": "智算科技_BP.pdf",
        "user_id": "investor_001"
    }
    
    Server pushes:
    DDWorkflowMessage with real-time progress updates
    """
    await websocket.accept()
    token = (websocket.query_params.get("token") or "").strip()
    try:
        current_user = await resolve_user_from_token(token)
    except Exception as auth_error:
        print(f"[DD WS] Authentication failed: {auth_error}", flush=True)
        await websocket.close(code=1008, reason="Authentication required")
        return

    print(f"[DEBUG] WebSocket connection accepted", flush=True)
    session_id = ""
    
    try:
        # 1. Receive initial request
        print(f"[DEBUG] Waiting for initial request...", flush=True)
        try:
            initial_request = await websocket.receive_json()
            print(f"[DEBUG] Received request: {initial_request}", flush=True)
        except Exception as recv_error:
            print(f"[ERROR] Failed to receive JSON: {recv_error}", flush=True)
            import traceback
            traceback.print_exc()
            raise
        
        company_name = initial_request.get("company_name")
        bp_file_base64 = initial_request.get("bp_file_base64")  # Legacy: base64 encoded file
        file_id = initial_request.get("file_id")  # V5: File ID from upload API
        bp_filename = initial_request.get("bp_filename", "business_plan.pdf")
        user_id = current_user.id

        # V5: Extract frontend configuration
        project_name = initial_request.get("project_name")
        selected_agents = initial_request.get("selected_agents", [])
        data_sources = initial_request.get("data_sources", [])
        priority = initial_request.get("priority", "normal")
        description = initial_request.get("description")
        knowledge_config = initial_request.get("knowledge", {})
        if not isinstance(knowledge_config, dict):
            knowledge_config = {}
        knowledge_enabled_raw = knowledge_config.get("enabled", initial_request.get("use_knowledge_base"))
        knowledge_category = knowledge_config.get("category", initial_request.get("knowledge_category"))
        knowledge_enabled = bool(knowledge_enabled_raw) if knowledge_enabled_raw is not None else False

        print(f"[DEBUG] company_name={company_name}, has_bp_base64={bp_file_base64 is not None}, file_id={file_id}", flush=True)
        print(f"[DEBUG] project_name={project_name}, selected_agents={selected_agents}", flush=True)
        print(f"[DEBUG] data_sources={data_sources}, priority={priority}", flush=True)
        print(f"[DEBUG] knowledge_enabled={knowledge_enabled}, knowledge_category={knowledge_category}", flush=True)

        if not company_name:
            print(f"[DEBUG] Missing company_name, closing connection", flush=True)
            await websocket.close(code=1008, reason="company_name is required")
            return

        # 2. Generate session ID
        session_id = f"dd_{company_name}_{uuid.uuid4().hex[:8]}"
        print(f"[DEBUG] Generated session_id: {session_id}", flush=True)

        # 3. Load BP file content
        import base64
        bp_file_content = None

        # V5: Try file_id first (new approach)
        if file_id:
            try:
                print(f"[DEBUG] Loading file from File Service: {file_id}", flush=True)
                try:
                    if session_store:
                        owner_user_id = session_store.get_uploaded_file_owner(file_id)
                        if owner_user_id and str(owner_user_id) != str(user_id):
                            await websocket.send_json({
                                "status": "error",
                                "message": "无权访问该上传文件"
                            })
                            await websocket.close(code=1008, reason="File ownership mismatch")
                            return
                except Exception as owner_check_error:
                    print(f"[WARN] File ownership check failed for {file_id}: {owner_check_error}", flush=True)

                # Load file from shared volume
                file_path = f"/var/uploads/{file_id}"

                if os.path.exists(file_path):
                    with open(file_path, "rb") as f:
                        bp_file_content = f.read()
                    print(f"[DEBUG] Loaded file from disk: {len(bp_file_content)} bytes", flush=True)
                else:
                    print(f"[ERROR] File not found: {file_path}", flush=True)
                    await websocket.send_json({
                        "status": "error",
                        "message": f"文件未找到: {file_id}"
                    })
                    await websocket.close(code=1011, reason="File not found")
                    return

            except Exception as file_load_error:
                print(f"[ERROR] Failed to load file {file_id}: {file_load_error}", flush=True)
                import traceback
                traceback.print_exc()
                await websocket.send_json({
                    "status": "error",
                    "message": f"文件加载失败: {str(file_load_error)}"
                })
                await websocket.close(code=1011, reason="File load error")
                return

        # Legacy: Fall back to base64 encoded file
        elif bp_file_base64:
            try:
                bp_file_content = base64.b64decode(bp_file_base64)
                print(f"[DEBUG] Decoded BP file from base64: {len(bp_file_content)} bytes", flush=True)
            except Exception as decode_error:
                print(f"[ERROR] Failed to decode BP file: {decode_error}", flush=True)
                raise
        else:
            print(f"[DEBUG] No BP file provided", flush=True)

        # 4. Create and run state machine
        print(f"[DEBUG] Creating DDStateMachine...", flush=True)
        try:
            state_machine = DDStateMachine(
                session_id=session_id,
                company_name=company_name,
                bp_file_content=bp_file_content,
                bp_filename=bp_filename,
                user_id=user_id,
                # V5: Pass frontend configuration
                project_name=project_name,
                selected_agents=selected_agents,
                data_sources=data_sources,
                priority=priority,
                description=description,
                knowledge_enabled=knowledge_enabled,
                knowledge_category=knowledge_category,
            )
            print(f"[DEBUG] DDStateMachine created successfully", flush=True)
        except Exception as create_error:
            print(f"[ERROR] Failed to create state machine: {create_error}", flush=True)
            import traceback
            traceback.print_exc()
            raise
        
        # Store session
        save_session(session_id, state_machine.get_current_context())
        print(f"[DEBUG] Session stored", flush=True)

        # 5. Execute workflow
        print(f"[DEBUG] Starting workflow execution...", flush=True)
        try:
            await state_machine.run(websocket)
            print(f"[DEBUG] Workflow completed", flush=True)
        except Exception as run_error:
            print(f"[ERROR] Workflow execution failed: {run_error}", flush=True)
            import traceback
            traceback.print_exc()
            raise

        # 6. Update stored session
        save_session(session_id, state_machine.get_current_context())

        # 7. Auto-save report after workflow completion
        try:
            context = state_machine.get_current_context()
            if context.get("current_state") == "COMPLETED":
                from datetime import datetime

                # Generate report ID
                report_id = f"report_{uuid.uuid4().hex[:12]}"

                # Serialize steps (convert Pydantic models to dict)
                steps_data = []
                if hasattr(state_machine, 'steps'):
                    for step in state_machine.steps:
                        if hasattr(step, 'dict'):
                            steps_data.append(step.dict())
                        elif isinstance(step, dict):
                            steps_data.append(step)

                # Create report data
                saved_report = {
                    "id": report_id,
                    "session_id": session_id,
                    "user_id": user_id,
                    "project_name": project_name or company_name,
                    "company_name": company_name,
                    "analysis_type": "due-diligence",
                    "preliminary_im": context.get("preliminary_im"),
                    "team_analysis": context.get("team_analysis"),
                    "market_analysis": context.get("market_analysis"),
                    "steps": steps_data,
                    "status": "completed",
                    "created_at": context.get("created_at", datetime.now().isoformat()),
                    "saved_at": datetime.now().isoformat()
                }

                # Save report to store
                _save_report_to_store(report_id, saved_report)

                print(f"[REPORTS] Auto-saved report {report_id} for {company_name}", flush=True)

                # Notify frontend about saved report
                await websocket.send_json({
                    "type": "report_saved",
                    "report_id": report_id,
                    "session_id": session_id,
                    "message": "报告已自动保存"
                })
        except Exception as save_error:
            print(f"[ERROR] Failed to auto-save report: {save_error}", flush=True)
            import traceback
            traceback.print_exc()
        
    except WebSocketDisconnect:
        print(f"[INFO] Client disconnected from DD session {session_id}", flush=True)
    except Exception as e:
        print(f"[ERROR] Error in DD workflow {session_id}: {e}", flush=True)
        import traceback
        traceback.print_exc()
        
        try:
            if websocket.client_state == 1:  # OPEN
                error_dict = {
                    "session_id": session_id or "unknown",
                    "status": "error",
                    "message": f"DD 工作流出现错误: {str(e)}"
                }
                await websocket.send_json(error_dict)
                await websocket.close(code=1011, reason=f"Internal error: {str(e)}")
        except Exception as close_error:
            print(f"[ERROR] Failed to send error message: {close_error}", flush=True)

# ============================================================================
# DD HTTP API - MOVED TO api/routers/dd_workflow.py
# Old paths (/start_dd_analysis_http, /dd_session/{session_id}) deprecated
# New paths: /api/dd/start_http, /api/dd/session/{session_id}
# ============================================================================

# ============================================================================
# V5: BP File Upload API - MOVED TO api/routers/files.py
# ============================================================================
# All file upload endpoints have been migrated to the new router architecture
# See: app/api/routers/files.py


# ==================== Reports CRUD moved to api/routers/reports.py ====================
# 旧的 Reports CRUD 端点已迁移到新架构

# ==================== Roundtable History API - MOVED TO api/routers/roundtable.py ====================
# 圆桌讨论历史端点已迁移到新架构
# See: app/api/routers/roundtable.py

# ==================== Report Export API - MOVED TO api/routers/export.py ====================
# PDF/Word/Excel/Charts export endpoints have been migrated to export router
# See: app/api/routers/export.py


@app.get("/health", tags=["System (Phase 2)"])
async def health_check():
    """
    Phase 2: System health check endpoint.

    Returns:
        Health status of the service and its dependencies
    """
    import time
    from datetime import datetime

    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "report_orchestrator",
        "version": "3.0.0-phase2",
        "checks": {}
    }

    # Check Redis connection
    try:
        session_store.redis_client.ping()
        health_status["checks"]["redis"] = {
            "status": "healthy",
            "message": "Connected to Redis"
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["redis"] = {
            "status": "unhealthy",
            "message": f"Redis connection failed: {str(e)}"
        }

    # Check LLM Gateway (optional - don't fail health check if down)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{LLM_GATEWAY_URL}/health", timeout=2.0)
            if response.status_code == 200:
                health_status["checks"]["llm_gateway"] = {
                    "status": "healthy",
                    "message": "LLM Gateway is reachable"
                }
            else:
                health_status["checks"]["llm_gateway"] = {
                    "status": "degraded",
                    "message": f"LLM Gateway returned status {response.status_code}"
                }
    except Exception as e:
        health_status["checks"]["llm_gateway"] = {
            "status": "degraded",
            "message": f"LLM Gateway unreachable: {str(e)}"
        }

    # System info
    health_status["system"] = {
        "python_version": "3.11",
        "uptime_seconds": int(time.time() - startup_time) if 'startup_time' in globals() else 0
    }

    return health_status


# Track startup time for uptime calculation
startup_time = time.time()


# ============================================================================
# DD HTTP API - MOVED TO api/routers/dd_workflow.py
# Old paths:
#   - /dd_session/{session_id} -> /api/dd/session/{session_id}
#   - /api/v1/dd/{session_id}/valuation -> /api/dd/{session_id}/valuation
# ============================================================================

# ============================================================================
# V4: Roundtable Discussion APIs - MOVED TO api/routers/roundtable.py
# ============================================================================
# inject_human_input and generate_summary endpoints have been migrated
# See: app/api/routers/roundtable.py

@app.websocket("/ws/roundtable")
async def websocket_roundtable_endpoint(websocket: WebSocket):
    """
    圆桌讨论 WebSocket 端点

    支持多智能体投资分析讨论

    Client sends:
    {
        "action": "start_discussion",
        "topic": "特斯拉2024Q4投资价值分析",
        "company_name": "特斯拉",
        "context": {...}  # Optional: 公司数据、财务数据等上下文
    }

    Server responses:
    {
        "type": "agent_event",
        "event": {
            "agent_name": "市场分析师",
            "event_type": "thinking" | "message" | "completed",
            "message": "...",
            "data": {...}
        }
    }

    OR:
    {
        "type": "discussion_complete",
        "summary": {...}
    }
    """
    await websocket.accept()
    print(f"[ROUNDTABLE] WebSocket connection accepted", flush=True)
    current_user = None

    token = (websocket.query_params.get("token") or "").strip()
    try:
        current_user = await resolve_user_from_token(token)
    except Exception as auth_error:
        print(f"[ROUNDTABLE] Authentication failed: {auth_error}", flush=True)
        await websocket.close(code=1008, reason="Authentication required")
        return

    # Import roundtable components
    from .core.roundtable import Meeting, Message
    from .core.agent_registry import get_registry
    from .core.roundtable.mcp_tools import (
        normalize_knowledge_category,
        reset_roundtable_knowledge_preferences,
        set_roundtable_knowledge_preferences,
    )
    from .core.agent_event_bus import AgentEventBus
    registry = get_registry()

    session_id = None
    runtime_state: Optional[Dict[str, Any]] = None
    kb_preferences_token = None

    # Best-effort cleanup for old completed/error sessions to avoid unbounded memory growth.
    now_ts = time.time()
    for sid, state in list(roundtable_sessions.items()):
        try:
            status = str(state.get("status") or "")
            updated_at = state.get("updated_at") or state.get("created_at")
            updated_ts = datetime.fromisoformat(updated_at).timestamp() if updated_at else now_ts
            ttl_seconds = 3600 if status in {"completed", "error"} else 6 * 3600
            if now_ts - updated_ts > ttl_seconds:
                roundtable_sessions.pop(sid, None)
        except Exception:
            continue

    try:
        # Wait for initial request
        initial_request = await websocket.receive_json()
        print(f"[ROUNDTABLE] Received request: {initial_request}", flush=True)

        action = initial_request.get("action")

        if action == "resume_discussion":
            session_id = str(initial_request.get("session_id") or "").strip()
            runtime_state = roundtable_sessions.get(session_id)
            if not session_id or not runtime_state:
                await websocket.send_json({
                    "type": "error",
                    "message": "未找到可恢复的讨论会话，请重新发起讨论。"
                })
                return

            if str(runtime_state.get("user_id") or "") != str(current_user.id):
                await websocket.close(code=1008, reason="Session ownership mismatch")
                return

            meeting = runtime_state.get("meeting")
            event_bus = runtime_state.get("event_bus")
            if not meeting or not event_bus:
                await websocket.send_json({
                    "type": "error",
                    "message": "会话运行时不可用，请重新发起讨论。"
                })
                return

            await event_bus.subscribe(websocket)

            # Replay persisted event history first (full stream), fallback to in-memory event bus.
            replay_payloads: List[Dict[str, Any]] = []
            if session_store:
                try:
                    persisted_events = session_store.get_session_events(
                        session_id,
                        after_seq=0,
                        limit=5000,
                    )
                    for item in persisted_events:
                        if isinstance(item, dict) and item.get("type") == "agent_event" and isinstance(item.get("event"), dict):
                            replay_payloads.append(item.get("event"))
                except Exception as replay_err:
                    logger.warning(f"[ROUNDTABLE] Failed to replay persisted events for {session_id}: {replay_err}")

            if not replay_payloads:
                replay_payloads = [evt.dict() for evt in event_bus.get_history()]

            for evt in replay_payloads:
                try:
                    await websocket.send_json({
                        "type": "agent_event",
                        "event": evt,
                    })
                except Exception:
                    break

            await websocket.send_json({
                "type": "agents_ready",
                "session_id": session_id,
                "agents": runtime_state.get("agents", []),
                "message": "已恢复讨论会话",
            })

            if runtime_state.get("status") in {"completed", "error"}:
                if runtime_state.get("status") == "completed":
                    await websocket.send_json({
                        "type": "discussion_complete",
                        "session_id": session_id,
                        "report_id": runtime_state.get("report_id"),
                        "summary": runtime_state.get("summary", {}),
                    })
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": runtime_state.get("error") or "讨论已异常结束",
                    })

            while True:
                msg = await websocket.receive_json()
                if isinstance(msg, dict) and msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})

        elif action == "start_discussion":
            topic = initial_request.get("topic", "投资价值分析")
            company_name = initial_request.get("company_name", "目标公司")
            context = initial_request.get("context", {})
            language = initial_request.get("language", "en")  # Default to English for hybrid mode

            knowledge_context = context.get("knowledge", {}) if isinstance(context, dict) else {}
            if not isinstance(knowledge_context, dict):
                knowledge_context = {}
            knowledge_enabled_raw = knowledge_context.get("enabled")
            if knowledge_enabled_raw is None and isinstance(context, dict):
                knowledge_enabled_raw = context.get("use_knowledge_base")
            knowledge_category_raw = knowledge_context.get("category")
            if knowledge_category_raw is None and isinstance(context, dict):
                knowledge_category_raw = context.get("knowledge_category")
            knowledge_enabled = bool(knowledge_enabled_raw) if knowledge_enabled_raw is not None else False
            knowledge_category = normalize_knowledge_category(knowledge_category_raw)
            kb_preferences_token = set_roundtable_knowledge_preferences(
                enabled=knowledge_enabled,
                category=knowledge_category,
            )
            print(
                f"[ROUNDTABLE] Knowledge config: enabled={knowledge_enabled}, category={knowledge_category or 'all'}",
                flush=True,
            )

            # Generate session ID
            session_id = f"roundtable_{company_name}_{uuid.uuid4().hex[:8]}"
            print(f"[ROUNDTABLE] Starting discussion for: {company_name}, session: {session_id}", flush=True)

            # Create agent event bus for real-time updates
            event_bus = AgentEventBus()
            event_bus.max_history = max(event_bus.max_history, 5000)
            await event_bus.subscribe(websocket)

            async def _persist_roundtable_event(event):
                if runtime_state is not None:
                    runtime_state["updated_at"] = datetime.now().isoformat()
                if not session_store:
                    return
                try:
                    session_store.append_session_event(
                        session_id,
                        {
                            "type": "agent_event",
                            "event": event.dict(),
                        },
                        ttl_days=30,
                        max_events=5000,
                    )
                except Exception as persist_err:
                    logger.warning(f"[ROUNDTABLE] Failed to persist event for {session_id}: {persist_err}")

            event_bus.add_local_handler(_persist_roundtable_event)

            # Get selected experts from context (sent by frontend)
            selected_experts = context.get('experts', [])
            print(f"[ROUNDTABLE] Frontend selected experts: {selected_experts}", flush=True)

            # Get max_rounds from frontend context (default to 5 if not provided)
            max_rounds = int(
                context.get(
                    "max_rounds",
                    _ROUNDTABLE_TEMPLATE.get("default_max_rounds", 5),
                )
            )

            # Calculate timeout dynamically:
            # - Each round needs time for all agents to think and respond
            # - Keep at least 1 hour total for long brainstorm sessions
            seconds_per_round = int(
                os.getenv(
                    "ROUNDTABLE_SECONDS_PER_ROUND",
                    str(_ROUNDTABLE_TEMPLATE.get("seconds_per_round", 600)),
                )
            )
            minimum_meeting_duration_seconds = int(
                os.getenv(
                    "ROUNDTABLE_MINIMUM_DURATION_SECONDS",
                    str(_ROUNDTABLE_TEMPLATE.get("minimum_duration_seconds", 3600)),
                )
            )
            max_duration = max(max_rounds * seconds_per_round, minimum_meeting_duration_seconds)

            # Create a placeholder meeting first (we'll set agents later)
            # This allows us to pass the meeting reference to Leader for the end_meeting tool
            from .core.roundtable.tool import FunctionTool

            # Create expert team dynamically based on frontend selection
            agents = []

            # We need to create a temporary meeting object to pass to Leader
            # Then update it with all agents
            temp_meeting_state = {"should_conclude": False, "conclusion_reason": ""}

            def conclude_meeting_func(reason: str = "Leader决定结束会议") -> str:
                """结束会议的函数"""
                temp_meeting_state["should_conclude"] = True
                temp_meeting_state["conclusion_reason"] = reason
                print(f"[ROUNDTABLE] conclude_meeting called: {reason}", flush=True)
                return f"会议将在当前轮次结束后终止。原因: {reason}"

            # ALWAYS ensure leader is created first - Leader is essential for meeting orchestration
            # Frontend intentionally excludes 'leader' from selection (it's always auto-included)
            leader = registry.create_agent("leader", language=language)
            # Register end_meeting tool for Leader
            end_meeting_tool = FunctionTool(
                name="end_meeting",
                description="结束圆桌会议。当讨论已经充分、已形成投资建议、所有专家观点已收集时调用此工具。调用后会议将终止并生成会议纪要。",
                func=conclude_meeting_func,
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "reason": {
                            "type": "string",
                            "description": "结束会议的原因，例如'所有专家已充分表达观点，已形成投资建议'"
                        }
                    },
                    "required": ["reason"]
                }
            )
            leader.register_tool(end_meeting_tool)
            print(f"[ROUNDTABLE] Leader ALWAYS created with end_meeting tool", flush=True)
            agents.append(leader)

            enabled_roundtable_ids = {
                str(cfg.get("agent_id"))
                for cfg in registry.list_agents(scope="roundtable")
                if str(cfg.get("agent_id") or "").strip()
            }

            def _to_registry_agent_id(expert_id: str) -> str:
                if not expert_id:
                    return ""
                chat_id = str(expert_id).strip()
                if chat_id in EXPERT_CHAT_AGENT_REGISTRY_IDS:
                    return EXPERT_CHAT_AGENT_REGISTRY_IDS[chat_id]
                return chat_id.replace("-", "_")

            # Add other agents based on selection
            added_registry_ids = {"leader"}
            for expert_id in selected_experts:
                registry_id = _to_registry_agent_id(expert_id)
                if not registry_id or registry_id == "leader":
                    continue
                if registry_id not in enabled_roundtable_ids:
                    continue
                if registry_id in added_registry_ids:
                    continue
                try:
                    agents.append(registry.create_agent(registry_id, language=language, quick_mode=False))
                    added_registry_ids.add(registry_id)
                except Exception as create_error:
                    logger.warning(
                        "[ROUNDTABLE] Failed to create selected expert '%s' (%s): %s",
                        expert_id,
                        registry_id,
                        create_error,
                    )

            # Fallback: if no agents selected, use default 5 agents
            if len(agents) <= 1:
                print(f"[ROUNDTABLE] No agents selected, using defaults", flush=True)
                default_registry_ids = [
                    "market_analyst",
                    "financial_expert",
                    "team_evaluator",
                    "risk_assessor",
                ]
                for registry_id in default_registry_ids:
                    if registry_id in added_registry_ids:
                        continue
                    if registry_id not in enabled_roundtable_ids:
                        continue
                    agents.append(registry.create_agent(registry_id, language=language, quick_mode=False))
                    added_registry_ids.add(registry_id)

            for agent in agents:
                setattr(agent, "user_id", str(current_user.id))
                setattr(agent, "session_id", session_id)
                agent_id = getattr(agent, "id", None) or getattr(agent, "name", None) or "unknown"
                setattr(agent, "atomic_agent_id", str(agent_id))

            num_agents = len(agents)
            print(f"[ROUNDTABLE] Created {num_agents} agents: {[a.name for a in agents]}", flush=True)

            # Send agent list to frontend
            await websocket.send_json({
                "type": "agents_ready",
                "session_id": session_id,
                "agents": [agent.name for agent in agents],
                "message": f"圆桌讨论准备就绪，共{num_agents}位专家参与"
            })

            print(f"[ROUNDTABLE] Config: max_rounds={max_rounds}, agents={num_agents}, timeout={max_duration}s ({max_duration//60} min)", flush=True)

            # Create meeting with dynamic configuration
            meeting = Meeting(
                agents=agents,
                agent_event_bus=event_bus,
                max_turns=max_rounds,
                max_duration_seconds=max_duration
            )

            # Store meeting in global dict for Human-in-the-Loop support
            active_meetings[session_id] = meeting
            meeting._owner_user_id = current_user.id
            runtime_state = {
                "session_id": session_id,
                "user_id": str(current_user.id),
                "topic": topic,
                "company_name": company_name,
                "status": "running",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "max_rounds": max_rounds,
                "agents": [agent.name for agent in agents],
                "knowledge": {
                    "enabled": knowledge_enabled,
                    "category": knowledge_category or "all",
                },
                "meeting": meeting,
                "event_bus": event_bus,
                "summary": None,
                "report_id": None,
                "error": None,
            }
            roundtable_sessions[session_id] = runtime_state
            print(f"[ROUNDTABLE] Meeting stored with session_id: {session_id}", flush=True)

            # Link the meeting state to the meeting object
            # This allows conclude_meeting_func to actually affect the meeting
            def check_conclude():
                if temp_meeting_state["should_conclude"]:
                    meeting.should_conclude = True
                    meeting.conclusion_reason = temp_meeting_state["conclusion_reason"]

            # We'll check this in the meeting loop - patch the meeting's run method
            original_should_conclude = meeting.should_conclude
            meeting._temp_state = temp_meeting_state

            # Check for unpredictable topics (short-term price predictions, etc.)
            unpredictable_patterns = [
                ("价格预测", "价格走势"),
                ("未来.*天", "短期走势"),
                ("会涨还是跌", "价格方向"),
                ("明天.*走势", "短期走势"),
                ("短期.*预测", "短期预测"),
                ("能不能买", "投资时机"),
                ("现在买.*合适", "投资时机"),
                ("接下来.*会怎么", "短期走势"),
            ]

            import re
            unpredictability_warning = None
            for pattern, category in unpredictable_patterns:
                if re.search(pattern, topic):
                    unpredictability_warning = category
                    print(f"[ROUNDTABLE] Detected unpredictable topic: {category}", flush=True)
                    break

            # Build initial message based on context
            initial_content = f"各位专家好！今天我们要讨论{company_name}的{topic}。"

            # Add unpredictability warning if detected
            if unpredictability_warning:
                initial_content += f"""

---
## ⚠️ 重要声明：关于「{unpredictability_warning}」类问题的说明

**请所有专家注意**：此次讨论涉及短期市场走势或价格预测。以下是重要提醒：

1. **本质上不可预测**：短期市场走势受到随机事件、突发新闻、市场情绪等多种不可控因素影响，任何预测都具有高度不确定性。

2. **无人能可靠预测短期价格**：即使是华尔街顶级交易员也无法可靠预测3天、1周甚至1个月的价格走势。

3. **基于数据分析，而非猜测**：请各位专家：
   - 使用搜索工具获取最新的市场数据和新闻（使用 time_range="day" 或 days=3）
   - 分析当前的基本面和技术指标
   - 识别潜在的风险和机会
   - **但不要做出确定性的价格预测**

4. **表达不确定性**：请在结论中明确表达置信度，例如：
   - "基于当前数据，存在看涨信号，但置信度较低（约40%）"
   - "市场情绪偏空，但短期走势高度不确定"

5. **避免极端结论**：请勿给出"强烈建议做多/做空"这类确定性结论，而是提供分析框架和风险提示。

---
"""

            # Add context if available
            if context:
                if context.get("summary"):
                    initial_content += f"\n\n公司概况：\n{context['summary']}"
                if context.get("financial_data"):
                    initial_content += f"\n\n关键财务数据已提供。"
                if context.get("market_data"):
                    initial_content += f"\n\n市场数据已提供。"

            # Check for history reference - continuation from previous discussion
            history_reference = context.get("history_reference") if context else None
            if history_reference:
                previous_topic = history_reference.get("topic", "")
                previous_minutes = history_reference.get("meeting_minutes", "")
                excerpt_chars = int(_ROUNDTABLE_TEMPLATE.get("history_excerpt_chars", 2000))

                print(f"[ROUNDTABLE] Using history reference from: {previous_topic}", flush=True)

                initial_content += f"""

---
## ⚠️ 重要背景：这是一次延续性讨论

我们之前对「{previous_topic}」进行过讨论，以下是上次会议的纪要摘要：

<previous_meeting_minutes>
{previous_minutes[:excerpt_chars]}{'...(摘要已截断)' if len(previous_minutes) > excerpt_chars else ''}
</previous_meeting_minutes>

### 🔴 关键提醒（请所有专家注意）：

1. **不要被上次结论束缚**：上次的结论是基于当时的信息和分析，市场和情况可能已经变化。

2. **批判性审视**：请每位专家先审视上次结论的假设是否仍然成立，是否有新的数据或情况需要考虑。

3. **鼓励提出异议**：如果你有不同于上次结论的观点，请大胆提出并说明理由。新的视角可能揭示之前忽略的风险或机会。

4. **更新数据支撑**：请使用搜索工具获取最新的市场数据和新闻，确保分析基于最新信息。

5. **明确记录变化**：如果你的观点与上次相同，请说明原因；如果改变了观点，也请说明原因。

---
"""

            initial_content += "\n\n请各位从自己的专业角度分析，给出投资建议。请领导者主持讨论。"

            initial_message = Message(
                sender="主持人",
                recipient="ALL",
                content=initial_content
            )

            print(f"[ROUNDTABLE] Starting meeting...", flush=True)

            # Run discussion
            try:
                result = await meeting.run(initial_message=initial_message)

                print(f"[ROUNDTABLE] Discussion completed", flush=True)
                if runtime_state is not None:
                    runtime_state["status"] = "completed"
                    runtime_state["updated_at"] = datetime.now().isoformat()
                    runtime_state["summary"] = result

                # Save meeting minutes as a report
                meeting_minutes = result.get("meeting_minutes", "")
                if meeting_minutes:
                    report_id = f"roundtable_{session_id}"
                    report_title = await _generate_roundtable_report_title(
                        topic=topic,
                        meeting_minutes=meeting_minutes,
                        language=language,
                    )
                    enriched_minutes = _prepend_original_topic_to_minutes(
                        meeting_minutes=meeting_minutes,
                        topic=topic,
                        language=language,
                    )
                    roundtable_report = {
                        "id": report_id,
                        "user_id": current_user.id,
                        "type": "roundtable",  # 圆桌会议类型
                        "topic": topic,  # 用户原始输入课题
                        "original_topic": topic,
                        "display_title": report_title,
                        "title": report_title,  # 兼容性字段
                        "project_name": report_title,
                        "company_name": company_name,
                        "scenario": "roundtable-discussion",
                        "created_at": datetime.now().isoformat(),
                        "status": "completed",
                        "session_id": session_id,
                        "config": {
                            "max_rounds": max_rounds,
                            "num_agents": num_agents,
                            "agents": [a.name for a in agents],
                            "language": language,
                            "knowledge": {
                                "enabled": knowledge_enabled,
                                "category": knowledge_category or "all",
                            },
                        },
                        "meeting_minutes": enriched_minutes,  # 会议纪要 (Markdown)
                        "discussion_summary": {
                            "total_turns": result.get("total_turns", 0),
                            "total_messages": result.get("total_messages", 0),
                            "total_duration_seconds": result.get("total_duration_seconds", 0),
                            "participating_agents": result.get("participating_agents", []),
                            "agent_stats": result.get("agent_stats", {}),
                            "message_type_stats": result.get("message_type_stats", {}),
                            "conversation_history": result.get("conversation_history", [])  # 添加消息历史
                        },
                        "message_count": result.get("total_messages", 0),
                        "total_turns": result.get("total_turns", 0),
                        "conclusion_reason": meeting.conclusion_reason if hasattr(meeting, 'conclusion_reason') else ""
                    }

                    # Save to Redis
                    if _save_report_to_store(report_id, roundtable_report):
                        print(f"[ROUNDTABLE] Meeting minutes saved as report: {report_id}", flush=True)
                    else:
                        print(f"[ROUNDTABLE] Failed to save meeting minutes", flush=True)

                    # Add report_id to result for frontend
                    result["report_id"] = report_id
                    if runtime_state is not None:
                        runtime_state["report_id"] = report_id

                if runtime_state is not None:
                    runtime_state["summary"] = result

                # Send completion summary (check WebSocket state first)
                try:
                    from starlette.websockets import WebSocketState
                    if websocket.client_state == WebSocketState.CONNECTED:
                        await websocket.send_json({
                            "type": "discussion_complete",
                            "session_id": session_id,
                            "report_id": result.get("report_id"),
                            "summary": result
                        })
                except Exception as send_err:
                    print(f"[ROUNDTABLE] Failed to send completion (WebSocket may be closed): {send_err}", flush=True)

            except Exception as meeting_error:
                print(f"[ROUNDTABLE] Meeting error: {meeting_error}", flush=True)
                import traceback
                traceback.print_exc()
                if runtime_state is not None:
                    runtime_state["status"] = "error"
                    runtime_state["error"] = str(meeting_error)
                    runtime_state["updated_at"] = datetime.now().isoformat()

                # Check if WebSocket is still open before sending error
                try:
                    from starlette.websockets import WebSocketState
                    if websocket.client_state == WebSocketState.CONNECTED:
                        await websocket.send_json({
                            "type": "error",
                            "message": f"讨论过程中出现错误: {str(meeting_error)}"
                        })
                except Exception as send_err:
                    print(f"[ROUNDTABLE] Failed to send error (WebSocket may be closed): {send_err}", flush=True)

            finally:
                # Unsubscribe event bus
                await event_bus.unsubscribe(websocket)
                if runtime_state is not None and runtime_state.get("status") in {"completed", "error"}:
                    removed = active_meetings.pop(session_id, None)
                    if removed is not None:
                        print(f"[ROUNDTABLE] Cleaned up active meeting: {session_id}", flush=True)

        else:
            await websocket.send_json({
                "type": "error",
                "message": f"未知的操作: {action}"
            })

    except WebSocketDisconnect:
        print(f"[ROUNDTABLE] Client disconnected from session {session_id}", flush=True)
    except Exception as e:
        print(f"[ROUNDTABLE] Error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        if runtime_state is not None:
            runtime_state["status"] = "error"
            runtime_state["error"] = str(e)
            runtime_state["updated_at"] = datetime.now().isoformat()

        try:
            if websocket.client_state == 1:  # OPEN
                await websocket.send_json({
                    "type": "error",
                    "message": f"圆桌讨论出现错误: {str(e)}"
                })
        except Exception as send_error:
            print(f"[ROUNDTABLE] Failed to send error message: {send_error}", flush=True)
    finally:
        if kb_preferences_token is not None:
            reset_roundtable_knowledge_preferences(kb_preferences_token)
        if runtime_state is not None:
            try:
                event_bus = runtime_state.get("event_bus")
                if event_bus:
                    await event_bus.unsubscribe(websocket)
            except Exception:
                pass
            if runtime_state.get("status") in {"completed", "error"} and session_id:
                active_meetings.pop(session_id, None)


# ============================================================================
# V4: Intelligent Conversation WebSocket Endpoint
# ============================================================================

@app.websocket("/ws/expert-chat")
async def websocket_expert_chat_endpoint(websocket: WebSocket):
    """
    Expert Chat Hub WebSocket endpoint.

    Core routing rules:
    1) Default (no @): Leader handles and may delegate to specialists.
    2) Direct mention (@agent): route directly to that specialist, Leader does not intervene.
    """
    await websocket.accept()
    token = (websocket.query_params.get("token") or "").strip()
    try:
        current_user = await resolve_user_from_token(token)
    except Exception as auth_error:
        logger.warning(f"[ExpertChat] Authentication failed: {auth_error}")
        await websocket.close(code=1008, reason="Authentication required")
        return

    session_id = f"expertchat_{uuid.uuid4().hex[:10]}"
    language = "zh-CN"
    knowledge_enabled = False
    knowledge_category = "all"

    active_chat_sessions[session_id] = {
        "user_id": str(current_user.id),
        "messages": [],
        "language": language,
        "knowledge_enabled": knowledge_enabled,
        "knowledge_category": knowledge_category,
        "shared_evidence_board": [],
        "agents": {},
        "agent_pool_signature": "",
    }
    _ensure_expert_chat_agent_pool(
        active_chat_sessions[session_id],
        language=language,
        knowledge_enabled=knowledge_enabled,
        knowledge_category=knowledge_category,
        user_id=str(current_user.id),
        session_id=session_id,
    )
    inflight_turn_tasks: Set[asyncio.Task] = set()

    def _track_turn_task(task: asyncio.Task) -> asyncio.Task:
        inflight_turn_tasks.add(task)
        task.add_done_callback(lambda t: inflight_turn_tasks.discard(t))
        return task

    try:
        await websocket.send_json(
            {
                "type": "session_started",
                "session_id": session_id,
                "agents": _build_expert_chat_agents(language),
            }
        )

        while True:
            payload = await websocket.receive_json()
            message_type = payload.get("type", "user_message")

            if message_type == "ping":
                await websocket.send_json({"type": "pong", "session_id": session_id})
                continue

            if message_type == "start_session":
                language = payload.get("language", language) or language
                kb = payload.get("knowledge", {})
                if isinstance(kb, dict):
                    knowledge_enabled = bool(kb.get("enabled", knowledge_enabled))
                    knowledge_category = str(kb.get("category", knowledge_category) or "all")
                requested_session_id = str(payload.get("session_id", "") or "").strip()
                resume_history = _sanitize_resume_history(payload.get("history", []))

                if requested_session_id and requested_session_id != session_id:
                    existing = active_chat_sessions.get(requested_session_id)
                    if existing and str(existing.get("user_id")) != str(current_user.id):
                        await websocket.send_json(
                            {
                                "type": "error",
                                "session_id": session_id,
                                "message": "Invalid session ownership",
                            }
                        )
                        continue

                    active_chat_sessions.pop(session_id, None)
                    if existing:
                        session_id = requested_session_id
                    else:
                        session_id = requested_session_id
                        active_chat_sessions[session_id] = {
                            "user_id": str(current_user.id),
                            "messages": resume_history,
                            "language": language,
                            "knowledge_enabled": knowledge_enabled,
                            "knowledge_category": knowledge_category,
                            "shared_evidence_board": _rebuild_shared_evidence_board_from_history(resume_history),
                            "agents": {},
                            "agent_pool_signature": "",
                        }
                elif requested_session_id and requested_session_id == session_id and resume_history:
                    if not active_chat_sessions[session_id]["messages"]:
                        active_chat_sessions[session_id]["messages"] = resume_history

                active_chat_sessions.setdefault(
                    session_id,
                    {
                        "user_id": str(current_user.id),
                        "messages": [],
                        "language": language,
                        "knowledge_enabled": knowledge_enabled,
                        "knowledge_category": knowledge_category,
                        "shared_evidence_board": [],
                        "agents": {},
                        "agent_pool_signature": "",
                    },
                )
                active_chat_sessions[session_id]["language"] = language
                active_chat_sessions[session_id]["knowledge_enabled"] = knowledge_enabled
                active_chat_sessions[session_id]["knowledge_category"] = knowledge_category
                _ensure_expert_chat_agent_pool(
                    active_chat_sessions[session_id],
                    language=language,
                    knowledge_enabled=knowledge_enabled,
                    knowledge_category=knowledge_category,
                    user_id=str(current_user.id),
                    session_id=session_id,
                )
                await websocket.send_json(
                    {
                        "type": "session_ready",
                        "session_id": session_id,
                        "agents": _build_expert_chat_agents(language),
                    }
                )
                continue

            if message_type != "user_message":
                await websocket.send_json(
                    {
                        "type": "error",
                        "session_id": session_id,
                        "message": f"Unsupported message type: {message_type}",
                    }
                )
                continue

            content = str(payload.get("content", "")).strip()
            attachments = _sanitize_expert_chat_attachments(payload.get("attachments", []))
            if not content and not attachments:
                await websocket.send_json(
                    {"type": "error", "session_id": session_id, "message": "Empty message"}
                )
                continue

            language = payload.get("language", language) or language
            kb = payload.get("knowledge", {})
            attachment_summary = _attachments_summary(attachments, language)
            effective_content = content or (
                "请基于上传图片进行分析并给出结论。"
                if _is_zh(language)
                else "Please analyze the uploaded image and provide conclusions."
            )
            if isinstance(kb, dict):
                knowledge_enabled = bool(kb.get("enabled", knowledge_enabled))
                knowledge_category = str(kb.get("category", knowledge_category) or "all")
            session_state = active_chat_sessions.setdefault(
                session_id,
                {
                    "user_id": str(current_user.id),
                    "messages": [],
                    "language": language,
                    "knowledge_enabled": knowledge_enabled,
                    "knowledge_category": knowledge_category,
                    "shared_evidence_board": [],
                    "agents": {},
                    "agent_pool_signature": "",
                },
            )
            session_state.setdefault("shared_evidence_board", [])
            if not session_state.get("shared_evidence_board") and session_state.get("messages"):
                session_state["shared_evidence_board"] = _rebuild_shared_evidence_board_from_history(
                    session_state["messages"]
                )
            session_state["language"] = language
            session_state["knowledge_enabled"] = knowledge_enabled
            session_state["knowledge_category"] = knowledge_category
            session_agents = _ensure_expert_chat_agent_pool(
                session_state,
                language=language,
                knowledge_enabled=knowledge_enabled,
                knowledge_category=knowledge_category,
                user_id=str(current_user.id),
                session_id=session_id,
            )

            history = session_state["messages"]
            history.append(
                {
                    "speaker": "User",
                    "role": "user",
                    "content": effective_content if not attachments else f"{effective_content}\n\n[{attachment_summary}]",
                    "timestamp": datetime.utcnow().isoformat(),
                    "attachments": [
                        {"name": att.get("name"), "mime_type": att.get("mime_type"), "size": att.get("size")}
                        for att in attachments
                    ],
                }
            )

            attachment_context = await _build_attachment_context(
                user_message=effective_content,
                attachments=attachments,
                language=language,
            )

            mentions = _extract_mentions(effective_content)
            direct_targets = [m for m in mentions if m in EXPERT_CHAT_AGENT_PROFILES]

            try:
                # Direct mode: user explicitly mentions specialists.
                if direct_targets:
                    targets = [m for m in direct_targets if m != "leader"]
                    if not targets:
                        targets = ["leader"]
                    record_route_decision(
                        channel="expert_chat",
                        mode="direct",
                        status="success",
                        latency_seconds=0.0,
                    )

                    await websocket.send_json(
                        {
                            "type": "route_decided",
                            "session_id": session_id,
                            "mode": "direct",
                            "targets": targets,
                        }
                    )

                    for agent_id in targets:
                        agent_name = _display_agent_name(agent_id, language)
                        shared_evidence_board = session_state.get("shared_evidence_board", [])
                        shared_evidence_context = format_shared_evidence_context(
                            shared_evidence_board,
                            language=language,
                        )
                        await websocket.send_json(
                            {
                                "type": "agent_thinking",
                                "session_id": session_id,
                                "agent_id": agent_id,
                                "agent_name": agent_name,
                            }
                        )

                        if agent_id == "leader":
                            response_text = await _leader_direct_reply(
                                user_message=effective_content,
                                history=history,
                                language=language,
                                knowledge_enabled=knowledge_enabled,
                                knowledge_category=knowledge_category,
                                user_id=str(current_user.id),
                                session_id=session_id,
                                attachments=attachments,
                                attachment_context=attachment_context,
                                session_agents=session_agents,
                            )
                            response_summary = compact_text(
                                response_text.replace("\n", " "),
                                max_chars=280,
                            )
                        else:
                            specialist_result = await _ask_specialist(
                                agent_id=agent_id,
                                user_message=effective_content,
                                history=history,
                                language=language,
                                knowledge_enabled=knowledge_enabled,
                                knowledge_category=knowledge_category,
                                user_id=str(current_user.id),
                                session_id=session_id,
                                attachments=attachments,
                                attachment_context=attachment_context,
                                shared_evidence_context=shared_evidence_context,
                                session_agents=session_agents,
                                delegated_by_leader=False,
                            )
                            response_text = str(specialist_result.get("content", "")).strip()
                            response_summary = str(specialist_result.get("summary", "")).strip()[:320]
                            evidence_packet = specialist_result.get("evidence_packet") or {}
                            if isinstance(evidence_packet, dict) and evidence_packet.get("summary"):
                                shared_evidence_board.append(evidence_packet)
                                if len(shared_evidence_board) > 24:
                                    del shared_evidence_board[:-24]

                        history.append(
                            {
                                "speaker": agent_name,
                                "role": "assistant",
                                "agent_id": agent_id,
                                "content": response_text,
                                "content_summary": response_summary,
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        )
                        await websocket.send_json(
                            {
                                "type": "agent_message",
                                "session_id": session_id,
                                "agent_id": agent_id,
                                "agent_name": agent_name,
                                "content": response_text,
                                "mode": "direct",
                            }
                        )

                # Default mode: Leader first, then optional delegation.
                else:
                    await websocket.send_json(
                        {
                            "type": "route_decided",
                            "session_id": session_id,
                            "mode": "leader",
                            "targets": ["leader"],
                        }
                    )

                    try:
                        plan = await _leader_plan_route(
                            user_message=effective_content,
                            history=history,
                            language=language,
                            knowledge_enabled=knowledge_enabled,
                            knowledge_category=knowledge_category,
                            attachments_summary=attachment_summary,
                        )
                    except Exception as route_error:
                        logger.warning(
                            "[ExpertChat] Leader route planning failed, fallback to leader direct reply: %s",
                            route_error,
                        )
                        plan = {
                            "need_specialists": False,
                            "specialists": [],
                            "leader_reply": "",
                            "reason": "leader_router_error",
                        }
                        await websocket.send_json(
                            {
                                "type": "route_fallback",
                                "session_id": session_id,
                                "mode": "leader",
                                "reason": "leader_router_error",
                            }
                        )

                    delegated_ids = [
                        sid for sid in plan.get("specialists", []) if sid in EXPERT_SPECIALIST_IDS
                    ]
                    specialist_outputs: List[Dict[str, str]] = []
                    planned_leader_reply = str(plan.get("leader_reply", "")).strip()
                    shared_evidence_board = session_state.get("shared_evidence_board", [])

                    if delegated_ids:
                        execution_stages = build_execution_stages(
                            delegated_ids,
                            max_parallel=EXPERT_CHAT_MAX_PARALLEL_SPECIALISTS,
                        )
                        await websocket.send_json(
                            {
                                "type": "delegation_started",
                                "session_id": session_id,
                                "from": "leader",
                                "targets": delegated_ids,
                                "stages": execution_stages,
                                "reason": plan.get("reason", "leader_decision"),
                            }
                        )

                        for stage_index, stage_agent_ids in enumerate(execution_stages, start=1):
                            await websocket.send_json(
                                {
                                    "type": "delegation_stage",
                                    "session_id": session_id,
                                    "stage_index": stage_index,
                                    "stage_total": len(execution_stages),
                                    "targets": stage_agent_ids,
                                }
                            )
                            stage_history = list(history)
                            shared_evidence_context = format_shared_evidence_context(
                                shared_evidence_board,
                                language=language,
                            )
                            stage_tasks: Dict[str, asyncio.Task] = {}
                            for sid in stage_agent_ids:
                                specialist_name = _display_agent_name(sid, language)
                                await websocket.send_json(
                                    {
                                        "type": "agent_thinking",
                                        "session_id": session_id,
                                        "agent_id": sid,
                                        "agent_name": specialist_name,
                                    }
                                )
                                stage_tasks[sid] = _track_turn_task(
                                    asyncio.create_task(
                                        _ask_specialist(
                                            agent_id=sid,
                                            user_message=effective_content,
                                            history=stage_history,
                                            language=language,
                                            knowledge_enabled=knowledge_enabled,
                                            knowledge_category=knowledge_category,
                                            user_id=str(current_user.id),
                                            session_id=session_id,
                                            attachments=attachments,
                                            attachment_context=attachment_context,
                                            shared_evidence_context=shared_evidence_context,
                                            session_agents=session_agents,
                                            delegated_by_leader=True,
                                        )
                                    )
                                )

                            stage_results = await asyncio.gather(
                                *[stage_tasks[sid] for sid in stage_agent_ids],
                                return_exceptions=True,
                            )
                            for sid, result in zip(stage_agent_ids, stage_results):
                                if isinstance(result, Exception):
                                    raise RuntimeError(
                                        f"Specialist '{sid}' execution failed: {result}"
                                    ) from result
                                specialist_name = _display_agent_name(sid, language)
                                output = str(result.get("content", "")).strip()
                                output_summary = str(result.get("summary", "")).strip()[:320]
                                specialist_outputs.append(
                                    {
                                        "agent_id": sid,
                                        "agent_name": specialist_name,
                                        "content": compact_text(output, max_chars=1400),
                                    }
                                )
                                evidence_packet = result.get("evidence_packet") or {}
                                if isinstance(evidence_packet, dict) and evidence_packet.get("summary"):
                                    shared_evidence_board.append(evidence_packet)
                                    if len(shared_evidence_board) > 24:
                                        del shared_evidence_board[:-24]
                                history.append(
                                    {
                                        "speaker": specialist_name,
                                        "role": "assistant",
                                        "agent_id": sid,
                                        "content": output,
                                        "content_summary": output_summary,
                                        "timestamp": datetime.utcnow().isoformat(),
                                    }
                                )
                                await websocket.send_json(
                                    {
                                        "type": "agent_message",
                                        "session_id": session_id,
                                        "agent_id": sid,
                                        "agent_name": specialist_name,
                                        "content": output,
                                        "mode": "delegated",
                                        "stage_index": stage_index,
                                        "stage_total": len(execution_stages),
                                    }
                                )

                        await websocket.send_json(
                            {
                                "type": "delegation_finished",
                                "session_id": session_id,
                                "from": "leader",
                                "targets": delegated_ids,
                                "stages": execution_stages,
                            }
                        )

                    should_send_leader_followup = (
                        not specialist_outputs or EXPERT_CHAT_LEADER_FOLLOWUP_AFTER_DELEGATION
                    )
                    if should_send_leader_followup:
                        leader_name = _display_agent_name("leader", language)
                        await websocket.send_json(
                            {
                                "type": "agent_thinking",
                                "session_id": session_id,
                                "agent_id": "leader",
                                "agent_name": leader_name,
                            }
                        )

                        if specialist_outputs:
                            leader_response = await _leader_summarize_with_specialists(
                                user_message=effective_content,
                                specialist_outputs=specialist_outputs,
                                history=history,
                                language=language,
                                user_id=str(current_user.id),
                                session_id=session_id,
                                attachments=attachments,
                                attachment_context=attachment_context,
                                session_agents=session_agents,
                            )
                        elif planned_leader_reply:
                            leader_response = planned_leader_reply
                        else:
                            leader_response = await _leader_direct_reply(
                                user_message=effective_content,
                                history=history,
                                language=language,
                                knowledge_enabled=knowledge_enabled,
                                knowledge_category=knowledge_category,
                                user_id=str(current_user.id),
                                session_id=session_id,
                                attachments=attachments,
                                attachment_context=attachment_context,
                                session_agents=session_agents,
                            )

                        history.append(
                            {
                                "speaker": leader_name,
                                "role": "assistant",
                                "agent_id": "leader",
                                "content": leader_response,
                                "content_summary": compact_text(
                                    leader_response.replace("\n", " "),
                                    max_chars=280,
                                ),
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        )
                        await websocket.send_json(
                            {
                                "type": "agent_message",
                                "session_id": session_id,
                                "agent_id": "leader",
                                "agent_name": leader_name,
                                "content": leader_response,
                                "mode": "leader",
                            }
                        )

                # Keep context bounded.
                if len(history) > EXPERT_CHAT_MAX_HISTORY:
                    active_chat_sessions[session_id]["messages"] = history[-EXPERT_CHAT_MAX_HISTORY:]

            except Exception as llm_error:
                logger.exception("[ExpertChat] message handling failed")
                await websocket.send_json(
                    {
                        "type": "error",
                        "session_id": session_id,
                        "message": f"专家对话处理失败: {str(llm_error)}",
                    }
                )

    except WebSocketDisconnect:
        logger.info(f"[ExpertChat] Client disconnected: {session_id}")
        pending = [t for t in list(inflight_turn_tasks) if not t.done()]
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
    except Exception as e:
        logger.exception(f"[ExpertChat] Fatal error: {e}")
        try:
            if websocket.client_state == 1:
                await websocket.send_json(
                    {
                        "type": "error",
                        "session_id": session_id,
                        "message": f"会话异常中断: {str(e)}",
                    }
                )
        except Exception:
            pass
    finally:
        pending = [t for t in list(inflight_turn_tasks) if not t.done()]
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        active_chat_sessions.pop(session_id, None)

@app.websocket("/ws/conversation")
async def websocket_conversation_endpoint(websocket: WebSocket):
    """
    V4 智能对话WebSocket端点

    支持意图识别、对话式交互、用户确认后再启动分析

    Client sends:
    {
        "type": "message",
        "content": "用户输入的消息",
        "bp_file_base64": "...",  # Optional
        "bp_filename": "..."       # Optional
    }

    OR:
    {
        "type": "action",
        "action": "start_dd_analysis",  # 或其他action
        "company_name": "...",
        "bp_file_base64": "...",  # Optional
        "bp_filename": "...",      # Optional
        "user_id": "..."
    }

    Server responses:
    {
        "type": "intent_recognized",
        "intent": {...},
        "message": "...",
        "options": [...] 
    }

    OR:
    {
        "type": "dd_progress",
        "session_id": "...",
        "status": "...",
        "current_step": {...}
    }
    """
    await websocket.accept()
    print(f"[CONVERSATION] WebSocket connection accepted", flush=True)
    token = (websocket.query_params.get("token") or "").strip()
    try:
        current_user = await resolve_user_from_token(token)
    except Exception as auth_error:
        print(f"[CONVERSATION] Authentication failed: {auth_error}", flush=True)
        await websocket.close(code=1008, reason="Authentication required")
        return

    # Initialize intent recognizer and conversation manager
    intent_recognizer = IntentRecognizer(llm_gateway_url=LLM_GATEWAY_URL)
    conversation_manager = ConversationManager(intent_recognizer)

    session_id = None

    try:
        while True:
            # Receive message from client
            try:
                message = await websocket.receive_json()
                print(f"[CONVERSATION] Received message: {message}", flush=True)
            except Exception as recv_error:
                print(f"[CONVERSATION] Error receiving message: {recv_error}", flush=True)
                break

            message_type = message.get("type", "message")

            if message_type == "message":
                # User sent a text message - recognize intent
                user_input = message.get("content", "")

                if not user_input:
                    await websocket.send_json({
                        "type": "error",
                        "message": "请输入消息内容"
                    })
                    continue

                # Process message with conversation manager
                response = await conversation_manager.process_message(user_input)

                # Send intent recognition result
                await websocket.send_json({
                    "type": "intent_recognized",
                    "intent": {
                        "type": response["intent"].type,
                        "confidence": response["intent"].confidence,
                        "entities": response["intent"].extracted_entities
                    },
                    "response_type": response["response_type"],
                    "message": response.get("message", ""),
                    "options": response.get("options", []),
                    "suggested_action": response.get("suggested_action"),
                    "file_upload_hint": response.get("file_upload_hint")
                })
                print(f"[CONVERSATION] Sent intent recognition response", flush=True)

            elif message_type == "action":
                # User confirmed an action - execute it
                action = message.get("action")
                company_name = message.get("company_name", "")
                bp_file_base64 = message.get("bp_file_base64")
                bp_filename = message.get("bp_filename", "business_plan.pdf")
                requested_user_id = message.get("user_id")
                user_id = current_user.id
                if requested_user_id and str(requested_user_id) != str(user_id):
                    print(
                        f"[CONVERSATION] Ignoring mismatched requested user_id={requested_user_id}; using authenticated user_id={user_id}",
                        flush=True,
                    )

                if action == "start_dd_analysis":
                    # Start DD analysis workflow
                    print(f"[CONVERSATION] Starting DD analysis for: {company_name}", flush=True)

                    # Generate session ID
                    session_id = f"dd_{company_name}_{uuid.uuid4().hex[:8]}"

                    # Decode BP file if provided
                    import base64
                    bp_file_content = None
                    if bp_file_base64:
                        try:
                            bp_file_content = base64.b64decode(bp_file_base64)
                            print(f"[CONVERSATION] Decoded BP file: {len(bp_file_content)} bytes", flush=True)
                        except Exception as decode_error:
                            print(f"[CONVERSATION] Failed to decode BP file: {decode_error}", flush=True)
                            await websocket.send_json({
                                "type": "error",
                                "message": "BP文件解码失败"
                            })
                            continue

                    # Send acknowledgment
                    await websocket.send_json({
                        "type": "action_started",
                        "action": "dd_analysis",
                        "session_id": session_id,
                        "message": f"正在为「{company_name}」启动完整尽职调查分析..."
                    })

                    # Create and run DD state machine
                    try:
                        state_machine = DDStateMachine(
                            session_id=session_id,
                            company_name=company_name,
                            bp_file_content=bp_file_content,
                            bp_filename=bp_filename,
                            user_id=user_id,
                            knowledge_enabled=bool(message.get("use_knowledge_base", False)),
                            knowledge_category=message.get("knowledge_category"),
                        )

                        # Store session
                        save_session(session_id, state_machine.get_current_context())

                        # Execute workflow (this will send progress updates via websocket)
                        await state_machine.run(websocket)

                        # Update stored session
                        save_session(session_id, state_machine.get_current_context())

                        print(f"[CONVERSATION] DD analysis completed for {session_id}", flush=True)

                    except Exception as dd_error:
                        print(f"[CONVERSATION] DD analysis failed: {dd_error}", flush=True)
                        import traceback
                        traceback.print_exc()

                        await websocket.send_json({
                            "type": "error",
                            "message": f"分析过程中出现错误: {str(dd_error)}"
                        })

                elif action == "quick_overview":
                    # Quick overview (simplified analysis)
                    print(f"[CONVERSATION] Starting quick overview for: {company_name}", flush=True)

                    await websocket.send_json({
                        "type": "action_started",
                        "action": "quick_overview",
                        "message": f"正在快速获取「{company_name}」的基本信息..."
                    })

                    try:
                        async with httpx.AsyncClient(timeout=30.0) as client:
                            # Step 1: Get company basic info
                            await websocket.send_json({
                                "type": "quick_overview_progress",
                                "step": "fetching_data",
                                "message": "正在获取公司数据..."
                            })

                            public_data_resp = await client.post(
                                f"{EXTERNAL_DATA_URL}/get_company_info",
                                json={"ticker": company_name}
                            )

                            if public_data_resp.status_code != 200:
                                raise Exception(f"无法获取公司信息: {public_data_resp.status_code}")

                            response_data = public_data_resp.json()

                            # Handle ambiguity - return options to user
                            if response_data.get('status') == 'multiple_options':
                                await websocket.send_json({
                                    "type": "quick_overview_ambiguity",
                                    "company_name": company_name,
                                    "options": response_data.get('data', []),
                                    "message": "找到多个匹配的公司，请选择："
                                })
                                continue

                            public_data = response_data.get('data', {})

                            # Step 2: Generate quick summary with LLM
                            await websocket.send_json({
                                "type": "quick_overview_progress",
                                "step": "generating_summary",
                                "message": "正在生成概览..."
                            })

                            prompt = f"""请根据以下公司数据，生成一份简洁的快速概览（不超过200字）。
包含：公司名称、主营业务、市值/估值、近期表现亮点。

公司数据:
{json.dumps(public_data, ensure_ascii=False, indent=2)}

请用中文回复，格式简洁明了。"""

                            summary = await call_llm_gateway(client, [{"role": "user", "parts": [prompt]}])

                            # Build quick overview result
                            overview_result = {
                                "company_name": public_data.get('company_name', company_name),
                                "ticker": public_data.get('ticker', company_name),
                                "summary": summary,
                                "key_metrics": {
                                    "market_cap": public_data.get('market_cap'),
                                    "sector": public_data.get('sector'),
                                    "industry": public_data.get('industry'),
                                    "price": public_data.get('current_price'),
                                    "change_percent": public_data.get('price_change_percent'),
                                },
                                "generated_at": datetime.now().isoformat()
                            }

                            await websocket.send_json({
                                "type": "quick_overview_result",
                                "company_name": overview_result["company_name"],
                                "ticker": overview_result["ticker"],
                                "summary": overview_result["summary"],
                                "key_metrics": overview_result["key_metrics"],
                                "generated_at": overview_result["generated_at"]
                            })

                            print(f"[CONVERSATION] Quick overview completed for: {company_name}", flush=True)

                    except Exception as overview_error:
                        print(f"[CONVERSATION] Quick overview failed: {overview_error}", flush=True)
                        import traceback
                        traceback.print_exc()

                        await websocket.send_json({
                            "type": "quick_overview_error",
                            "company_name": company_name,
                            "error": str(overview_error),
                            "message": f"快速概览获取失败: {str(overview_error)}"
                        })

                elif action == "free_chat":
                    # Free chat mode
                    print(f"[CONVERSATION] Entering free chat mode", flush=True)

                    await websocket.send_json({
                        "type": "chat_mode_active",
                        "message": "已进入自由对话模式。有什么我可以帮助您的吗？"
                    })

                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"未知的操作: {action}"
                    })

            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"未知的消息类型: {message_type}"
                })

    except WebSocketDisconnect:
        print(f"[CONVERSATION] Client disconnected", flush=True)
    except Exception as e:
        print(f"[CONVERSATION] Error: {e}", flush=True)
        import traceback
        traceback.print_exc()

        try:
            if websocket.client_state == 1:  # OPEN
                await websocket.send_json({
                    "type": "error",
                    "message": f"对话过程中出现错误: {str(e)}"
                })
        except Exception as send_error:
            print(f"[CONVERSATION] Failed to send error message: {send_error}", flush=True)

# ============================================================================
# Phase 2: Knowledge Base Management APIs - MOVED TO api/routers/knowledge.py
# ============================================================================
# All Knowledge Base endpoints have been migrated to the new router architecture
# See: app/api/routers/knowledge.py


# ============================================================================
# Analysis Module V2 - 统一分析API (5个投资场景)
# ============================================================================

from .models.analysis_models import (
    AnalysisRequest,
    InvestmentScenario
)
from .core.orchestrators.early_stage_orchestrator import EarlyStageInvestmentOrchestrator
from .core.orchestrators.growth_orchestrator import GrowthInvestmentOrchestrator
from .core.orchestrators.public_market_orchestrator import PublicMarketInvestmentOrchestrator
from .core.orchestrators.alternative_orchestrator import AlternativeInvestmentOrchestrator
from .core.orchestrators.industry_research_orchestrator import IndustryResearchOrchestrator


# POST /api/v2/analysis/start - MOVED TO api/routers/analysis.py

ANALYSIS_RUNTIME_MAX_EVENTS = int(os.getenv("ANALYSIS_RUNTIME_MAX_EVENTS", "5000"))
analysis_runtime_sessions: Dict[str, Dict[str, Any]] = {}


def _analysis_runtime_active(runtime: Optional[Dict[str, Any]]) -> bool:
    if not runtime:
        return False
    task = runtime.get("task")
    return bool(task and not task.done())


def _analysis_store_event(session_id: str, event: Dict[str, Any]):
    if not session_store:
        return
    try:
        session_store.append_session_event(session_id, event, ttl_days=30, max_events=ANALYSIS_RUNTIME_MAX_EVENTS)
    except Exception as store_err:
        logger.warning(f"[V2 Runtime] Failed to persist event for {session_id}: {store_err}")


async def _analysis_emit_event(runtime: Dict[str, Any], event: Dict[str, Any]):
    session_id = runtime["session_id"]
    runtime["updated_at"] = datetime.now().isoformat()
    runtime["last_event_seq"] = int(runtime.get("last_event_seq", 0)) + 1
    payload = {
        **event,
        "session_id": session_id,
        "seq": runtime["last_event_seq"],
        "timestamp": event.get("timestamp") or datetime.now().isoformat(),
    }

    runtime.setdefault("events", []).append(payload)
    if len(runtime["events"]) > ANALYSIS_RUNTIME_MAX_EVENTS:
        runtime["events"] = runtime["events"][-ANALYSIS_RUNTIME_MAX_EVENTS:]

    _analysis_store_event(session_id, payload)

    stale = []
    for ws in runtime.get("subscribers", []):
        try:
            await ws.send_json(payload)
        except Exception:
            stale.append(ws)
    if stale:
        runtime["subscribers"] = [ws for ws in runtime.get("subscribers", []) if ws not in stale]


def _create_analysis_orchestrator(
    session_id: str,
    request: AnalysisRequest,
    event_callback,
):
    common_kwargs = {
        "session_id": session_id,
        "request": request,
        "websocket": None,
        "event_callback": event_callback,
    }
    if request.scenario == InvestmentScenario.EARLY_STAGE:
        return EarlyStageInvestmentOrchestrator(**common_kwargs)
    if request.scenario == InvestmentScenario.GROWTH:
        return GrowthInvestmentOrchestrator(**common_kwargs)
    if request.scenario == InvestmentScenario.PUBLIC_MARKET:
        return PublicMarketInvestmentOrchestrator(**common_kwargs)
    if request.scenario == InvestmentScenario.ALTERNATIVE:
        return AlternativeInvestmentOrchestrator(**common_kwargs)
    if request.scenario == InvestmentScenario.INDUSTRY_RESEARCH:
        return IndustryResearchOrchestrator(**common_kwargs)
    raise ValueError(f"场景 {request.scenario.value} 暂未实现")


async def _run_analysis_runtime(session_id: str):
    runtime = analysis_runtime_sessions.get(session_id)
    if not runtime:
        return

    request: AnalysisRequest = runtime["request"]
    user_id = runtime["user_id"]
    runtime["status"] = "running"
    runtime["updated_at"] = datetime.now().isoformat()

    async def event_callback(event: Dict[str, Any]):
        await _analysis_emit_event(runtime, event)

    try:
        orchestrator = _create_analysis_orchestrator(
            session_id=session_id,
            request=request,
            event_callback=event_callback,
        )
        result = await orchestrator.orchestrate()
        runtime["result"] = result
        runtime["status"] = "completed"
        runtime["updated_at"] = datetime.now().isoformat()
        logger.info(f"[V2 Runtime] Completed session={session_id}")
    except Exception as e:
        runtime["status"] = "error"
        runtime["error"] = str(e)
        runtime["updated_at"] = datetime.now().isoformat()
        logger.error(f"[V2 Runtime] Failed session={session_id}: {e}")
        await _analysis_emit_event(
            runtime,
            {
                "type": "error",
                "data": {"error": str(e)},
            },
        )
        if session_store:
            try:
                session = session_store.get_session(session_id, user_id=user_id) or {}
                session["status"] = "error"
                session["error"] = str(e)
                session["updated_at"] = datetime.now().isoformat()
                session_store.save_session(session_id, session, ttl_days=30)
            except Exception:
                pass


async def _start_analysis_runtime(session_id: str, request: AnalysisRequest, user_id: str):
    now_ts = time.time()
    for sid, rt in list(analysis_runtime_sessions.items()):
        try:
            status = str(rt.get("status") or "")
            updated_at = rt.get("updated_at") or rt.get("created_at")
            updated_ts = datetime.fromisoformat(updated_at).timestamp() if updated_at else now_ts
            ttl_seconds = 3600 if status in {"completed", "error"} else 6 * 3600
            if now_ts - updated_ts > ttl_seconds:
                analysis_runtime_sessions.pop(sid, None)
        except Exception:
            continue

    existing = analysis_runtime_sessions.get(session_id)
    if existing and _analysis_runtime_active(existing):
        return

    runtime = existing or {
        "session_id": session_id,
        "user_id": str(user_id),
        "request": request,
        "status": "created",
        "error": None,
        "events": [],
        "last_event_seq": 0,
        "subscribers": [],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "result": None,
        "task": None,
    }
    runtime["user_id"] = str(user_id)
    runtime["request"] = request
    runtime["error"] = None
    runtime["status"] = "created"
    runtime["updated_at"] = datetime.now().isoformat()
    analysis_runtime_sessions[session_id] = runtime

    runtime["task"] = asyncio.create_task(_run_analysis_runtime(session_id))
    logger.info(f"[V2 Runtime] Started background analysis session={session_id}")


async def _load_analysis_request_from_store(session_id: str, user_id: str) -> Optional[AnalysisRequest]:
    if not session_store:
        return None
    try:
        session = session_store.get_session(session_id, user_id=user_id)
        if not session:
            return None
        req_payload = session.get("request")
        if not isinstance(req_payload, dict):
            return None
        request = AnalysisRequest(**req_payload)
        request = request.model_copy(update={"user_id": user_id})
        return request
    except Exception as e:
        logger.warning(f"[V2 Runtime] Failed to load request from store for {session_id}: {e}")
        return None


async def _load_analysis_session_from_store(session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    if not session_store:
        return None
    try:
        session = session_store.get_session(session_id, user_id=user_id)
        return session if isinstance(session, dict) else None
    except Exception as e:
        logger.warning(f"[V2 Runtime] Failed to load session snapshot for {session_id}: {e}")
        return None


async def _analysis_subscribe_websocket(
    runtime: Dict[str, Any],
    websocket: WebSocket,
    after_seq: int = 0,
):
    if websocket not in runtime["subscribers"]:
        runtime["subscribers"].append(websocket)

    await websocket.send_json({
        "type": "session_snapshot",
        "session_id": runtime["session_id"],
        "timestamp": datetime.now().isoformat(),
        "data": {
            "status": runtime.get("status", "unknown"),
            "updated_at": runtime.get("updated_at"),
            "error": runtime.get("error"),
        },
    })

    # Replay from in-memory runtime first (fast path).
    replay_events = [
        evt for evt in runtime.get("events", [])
        if int(evt.get("seq", 0)) > int(after_seq)
    ]

    # If no in-memory replay is available, fallback to Redis event stream.
    if not replay_events and session_store:
        try:
            replay_events = session_store.get_session_events(
                runtime["session_id"],
                after_seq=int(after_seq),
                limit=ANALYSIS_RUNTIME_MAX_EVENTS,
            )
        except Exception:
            replay_events = []

    for event in replay_events:
        await websocket.send_json(event)


set_analysis_runtime_starter(_start_analysis_runtime)


@app.websocket("/ws/v2/analysis/{session_id}")
async def websocket_analysis_v2(websocket: WebSocket, session_id: str):
    """
    V2: 统一分析WebSocket端点（订阅模式）
    - 分析任务在后台持续运行，不绑定单个WebSocket生命周期
    - WebSocket仅用于订阅实时事件、断线重连和事件回放
    """
    await websocket.accept()
    token = (websocket.query_params.get("token") or "").strip()
    try:
        current_user = await resolve_user_from_token(token)
    except Exception as auth_error:
        logger.warning(f"[V2 WS] Authentication failed for session={session_id}: {auth_error}")
        await websocket.close(code=1008, reason="Authentication required")
        return

    # Ensure the pre-created session belongs to the authenticated user.
    if session_store:
        try:
            existing = session_store.get_session(session_id, user_id=current_user.id)
            if not existing and session_store.session_exists(session_id):
                await websocket.close(code=1008, reason="Session ownership mismatch")
                return
        except Exception as store_err:
            logger.warning(f"[V2 WS] Session ownership check skipped due to store error: {store_err}")

    logger.info(f"[V2 WS] Client connected: session={session_id}")
    runtime = analysis_runtime_sessions.get(session_id)
    requested_after_seq = 0
    initial_payload = None

    try:
        try:
            initial_payload = await asyncio.wait_for(websocket.receive_json(), timeout=5.0)
        except asyncio.TimeoutError:
            initial_payload = None

        if isinstance(initial_payload, dict):
            msg_type = initial_payload.get("type")
            if msg_type == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat(),
                })
                initial_payload = None
            elif msg_type == "subscribe":
                requested_after_seq = int(initial_payload.get("cursor") or 0)

        if runtime and str(runtime.get("user_id")) != str(current_user.id):
            await websocket.close(code=1008, reason="Session ownership mismatch")
            return

        if not runtime:
            session_snapshot = await _load_analysis_session_from_store(session_id, str(current_user.id))
            session_status = str((session_snapshot or {}).get("status") or "").lower()

            # Completed/errored sessions should be replayed, not restarted.
            if session_snapshot and session_status in {"completed", "error"}:
                req_payload = session_snapshot.get("request")
                request_obj: Optional[AnalysisRequest] = None
                if isinstance(req_payload, dict):
                    try:
                        request_obj = AnalysisRequest(**req_payload)
                        request_obj = request_obj.model_copy(update={"user_id": current_user.id})
                    except Exception:
                        request_obj = None

                runtime = {
                    "session_id": session_id,
                    "user_id": str(current_user.id),
                    "request": request_obj,
                    "status": session_status,
                    "error": session_snapshot.get("error"),
                    "events": [],
                    "last_event_seq": session_store.get_latest_session_event_seq(session_id) if session_store else 0,
                    "subscribers": [],
                    "created_at": session_snapshot.get("started_at") or datetime.now().isoformat(),
                    "updated_at": session_snapshot.get("updated_at") or datetime.now().isoformat(),
                    "result": session_snapshot.get("final_report"),
                    "task": None,
                }
                analysis_runtime_sessions[session_id] = runtime

            if not runtime:
                request_obj = None
                if isinstance(initial_payload, dict) and initial_payload.get("scenario"):
                    request_obj = AnalysisRequest(**initial_payload)
                    request_obj = request_obj.model_copy(update={"user_id": current_user.id})
                else:
                    request_obj = await _load_analysis_request_from_store(session_id, str(current_user.id))

                if not request_obj:
                    await websocket.send_json({
                        "type": "error",
                        "session_id": session_id,
                        "timestamp": datetime.now().isoformat(),
                        "data": {
                            "error": "No analysis request payload found for this session"
                        }
                    })
                    await websocket.close(code=1008, reason="Missing analysis request payload")
                    return

                await _start_analysis_runtime(session_id, request_obj, str(current_user.id))
                runtime = analysis_runtime_sessions.get(session_id)

        if not runtime:
            await websocket.close(code=1011, reason="Failed to initialize runtime")
            return

        await _analysis_subscribe_websocket(runtime, websocket, after_seq=requested_after_seq)

        # Message loop: keep-alive + optional manual replay
        while True:
            message = await websocket.receive_json()
            if not isinstance(message, dict):
                continue

            msg_type = message.get("type")
            if msg_type == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat(),
                })
            elif msg_type == "subscribe":
                cursor = int(message.get("cursor") or 0)
                await _analysis_subscribe_websocket(runtime, websocket, after_seq=cursor)

    except WebSocketDisconnect:
        logger.info(f"[V2 WS] Client disconnected: session={session_id}")
    except Exception as e:
        logger.error(f"[V2 WS] Error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "error": str(e)
                }
            })
        except Exception:
            pass
    finally:
        if runtime and websocket in runtime.get("subscribers", []):
            runtime["subscribers"] = [ws for ws in runtime.get("subscribers", []) if ws is not websocket]


# GET /api/v2/analysis/{session_id}/status - MOVED TO api/routers/analysis.py
# GET /api/v2/analysis/scenarios - MOVED TO api/routers/analysis.py
