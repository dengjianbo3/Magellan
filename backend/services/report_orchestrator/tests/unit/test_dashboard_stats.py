import os
import sys
import unittest

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.main import app  # noqa: E402


class TestDashboardStats(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_stats_total_reports_matches_reports_api_count(self):
        r = self.client.post(
            "/api/reports",
            json={
                "session_id": "dd_dash_1",
                "project_name": "Dash",
                "company_name": "Dash Co",
                "analysis_type": "due-diligence",
                "steps": [],
                "status": "completed",
            },
        )
        self.assertEqual(r.status_code, 200)

        reports = self.client.get("/api/reports")
        self.assertEqual(reports.status_code, 200)
        report_count = reports.json()["count"]

        stats = self.client.get("/api/dashboard/stats")
        self.assertEqual(stats.status_code, 200)
        total_reports = stats.json()["stats"]["total_reports"]["value"]
        self.assertEqual(total_reports, report_count)


if __name__ == "__main__":
    unittest.main()

