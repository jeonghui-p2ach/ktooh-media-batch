from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

TrajectoryStage = Literal[
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
]

ArtifactFormat = Literal["json", "pkl"]

TRAJECTORY_STEPS: tuple[TrajectoryStage, ...] = (
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


@dataclass(frozen=True, slots=True)
class TrajectoryBatchRequest:
    target_date: date
    run_root: Path
    media_id: int
    camera_codes: tuple[str, ...]
    force: bool


@dataclass(frozen=True, slots=True)
class ArtifactSpec:
    name: str
    stage: TrajectoryStage
    relative_path: Path
    artifact_format: ArtifactFormat
    required_columns: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    spec: ArtifactSpec
    path: Path


@dataclass(frozen=True, slots=True)
class TrajectoryPipelinePlan:
    request: TrajectoryBatchRequest
    steps: tuple[TrajectoryStage, ...]
    artifacts: tuple[ArtifactRef, ...]


NOTEBOOK_DEPENDENCIES: tuple[str, ...] = (
    "kt_local_pipeline_runner.run_s3_groundplane_stage",
    "kt_local_pipeline_runner.run_local_scene_stitch_stage",
    "kt_topology_static_v2.build_topology_static_stage",
    "kt_route_grid_v2.build_route_family_table",
    "06.integrated_local_global_revised_pipeline.build_revised_global_inputs",
    "06.integrated_local_global_revised_pipeline.build_revised_candidate_edges",
    "06.integrated_local_global_revised_pipeline.solve_revised_global_edges",
    "06.integrated_local_global_revised_pipeline.materialize_revised_global_units",
    "06.integrated_local_global_revised_pipeline.assign_episodes_to_global_units",
    "06.integrated_local_global_revised_pipeline.finalize_global_units",
    "06.integrated_local_global_revised_pipeline.build_corrected_hourly_metrics",
)

ARTIFACT_SPECS: tuple[ArtifactSpec, ...] = (
    ArtifactSpec(
        name="prepared_all",
        stage="local-stitch",
        relative_path=Path("local_stitch_v2/prepared_all.pkl"),
        artifact_format="pkl",
        required_columns=(
            "tracklet_id",
            "camera_name",
            "start_time",
            "end_time",
            "start_xy",
            "end_xy",
            "world_points_arr",
            "track_quality",
        ),
    ),
    ArtifactSpec(
        name="stitched_df_all",
        stage="local-stitch",
        relative_path=Path("local_stitch_v2/stitched_df_all.pkl"),
        artifact_format="pkl",
        required_columns=(
            "camera_name",
            "start_time",
            "end_time",
            "raw_tracklet_ids",
            "local_confidence",
            "start_xy",
            "end_xy",
            "world_points_arr",
        ),
    ),
    ArtifactSpec(
        name="presence_episode_df",
        stage="local-stitch",
        relative_path=Path("local_stitch_v2/presence_episode_df.pkl"),
        artifact_format="pkl",
        required_columns=(
            "episode_id",
            "camera_name",
            "episode_start_time",
            "episode_end_time",
            "episode_dwell_s",
            "support_tracklet_ids",
            "episode_confidence",
            "episode_kpi_eligible",
        ),
    ),
    ArtifactSpec(
        name="episode_units_df",
        stage="build-revised-global-input",
        relative_path=Path("global_stitch_v2_revised_impl/global_input/episode_units_df.pkl"),
        artifact_format="pkl",
        required_columns=(
            "local_unit_id",
            "unit_kind",
            "camera_name",
            "start_time",
            "end_time",
            "support_tracklet_ids",
            "local_confidence",
            "kpi_eligible",
            "episode_dwell_s",
            "anchor_xy",
        ),
    ),
    ArtifactSpec(
        name="transition_units_df",
        stage="build-revised-global-input",
        relative_path=Path("global_stitch_v2_revised_impl/global_input/transition_units_df.pkl"),
        artifact_format="pkl",
        required_columns=(
            "local_unit_id",
            "unit_kind",
            "camera_name",
            "start_time",
            "end_time",
            "support_tracklet_ids",
            "local_confidence",
            "kpi_eligible",
            "route_points",
            "dwell_s",
            "route_length_m",
            "is_transition_support",
        ),
    ),
    ArtifactSpec(
        name="transition_nodes_df",
        stage="build-revised-global-input",
        relative_path=Path("global_stitch_v2_revised_impl/global_input/transition_nodes_df.pkl"),
        artifact_format="pkl",
        required_columns=(
            "transition_node_id",
            "parent_local_unit_id",
            "camera_name",
            "transition_role",
            "node_time",
            "node_xy",
            "boundary_zone_id",
            "dist_to_zone_m",
            "transition_score",
        ),
    ),
    ArtifactSpec(
        name="global_candidate_edges_df",
        stage="solve-global-edges",
        relative_path=Path(
            "global_stitch_v2_revised_impl/global_association/global_candidate_edges_df.pkl"
        ),
        artifact_format="pkl",
        required_columns=(
            "src_transition_node_id",
            "dst_transition_node_id",
            "src_local_unit_id",
            "dst_local_unit_id",
            "src_camera",
            "dst_camera",
            "gap_s",
            "shortest_path_dist_m",
            "implied_speed_mps",
            "total_edge_cost",
        ),
    ),
    ArtifactSpec(
        name="selected_global_edges_df",
        stage="solve-global-edges",
        relative_path=Path(
            "global_stitch_v2_revised_impl/global_association/selected_global_edges_df.pkl"
        ),
        artifact_format="pkl",
        required_columns=(
            "src_transition_node_id",
            "dst_transition_node_id",
            "src_local_unit_id",
            "dst_local_unit_id",
            "src_camera",
            "dst_camera",
            "gap_s",
            "shortest_path_dist_m",
            "implied_speed_mps",
            "total_edge_cost",
        ),
    ),
    ArtifactSpec(
        name="base_global_units_df",
        stage="finalize-global-units",
        relative_path=Path(
            "global_stitch_v2_revised_impl/global_association/base_global_units_df.pkl"
        ),
        artifact_format="pkl",
        required_columns=(
            "global_unit_id",
            "global_start_time",
            "global_end_time",
            "elapsed_dwell_s",
            "n_cameras",
            "camera_path",
            "global_confidence",
            "seed_kind",
        ),
    ),
    ArtifactSpec(
        name="base_global_unit_members_df",
        stage="finalize-global-units",
        relative_path=Path(
            "global_stitch_v2_revised_impl/global_association/base_global_unit_members_df.pkl"
        ),
        artifact_format="pkl",
        required_columns=(
            "global_unit_id",
            "local_unit_id",
            "camera_name",
            "member_order",
            "unit_kind",
            "start_time",
            "end_time",
        ),
    ),
    ArtifactSpec(
        name="global_units_df",
        stage="finalize-global-units",
        relative_path=Path("global_stitch_v2_revised_impl/global_association/global_units_df.pkl"),
        artifact_format="pkl",
        required_columns=(
            "global_unit_id",
            "global_start_time",
            "global_end_time",
            "elapsed_dwell_s",
            "n_cameras",
            "camera_path",
            "global_confidence",
            "seed_kind",
            "visible_start_time",
            "visible_end_time",
            "visible_episode_count",
            "visible_camera_count",
        ),
    ),
    ArtifactSpec(
        name="global_presence_episode_df",
        stage="build-hourly-metrics",
        relative_path=Path("global_stitch_v2_revised_impl/metrics/global_presence_episode_df.pkl"),
        artifact_format="pkl",
        required_columns=(
            "local_unit_id",
            "camera_name",
            "episode_start_time",
            "episode_end_time",
            "episode_dwell_s",
            "episode_kpi_eligible",
            "global_unit_id",
            "assignment_mode",
        ),
    ),
    ArtifactSpec(
        name="hourly_metric_summary_df",
        stage="build-hourly-metrics",
        relative_path=Path("global_stitch_v2_revised_impl/metrics/hourly_metric_summary_df.pkl"),
        artifact_format="pkl",
        required_columns=(
            "date",
            "hour",
            "hour_start",
            "hour_end",
            "unique_global_units",
            "visible_unique_units",
            "total_visible_dwell_s",
            "metrics_version",
        ),
    ),
    ArtifactSpec(
        name="route_family_df",
        stage="build-route-family",
        relative_path=Path("global_stitch_v2_revised_impl/routes_grid/route_family_df.pkl"),
        artifact_format="pkl",
        required_columns=(
            "route_family_id",
            "camera_path",
            "unit_count",
            "visible_unit_count",
            "median_visible_dwell_s",
            "mean_route_confidence",
            "median_elapsed_s",
            "route_grid_version",
        ),
    ),
    ArtifactSpec(
        name="manifest",
        stage="save-artifacts",
        relative_path=Path("global_stitch_v2_revised_impl/manifest.json"),
        artifact_format="json",
        required_columns=(),
    ),
)


def build_trajectory_request(
    *,
    target_date: date,
    run_root: Path,
    media_id: int,
    camera_codes: tuple[str, ...] = (),
    force: bool = False,
) -> TrajectoryBatchRequest:
    if media_id <= 0:
        raise ValueError("media_id must be positive")
    if not str(run_root).strip():
        raise ValueError("run_root must not be empty")
    return TrajectoryBatchRequest(
        target_date=target_date,
        run_root=run_root,
        media_id=media_id,
        camera_codes=tuple(str(camera_code).strip() for camera_code in camera_codes),
        force=force,
    )


def build_artifact_refs(run_root: Path) -> tuple[ArtifactRef, ...]:
    return tuple(
        ArtifactRef(spec=spec, path=run_root / spec.relative_path)
        for spec in ARTIFACT_SPECS
    )


def validate_step_name(step_name: str) -> TrajectoryStage:
    matches = tuple(step for step in TRAJECTORY_STEPS if step == step_name)
    if len(matches) != 1:
        raise ValueError(f"unknown trajectory step: {step_name}")
    return matches[0]
