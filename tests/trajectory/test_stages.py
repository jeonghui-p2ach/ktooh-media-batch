from datetime import date
from pathlib import Path
from typing import Any

from src.trajectory.contracts import build_trajectory_request
from src.trajectory.stages import (
    LocalStageConfig,
    PreprocessStageConfig,
    RevisedGlobalStageConfig,
    run_local_stage,
    run_preprocess_stage,
    run_revised_global_stage,
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


class FakeRevisedGlobalFunctions:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def build_revised_global_inputs(self, local_dir: Path, cfg: Any) -> dict[str, Any]:
        self.calls.append("build_revised_global_inputs")
        return {
            "episode_units_df": "episodes",
            "transition_units_df": "transitions",
            "transition_nodes_df": "nodes",
        }

    def build_topology_static_stage(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append("build_topology_static_stage")
        return {
            "links_df": "links",
            "pairwise_offsets_df": "offsets",
            "hour_speed_prior_df": "speed",
        }

    def build_revised_candidate_edges(self, **kwargs: Any) -> str:
        self.calls.append("build_revised_candidate_edges")
        return "candidate_edges"

    def solve_revised_global_edges(self, candidate_edges: Any, cfg: Any) -> str:
        self.calls.append("solve_revised_global_edges")
        return "selected_edges"

    def materialize_revised_global_units(
        self,
        transition_units: Any,
        selected_edges: Any,
    ) -> tuple[str, str]:
        self.calls.append("materialize_revised_global_units")
        return "base_global_units", "base_global_members"

    def assign_episodes_to_global_units(
        self,
        episode_units: Any,
        transition_units: Any,
        global_members: Any,
    ) -> str:
        self.calls.append("assign_episodes_to_global_units")
        return "global_presence"

    def finalize_global_units(self, base_global_units: Any, assigned_episodes: Any) -> str:
        self.calls.append("finalize_global_units")
        return "global_units"

    def build_corrected_hourly_metrics(self, global_units: Any, global_presence: Any) -> str:
        self.calls.append("build_corrected_hourly_metrics")
        return "hourly"

    def build_route_family_table(self, global_units: Any, global_presence: Any) -> str:
        self.calls.append("build_route_family_table")
        return "routes"


def test_run_preprocess_stage_calls_runner_with_target_date() -> None:
    request = build_trajectory_request(
        target_date=date(2026, 4, 23),
        run_root=Path("/tmp/ktooh-run"),
        media_id=101,
        force=True,
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


def test_run_revised_global_stage_calls_notebook_functions_in_order() -> None:
    request = build_trajectory_request(
        target_date=date(2026, 4, 23),
        run_root=Path("/tmp/ktooh-run"),
        media_id=101,
    )
    functions = FakeRevisedGlobalFunctions()

    result = run_revised_global_stage(
        request=request,
        functions=functions,
        config=RevisedGlobalStageConfig(
            local_dir_name="local_stitch_v2",
            output_name="global_stitch_v2_revised_impl",
            global_config={"cfg": "value"},
            verbose=False,
        ),
    )

    assert functions.calls == [
        "build_revised_global_inputs",
        "build_topology_static_stage",
        "build_revised_candidate_edges",
        "solve_revised_global_edges",
        "materialize_revised_global_units",
        "assign_episodes_to_global_units",
        "finalize_global_units",
        "build_corrected_hourly_metrics",
        "build_route_family_table",
    ]
    assert result.global_units == "global_units"
    assert result.hourly_metrics == "hourly"
    assert result.route_family == "routes"
