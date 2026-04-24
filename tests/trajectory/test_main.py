from datetime import date

from typer.testing import CliRunner

from src.trajectory.main import app, parse_camera_codes, parse_target_date


def test_parse_target_date_accepts_iso_date() -> None:
    assert parse_target_date("2026-04-23") == date(2026, 4, 23)


def test_parse_camera_codes_trims_empty_parts() -> None:
    assert parse_camera_codes(" CAM_14, ,CAM_5 ") == ("CAM_14", "CAM_5")


def test_plan_command_prints_steps_and_artifacts() -> None:
    result = CliRunner().invoke(
        app,
        [
            "plan",
            "--target-date",
            "2026-04-23",
            "--run-root",
            "/tmp/ktooh-run",
            "--media-id",
            "101",
            "--camera-codes",
            "CAM_14,CAM_5",
        ],
    )

    assert result.exit_code == 0
    assert "target_date=2026-04-23" in result.stdout
    assert "media_id=101" in result.stdout
    assert "camera_codes=CAM_14,CAM_5" in result.stdout
    assert "steps=preprocess-groundplane,local-stitch" in result.stdout
    assert "/tmp/ktooh-run/local_stitch_v2/prepared_all.pkl" in result.stdout
