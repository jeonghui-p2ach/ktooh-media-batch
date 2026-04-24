from __future__ import annotations

from dataclasses import dataclass

from src.trajectory.contracts import ArtifactRef


@dataclass(frozen=True, slots=True)
class ArtifactFileCheck:
    artifact_name: str
    path: str
    exists: bool


@dataclass(frozen=True, slots=True)
class ArtifactVerificationSummary:
    checks: tuple[ArtifactFileCheck, ...]

    @property
    def missing_count(self) -> int:
        return sum(1 for check in self.checks if not check.exists)

    @property
    def ok(self) -> bool:
        return self.missing_count == 0


def verify_artifact_files(artifact_refs: tuple[ArtifactRef, ...]) -> ArtifactVerificationSummary:
    return ArtifactVerificationSummary(
        checks=tuple(
            ArtifactFileCheck(
                artifact_name=artifact_ref.spec.name,
                path=str(artifact_ref.path),
                exists=artifact_ref.path.exists(),
            )
            for artifact_ref in artifact_refs
        )
    )
