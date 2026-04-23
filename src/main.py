from datetime import date
from typing import Annotated

import typer

from src.config import Settings
from src.logging_config import get_logger
from src.models import BatchRequest
from src.pipeline import PipelineBuilder, validate_step_name
from src.service import execute_batch, execute_step

app = typer.Typer(no_args_is_help=True)
logger = get_logger(__name__)


def parse_target_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise typer.BadParameter("target_date must be in YYYY-MM-DD format") from error


@app.command()
def plan(
    target_date: Annotated[str, typer.Option("--target-date")],
    media_id: Annotated[int, typer.Option("--media-id")],
) -> None:
    parsed_target_date = parse_target_date(target_date)
    pipeline_plan = PipelineBuilder().build_plan(
        target_date=parsed_target_date,
        media_id=media_id,
    )
    logger.info(
        "pipeline_plan_built",
        target_date=parsed_target_date.isoformat(),
        media_id=media_id,
        step_count=len(pipeline_plan.steps),
    )
    typer.echo(f"target_date={pipeline_plan.window.target_date.isoformat()}")
    typer.echo(f"media_id={pipeline_plan.window.media_id}")
    typer.echo(f"timezone={pipeline_plan.window.timezone_name}")
    typer.echo(f"steps={','.join(pipeline_plan.steps)}")


@app.command("run-step")
def run_step(
    step_name: str,
    target_date: Annotated[str, typer.Option("--target-date")],
    media_id: Annotated[int, typer.Option("--media-id")],
) -> None:
    validated_step_name = validate_step_name(step_name)
    settings = Settings()
    request = BatchRequest(
        target_date=parse_target_date(target_date),
        media_id=media_id,
        source_type="all",
        camera_code=None,
        dry_run=True,
    )
    context = execute_step(request, settings, validated_step_name)
    logger.info(
        "step_completed",
        step_name=validated_step_name,
        target_date=request.target_date.isoformat(),
        media_id=media_id,
        collected_objects=context.collected_objects,
        demographic_records=context.demographic_records,
        floating_records=context.floating_records,
        rejected_rows=context.rejected_rows,
        audience_rows=context.audience_rows,
        traffic_rows=context.traffic_rows,
    )
    typer.echo(f"step={validated_step_name}")
    typer.echo(f"target_date={request.target_date.isoformat()}")
    typer.echo(f"media_id={media_id}")
    typer.echo(f"collected_objects={context.collected_objects}")
    typer.echo(f"demographic_records={context.demographic_records}")
    typer.echo(f"floating_records={context.floating_records}")
    typer.echo(f"rejected_rows={context.rejected_rows}")
    typer.echo(f"audience_rows={context.audience_rows}")
    typer.echo(f"traffic_rows={context.traffic_rows}")


@app.command("run-batch")
def run_batch(
    target_date: Annotated[str, typer.Option("--target-date")],
    media_id: Annotated[int, typer.Option("--media-id")],
    source_type: Annotated[str, typer.Option("--source-type")] = "all",
    camera_code: Annotated[str | None, typer.Option("--camera-code")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    settings = Settings()
    if not dry_run and not settings.database_url:
        raise typer.BadParameter("MEDIA_BATCH_DATABASE_URL must be configured for non-dry-run")
    request = BatchRequest(
        target_date=parse_target_date(target_date),
        media_id=media_id,
        source_type=source_type,
        camera_code=camera_code,
        dry_run=dry_run,
    )
    context = execute_batch(request, settings)
    logger.info(
        "batch_completed",
        target_date=request.target_date.isoformat(),
        media_id=request.media_id,
        dry_run=request.dry_run,
        collected_objects=context.collected_objects,
        demographic_records=context.demographic_records,
        floating_records=context.floating_records,
        rejected_rows=context.rejected_rows,
        audience_rows=context.audience_rows,
        traffic_rows=context.traffic_rows,
    )
    typer.echo(f"target_date={request.target_date.isoformat()}")
    typer.echo(f"media_id={request.media_id}")
    typer.echo(f"dry_run={request.dry_run}")
    typer.echo(f"collected_objects={context.collected_objects}")
    typer.echo(f"demographic_records={context.demographic_records}")
    typer.echo(f"floating_records={context.floating_records}")
    typer.echo(f"rejected_rows={context.rejected_rows}")
    typer.echo(f"audience_rows={context.audience_rows}")
    typer.echo(f"traffic_rows={context.traffic_rows}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
