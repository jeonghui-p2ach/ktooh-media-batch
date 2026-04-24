from dataclasses import dataclass
from datetime import date

from src.measurement.models import BatchWindow, PipelinePlan

DEFAULT_STEPS = (
    "load-media-cameras",
    "collect-s3-objects",
    "parse-jsonl",
    "normalize-demographic-events",
    "normalize-floating-events",
    "resolve-attribution",
    "load-audience-facts",
    "load-traffic",
    "trigger-aggregates",
    "verify",
)

WORKFLOW_STATUSES = (
    "Succeeded",
    "Failed",
    "Error",
)


@dataclass(frozen=True, slots=True)
class PipelineBuilder:
    timezone_name: str = "UTC"

    def build_plan(self, *, target_date: date, media_id: int) -> PipelinePlan:
        return PipelinePlan(
            window=BatchWindow(
                target_date=target_date,
                timezone_name=self.timezone_name,
                media_id=media_id,
            ),
            steps=DEFAULT_STEPS,
        )


def validate_step_name(step_name: str) -> str:
    if step_name not in DEFAULT_STEPS:
        raise ValueError(f"unsupported step: {step_name}")
    return step_name


def validate_workflow_status(workflow_status: str) -> str:
    if workflow_status not in WORKFLOW_STATUSES:
        raise ValueError(f"unsupported workflow status: {workflow_status}")
    return workflow_status
