"""Tests for the local dashboard backend service."""

from __future__ import annotations

from pathlib import Path

from src.web.dashboard import DashboardService


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def test_dashboard_state_is_empty_before_first_run(tmp_path: Path) -> None:
    """The dashboard should report an empty workspace cleanly."""

    service = DashboardService(workspace_root=tmp_path)

    state = service.build_dashboard_state()

    assert state["overview"]["instance_count"] == 0
    assert state["overview"]["benchmark_rows"] == 0
    assert state["solver_leaderboard"] == []
    assert state["artifacts"]["demo_features"]["exists"] is False
    assert state["mode_controls"]["real"]["instance_count"] == 0
    assert state["instance_inspector"]["title"] == "No instance loaded"


def test_load_real_instance_updates_dashboard_inspector(tmp_path: Path) -> None:
    """Loading a real XML should populate the inspector without running the demo pipeline."""

    real_dir = tmp_path / "data" / "raw" / "real"
    real_dir.mkdir(parents=True)
    (real_dir / "sample.xml").write_text(
        (FIXTURES_DIR / "sample_robinx.xml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    service = DashboardService(workspace_root=tmp_path)
    state = service.load_real_instance("sample.xml")

    assert state["instance_inspector"]["source_kind"] == "real"
    assert state["instance_inspector"]["source_badge"] == "Real"
    assert state["instance_inspector"]["title"] == "SampleRobinX"
    assert any(item["label"] == "Teams" and item["value"] == 3 for item in state["instance_inspector"]["summary_items"])
    feature_groups = state["instance_inspector"]["feature_groups"]
    assert any(group["group"] == "size" for group in feature_groups)
    assert state["overview"]["benchmark_rows"] == 0


def test_generate_synthetic_preview_marks_instance_as_synthetic(tmp_path: Path) -> None:
    """Synthetic preview mode should create a labeled synthetic instance in the demo preview area."""

    service = DashboardService(
        workspace_root=tmp_path,
        default_random_seed=5,
    )
    state = service.generate_synthetic_preview(
        difficulty_level="easy",
        random_seed=5,
    )

    assert state["instance_inspector"]["source_kind"] == "synthetic"
    assert state["instance_inspector"]["source_badge"] == "Synthetic"
    assert state["instance_inspector"]["mode"] == "synthetic"
    assert "data/raw/synthetic/demo_preview" in (state["instance_inspector"]["workspace_path"] or "")
    assert state["artifacts"]["synthetic_preview"]["exists"] is True


def test_bootstrap_demo_pipeline_creates_dashboard_artifacts(tmp_path: Path) -> None:
    """Running the dashboard bootstrap should generate artifacts and metrics."""

    service = DashboardService(
        workspace_root=tmp_path,
        default_instance_count=4,
        default_random_seed=7,
        default_time_limit_seconds=1,
    )

    state = service.bootstrap_demo_pipeline(
        instance_count=4,
        random_seed=7,
        time_limit_seconds=1,
    )

    assert state["overview"]["instance_count"] == 4
    assert state["overview"]["feature_rows"] == 4
    assert state["overview"]["benchmark_rows"] == 12
    assert state["overview"]["selection_rows"] == 4
    assert state["training"]["model_name"] == "random_forest"
    assert 0.0 <= float(state["training"]["accuracy"]) <= 1.0
    assert state["evaluation"]["num_test_instances"] >= 1
    assert state["instance_inspector"]["source_kind"] == "synthetic"
    assert state["artifacts"]["demo_model"]["exists"] is True
    assert state["artifacts"]["demo_instances"]["path"].startswith("data/raw/synthetic/")
    assert state["previews"]["benchmarks"]
