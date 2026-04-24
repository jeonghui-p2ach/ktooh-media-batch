from datetime import date
from pathlib import Path
from typing import Annotated

import typer

from src.common.logging_config import get_logger
from src.trajectory.contracts import build_trajectory_request
from src.trajectory.pipeline import TrajectoryPipelineBuilder

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


def main() -> None:
    app()


if __name__ == "__main__":
    main()
