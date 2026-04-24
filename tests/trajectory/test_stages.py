import pickle
from datetime import date, datetime
from pathlib import Path
from typing import Any

from src.trajectory.contracts import build_trajectory_request
from src.trajectory.stages import (
    LocalStageConfig,
    PreprocessStageConfig,
    RevisedGlobalStageConfig,
    run_local_stage,
    run_preprocess_stage,
    run_revised_global_stage_with_topology_boundary,
    run_trajectory_with_boundaries,
)


class FakeLocalRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def run_s3_groundplane_stage(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("preprocess", kwargs))
        return {"camera_tables": {"CAM_14": "table"}}

    def run_local_scene_stitch_stage(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("local", kwargs))
        return {"output_dir": kwargs["run_root"] / "local_stitch_v2"}


class FakeTopologyRunner:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def build_topology_static_stage(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        return {
            "links_df": (
                {"src_camera": "CAM_A", "dst_camera": "CAM_A", "shortest_path_dist_m": 0.0},
            ),
            "pairwise_offsets_df": (),
            "hour_speed_prior_df": ({"hour": 9, "speed_mps": 1.0},),
        }


def test_run_preprocess_stage_calls_runner_with_target_date() -> None:
    request = build_trajectory_request(
        target_date=date(2026, 4, 23), run_root=Path("/tmp/ktooh-run"), media_id=101, force=True
    )
    runner = FakeLocalRunner()
    result = run_preprocess_stage(
        request=request,
        runner=runner,
        config=PreprocessStageConfig(
            input_paths_kwargs={"bucket": "ignored"},
            raw_cfg_kwargs={},
            base_module_path=None,
            verbose=False,
        ),
    )
    assert result == {"camera_tables": {"CAM_14": "table"}}
    assert runner.calls[0][1]["start_date"] == "2026-04-23"
    assert runner.calls[0][1]["end_date"] == "2026-04-23"
    assert runner.calls[0][1]["force"] is True


def test_run_local_stage_passes_camera_filter() -> None:
    request = build_trajectory_request(
        target_date=date(2026, 4, 23),
        run_root=Path("/tmp/ktooh-run"),
        media_id=101,
        camera_codes=("CAM_14",),
        force=False,
    )
    runner = FakeLocalRunner()
    result = run_local_stage(
        request=request,
        runner=runner,
        camera_tables={"CAM_14": "table"},
        config=LocalStageConfig(
            target_hours=(9, 10),
            max_rows_per_camera=100,
            camera_profiles=None,
            verbose=False,
            checkpoint_per_camera=True,
        ),
    )
    assert result == {"output_dir": Path("/tmp/ktooh-run/local_stitch_v2")}
    assert runner.calls[0][1]["target_cameras"] == ("CAM_14",)
    assert runner.calls[0][1]["target_hours"] == (9, 10)


def test_run_revised_global_stage_with_topology_boundary(tmp_path: Path) -> None:
    local_dir = tmp_path / "local_stitch_v2"
    local_dir.mkdir(parents=True)
    _write_pickle(local_dir / "prepared_all.pkl", [])
    _write_pickle(
        local_dir / "stitched_df_all.pkl",
        [
            {
                "stitched_id": "ST-1",
                "camera_name": "CAM_A",
                "start_time": datetime(2026, 4, 23, 9, 0),
                "end_time": datetime(2026, 4, 23, 9, 10),
                "raw_tracklet_ids": ["T1"],
                "local_confidence": 0.8,
                "world_points_arr": [(0.0, 0.0), (1.0, 1.0)],
            }
        ],
    )
    _write_pickle(
        local_dir / "presence_episode_df.pkl",
        [
            {
                "episode_id": "EP-1",
                "camera_name": "CAM_A",
                "episode_start_time": datetime(2026, 4, 23, 9, 1),
                "episode_end_time": datetime(2026, 4, 23, 9, 5),
                "episode_dwell_s": 240.0,
                "support_tracklet_ids": ["T1"],
                "episode_confidence": 0.9,
                "episode_kpi_eligible": True,
            }
        ],
    )
    request = build_trajectory_request(
        target_date=date(2026, 4, 23), run_root=tmp_path, media_id=101
    )
    topology_runner = FakeTopologyRunner()
    result = run_revised_global_stage_with_topology_boundary(
        request=request,
        topology_runner=topology_runner,
        config=RevisedGlobalStageConfig(
            local_dir_name="local_stitch_v2",
            output_name="global_stitch_v2_revised_impl",
            global_config={"max_speed_mps": 5.0},
            verbose=False,
        ),
        metrics_version="metrics-v4",
        route_grid_version="grid-v4",
    )
    assert len(topology_runner.calls) == 1
    assert result.revised_inputs["episode_units_df"][0]["local_unit_id"] == "EP-1"
    assert result.candidate_edges == ()
    assert result.selected_edges == ()
    assert result.base_global_units[0]["global_unit_id"] == "GU_000000"
    assert result.global_units[0]["visible_episode_count"] == 1
    assert result.hourly_metrics[0]["metrics_version"] == "metrics-v4"
    assert result.route_family[0]["route_grid_version"] == "grid-v4"


def test_run_trajectory_with_boundaries(tmp_path: Path) -> None:
    local_dir = tmp_path / "local_stitch_v2"
    local_dir.mkdir(parents=True)
    _write_pickle(local_dir / "prepared_all.pkl", [])
    _write_pickle(
        local_dir / "stitched_df_all.pkl",
        [
            {
                "stitched_id": "ST-1",
                "camera_name": "CAM_A",
                "start_time": datetime(2026, 4, 23, 9, 0),
                "end_time": datetime(2026, 4, 23, 9, 10),
                "raw_tracklet_ids": ["T1"],
                "local_confidence": 0.8,
                "world_points_arr": [(0.0, 0.0), (1.0, 1.0)],
            }
        ],
    )
    _write_pickle(
        local_dir / "presence_episode_df.pkl",
        [
            {
                "episode_id": "EP-1",
                "camera_name": "CAM_A",
                "episode_start_time": datetime(2026, 4, 23, 9, 1),
                "episode_end_time": datetime(2026, 4, 23, 9, 5),
                "episode_dwell_s": 240.0,
                "support_tracklet_ids": ["T1"],
                "episode_confidence": 0.9,
                "episode_kpi_eligible": True,
            }
        ],
    )
    request = build_trajectory_request(
        target_date=date(2026, 4, 23), run_root=tmp_path, media_id=101
    )
    runner = FakeLocalRunner()
    topology_runner = FakeTopologyRunner()
    result = run_trajectory_with_boundaries(
        request=request,
        local_runner=runner,
        topology_runner=topology_runner,
        preprocess_config=PreprocessStageConfig(
            input_paths_kwargs={"bucket": "ignored"},
            raw_cfg_kwargs={},
            base_module_path=None,
            verbose=False,
        ),
        local_config=LocalStageConfig(
            target_hours=(9,),
            max_rows_per_camera=100,
            camera_profiles=None,
            verbose=False,
            checkpoint_per_camera=True,
        ),
        revised_global_config=RevisedGlobalStageConfig(
            local_dir_name="local_stitch_v2",
            output_name="global_stitch_v2_revised_impl",
            global_config={"max_speed_mps": 5.0},
            verbose=False,
        ),
        metrics_version="metrics-v5",
        route_grid_version="grid-v5",
    )
    assert len(runner.calls) == 2
    assert len(topology_runner.calls) == 1
    assert result.preprocess["camera_tables"] == {"CAM_14": "table"}
    assert result.local["output_dir"] == tmp_path / "local_stitch_v2"
    assert result.revised_global.hourly_metrics[0]["metrics_version"] == "metrics-v5"
    assert result.revised_global.route_family[0]["route_grid_version"] == "grid-v5"


def _write_pickle(path: Path, value: object) -> None:
    path.write_bytes(pickle.dumps(value))
