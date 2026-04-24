from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from src.trajectory.assignment import (
    assign_episodes_to_global_units as assign_episodes_to_global_units_impl,
)
from src.trajectory.contracts import TrajectoryBatchRequest
from src.trajectory.global_units import finalize_global_units as finalize_global_units_impl
from src.trajectory.materialization import (
    materialize_revised_global_units as materialize_revised_global_units_impl,
)
from src.trajectory.metrics import (
    build_corrected_hourly_metrics as build_corrected_hourly_metrics_impl,
)
from src.trajectory.revised_input import (
    build_revised_global_inputs as build_revised_global_inputs_impl,
)
from src.trajectory.routes import build_route_family_table as build_route_family_table_impl
from src.trajectory.scoring import (
    build_revised_candidate_edges as build_revised_candidate_edges_impl,
)
from src.trajectory.solver import solve_revised_global_edges as solve_revised_global_edges_impl


class LocalPipelineRunner(Protocol):
    def run_s3_groundplane_stage(
        self,
        *,
        start_date: str,
        end_date: str,
        run_root: Path,
        input_paths_kwargs: dict[str, Any],
        raw_cfg_kwargs: dict[str, Any],
        base_module_path: Path | None,
        force: bool,
        verbose: bool,
    ) -> dict[str, Any]: ...

    def run_local_scene_stitch_stage(
        self,
        *,
        camera_tables: Any,
        run_root: Path,
        target_hours: tuple[int, ...] | None,
        target_cameras: tuple[str, ...] | None,
        max_rows_per_camera: int | None,
        camera_profiles: Any,
        force: bool,
        verbose: bool,
        checkpoint_per_camera: bool,
    ) -> dict[str, Any]: ...


class TopologyStageRunner(Protocol):
    def build_topology_static_stage(
        self,
        *,
        transition_nodes: Any,
        output_dir: Path,
        cfg: Any,
        verbose: bool,
    ) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class PreprocessStageConfig:
    input_paths_kwargs: dict[str, Any]
    raw_cfg_kwargs: dict[str, Any]
    base_module_path: Path | None
    verbose: bool


@dataclass(frozen=True, slots=True)
class LocalStageConfig:
    target_hours: tuple[int, ...] | None
    max_rows_per_camera: int | None
    camera_profiles: Any
    verbose: bool
    checkpoint_per_camera: bool


@dataclass(frozen=True, slots=True)
class RevisedGlobalStageConfig:
    local_dir_name: str
    output_name: str
    global_config: Any
    verbose: bool


@dataclass(frozen=True, slots=True)
class RevisedGlobalResult:
    revised_inputs: dict[str, Any]
    topology: dict[str, Any]
    candidate_edges: Any
    selected_edges: Any
    base_global_units: Any
    base_global_members: Any
    global_presence: Any
    global_units: Any
    hourly_metrics: Any
    route_family: Any


@dataclass(frozen=True, slots=True)
class TrajectoryBoundaryRunResult:
    preprocess: dict[str, Any]
    local: dict[str, Any]
    revised_global: RevisedGlobalResult


def run_preprocess_stage(
    *,
    request: TrajectoryBatchRequest,
    runner: LocalPipelineRunner,
    config: PreprocessStageConfig,
) -> dict[str, Any]:
    target_date = request.target_date.isoformat()
    return runner.run_s3_groundplane_stage(
        start_date=target_date,
        end_date=target_date,
        run_root=request.run_root,
        input_paths_kwargs=config.input_paths_kwargs,
        raw_cfg_kwargs=config.raw_cfg_kwargs,
        base_module_path=config.base_module_path,
        force=request.force,
        verbose=config.verbose,
    )


def run_local_stage(
    *,
    request: TrajectoryBatchRequest,
    runner: LocalPipelineRunner,
    camera_tables: Any,
    config: LocalStageConfig,
) -> dict[str, Any]:
    return runner.run_local_scene_stitch_stage(
        camera_tables=camera_tables,
        run_root=request.run_root,
        target_hours=config.target_hours,
        target_cameras=request.camera_codes or None,
        max_rows_per_camera=config.max_rows_per_camera,
        camera_profiles=config.camera_profiles,
        force=request.force,
        verbose=config.verbose,
        checkpoint_per_camera=config.checkpoint_per_camera,
    )


def run_revised_global_stage_with_topology_boundary(
    *,
    request: TrajectoryBatchRequest,
    topology_runner: TopologyStageRunner,
    config: RevisedGlobalStageConfig,
    metrics_version: str = "metrics-v1",
    route_grid_version: str = "route-grid-v1",
) -> RevisedGlobalResult:
    local_dir = request.run_root / config.local_dir_name
    revised_global_dir = request.run_root / config.output_name
    revised_inputs = build_revised_global_inputs_impl(local_dir, config.global_config)
    topology = topology_runner.build_topology_static_stage(
        transition_nodes=revised_inputs["transition_nodes_df"],
        output_dir=revised_global_dir / "topology_static",
        cfg=config.global_config,
        verbose=config.verbose,
    )
    candidate_edges = build_revised_candidate_edges_impl(
        revised_inputs["transition_nodes_df"],
        topology["links_df"],
        topology["pairwise_offsets_df"],
        topology["hour_speed_prior_df"],
        config.global_config,
    )
    selected_edges = solve_revised_global_edges_impl(candidate_edges, config.global_config)
    base_global_units, base_global_members = materialize_revised_global_units_impl(
        revised_inputs["transition_units_df"],
        selected_edges,
    )
    global_presence = assign_episodes_to_global_units_impl(
        revised_inputs["episode_units_df"],
        revised_inputs["transition_units_df"],
        base_global_members,
    )
    global_units = finalize_global_units_impl(base_global_units, global_presence)
    hourly_metrics = build_corrected_hourly_metrics_impl(
        global_units,
        global_presence,
        metrics_version=metrics_version,
    )
    route_family = build_route_family_table_impl(
        global_units,
        global_presence,
        route_grid_version=route_grid_version,
    )
    return RevisedGlobalResult(
        revised_inputs=revised_inputs,
        topology=topology,
        candidate_edges=candidate_edges,
        selected_edges=selected_edges,
        base_global_units=base_global_units,
        base_global_members=base_global_members,
        global_presence=global_presence,
        global_units=global_units,
        hourly_metrics=hourly_metrics,
        route_family=route_family,
    )


def run_trajectory_with_boundaries(
    *,
    request: TrajectoryBatchRequest,
    local_runner: LocalPipelineRunner,
    topology_runner: TopologyStageRunner,
    preprocess_config: PreprocessStageConfig,
    local_config: LocalStageConfig,
    revised_global_config: RevisedGlobalStageConfig,
    metrics_version: str = "metrics-v1",
    route_grid_version: str = "route-grid-v1",
) -> TrajectoryBoundaryRunResult:
    preprocess = run_preprocess_stage(
        request=request,
        runner=local_runner,
        config=preprocess_config,
    )
    local = run_local_stage(
        request=request,
        runner=local_runner,
        camera_tables=preprocess["camera_tables"],
        config=local_config,
    )
    revised_global = run_revised_global_stage_with_topology_boundary(
        request=request,
        topology_runner=topology_runner,
        config=revised_global_config,
        metrics_version=metrics_version,
        route_grid_version=route_grid_version,
    )
    return TrajectoryBoundaryRunResult(
        preprocess=preprocess,
        local=local,
        revised_global=revised_global,
    )
