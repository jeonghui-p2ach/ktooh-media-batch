from datetime import date

from src.measurement.pipeline import PipelineBuilder, validate_step_name, validate_workflow_status


def test_build_plan_uses_media_id() -> None:
    plan = PipelineBuilder().build_plan(target_date=date(2026, 4, 23), media_id=101)

    assert plan.window.media_id == 101
    assert plan.window.timezone_name == "UTC"
    assert "collect-s3-objects" in plan.steps


def test_validate_step_name_accepts_known_step() -> None:
    assert validate_step_name("load-audience-facts") == "load-audience-facts"


def test_validate_workflow_status_accepts_known_status() -> None:
    assert validate_workflow_status("Succeeded") == "Succeeded"
