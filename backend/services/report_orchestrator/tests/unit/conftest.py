import pytest

from app.core.auth import CurrentUser


@pytest.fixture(autouse=True)
def _mock_authenticated_user(monkeypatch):
    """
    Unit tests should focus on business behavior, not external auth_service calls.
    Provide a stable authenticated user context for all unit tests.
    """

    def _fake_extract_token_from_request(_request, _authorization):
        return "unit-test-token"

    async def _fake_resolve_user_from_token(_token: str):
        return CurrentUser(id="unit_test_user", email="unit@test.local", role="tester")

    monkeypatch.setattr(
        "app.core.auth.extract_token_from_request",
        _fake_extract_token_from_request,
    )
    monkeypatch.setattr(
        "app.core.auth.resolve_user_from_token",
        _fake_resolve_user_from_token,
    )
