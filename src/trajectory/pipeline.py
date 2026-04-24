from __future__ import annotations

from src.trajectory.contracts import (
    TRAJECTORY_STEPS,
    TrajectoryBatchRequest,
    TrajectoryPipelinePlan,
    build_artifact_refs,
)


class TrajectoryPipelineBuilder:
    def build_plan(self, request: TrajectoryBatchRequest) -> TrajectoryPipelinePlan:
        return TrajectoryPipelinePlan(
            request=request,
            steps=TRAJECTORY_STEPS,
            artifacts=build_artifact_refs(request.run_root),
        )
