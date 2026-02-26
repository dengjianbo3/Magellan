from app.core.model_policy import load_model_policy, resolve_model_for_role


def test_model_policy_has_expected_defaults():
    policy = load_model_policy(force_reload=True)
    assert policy.get("leader_router") in {"flash", "pro", "default"}
    assert "specialist_chat" in policy


def test_resolve_model_for_role_returns_optional_model():
    model = resolve_model_for_role("leader_router")
    assert model in {None, "pro", "flash"} or str(model).startswith("gemini-")
