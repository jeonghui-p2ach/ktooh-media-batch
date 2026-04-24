from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from src.trajectory.contracts import TrajectoryBatchRequest


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


class RevisedGlobalFunctions(Protocol):
    def build_revised_global_inputs(self, local_dir: Path, cfg: Any) -> dict[str, Any]: ...

    def build_topology_static_stage(
        self,
        *,
        transition_nodes: Any,
        output_dir: Path,
        cfg: Any,
        verbose: bool,
    ) -> dict[str, Any]: ...

    def build_revised_candidate_edges(
        self,
        transition_nodes: Any,
        links_df: Any,
        offset_df: Any,
        hour_speed_df: Any,
        cfg: Any,
    ) -> Any: ...

    def solve_revised_global_edges(self, candidate_edges: Any, cfg: Any) -> Any: ...

    def materialize_revised_global_units(
        self,
        transition_units: Any,
        selected_edges: Any,
    ) -> tuple[Any, Any]: ...

    def assign_episodes_to_global_units(
        self,
        episode_units: Any,
        transition_units: Any,
        global_members: Any,
    ) -> Any: ...

    def finalize_global_units(self, base_global_units: Any, assigned_episodes: Any) -> Any: ...

    def build_corrected_hourly_metrics(self, global_units: Any, global_presence: Any) -> Any: ...

    def build_route_family_table(self, global_units: Any, global_presence: Any) -> Any: ...


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


def run_revised_global_stage(
    *,
    request: TrajectoryBatchRequest,
    functions: RevisedGlobalFunctions,
    config: RevisedGlobalStageConfig,
) -> RevisedGlobalResult:
    local_dir = request.run_root / config.local_dir_name
    revised_global_dir = request.run_root / config.output_name
    revised_inputs = functions.build_revised_global_inputs(local_dir, config.global_config)
    topology = functions.build_topology_static_stage(
        transition_nodes=revised_inputs["transition_nodes_df"],
        output_dir=revised_global_dir / "topology_static",
        cfg=config.global_config,
        verbose=config.verbose,
    )
    candidate_edges = functions.build_revised_candidate_edges(
        transition_nodes=revised_inputs["transition_nodes_df"],
        links_df=topology["links_df"],
        offset_df=topology["pairwise_offsets_df"],
        hour_speed_df=topology["hour_speed_prior_df"],
        cfg=config.global_config,
    )
    selected_edges = functions.solve_revised_global_edges(candidate_edges, config.global_config)
    base_global_units, base_global_members = functions.materialize_revised_global_units(
        revised_inputs["transition_units_df"],
        selected_edges,
    )
    global_presence = functions.assign_episodes_to_global_units(
        revised_inputs["episode_units_df"],
        revised_inputs["transition_units_df"],
        base_global_members,
    )
    global_units = functions.finalize_global_units(base_global_units, global_presence)
    hourly_metrics = functions.build_corrected_hourly_metrics(global_units, global_presence)
    route_family = functions.build_route_family_table(global_units, global_presence)
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
