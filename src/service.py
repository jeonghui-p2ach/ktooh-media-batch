from __future__ import annotations

from dataclasses import dataclass

from src.attribution import resolve_attribution
from src.collector import collect_objects
from src.config import Settings
from src.dashboard_registry import load_attribution_context, load_dashboard_bindings
from src.loader_audience import load_audience_facts, trigger_aggregates
from src.loader_traffic import load_traffic_rows
from src.models import BatchRequest, DashboardBinding, LoadSummary
from src.normalization_demographic import normalize_demographic_records
from src.normalization_floating import normalize_floating_records
from src.parser_demographic import parse_demographic_objects
from src.parser_floating import parse_floating_objects
from src.verify import verify_batch_load


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    bindings: tuple[DashboardBinding, ...] = ()
    collected_objects: int = 0
    demographic_records: int = 0
    floating_records: int = 0
    rejected_rows: int = 0
    audience_rows: int = 0
    traffic_rows: int = 0


def execute_batch(request: BatchRequest, settings: Settings) -> ExecutionContext:
    return _execute(request=request, settings=settings, stop_after_step=None)


def execute_step(request: BatchRequest, settings: Settings, step_name: str) -> ExecutionContext:
    return _execute(request=request, settings=settings, stop_after_step=step_name)


def _execute(
    *,
    request: BatchRequest,
    settings: Settings,
    stop_after_step: str | None,
) -> ExecutionContext:
    bindings = load_dashboard_bindings(
        database_url=settings.effective_dashboard_database_url(),
        media_id=request.media_id,
    )
    if not bindings:
        bindings = _fallback_bindings(request)
    bindings = tuple(
        binding
        for binding in bindings
        if (request.source_type == "all" or binding.source_type == request.source_type)
        and (request.camera_code is None or binding.camera_code == request.camera_code)
    )
    context = ExecutionContext(bindings=bindings)
    if stop_after_step == "load-media-cameras":
        return context

    objects = collect_objects(
        target_date=request.target_date,
        bindings=bindings,
        settings=settings,
    )
    context = ExecutionContext(bindings=bindings, collected_objects=len(objects))
    if stop_after_step == "collect-s3-objects":
        return context

    demographic_records, demographic_rejected = parse_demographic_objects(objects)
    floating_records, floating_rejected = parse_floating_objects(objects)
    rejected_rows = len(demographic_rejected) + len(floating_rejected)
    context = ExecutionContext(
        bindings=bindings,
        collected_objects=len(objects),
        demographic_records=len(demographic_records),
        floating_records=len(floating_records),
        rejected_rows=rejected_rows,
    )
    if stop_after_step == "parse-jsonl":
        return context

    media_id_by_camera_code = {
        binding.camera_code: binding.media_id
        for binding in bindings
    }
    audience_demographic = normalize_demographic_records(
        demographic_records,
        media_id_by_camera_code=media_id_by_camera_code,
    )
    context = ExecutionContext(
        bindings=bindings,
        collected_objects=len(objects),
        demographic_records=len(demographic_records),
        floating_records=len(floating_records),
        rejected_rows=rejected_rows,
        audience_rows=len(audience_demographic),
    )
    if stop_after_step == "normalize-demographic-events":
        return context

    traffic_rows, audience_pedestrian = normalize_floating_records(
        floating_records,
        media_id_by_camera_code=media_id_by_camera_code,
        include_pedestrian_pattern=settings.include_pedestrian_pattern,
        direction_mode=settings.traffic_direction_mode,
    )
    context = ExecutionContext(
        bindings=bindings,
        collected_objects=len(objects),
        demographic_records=len(demographic_records),
        floating_records=len(floating_records),
        rejected_rows=rejected_rows,
        audience_rows=len(audience_demographic) + len(audience_pedestrian),
        traffic_rows=len(traffic_rows),
    )
    if stop_after_step == "normalize-floating-events":
        return context

    attributed_audience, attribution_rejected = resolve_attribution(
        audience_demographic + audience_pedestrian,
        attribution_context=load_attribution_context(
            database_url=settings.effective_dashboard_database_url(),
            media_id=request.media_id,
        ),
    )
    rejected_rows += len(attribution_rejected)
    context = ExecutionContext(
        bindings=bindings,
        collected_objects=len(objects),
        demographic_records=len(demographic_records),
        floating_records=len(floating_records),
        rejected_rows=rejected_rows,
        audience_rows=len(attributed_audience),
        traffic_rows=len(traffic_rows),
    )
    if stop_after_step == "resolve-attribution":
        return context

    audience_count = load_audience_facts(
        attributed_audience,
        database_url=settings.database_url,
        media_id=request.media_id,
        target_date=request.target_date,
        dry_run=request.dry_run,
    )
    context = ExecutionContext(
        bindings=bindings,
        collected_objects=len(objects),
        demographic_records=len(demographic_records),
        floating_records=len(floating_records),
        rejected_rows=rejected_rows,
        audience_rows=audience_count,
        traffic_rows=len(traffic_rows),
    )
    if stop_after_step == "load-audience-facts":
        return context

    traffic_count = load_traffic_rows(
        traffic_rows,
        database_url=settings.database_url,
        media_id=request.media_id,
        target_date=request.target_date,
        dry_run=request.dry_run,
    )
    context = ExecutionContext(
        bindings=bindings,
        collected_objects=len(objects),
        demographic_records=len(demographic_records),
        floating_records=len(floating_records),
        rejected_rows=rejected_rows,
        audience_rows=audience_count,
        traffic_rows=traffic_count,
    )
    if stop_after_step == "load-traffic":
        return context

    trigger_aggregates(
        database_url=settings.database_url,
        media_id=request.media_id,
        target_date=request.target_date,
        dry_run=request.dry_run,
    )
    if stop_after_step == "trigger-aggregates":
        return context

    verification = verify_batch_load(
        database_url=settings.database_url,
        media_id=request.media_id,
        target_date=request.target_date,
        summary=LoadSummary(
            collected_objects=len(objects),
            demographic_records=len(demographic_records),
            floating_records=len(floating_records),
            rejected_rows=rejected_rows,
            audience_rows=audience_count,
            traffic_rows=traffic_count,
        ),
        dry_run=request.dry_run,
    )
    return ExecutionContext(
        bindings=bindings,
        collected_objects=len(objects),
        demographic_records=len(demographic_records),
        floating_records=len(floating_records),
        rejected_rows=rejected_rows,
        audience_rows=verification["audience_rows"],
        traffic_rows=verification["traffic_rows"],
    )


def _fallback_bindings(request: BatchRequest) -> tuple[DashboardBinding, ...]:
    default_bindings = (
        DashboardBinding(camera_code="CAM_5", source_type="demographic", media_id=request.media_id, camera_id=None),
        DashboardBinding(camera_code="CAM_14", source_type="floating", media_id=request.media_id, camera_id=None),
    )
    return tuple(
        binding
        for binding in default_bindings
        if (request.source_type == "all" or binding.source_type == request.source_type)
        and (request.camera_code is None or binding.camera_code == request.camera_code)
    )
