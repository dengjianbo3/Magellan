from app.core.expert_chat.orchestration import (
    build_execution_stages,
    extract_specialist_response,
    format_shared_evidence_context,
)


def test_build_execution_stages_dependency_aware():
    stages = build_execution_stages(
        ["risk-assessor", "technical-analyst", "market-analyst"],
        max_parallel=2,
    )
    assert stages == [["technical-analyst", "market-analyst"], ["risk-assessor"]]


def test_build_execution_stages_bounded_parallel_chunks():
    stages = build_execution_stages(
        ["technical-analyst", "market-analyst", "macro-economist"],
        max_parallel=2,
    )
    assert stages == [["technical-analyst", "market-analyst"], ["macro-economist"]]


def test_extract_specialist_response_strips_internal_packet():
    raw = """
核心结论：趋势偏空，短线谨慎。
- 价格跌破关键均线
- 成交量未有效放大

[INTERNAL_EVIDENCE_PACKET]
{"summary":"偏空","key_points":["跌破均线","反弹乏力"],"risks":["假突破"],"confidence":78}
[/INTERNAL_EVIDENCE_PACKET]
""".strip()

    parsed = extract_specialist_response(
        agent_id="technical-analyst",
        agent_name="技术分析师",
        raw_content=raw,
        language="zh-CN",
    )
    assert "INTERNAL_EVIDENCE_PACKET" not in parsed["content"]
    assert parsed["evidence_packet"]["summary"] == "偏空"
    assert parsed["evidence_packet"]["confidence"] == 78


def test_format_shared_evidence_context_includes_recent_packets():
    context = format_shared_evidence_context(
        [
            {
                "agent_id": "technical-analyst",
                "agent_name": "技术分析师",
                "summary": "日线破位，反弹力度弱。",
                "key_points": ["EMA空头排列", "RSI接近超卖"],
                "confidence": 80,
            },
            {
                "agent_id": "macro-economist",
                "agent_name": "宏观分析师",
                "summary": "美元偏弱，对风险资产中期支撑仍在。",
                "key_points": ["DXY低位", "长端利率平稳"],
                "confidence": 72,
            },
        ],
        language="zh-CN",
    )
    assert "技术分析师" in context
    assert "宏观分析师" in context
    assert "置信度" in context

