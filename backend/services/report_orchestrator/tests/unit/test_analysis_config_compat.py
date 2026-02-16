from app.models.analysis_models import AnalysisRequest, AnalysisDepth


def test_analysis_config_accepts_legacy_mode_field():
    request = AnalysisRequest(
        project_name="Compat Test",
        scenario="early-stage-investment",
        target={"company_name": "ACME", "stage": "seed"},
        config={"mode": "quick", "language": "zh"},
    )

    assert request.config.depth == AnalysisDepth.QUICK


def test_analysis_config_accepts_legacy_focus_areas_field():
    request = AnalysisRequest(
        project_name="Compat Test",
        scenario="early-stage-investment",
        target={"company_name": "ACME", "stage": "seed"},
        config={"depth": "standard", "focusAreas": ["team", "market"]},
    )

    assert request.config.focus_areas == ["team", "market"]
