from datetime import date
from pathlib import Path

import pytest

from src.trajectory.contracts import (
    ARTIFACT_SPECS,
    NOTEBOOK_DEPENDENCIES,
    TRAJECTORY_STEPS,
    build_artifact_refs,
    build_trajectory_request,
    validate_step_name,
)
from src.trajectory.pipeline import TrajectoryPipelineBuilder


def test_trajectory_steps_match_notebook_execution_order() -> None:
    assert TRAJECTORY_STEPS == (
        "preprocess-groundplane",
        "local-stitch",
        "build-revised-global-input",
        "build-topology-static",
        "solve-global-edges",
        "finalize-global-units",
        "build-hourly-metrics",
        "build-route-family",
        "save-artifacts",
        "verify",
    )


def test_notebook_dependencies_include_all_extracted_functions() -> None:
    assert "kt_local_pipeline_runner.run_s3_groundplane_stage" in NOTEBOOK_DEPENDENCIES
    assert "kt_local_pipeline_runner.run_local_scene_stitch_stage" in NOTEBOOK_DEPENDENCIES
    assert "kt_topology_static_v2.build_topology_static_stage" in NOTEBOOK_DEPENDENCIES
    assert "kt_route_grid_v2.build_route_family_table" in NOTEBOOK_DEPENDENCIES
    assert (
        "06.integrated_local_global_revised_pipeline.build_revised_global_inputs"
        in NOTEBOOK_DEPENDENCIES
    )
    assert (
        "06.integrated_local_global_revised_pipeline.build_corrected_hourly_metrics"
        in NOTEBOOK_DEPENDENCIES
    )


def test_artifact_contract_contains_core_notebook_outputs() -> None:
    artifact_names = tuple(spec.name for spec in ARTIFACT_SPECS)

    assert artifact_names == (
        "prepared_all",
        "stitched_df_all",
        "presence_episode_df",
        "episode_units_df",
        "transition_units_df",
        "transition_nodes_df",
        "global_candidate_edges_df",
        "selected_global_edges_df",
        "base_global_units_df",
        "base_global_unit_members_df",
        "global_units_df",
        "global_presence_episode_df",
        "hourly_metric_summary_df",
        "route_family_df",
        "manifest",
    )


def test_hourly_and_route_required_columns_are_fixed() -> None:
    specs = {spec.name: spec for spec in ARTIFACT_SPECS}

    assert "visible_unique_units" in specs["hourly_metric_summary_df"].required_columns
    assert "total_visible_dwell_s" in specs["hourly_metric_summary_df"].required_columns
    assert "route_family_id" in specs["route_family_df"].required_columns
    assert "camera_path" in specs["route_family_df"].required_columns


def test_build_artifact_refs_uses_run_root_without_mutating_specs() -> None:
    run_root = Path("/tmp/ktooh-run")
    refs = build_artifact_refs(run_root)

    assert refs[0].path == run_root / "local_stitch_v2/prepared_all.pkl"
    assert refs[-1].path == run_root / "global_stitch_v2_revised_impl/manifest.json"
    assert ARTIFACT_SPECS[0].relative_path == Path("local_stitch_v2/prepared_all.pkl")


def test_build_trajectory_plan_is_pure_contract() -> None:
    request = build_trajectory_request(
        target_date=date(2026, 4, 23),
        run_root=Path("/tmp/ktooh-run"),
        media_id=101,
        camera_codes=("CAM_14", "CAM_5"),
        force=False,
    )
    plan = TrajectoryPipelineBuilder().build_plan(request)

    assert plan.request == request
    assert plan.steps == TRAJECTORY_STEPS
    assert len(plan.artifacts) == len(ARTIFACT_SPECS)


def test_validate_step_name_rejects_unknown_step() -> None:
    assert validate_step_name("local-stitch") == "local-stitch"
    with pytest.raises(ValueError, match="unknown trajectory step"):
        validate_step_name("load-dashboard")
