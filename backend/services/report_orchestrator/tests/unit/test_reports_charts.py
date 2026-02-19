import os
import sys
import unittest

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.main import app  # noqa: E402


def _is_png(content: bytes) -> bool:
    return content[:8] == b"\x89PNG\r\n\x1a\n"


class TestReportsCharts(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_chart_returns_png_even_when_no_structured_data(self):
        r = self.client.post(
            "/api/reports",
            json={
                "session_id": "dd_test_min",
                "project_name": "Test",
                "company_name": "NoData Co",
                "analysis_type": "due-diligence",
                "steps": [],
                "status": "completed",
            },
        )
        self.assertEqual(r.status_code, 200)
        report_id = r.json()["report_id"]

        c = self.client.get(f"/api/reports/{report_id}/charts/revenue?language=zh")
        self.assertEqual(c.status_code, 200)
        self.assertEqual(c.headers.get("content-type"), "image/png")
        self.assertTrue(_is_png(c.content))


if __name__ == "__main__":
    unittest.main()

