from pathlib import Path

from src.trajectory.contracts import build_artifact_refs
from src.trajectory.verify import verify_artifact_files


def test_verify_artifact_files_reports_missing_files(tmp_path: Path) -> None:
    refs = build_artifact_refs(tmp_path)

    summary = verify_artifact_files(refs)

    assert not summary.ok
    assert summary.missing_count == len(refs)


def test_verify_artifact_files_reports_existing_files(tmp_path: Path) -> None:
    refs = build_artifact_refs(tmp_path)
    for ref in refs:
        ref.path.parent.mkdir(parents=True, exist_ok=True)
        ref.path.write_text("", encoding="utf-8")

    summary = verify_artifact_files(refs)

    assert summary.ok
    assert summary.missing_count == 0
