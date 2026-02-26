"""
Roundtable Router
圆桌会议路由

提供圆桌讨论的历史、搜索、注入用户输入和会议纪要生成功能
"""

import logging
import os
from typing import Dict, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from ...core.auth import CurrentUser, get_current_user
from ...core.model_policy import resolve_model_for_role

logger = logging.getLogger(__name__)

router = APIRouter()

# Global references - will be set from main.py
_active_meetings: Dict[str, Any] = {}
_llm_gateway_url: str = os.getenv("LLM_GATEWAY_URL", "http://llm_gateway:8003")


def set_active_meetings(meetings: Dict[str, Any]):
    """Set the active meetings reference"""
    global _active_meetings
    _active_meetings = meetings


def set_llm_gateway_url(url: str):
    """Set the LLM Gateway URL"""
    global _llm_gateway_url
    _llm_gateway_url = url


@router.get("/history", tags=["Roundtable"])
async def get_roundtable_history(
    limit: int = 20,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    获取圆桌讨论历史列表

    用于在开始新讨论时选择历史讨论作为参考基础
    """
    try:
        from ...core.session_store import SessionStore
        store = SessionStore()

        roundtable_reports = store.get_roundtable_reports(limit=limit, user_id=current_user.id)

        return {
            "success": True,
            "total": len(roundtable_reports),
            "roundtables": roundtable_reports
        }
    except Exception as e:
        logger.error(f"Failed to get roundtable history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{report_id}", tags=["Roundtable"])
async def get_roundtable_detail(
    report_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    获取圆桌讨论详情

    获取完整的会议纪要和讨论记录，用于参考
    """
    try:
        from ...core.session_store import SessionStore
        store = SessionStore()

        report = store.get_roundtable_report_full(report_id, user_id=current_user.id)

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
async def search_similar_roundtables(
    topic: str,
    limit: int = 5,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    搜索相似的圆桌讨论

    根据主题关键词搜索历史讨论，用于自动推荐参考
    """
    try:
        from ...core.session_store import SessionStore
        store = SessionStore()

        similar_reports = store.search_similar_roundtables(topic=topic, limit=limit, user_id=current_user.id)

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
async def inject_human_input(
    request: dict,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    注入用户补充信息到正在进行的圆桌讨论中 (Human-in-the-Loop)

    Request body:
    {
        "session_id": "roundtable_xxx_12345678",
        "content": "用户补充的信息内容",
        "anchor_message_id": "可选，选择一个历史消息作为分叉点"
    }

    Returns:
    {
        "status": "success",
        "message": "用户输入已注入到讨论中"
    }
    """
    session_id = request.get("session_id")
    content = request.get("content", "")
    anchor_message_id = request.get("anchor_message_id", "")

    if not session_id:
        raise HTTPException(status_code=400, detail="Missing session_id")

    # Find the active meeting
    meeting = _active_meetings.get(session_id)
    if not meeting:
        raise HTTPException(status_code=404, detail=f"No active meeting found for session_id: {session_id}")
    owner_user_id = getattr(meeting, "_owner_user_id", None)
    if owner_user_id and str(owner_user_id) != str(current_user.id):
        raise HTTPException(status_code=404, detail=f"No active meeting found for session_id: {session_id}")

    # Check if meeting is actually waiting for human input
    if not meeting.waiting_for_human:
        logger.warning(f"Meeting {session_id} is not waiting for human input, but injecting anyway")

    # Inject the human input
    try:
        await meeting.inject_human_input(content, anchor_message_id=anchor_message_id)
        logger.info(f"Successfully injected human input for session: {session_id}")
        has_content = bool((content or "").strip())
        return {
            "status": "success",
            "message": "用户输入已注入到讨论中" if has_content else "已继续讨论（无补充）",
            "has_content": has_content,
            "anchor_message_id": anchor_message_id or None,
            "session_id": session_id
        }
    except Exception as e:
        logger.error(f"Error injecting human input: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to inject human input: {str(e)}")


@router.post("/pause_for_human_input", tags=["Roundtable"])
async def pause_for_human_input(
    request: dict,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    主动打断当前会议，让会议进入“等待用户输入”状态。

    Request body:
    {
        "session_id": "roundtable_xxx_12345678"
    }
    """
    session_id = request.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing session_id")

    meeting = _active_meetings.get(session_id)
    if not meeting:
        raise HTTPException(status_code=404, detail=f"No active meeting found for session_id: {session_id}")

    owner_user_id = getattr(meeting, "_owner_user_id", None)
    if owner_user_id and str(owner_user_id) != str(current_user.id):
        raise HTTPException(status_code=404, detail=f"No active meeting found for session_id: {session_id}")

    try:
        paused_now = await meeting.pause_for_human_intervention(reason="manual_interrupt")
        return {
            "status": "success",
            "session_id": session_id,
            "waiting_for_human": True,
            "already_waiting": not paused_now,
            "message": "会议已暂停，等待用户补充信息" if paused_now else "会议已在等待用户输入",
        }
    except Exception as e:
        logger.error(f"Error pausing meeting for human input: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to pause meeting: {str(e)}")


@router.post("/generate_summary", tags=["Roundtable"])
async def generate_roundtable_summary(
    request: dict,
    _: CurrentUser = Depends(get_current_user),
):
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
        language = request.get("language", "en")  # Default to English

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
                    "model": resolve_model_for_role("roundtable_summary"),
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


@router.post("/generate_summary_stream", tags=["Roundtable"])
async def generate_roundtable_summary_stream(
    request: dict,
    _: CurrentUser = Depends(get_current_user),
):
    """
    流式生成会议纪要 - 使用 Server-Sent Events (SSE)
    
    实时逐字返回生成的内容，减少用户等待感
    """
    from fastapi.responses import StreamingResponse
    import json
    
    topic = request.get("topic", "投资讨论")
    messages = request.get("messages", [])
    participants = request.get("participants", [])
    rounds = request.get("rounds", 0)
    language = request.get("language", "en")  # Default to English
    
    # 构建对话历史
    dialogue_text = "\n\n".join([
        f"【{msg.get('speaker')}】\n{msg.get('content')}"
        for msg in messages
    ])
    
    # 构建prompt
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

### 1. Key Viewpoints Summary
### 2. Key Discussion Points  
### 3. Consensus Reached
### 4. Action Recommendations
### 5. Risk Alerts
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

### 一、核心观点总结
### 二、关键讨论点
### 三、达成的共识
### 四、行动建议
### 五、风险提示
"""

    async def generate_stream():
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                # 调用LLM Gateway的流式端点
                async with client.stream(
                    "POST",
                    f"{_llm_gateway_url}/chat/stream",
                    json={
                        "history": [
                            {"role": "user", "parts": ["你是一位专业的会议记录员，擅长总结和提炼会议要点。"]},
                            {"role": "model", "parts": ["好的，我会以专业、简洁的方式为您整理会议纪要。"]},
                            {"role": "user", "parts": [summary_prompt]}
                        ],
                        "temperature": 0.3,
                        "model": resolve_model_for_role("roundtable_summary"),
                    }
                ) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            # 直接转发SSE事件
                            yield f"{line}\n\n"
                            
        except Exception as e:
            logger.error(f"Streaming summary error: {e}")
            yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
