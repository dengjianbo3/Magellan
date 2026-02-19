from datetime import datetime
import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

# Ensure /usr/src/app is importable in service containers.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app.main as auth_main
from app.api import auth as auth_api
from app.core.security import TokenPair
from app.models.user import UserRole


def _fake_user(email: str = "smoke@example.com"):
    return SimpleNamespace(
        id=uuid4(),
        email=email,
        name="Smoke User",
        organization="Magellan",
        role=UserRole.ANALYST,
        is_active=True,
        created_at=datetime.utcnow(),
        last_login=None,
    )


@pytest.fixture
def client(monkeypatch):
    async def _noop():
        return None

    async def _fake_db():
        yield object()

    monkeypatch.setattr(auth_main, "init_db", _noop)
    monkeypatch.setattr(auth_main, "close_db", _noop)
    auth_main.app.dependency_overrides[auth_api.get_db] = _fake_db

    with TestClient(auth_main.app) as test_client:
        yield test_client

    auth_main.app.dependency_overrides.clear()


def test_root_health(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == "1.0.0"


def test_register_success(client, monkeypatch):
    user = _fake_user(email="new_user@example.com")
    tokens = TokenPair(access_token="access-token", refresh_token="refresh-token")

    monkeypatch.setattr(auth_api.AuthService, "create_user", AsyncMock(return_value=user))
    monkeypatch.setattr(auth_api.AuthService, "authenticate", AsyncMock(return_value=(user, tokens)))

    response = client.post(
        "/api/auth/register",
        json={
            "email": "new_user@example.com",
            "password": "Password123!",
            "name": "Smoke User",
            "organization": "Magellan",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["access_token"] == "access-token"
    assert body["refresh_token"] == "refresh-token"
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "new_user@example.com"
    assert body["user"]["role"] == "analyst"


def test_login_invalid_credentials(client, monkeypatch):
    monkeypatch.setattr(auth_api.AuthService, "authenticate", AsyncMock(return_value=None))

    response = client.post(
        "/api/auth/login",
        json={"email": "unknown@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_get_me_requires_auth(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"
