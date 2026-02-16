import os
import sys
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.main import app  # noqa: E402


class _StubStore:
    def __init__(self):
        self.sessions = {}

    def save_session(self, session_id, context, ttl_days=30):
        self.sessions[session_id] = context
        return True

    def get_session(self, session_id):
        return self.sessions.get(session_id)


class TestAnalysisV2Status(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_start_persists_created_session_and_status(self):
        from app.api.routers import analysis as analysis_router_module

        stub = _StubStore()
        with patch.object(analysis_router_module, "_safe_session_store", autospec=True, return_value=stub):
            req = {
                "project_name": "UnitTest",
                "scenario": "early-stage-investment",
                "target": {"company_name": "ACME", "stage": "seed"},
                "config": {"depth": "quick", "language": "zh"},
                "user_id": "u_test",
            }

            r = self.client.post("/api/v2/analysis/start", json=req)
            self.assertEqual(r.status_code, 200)
            sid = r.json()["session_id"]

            s = self.client.get(f"/api/v2/analysis/{sid}/status")
            self.assertEqual(s.status_code, 200)
            payload = s.json()
            self.assertEqual(payload["session_id"], sid)
            self.assertIn(payload["status"], ("created", "running", "initializing"))
            self.assertEqual(payload["progress"], 0)


if __name__ == "__main__":
    unittest.main()

