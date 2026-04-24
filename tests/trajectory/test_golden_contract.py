import json
from pathlib import Path

import pytest

GOLDEN_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "trajectory" / "golden"
GOLDEN_MANIFEST = GOLDEN_ROOT / "manifest.json"
REQUIRED_GOLDEN_ARTIFACTS = (
    "presence_episode_df.pkl",
    "transition_units_df.pkl",
    "transition_nodes_df.pkl",
    "global_units_df.pkl",
    "global_presence_episode_df.pkl",
    "hourly_metric_summary_df.pkl",
    "route_family_df.pkl",
)


def test_golden_fixture_directory_is_fixed() -> None:
    assert GOLDEN_ROOT.exists()
    assert GOLDEN_ROOT.is_dir()


def test_golden_manifest_skip_policy_is_explicit() -> None:
    if not GOLDEN_MANIFEST.exists():
        pytest.skip("golden manifest is not committed yet")

    manifest = json.loads(GOLDEN_MANIFEST.read_text())

    assert manifest["source_notebook_path"]
    assert manifest["run_date"]
    assert manifest["config_snapshot"]
    assert isinstance(manifest["row_counts"], dict)
    assert isinstance(manifest["column_sets"], dict)


def test_golden_manifest_declares_required_artifacts() -> None:
    if not GOLDEN_MANIFEST.exists():
        pytest.skip("golden manifest is not committed yet")

    manifest = json.loads(GOLDEN_MANIFEST.read_text())
    artifact_files = tuple(manifest["artifacts"])

    assert artifact_files == REQUIRED_GOLDEN_ARTIFACTS
    for artifact_name in artifact_files:
        assert (GOLDEN_ROOT / artifact_name).exists()
