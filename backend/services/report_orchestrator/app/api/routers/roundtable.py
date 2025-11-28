"""
Roundtable Router
圆桌会议路由

提供圆桌讨论的历史、搜索、注入用户输入和会议纪要生成功能
"""

import logging
from typing import Dict, Any

import httpx
from fastapi import APIRouter, HTTPException, Depends

logger = logging.getLogger(__name__)

router = APIRouter()

# Global references - will be set from main.py
_active_meetings: Dict[str, Any] = {}
_llm_gateway_url: str = "http://llm_gateway:8003"


def set_active_meetings(meetings: Dict[str, Any]):
    """Set the active meetings reference"""
    global _active_meetings
    _active_meetings = meetings


def set_llm_gateway_url(url: str):
    """Set the LLM Gateway URL"""
    global _llm_gateway_url
    _llm_gateway_url = url


@router.get("/history", tags=["Roundtable"])
async def get_roundtable_history(limit: int = 20):
    """
    获取圆桌讨论历史列表

    用于在开始新讨论时选择历史讨论作为参考基础
    """
    try:
        from ...core.session_store import SessionStore
        store = SessionStore()

        roundtable_reports = store.get_roundtable_reports(limit=limit)

        return {
            "success": True,
            "total": len(roundtable_reports),
            "roundtables": roundtable_reports
        }
    except Exception as e:
        logger.error(f"Failed to get roundtable history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{report_id}", tags=["Roundtable"])
async def get_roundtable_detail(report_id: str):
    """
    获取圆桌讨论详情

    获取完整的会议纪要和讨论记录，用于参考
    """
    try:
        from ...core.session_store import SessionStore
        store = SessionStore()

        report = store.get_roundtable_report_full(report_id)

        if not report:
            raise HTTPException(status_code=404, detail=f"Roundtable report {report_id} not found")

        return {
            "success": True,
            "roundtable": report
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get roundtable detail {report_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/similar", tags=["Roundtable"])
async def search_similar_roundtables(topic: str, limit: int = 5):
    """
    搜索相似的圆桌讨论

    根据主题关键词搜索历史讨论，用于自动推荐参考
    """
    try:
        from ...core.session_store import SessionStore
        store = SessionStore()

        similar_reports = store.search_similar_roundtables(topic=topic, limit=limit)

        return {
            "success": True,
            "query": topic,
            "total": len(similar_reports),
            "similar_roundtables": similar_reports
        }
    except Exception as e:
        logger.error(f"Failed to search similar roundtables: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/inject_human_input", tags=["Roundtable"])
async def inject_human_input(request: dict):
    """
    注入用户补充信息到正在进行的圆桌讨论中 (Human-in-the-Loop)

    Request body:
    {
        "session_id": "roundtable_xxx_12345678",
        "content": "用户补充的信息内容"
    }

    Returns:
    {
        "status": "success",
        "message": "用户输入已注入到讨论中"
    }
    """
    session_id = request.get("session_id")
    content = request.get("content")

    if not session_id or not content:
        raise HTTPException(status_code=400, detail="Missing session_id or content")

    # Find the active meeting
    meeting = _active_meetings.get(session_id)
    if not meeting:
        raise HTTPException(status_code=404, detail=f"No active meeting found for session_id: {session_id}")

    # Check if meeting is actually waiting for human input
    if not meeting.waiting_for_human:
        logger.warning(f"Meeting {session_id} is not waiting for human input, but injecting anyway")

    # Inject the human input
    try:
        await meeting.inject_human_input(content)
        logger.info(f"Successfully injected human input for session: {session_id}")
        return {
            "status": "success",
            "message": "用户输入已注入到讨论中",
            "session_id": session_id
        }
    except Exception as e:
        logger.error(f"Error injecting human input: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to inject human input: {str(e)}")


@router.post("/generate_summary", tags=["Roundtable"])
async def generate_roundtable_summary(request: dict):
    """
    根据圆桌讨论历史生成会议纪要

    Request body:
    {
        "topic": "讨论主题",
        "messages": [{speaker, content, timestamp}],
        "participants": ["leader", "market-analyst", ...],
        "rounds": 5
    }
    """
    try:
        topic = request.get("topic", "投资讨论")
        messages = request.get("messages", [])
        participants = request.get("participants", [])
        rounds = request.get("rounds", 0)
        language = request.get("language", "zh")  # 获取语言偏好

        # 构建对话历史
        dialogue_text = "\n\n".join([
            f"【{msg.get('speaker')}】\n{msg.get('content')}"
            for msg in messages
        ])

        # 使用LLM生成会议纪要 - 根据语言选择prompt
        if language == "en":
            summary_prompt = f"""Based on the following roundtable discussion, generate a professional meeting minutes.

Discussion Topic: {topic}
Participants: {', '.join(participants)}
Discussion Rounds: {rounds}

Discussion Content:
{dialogue_text}

Please generate meeting minutes in the following format:

## Meeting Minutes

**Topic**: {topic}
**Participants**: {', '.join(participants)}
**Date & Time**: [Current time]

### 1. Key Viewpoints Summary
[Summarize main viewpoints of each expert, list by bullet points]

### 2. Key Discussion Points
[List key issues and disagreements in the discussion]

### 3. Consensus Reached
[List conclusions agreed upon by all parties]

### 4. Action Recommendations
[Specific recommendations based on the discussion]

### 5. Risk Alerts
[Risk factors mentioned in the discussion]

Please present in a professional and concise manner with clear logic.
"""
        else:
            summary_prompt = f"""基于以下圆桌讨论内容，生成一份专业的会议纪要。

讨论主题：{topic}
参与专家：{', '.join(participants)}
讨论轮次：{rounds}

讨论内容：
{dialogue_text}

请按以下格式生成会议纪要：

## 会议纪要

**会议主题**: {topic}
**参与人员**: {', '.join(participants)}
**讨论时间**: [当前时间]

### 一、核心观点总结
[总结各专家的主要观点，分点列出]

### 二、关键讨论点
[列出讨论中的关键问题和分歧点]

### 三、达成的共识
[列出各方达成一致的结论]

### 四、行动建议
[基于讨论提出的具体建议]

### 五、风险提示
[讨论中提到的风险因素]

请以专业、简洁的方式呈现，确保逻辑清晰。
"""

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{_llm_gateway_url}/v1/chat/completions",
                json={
                    "model": "gpt-4",
                    "messages": [
                        {"role": "system", "content": "你是一位专业的会议记录员，擅长总结和提炼会议要点。"},
                        {"role": "user", "content": summary_prompt}
                    ],
                    "temperature": 0.3
                }
            )

            if response.status_code == 200:
                llm_response = response.json()
                summary = llm_response.get("choices", [{}])[0].get("message", {}).get("content", "")

                return {
                    "success": True,
                    "summary": summary
                }
            else:
                raise HTTPException(status_code=500, detail="LLM服务调用失败")

    except Exception as e:
        logger.error(f"Failed to generate roundtable summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
