#!/usr/bin/env python3
"""
Generate real Expert Chat traffic against running report_orchestrator service (inside container).
Used to warm caches and produce live metrics for window sampling.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import string
from typing import Any, Dict, List

import requests
import websockets


AUTH_BASE = "http://auth_service:8007/api/auth"
WS_URL = "ws://localhost:8000/ws/expert-chat"


def _random_email() -> str:
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"loadtest_{suffix}@example.com"


def _register_or_login() -> str:
    email = _random_email()
    password = "Passw0rd!123"
    register_payload = {
        "email": email,
        "password": password,
        "name": "Load Test User",
        "organization": "Magellan",
    }
    resp = requests.post(f"{AUTH_BASE}/register", json=register_payload, timeout=20)
    if resp.status_code in (200, 201):
        body = resp.json()
        return body["access_token"]

    # fallback: login with same credentials (if register policy changes)
    login_payload = {"email": email, "password": password}
    login = requests.post(f"{AUTH_BASE}/login", json=login_payload, timeout=20)
    login.raise_for_status()
    return login.json()["access_token"]


async def _wait_for_event(
    ws: websockets.WebSocketClientProtocol,
    per_message_timeout: float,
) -> Dict[str, Any]:
    deadline = asyncio.get_event_loop().time() + per_message_timeout
    events: List[Dict[str, Any]] = []
    got_terminal = False
    while asyncio.get_event_loop().time() < deadline:
        timeout = max(0.1, min(3.0, deadline - asyncio.get_event_loop().time()))
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
        except asyncio.TimeoutError:
            if got_terminal:
                break
            continue
        msg = json.loads(raw)
        events.append(msg)
        msg_type = str(msg.get("type", ""))
        if msg_type in {"agent_message", "error"}:
            got_terminal = True
    return {"count": len(events), "events": events}


async def run(messages: List[str], per_message_timeout: float) -> Dict[str, Any]:
    token = _register_or_login()
    uri = f"{WS_URL}?token={token}"
    results = []
    async with websockets.connect(uri, open_timeout=15, ping_interval=None, max_size=10 * 1024 * 1024) as ws:
        # session_started
        _ = json.loads(await asyncio.wait_for(ws.recv(), timeout=20))

        await ws.send(
            json.dumps(
                {
                    "type": "start_session",
                    "language": "zh-CN",
                    "knowledge": {"enabled": False, "category": "all"},
                },
                ensure_ascii=False,
            )
        )
        _ = await _wait_for_event(ws, per_message_timeout=10)

        for content in messages:
            await ws.send(
                json.dumps(
                    {
                        "type": "user_message",
                        "content": content,
                        "language": "zh-CN",
                        "knowledge": {"enabled": False, "category": "all"},
                    },
                    ensure_ascii=False,
                )
            )
            result = await _wait_for_event(ws, per_message_timeout=per_message_timeout)
            result["content"] = content
            results.append(result)

    success = sum(
        1
        for item in results
        if any(str(evt.get("type")) == "agent_message" for evt in item.get("events", []))
    )
    errors = sum(
        1
        for item in results
        if any(str(evt.get("type")) == "error" for evt in item.get("events", []))
    )
    return {
        "sent_messages": len(messages),
        "agent_message_turns": success,
        "error_turns": errors,
        "details": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate real expert chat traffic in container")
    parser.add_argument("--timeout", type=float, default=45.0, help="Per message max wait seconds")
    args = parser.parse_args()

    messages = [
        "比特币现在的市场情况如何？",
        "比特币现在的市场情况如何？",
        "@technical-analyst 请给出BTC的RSI和MACD简要分析。",
        "@technical-analyst 请给出BTC的RSI和MACD简要分析。",
    ]
    out = asyncio.run(run(messages=messages, per_message_timeout=args.timeout))
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["sent_messages"] == out["agent_message_turns"] + out["error_turns"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

