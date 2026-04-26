from datetime import date
from pathlib import Path
from typing import Annotated

import typer

from src.common.logging_config import get_logger
from src.trajectory.contracts import build_trajectory_request
from src.trajectory.loader import (
    CameraCodeMapping,
    TrajectoryLoadContext,
    build_dashboard_rows,
    load_artifact_rows,
    persist_dashboard_rows,
)
from src.trajectory.pipeline import TrajectoryPipelineBuilder
from src.trajectory.spatial import CameraGeoTransform, SpatialCellConfig
from src.trajectory.verify import verify_artifact_files

app = typer.Typer(no_args_is_help=True)
logger = get_logger(__name__)


@app.callback()
def trajectory() -> None:
    pass


def parse_target_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise typer.BadParameter("target_date must be in YYYY-MM-DD format") from error


def parse_camera_codes(value: str | None) -> tuple[str, ...]:
    if value is None or not value.strip():
        return ()
    return tuple(
        camera_code
        for camera_code in (part.strip() for part in value.split(","))
        if camera_code
    )


def parse_camera_map(value: str | None) -> tuple[CameraCodeMapping, ...]:
    if value is None or not value.strip():
        return ()
    return tuple(
        CameraCodeMapping(camera_name=name.strip(), camera_code=code.strip())
        for item in value.split(",")
        if ":" in item
        for name, code in (item.split(":", 1),)
        if name.strip() and code.strip()
    )


def parse_geo_transforms(value: str | None) -> tuple[CameraGeoTransform, ...]:
    if value is None or not value.strip():
        return ()
    return tuple(_parse_geo_transform_item(item) for item in value.split(",") if item.strip())


def _parse_geo_transform_item(value: str) -> CameraGeoTransform:
    parts = tuple(part.strip() for part in value.split(":"))
    if len(parts) != 5:
        raise typer.BadParameter(
            "geo-transform must be camera_code:origin_lat:origin_lng:lat_per_y:lng_per_x"
        )
    return CameraGeoTransform(
        camera_code=parts[0],
        origin_lat=float(parts[1]),
        origin_lng=float(parts[2]),
        lat_per_world_y=float(parts[3]),
        lng_per_world_x=float(parts[4]),
    )


@app.command()
def plan(
    target_date: Annotated[str, typer.Option("--target-date")],
    run_root: Annotated[Path, typer.Option("--run-root")],
    media_id: Annotated[int, typer.Option("--media-id")],
    camera_codes: Annotated[str | None, typer.Option("--camera-codes")] = None,
    force: Annotated[bool, typer.Option("--force")] = False,
) -> None:
    request = build_trajectory_request(
        target_date=parse_target_date(target_date),
        run_root=run_root,
        media_id=media_id,
        camera_codes=parse_camera_codes(camera_codes),
        force=force,
    )
    pipeline_plan = TrajectoryPipelineBuilder().build_plan(request)
    logger.info(
        "trajectory_pipeline_plan_built",
        target_date=request.target_date.isoformat(),
        media_id=request.media_id,
        step_count=len(pipeline_plan.steps),
        artifact_count=len(pipeline_plan.artifacts),
    )
    typer.echo(f"target_date={pipeline_plan.request.target_date.isoformat()}")
    typer.echo(f"media_id={pipeline_plan.request.media_id}")
    typer.echo(f"run_root={pipeline_plan.request.run_root}")
    typer.echo(f"camera_codes={','.join(pipeline_plan.request.camera_codes)}")
    typer.echo(f"force={pipeline_plan.request.force}")
    typer.echo(f"steps={','.join(pipeline_plan.steps)}")
    typer.echo(
        "artifacts="
        + ",".join(str(artifact.path) for artifact in pipeline_plan.artifacts)
    )


@app.command("verify-artifacts")
def verify_artifacts(
    target_date: Annotated[str, typer.Option("--target-date")],
    run_root: Annotated[Path, typer.Option("--run-root")],
    media_id: Annotated[int, typer.Option("--media-id")],
    camera_codes: Annotated[str | None, typer.Option("--camera-codes")] = None,
) -> None:
    request = build_trajectory_request(
        target_date=parse_target_date(target_date),
        run_root=run_root,
        media_id=media_id,
        camera_codes=parse_camera_codes(camera_codes),
        force=False,
    )
    pipeline_plan = TrajectoryPipelineBuilder().build_plan(request)
    summary = verify_artifact_files(pipeline_plan.artifacts)
    logger.info(
        "trajectory_artifacts_verified",
        target_date=request.target_date.isoformat(),
        media_id=request.media_id,
        artifact_count=len(summary.checks),
        missing_count=summary.missing_count,
    )
    for check in summary.checks:
        typer.echo(f"{check.artifact_name}\texists={check.exists}\tpath={check.path}")
    typer.echo(f"missing_count={summary.missing_count}")
    if not summary.ok:
        raise typer.Exit(code=1)


@app.command("load-dashboard")
def load_dashboard(
    target_date: Annotated[str, typer.Option("--target-date", help="Target date in YYYY-MM-DD")],
    run_root: Annotated[Path, typer.Option("--run-root", help="Root directory of pipeline artifacts")],
    media_id: Annotated[int, typer.Option("--media-id", help="Media ID to associate")],
    database_url: Annotated[str | None, typer.Option("--database-url", help="Database URL")] = None,
    camera_map: Annotated[str | None, typer.Option("--camera-map")] = None,
    campaign_id: Annotated[int | None, typer.Option("--campaign-id")] = None,
    creative_id: Annotated[int | None, typer.Option("--creative-id")] = None,
    source_batch_id: Annotated[str | None, typer.Option("--source-batch-id")] = None,
    pipeline_version: Annotated[str | None, typer.Option("--pipeline-version")] = None,
    geo_transform: Annotated[str | None, typer.Option("--geo-transform")] = None,
    spatial_zoom: Annotated[int, typer.Option("--spatial-zoom")] = 18,
    spatial_cell_size_degrees: Annotated[
        float,
        typer.Option("--spatial-cell-size-degrees"),
    ] = 0.0001,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    """
    Load trajectory artifacts to the dashboard database.
    WARNING: This command will DELETE all existing trajectory data for the 
    specified --media-id and --target-date before performing insertion.
    """
    request = build_trajectory_request(
        target_date=parse_target_date(target_date),
        run_root=run_root,
        media_id=media_id,
        camera_codes=(),
        force=False,
    )
    if not dry_run and not database_url:
        raise typer.BadParameter("--database-url is required for non-dry-run")
    pipeline_plan = TrajectoryPipelineBuilder().build_plan(request)
    context = TrajectoryLoadContext(
        target_date=request.target_date,
        media_id=request.media_id,
        camera_codes=parse_camera_map(camera_map),
        campaign_id=campaign_id,
        creative_id=creative_id,
        source_batch_id=source_batch_id,
        pipeline_version=pipeline_version,
        config_version=pipeline_version,
        spatial_cell=SpatialCellConfig(
            zoom=spatial_zoom,
            cell_size_degrees=spatial_cell_size_degrees,
        ),
        geo_transforms=parse_geo_transforms(geo_transform),
    )
    rows = build_dashboard_rows(load_artifact_rows(pipeline_plan.artifacts), context)
    loaded_count = persist_dashboard_rows(
        rows,
        database_url=database_url,
        media_id=request.media_id,
        target_date=request.target_date,
        dry_run=dry_run,
    )
    logger.info(
        "trajectory_dashboard_rows_loaded",
        target_date=request.target_date.isoformat(),
        media_id=request.media_id,
        dry_run=dry_run,
        loaded_count=loaded_count,
    )
    typer.echo(f"target_date={request.target_date.isoformat()}")
    typer.echo(f"media_id={request.media_id}")
    typer.echo(f"dry_run={dry_run}")
    typer.echo(f"presence_episodes={len(rows.presence_episodes)}")
    typer.echo(f"global_units={len(rows.global_units)}")
    typer.echo(f"global_presence_episodes={len(rows.global_presence_episodes)}")
    typer.echo(f"hourly_metrics={len(rows.hourly_metrics)}")
    typer.echo(f"route_families={len(rows.route_families)}")
    typer.echo(f"spatial_heatmap_cells={len(rows.spatial_heatmap_cells)}")
    typer.echo(f"loaded_count={loaded_count}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
