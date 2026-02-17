import pytest

from app.api.routers.monitoring import (
    FrontendError,
    ErrorReportRequest,
    clear_errors,
    get_recent_errors,
    report_errors,
    error_buffers,
    user_metrics,
)
from app.core.auth import set_current_user_id


def _request(msg: str) -> ErrorReportRequest:
    return ErrorReportRequest(
        errors=[
            FrontendError(
                timestamp="2026-01-01T00:00:00",
                message=msg,
                type="js_error",
                url="/dashboard",
            )
        ]
    )


@pytest.mark.asyncio
async def test_monitoring_error_buffer_is_user_scoped():
    error_buffers.clear()
    user_metrics.clear()

    set_current_user_id("u1")
    await report_errors(_request("u1-error"))

    set_current_user_id("u2")
    await report_errors(_request("u2-error"))

    set_current_user_id("u1")
    u1_view = await get_recent_errors(limit=10)
    assert u1_view["user_id"] == "u1"
    assert len(u1_view["errors"]) == 1
    assert u1_view["errors"][0]["message"] == "u1-error"

    set_current_user_id("u2")
    u2_view = await get_recent_errors(limit=10)
    assert u2_view["user_id"] == "u2"
    assert len(u2_view["errors"]) == 1
    assert u2_view["errors"][0]["message"] == "u2-error"


@pytest.mark.asyncio
async def test_clear_errors_only_affects_current_user():
    error_buffers.clear()
    user_metrics.clear()

    set_current_user_id("u1")
    await report_errors(_request("u1-before-clear"))

    set_current_user_id("u2")
    await report_errors(_request("u2-before-clear"))

    set_current_user_id("u1")
    await clear_errors()

    u1_after = await get_recent_errors(limit=10)
    assert u1_after["total_in_buffer"] == 0

    set_current_user_id("u2")
    u2_after = await get_recent_errors(limit=10)
    assert u2_after["total_in_buffer"] == 1
    assert u2_after["errors"][0]["message"] == "u2-before-clear"
