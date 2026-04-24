import pickle
from datetime import date, datetime
from pathlib import Path

from typer.testing import CliRunner

from src.trajectory.contracts import ARTIFACT_SPECS
from src.trajectory.main import app


def test_load_dashboard_command_dry_run_prints_counts(tmp_path: Path) -> None:
    _write_artifacts(
        tmp_path,
        {
            "presence_episode_df": [
                {
                    "episode_id": "EP-1",
                    "camera_name": "CAM_14",
                    "episode_start_time": datetime(2026, 4, 23, 1),
                    "episode_end_time": datetime(2026, 4, 23, 1, 5),
                    "episode_dwell_s": 300,
                    "support_tracklet_ids": ["T1"],
                    "episode_confidence": 0.9,
                    "episode_kpi_eligible": True,
                }
            ],
            "hourly_metric_summary_df": [
                {
                    "date": date(2026, 4, 23),
                    "hour": 1,
                    "hour_start": datetime(2026, 4, 23, 1),
                    "hour_end": datetime(2026, 4, 23, 2),
                    "unique_global_units": 1,
                    "visible_unique_units": 1,
                    "total_visible_dwell_s": 300,
                }
            ],
        },
    )

    result = CliRunner().invoke(
        app,
        [
            "load-dashboard",
            "--target-date",
            "2026-04-23",
            "--run-root",
            str(tmp_path),
            "--media-id",
            "101",
            "--camera-map",
            "CAM_14:CAM_14",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "presence_episodes=1" in result.stdout
    assert "hourly_metrics=1" in result.stdout
    assert "loaded_count=2" in result.stdout


def _write_artifacts(run_root: Path, rows_by_name: dict[str, list[dict]]) -> None:
    for spec in ARTIFACT_SPECS:
        if spec.artifact_format != "pkl":
            continue
        path = run_root / spec.relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as file:
            pickle.dump(rows_by_name.get(spec.name, []), file)
