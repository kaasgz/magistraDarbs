"""Backend helpers for the local sports scheduling dashboard."""

from __future__ import annotations

import json
import logging
import math
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.features.feature_extractor import extract_features
from src.features.manifest import grouped_feature_names
from src.parsers import load_instance
from src.utils import collect_xml_files, validate_loaded_instance_source
from src.web.report_loader import (
    build_mixed_dataset_state,
    build_report_artifact_specs,
    build_thesis_reports_state,
    build_thesis_visualization_state,
)


LOGGER = logging.getLogger(__name__)
DEFAULT_SYNTHETIC_DIFFICULTY = "medium"
SYNTHETIC_DIFFICULTIES: tuple[str, ...] = ("easy", "medium", "hard")


@dataclass(frozen=True, slots=True)
class DashboardPaths:
    """Filesystem layout used by the local dashboard."""

    workspace_root: Path
    real_instance_folder: Path
    real_inventory_csv: Path
    synthetic_preview_folder: Path
    synthetic_preview_manifest_path: Path
    demo_instance_folder: Path
    demo_manifest_path: Path
    demo_features_csv: Path
    demo_benchmark_csv: Path
    demo_selection_dataset_csv: Path
    demo_model_output: Path
    demo_feature_importance_csv: Path
    demo_evaluation_csv: Path
    demo_evaluation_summary_csv: Path
    demo_evaluation_summary_markdown: Path
    demo_summary_json: Path
    main_features_csv: Path
    main_benchmark_csv: Path
    main_selection_dataset_csv: Path
    main_model_output: Path
    main_feature_importance_csv: Path
    main_evaluation_csv: Path
    main_evaluation_summary_csv: Path
    main_evaluation_summary_markdown: Path
    main_training_run_summary_json: Path
    main_evaluation_run_summary_json: Path
    thesis_dataset_metadata_csv: Path
    thesis_features_csv: Path
    thesis_benchmark_csv: Path
    thesis_selection_dataset_csv: Path
    thesis_model_output: Path
    thesis_feature_importance_csv: Path
    thesis_evaluation_csv: Path
    thesis_evaluation_summary_csv: Path
    thesis_evaluation_summary_markdown: Path
    thesis_training_run_summary_json: Path
    thesis_evaluation_run_summary_json: Path
    thesis_pipeline_summary_markdown: Path
    thesis_pipeline_run_summary_json: Path
    report_output_dir: Path
    report_solver_comparison_csv: Path
    report_solver_comparison_markdown: Path
    report_win_counts_csv: Path
    report_win_counts_markdown: Path
    report_average_objective_csv: Path
    report_average_objective_markdown: Path
    report_average_runtime_csv: Path
    report_average_runtime_markdown: Path
    report_selector_vs_baselines_csv: Path
    report_selector_vs_baselines_markdown: Path
    report_feature_importance_summary_csv: Path
    report_feature_importance_summary_markdown: Path
    report_summary_markdown: Path
    report_run_summary_json: Path

    @classmethod
    def from_workspace(cls, workspace_root: str | Path) -> "DashboardPaths":
        """Build default dashboard paths anchored at one workspace root."""

        root = Path(workspace_root)
        return cls(
            workspace_root=root,
            real_instance_folder=root / "data" / "raw" / "real",
            real_inventory_csv=root / "data" / "processed" / "real_dataset_inventory.csv",
            synthetic_preview_folder=root / "data" / "raw" / "synthetic" / "demo_preview",
            synthetic_preview_manifest_path=root / "data" / "processed" / "demo_preview_manifest.json",
            demo_instance_folder=root / "data" / "raw" / "synthetic" / "demo_instances",
            demo_manifest_path=root / "data" / "processed" / "demo_manifest.json",
            demo_features_csv=root / "data" / "processed" / "demo_features.csv",
            demo_benchmark_csv=root / "data" / "results" / "demo_benchmark_results.csv",
            demo_selection_dataset_csv=root / "data" / "processed" / "demo_selection_dataset.csv",
            demo_model_output=root / "data" / "results" / "demo_selector.joblib",
            demo_feature_importance_csv=root / "data" / "results" / "demo_feature_importance.csv",
            demo_evaluation_csv=root / "data" / "results" / "demo_selector_evaluation.csv",
            demo_evaluation_summary_csv=root / "data" / "results" / "demo_selector_evaluation_summary.csv",
            demo_evaluation_summary_markdown=root / "data" / "results" / "demo_selector_evaluation_summary.md",
            demo_summary_json=root / "data" / "results" / "demo_dashboard_summary.json",
            main_features_csv=root / "data" / "processed" / "features.csv",
            main_benchmark_csv=root / "data" / "results" / "benchmark_results.csv",
            main_selection_dataset_csv=root / "data" / "processed" / "selection_dataset.csv",
            main_model_output=root / "data" / "results" / "random_forest_selector.joblib",
            main_feature_importance_csv=root / "data" / "results" / "random_forest_feature_importance.csv",
            main_evaluation_csv=root / "data" / "results" / "selector_evaluation.csv",
            main_evaluation_summary_csv=root / "data" / "results" / "selector_evaluation_summary.csv",
            main_evaluation_summary_markdown=root / "data" / "results" / "selector_evaluation_summary.md",
            main_training_run_summary_json=root / "data" / "results" / "random_forest_selector_run_summary.json",
            main_evaluation_run_summary_json=root / "data" / "results" / "selector_evaluation_run_summary.json",
            thesis_dataset_metadata_csv=root / "data" / "raw" / "synthetic" / "generated" / "metadata.csv",
            thesis_features_csv=root / "data" / "processed" / "thesis_pipeline" / "features.csv",
            thesis_benchmark_csv=root / "data" / "results" / "thesis_pipeline" / "full_benchmark_results.csv",
            thesis_selection_dataset_csv=root / "data" / "processed" / "thesis_pipeline" / "selection_dataset.csv",
            thesis_model_output=root / "data" / "results" / "thesis_pipeline" / "random_forest_selector.joblib",
            thesis_feature_importance_csv=root / "data" / "results" / "thesis_pipeline" / "feature_importance.csv",
            thesis_evaluation_csv=root / "data" / "results" / "thesis_pipeline" / "selector_evaluation.csv",
            thesis_evaluation_summary_csv=root / "data" / "results" / "thesis_pipeline" / "selector_evaluation_summary.csv",
            thesis_evaluation_summary_markdown=root
            / "data"
            / "results"
            / "thesis_pipeline"
            / "selector_evaluation_summary.md",
            thesis_training_run_summary_json=root
            / "data"
            / "results"
            / "thesis_pipeline"
            / "selector_training_run_summary.json",
            thesis_evaluation_run_summary_json=root
            / "data"
            / "results"
            / "thesis_pipeline"
            / "selector_evaluation_run_summary.json",
            thesis_pipeline_summary_markdown=root
            / "data"
            / "results"
            / "thesis_pipeline"
            / "thesis_pipeline_summary.md",
            thesis_pipeline_run_summary_json=root
            / "data"
            / "results"
            / "thesis_pipeline"
            / "thesis_pipeline_run_summary.json",
            report_output_dir=root / "data" / "results" / "reports",
            report_solver_comparison_csv=root / "data" / "results" / "reports" / "solver_comparison.csv",
            report_solver_comparison_markdown=root / "data" / "results" / "reports" / "solver_comparison.md",
            report_win_counts_csv=root / "data" / "results" / "reports" / "solver_win_counts.csv",
            report_win_counts_markdown=root / "data" / "results" / "reports" / "solver_win_counts.md",
            report_average_objective_csv=root
            / "data"
            / "results"
            / "reports"
            / "average_objective_per_solver.csv",
            report_average_objective_markdown=root
            / "data"
            / "results"
            / "reports"
            / "average_objective_per_solver.md",
            report_average_runtime_csv=root
            / "data"
            / "results"
            / "reports"
            / "average_runtime_per_solver.csv",
            report_average_runtime_markdown=root
            / "data"
            / "results"
            / "reports"
            / "average_runtime_per_solver.md",
            report_selector_vs_baselines_csv=root
            / "data"
            / "results"
            / "reports"
            / "selector_vs_baselines.csv",
            report_selector_vs_baselines_markdown=root
            / "data"
            / "results"
            / "reports"
            / "selector_vs_baselines.md",
            report_feature_importance_summary_csv=root
            / "data"
            / "results"
            / "reports"
            / "feature_importance_summary.csv",
            report_feature_importance_summary_markdown=root
            / "data"
            / "results"
            / "reports"
            / "feature_importance_summary.md",
            report_summary_markdown=root / "data" / "results" / "reports" / "thesis_benchmark_report.md",
            report_run_summary_json=root
            / "data"
            / "results"
            / "reports"
            / "thesis_benchmark_report_run_summary.json",
        )


class DashboardService:
    """Serve dashboard-ready state for the local thesis project."""

    def __init__(
        self,
        workspace_root: str | Path,
        selected_solvers: list[str] | None = None,
        default_instance_count: int = 6,
        default_random_seed: int = 42,
        default_time_limit_seconds: int = 1,
        default_synthetic_difficulty: str = DEFAULT_SYNTHETIC_DIFFICULTY,
    ) -> None:
        """Initialize the service with stable default settings."""

        self.paths = DashboardPaths.from_workspace(workspace_root)
        self.selected_solvers = selected_solvers or [
            "random_baseline",
            "cpsat_solver",
            "simulated_annealing_solver",
        ]
        self.default_instance_count = default_instance_count
        self.default_random_seed = default_random_seed
        self.default_time_limit_seconds = default_time_limit_seconds
        self.default_synthetic_difficulty = _normalize_synthetic_difficulty(
            default_synthetic_difficulty,
            fallback=DEFAULT_SYNTHETIC_DIFFICULTY,
        )

        self._run_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._run_state: dict[str, Any] = {
            "is_running": False,
            "phase": "idle",
            "message": "Dashboard is ready for real-instance inspection or synthetic demo runs.",
            "last_error": None,
            "updated_at": _timestamp_now(),
        }
        self._instance_inspector: dict[str, Any] = _empty_instance_inspector()

    def build_dashboard_state(self) -> dict[str, Any]:
        """Collect the current dashboard state from the generated artifacts."""

        manifest = _load_json_file(self.paths.demo_manifest_path)
        summary = _load_json_file(self.paths.demo_summary_json)

        features = _safe_read_csv(self.paths.demo_features_csv)
        benchmarks = _safe_read_csv(self.paths.demo_benchmark_csv)
        selection_dataset = _safe_read_csv(self.paths.demo_selection_dataset_csv)
        evaluation = _safe_read_csv(self.paths.demo_evaluation_csv)
        feature_importance = _safe_read_csv(self.paths.demo_feature_importance_csv)

        instance_catalog = _build_instance_catalog(manifest)
        solver_leaderboard = _build_solver_leaderboard(benchmarks)
        best_solver_distribution = _build_best_solver_distribution(selection_dataset)
        feature_importance_preview = _build_feature_importance_preview(feature_importance)
        real_instances = _list_available_instances(
            self.paths.real_instance_folder,
            base_folder=self.paths.real_instance_folder,
            workspace_root=self.paths.workspace_root,
        )

        training_summary = summary.get("training", {}) if isinstance(summary, dict) else {}
        evaluation_summary = summary.get("evaluation", {}) if isinstance(summary, dict) else {}
        generation_summary = summary.get("generation", {}) if isinstance(summary, dict) else {}
        main_pipeline = _build_main_pipeline_state(self.paths)
        thesis_pipeline = _build_thesis_pipeline_state(self.paths)
        thesis_reports = build_thesis_reports_state(self.paths.workspace_root)
        thesis_visualization = build_thesis_visualization_state(self.paths.workspace_root)
        presentation_dashboard = thesis_visualization
        mixed_dataset = build_mixed_dataset_state(self.paths.workspace_root)
        benchmark_reports = thesis_reports
        artifact_browser = _build_artifact_browser_state(self.paths)

        return {
            "workspace_root": self.paths.workspace_root.as_posix(),
            "defaults": {
                "instance_count": self.default_instance_count,
                "random_seed": self.default_random_seed,
                "time_limit_seconds": self.default_time_limit_seconds,
                "selected_solvers": list(self.selected_solvers),
                "synthetic_difficulty": self.default_synthetic_difficulty,
            },
            "dashboard_scope": {
                "purpose": (
                    "Local thesis demo workspace for inspecting real XML instances and running "
                    "synthetic demo experiments."
                ),
                "not_for": (
                    "Not an authoritative benchmark runner for final thesis reporting and not a "
                    "place to mix real and synthetic experiment artifacts."
                ),
                "demo_output_prefix": "demo_",
            },
            "mode_controls": {
                "real": {
                    "instance_folder": _relative_path(self.paths.workspace_root, self.paths.real_instance_folder),
                    "available_instances": real_instances,
                    "instance_count": len(real_instances),
                },
                "synthetic": {
                    "preview_folder": _relative_path(
                        self.paths.workspace_root,
                        self.paths.synthetic_preview_folder,
                    ),
                    "difficulty_levels": list(SYNTHETIC_DIFFICULTIES),
                },
            },
            "instance_inspector": self.get_instance_inspector(),
            "run_state": self.get_run_state(),
            "overview": {
                "instance_count": len(instance_catalog),
                "feature_rows": len(features.index) if features is not None else 0,
                "benchmark_rows": len(benchmarks.index) if benchmarks is not None else 0,
                "selection_rows": len(selection_dataset.index) if selection_dataset is not None else 0,
                "labeled_instances": int(selection_dataset["best_solver"].notna().sum())
                if selection_dataset is not None and "best_solver" in selection_dataset.columns
                else 0,
                "solver_count": len(self.selected_solvers),
                "selected_solvers": list(self.selected_solvers),
                "last_generated_at": generation_summary.get("generated_at"),
                "diverse_best_solver_count": generation_summary.get("diverse_best_solver_count", 0),
                "pipeline_mode": generation_summary.get("mode", "synthetic_demo_pipeline"),
            },
            "training": training_summary,
            "evaluation": evaluation_summary,
            "thesis_pipeline": thesis_pipeline,
            "thesis_reports": thesis_reports,
            "thesis_visualization": thesis_visualization,
            "presentation_dashboard": presentation_dashboard,
            "mixed_dataset": mixed_dataset,
            "main_pipeline": main_pipeline,
            "benchmark_reports": benchmark_reports,
            "artifact_browser": artifact_browser,
            "solver_leaderboard": solver_leaderboard,
            "best_solver_distribution": best_solver_distribution,
            "feature_importance": feature_importance_preview,
            "instance_catalog": instance_catalog[:8],
            "artifacts": {
                "real_instances": _describe_path(self.paths.workspace_root, self.paths.real_instance_folder),
                "synthetic_preview": _describe_path(
                    self.paths.workspace_root,
                    self.paths.synthetic_preview_folder,
                ),
                "demo_instances": _describe_path(
                    self.paths.workspace_root,
                    self.paths.demo_instance_folder,
                ),
                "demo_manifest": _describe_path(self.paths.workspace_root, self.paths.demo_manifest_path),
                "demo_features": _describe_path(self.paths.workspace_root, self.paths.demo_features_csv),
                "demo_benchmarks": _describe_path(
                    self.paths.workspace_root,
                    self.paths.demo_benchmark_csv,
                ),
                "demo_selection_dataset": _describe_path(
                    self.paths.workspace_root,
                    self.paths.demo_selection_dataset_csv,
                ),
                "demo_model": _describe_path(self.paths.workspace_root, self.paths.demo_model_output),
                "demo_feature_importance": _describe_path(
                    self.paths.workspace_root,
                    self.paths.demo_feature_importance_csv,
                ),
                "demo_evaluation": _describe_path(
                    self.paths.workspace_root,
                    self.paths.demo_evaluation_csv,
                ),
                "demo_evaluation_summary_csv": _describe_path(
                    self.paths.workspace_root,
                    self.paths.demo_evaluation_summary_csv,
                ),
                "demo_evaluation_summary_markdown": _describe_path(
                    self.paths.workspace_root,
                    self.paths.demo_evaluation_summary_markdown,
                ),
            },
            "previews": {
                "instances": instance_catalog[:6],
                "features": _frame_preview(features, limit=6),
                "benchmarks": _frame_preview(benchmarks, limit=6),
                "selection_dataset": _frame_preview(selection_dataset, limit=6),
                "evaluation": _frame_preview(evaluation, limit=6),
            },
        }

    def preview_artifact(self, artifact_id: str) -> dict[str, Any]:
        """Return a small read-only preview for one whitelisted artifact."""

        artifact = _artifact_browser_lookup(self.paths).get(str(artifact_id or "").strip())
        if artifact is None:
            raise ValueError("Unknown dashboard artifact.")

        path = artifact["path"]
        if not isinstance(path, Path) or not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Artifact does not exist: {artifact.get('file_name', artifact_id)}")

        preview_kind = str(artifact.get("preview_kind") or "")
        base_payload = {
            "artifact": _browser_artifact_payload(
                artifact_id=str(artifact["artifact_id"]),
                path=path,
                workspace_root=self.paths.workspace_root,
                artifact_type=str(artifact["artifact_type"]),
                scope=str(artifact["scope"]),
                preview_kind=preview_kind,
            )
        }
        if preview_kind == "csv":
            return {
                **base_payload,
                "preview_kind": "csv",
                **_preview_csv_artifact(path),
            }
        if preview_kind == "markdown":
            return {
                **base_payload,
                "preview_kind": "markdown",
                **_preview_markdown_artifact(path),
            }

        raise ValueError("Only CSV and Markdown artifacts can be previewed in the dashboard.")

    def resolve_generated_file(self, relative_path: str) -> Path:
        """Resolve one generated thesis artifact file for read-only HTTP serving."""

        clean_relative = str(relative_path or "").strip().replace("\\", "/")
        if not clean_relative:
            raise ValueError("Generated file path is required.")

        candidate = (self.paths.workspace_root / clean_relative).resolve()
        results_root = (self.paths.workspace_root / "data" / "results").resolve()
        try:
            candidate.relative_to(results_root)
        except ValueError as exc:
            raise ValueError("Generated file path is outside the allowed results directory.") from exc
        if not candidate.exists() or not candidate.is_file():
            raise FileNotFoundError(f"Generated file not found: {clean_relative}")
        return candidate

    def load_real_instance(self, relative_path: str) -> dict[str, Any]:
        """Load one real XML instance and update the dashboard inspector."""

        if not self._run_lock.acquire(blocking=False):
            raise RuntimeError("A dashboard action is already in progress.")

        try:
            self._set_run_state(
                phase="loading_real_instance",
                message="Loading the selected real XML instance.",
                is_running=True,
                last_error=None,
            )
            xml_path = _resolve_xml_path(self.paths.real_instance_folder, relative_path)
            inspection = _inspect_instance_file(
                xml_path,
                workspace_root=self.paths.workspace_root,
                source_kind="real",
                mode="real",
                mode_label="Load Real Instance",
            )
            self._set_instance_inspector(inspection)
            self._set_run_state(
                phase="ready",
                message="Real instance loaded for inspection.",
                is_running=False,
                last_error=None,
            )
            return self.build_dashboard_state()
        except Exception as exc:
            self._set_run_state(
                phase="error",
                message="Failed to load the selected real instance.",
                is_running=False,
                last_error=str(exc),
            )
            raise
        finally:
            self._run_lock.release()

    def generate_synthetic_preview(
        self,
        *,
        difficulty_level: str | None = None,
        random_seed: int | None = None,
    ) -> dict[str, Any]:
        """Generate one synthetic preview instance and update the dashboard inspector."""

        if not self._run_lock.acquire(blocking=False):
            raise RuntimeError("A dashboard action is already in progress.")

        resolved_difficulty = _normalize_synthetic_difficulty(
            difficulty_level,
            fallback=self.default_synthetic_difficulty,
        )
        target_seed = random_seed if random_seed is not None else self.default_random_seed

        try:
            self._set_run_state(
                phase="generating_synthetic_preview",
                message=f"Generating one {resolved_difficulty} synthetic preview instance.",
                is_running=True,
                last_error=None,
            )
            from src.demo import generate_demo_instances

            generate_demo_instances(
                output_folder=self.paths.synthetic_preview_folder,
                manifest_path=self.paths.synthetic_preview_manifest_path,
                instance_count=1,
                random_seed=target_seed,
                difficulty_level=resolved_difficulty,
            )

            preview_files = collect_xml_files(self.paths.synthetic_preview_folder)
            if not preview_files:
                raise RuntimeError("Synthetic preview generation did not create an XML file.")

            inspection = _inspect_instance_file(
                preview_files[0],
                workspace_root=self.paths.workspace_root,
                source_kind="synthetic",
                mode="synthetic",
                mode_label="Generate Synthetic Instance",
            )
            self._set_instance_inspector(inspection)
            self._set_run_state(
                phase="ready",
                message="Synthetic preview instance is ready.",
                is_running=False,
                last_error=None,
            )
            return self.build_dashboard_state()
        except Exception as exc:
            self._set_run_state(
                phase="error",
                message="Synthetic preview generation failed.",
                is_running=False,
                last_error=str(exc),
            )
            raise
        finally:
            self._run_lock.release()

    def bootstrap_demo_pipeline(
        self,
        instance_count: int | None = None,
        random_seed: int | None = None,
        time_limit_seconds: int | None = None,
    ) -> dict[str, Any]:
        """Generate synthetic demo data and run the full demo pipeline."""

        if not self._run_lock.acquire(blocking=False):
            raise RuntimeError("A dashboard pipeline run is already in progress.")

        target_instance_count = instance_count or self.default_instance_count
        target_seed = random_seed if random_seed is not None else self.default_random_seed
        target_time_limit = time_limit_seconds or self.default_time_limit_seconds

        try:
            self._set_run_state(
                phase="preparing_demo_pipeline",
                message="Preparing synthetic demo workspace.",
                is_running=True,
                last_error=None,
            )

            used_seed = target_seed
            diversity_count = 0
            generation = None

            for attempt in range(3):
                candidate_seed = target_seed + attempt
                self._set_run_state(
                    phase="generating_demo_instances",
                    message=f"Generating synthetic demo batch with seed {candidate_seed}.",
                    is_running=True,
                    last_error=None,
                )
                from src.demo import generate_demo_instances

                generation = generate_demo_instances(
                    output_folder=self.paths.demo_instance_folder,
                    manifest_path=self.paths.demo_manifest_path,
                    instance_count=target_instance_count,
                    random_seed=candidate_seed,
                )

                self._set_run_state(
                    phase="building_demo_features",
                    message="Building structural features for synthetic demo instances.",
                    is_running=True,
                    last_error=None,
                )
                from src.features.build_feature_table import build_feature_table

                build_feature_table(
                    input_folder=str(self.paths.demo_instance_folder),
                    output_csv=self.paths.demo_features_csv,
                )

                self._set_run_state(
                    phase="running_demo_benchmarks",
                    message="Running solver benchmarks on synthetic demo instances.",
                    is_running=True,
                    last_error=None,
                )
                from src.experiments.run_benchmarks import run_benchmarks

                run_benchmarks(
                    instance_folder=str(self.paths.demo_instance_folder),
                    solver_names=list(self.selected_solvers),
                    time_limit_seconds=target_time_limit,
                    random_seed=candidate_seed,
                    output_csv=self.paths.demo_benchmark_csv,
                )

                self._set_run_state(
                    phase="building_demo_selection_dataset",
                    message="Building the synthetic demo selection dataset.",
                    is_running=True,
                    last_error=None,
                )
                from src.selection.build_selection_dataset import build_selection_dataset

                build_selection_dataset(
                    features_csv=self.paths.demo_features_csv,
                    benchmark_csv=self.paths.demo_benchmark_csv,
                    output_csv=self.paths.demo_selection_dataset_csv,
                    include_solver_objectives=True,
                )

                diversity_count = _count_best_solver_labels(self.paths.demo_selection_dataset_csv)
                used_seed = candidate_seed
                if diversity_count >= 2 or attempt == 2:
                    break

            self._set_run_state(
                phase="training_demo_selector",
                message="Training the selector on synthetic demo data.",
                is_running=True,
                last_error=None,
            )
            from src.selection.train_selector import train_selector

            training_result = train_selector(
                dataset_csv=self.paths.demo_selection_dataset_csv,
                model_path=self.paths.demo_model_output,
                feature_importance_csv=self.paths.demo_feature_importance_csv,
                random_seed=used_seed,
                test_size=0.25,
                model_name="random_forest",
            )

            self._set_run_state(
                phase="evaluating_demo_selector",
                message="Evaluating the selector against synthetic demo benchmarks.",
                is_running=True,
                last_error=None,
            )
            from src.selection.evaluate_selector import evaluate_selector

            evaluation_result = evaluate_selector(
                dataset_csv=self.paths.demo_selection_dataset_csv,
                benchmark_csv=self.paths.demo_benchmark_csv,
                model_path=self.paths.demo_model_output,
                report_csv=self.paths.demo_evaluation_csv,
                summary_csv=self.paths.demo_evaluation_summary_csv,
                summary_markdown=self.paths.demo_evaluation_summary_markdown,
                random_seed=used_seed,
                test_size=0.25,
            )

            if generation is None:
                raise RuntimeError("Synthetic demo generation did not produce any instances.")

            self._write_summary_json(
                generation_seed=used_seed,
                diversity_count=diversity_count,
                instance_count=generation.instance_count,
                time_limit_seconds=target_time_limit,
                training_result=training_result,
                evaluation_result=evaluation_result,
            )
            self._refresh_inspector_from_demo_batch()
            self._set_run_state(
                phase="ready",
                message="Synthetic demo pipeline artifacts are ready.",
                is_running=False,
                last_error=None,
            )
            return self.build_dashboard_state()
        except Exception as exc:
            LOGGER.exception("Dashboard demo pipeline failed.")
            self._set_run_state(
                phase="error",
                message="Synthetic demo pipeline failed.",
                is_running=False,
                last_error=str(exc),
            )
            raise
        finally:
            self._run_lock.release()

    def get_run_state(self) -> dict[str, Any]:
        """Return the latest in-memory run state snapshot."""

        with self._state_lock:
            return dict(self._run_state)

    def get_instance_inspector(self) -> dict[str, Any]:
        """Return the latest inspected real or synthetic instance summary."""

        with self._state_lock:
            return json.loads(json.dumps(self._instance_inspector))

    def _set_run_state(
        self,
        *,
        phase: str,
        message: str,
        is_running: bool,
        last_error: str | None,
    ) -> None:
        """Update the current run state in a thread-safe way."""

        with self._state_lock:
            self._run_state = {
                "is_running": is_running,
                "phase": phase,
                "message": message,
                "last_error": last_error,
                "updated_at": _timestamp_now(),
            }

    def _set_instance_inspector(self, payload: dict[str, Any]) -> None:
        """Update the current instance inspection snapshot."""

        with self._state_lock:
            self._instance_inspector = payload

    def _refresh_inspector_from_demo_batch(self) -> None:
        """Point the inspector at the first synthetic demo instance when available."""

        demo_files = collect_xml_files(self.paths.demo_instance_folder)
        if not demo_files:
            return

        inspection = _inspect_instance_file(
            demo_files[0],
            workspace_root=self.paths.workspace_root,
            source_kind="synthetic",
            mode="synthetic",
            mode_label="Synthetic Demo Pipeline",
        )
        self._set_instance_inspector(inspection)

    def _write_summary_json(
        self,
        *,
        generation_seed: int,
        diversity_count: int,
        instance_count: int,
        time_limit_seconds: int,
        training_result: object,
        evaluation_result: object,
    ) -> None:
        """Persist a compact JSON summary for fast dashboard reloads."""

        self.paths.demo_summary_json.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "generation": {
                "mode": "synthetic_demo_pipeline",
                "artifact_prefix": "demo_",
                "generated_at": _timestamp_now(),
                "instance_count": instance_count,
                "random_seed": generation_seed,
                "time_limit_seconds": time_limit_seconds,
                "selected_solvers": list(self.selected_solvers),
                "diverse_best_solver_count": diversity_count,
            },
            "training": {
                "model_name": training_result.model_name,
                "model_path": _relative_path(self.paths.workspace_root, training_result.model_path),
                "feature_importance_path": _relative_path(
                    self.paths.workspace_root,
                    training_result.feature_importance_path,
                ),
                "accuracy": training_result.accuracy,
                "balanced_accuracy": training_result.balanced_accuracy,
                "num_labeled_rows": training_result.num_labeled_rows,
                "num_validation_splits": training_result.num_validation_splits,
                "split_strategy": training_result.split_strategy,
                "num_train_rows": training_result.num_train_rows,
                "num_test_rows": training_result.num_test_rows,
                "confusion_matrix": _serialize_confusion_matrix(training_result.confusion_matrix),
            },
            "evaluation": {
                "report_path": _relative_path(self.paths.workspace_root, evaluation_result.report_path),
                "summary_csv_path": _relative_path(
                    self.paths.workspace_root,
                    evaluation_result.summary_csv_path,
                ),
                "summary_markdown_path": _relative_path(
                    self.paths.workspace_root,
                    evaluation_result.summary_markdown_path,
                ),
                "single_best_solver_name": evaluation_result.single_best_solver_name,
                "classification_accuracy": evaluation_result.classification_accuracy,
                "balanced_accuracy": evaluation_result.balanced_accuracy,
                "average_selected_objective": evaluation_result.average_selected_objective,
                "average_virtual_best_objective": evaluation_result.average_virtual_best_objective,
                "average_single_best_objective": evaluation_result.average_single_best_objective,
                "regret_vs_virtual_best": evaluation_result.regret_vs_virtual_best,
                "delta_vs_single_best": evaluation_result.delta_vs_single_best,
                "improvement_vs_single_best": evaluation_result.improvement_vs_single_best,
                "num_test_instances": evaluation_result.num_test_instances,
                "num_validation_splits": evaluation_result.num_validation_splits,
                "split_strategy": evaluation_result.split_strategy,
            },
        }
        self.paths.demo_summary_json.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )


def _list_available_instances(
    folder: Path,
    *,
    base_folder: Path,
    workspace_root: Path,
) -> list[dict[str, Any]]:
    """List XML files available under one dashboard folder."""

    if not folder.exists() or not folder.is_dir():
        return []

    return [
        {
            "relative_path": path.relative_to(base_folder).as_posix(),
            "workspace_path": _relative_path(workspace_root, path),
            "file_name": path.name,
        }
        for path in collect_xml_files(folder)
    ]


def _inspect_instance_file(
    xml_path: Path,
    *,
    workspace_root: Path,
    source_kind: str,
    mode: str,
    mode_label: str,
) -> dict[str, Any]:
    """Build a concise dashboard inspection payload for one XML file."""

    instance = load_instance(str(xml_path))
    validate_loaded_instance_source(instance, xml_path, expected_source=source_kind)
    features = extract_features(instance)
    metadata = getattr(instance, "metadata", None)

    resolved_source_kind = "synthetic" if getattr(metadata, "synthetic", None) is True else source_kind
    summary_items = _instance_summary_items(
        instance=instance,
        xml_path=xml_path,
        workspace_root=workspace_root,
        source_kind=resolved_source_kind,
    )
    parser_notes = [
        {
            "severity": str(getattr(note, "severity", "info")),
            "code": str(getattr(note, "code", "parser_note")),
            "message": str(getattr(note, "message", "")),
        }
        for note in getattr(instance, "parser_notes", []) or []
    ]

    return {
        "mode": mode,
        "mode_label": mode_label,
        "title": getattr(metadata, "name", None) or xml_path.stem,
        "source_kind": resolved_source_kind,
        "source_badge": "Synthetic" if resolved_source_kind == "synthetic" else "Real",
        "source_description": (
            "Synthetic dashboard preview or demo instance."
            if resolved_source_kind == "synthetic"
            else "Real XML instance loaded from the benchmark intake folder."
        ),
        "workspace_path": _relative_path(workspace_root, xml_path),
        "summary_items": summary_items,
        "feature_groups": _group_feature_rows(features),
        "parser_notes": parser_notes,
        "loaded_at": _timestamp_now(),
    }


def _instance_summary_items(
    *,
    instance: object,
    xml_path: Path,
    workspace_root: Path,
    source_kind: str,
) -> list[dict[str, Any]]:
    """Create a concise summary block for one inspected instance."""

    metadata = getattr(instance, "metadata", None)
    objective_name = getattr(metadata, "objective_name", None) or ""
    objective_sense = getattr(metadata, "objective_sense", None) or ""
    objective_text = " / ".join(value for value in (objective_name, objective_sense) if value) or "Not specified"

    items: list[dict[str, Any]] = [
        {"label": "Source", "value": "Synthetic" if source_kind == "synthetic" else "Real"},
        {"label": "XML Path", "value": _relative_path(workspace_root, xml_path)},
        {"label": "Teams", "value": getattr(instance, "team_count", 0)},
        {"label": "Slots", "value": getattr(instance, "slot_count", 0)},
        {"label": "Constraints", "value": getattr(instance, "constraint_count", 0)},
        {"label": "Objective", "value": objective_text},
    ]

    round_robin_mode = getattr(metadata, "round_robin_mode", None)
    difficulty_level = getattr(metadata, "difficulty_level", None)
    generation_seed = getattr(metadata, "generation_seed", None)
    generated_at = getattr(metadata, "generated_at", None)

    if round_robin_mode:
        items.append({"label": "Round Robin Mode", "value": round_robin_mode})
    if difficulty_level:
        items.append({"label": "Difficulty", "value": difficulty_level})
    if generation_seed is not None:
        items.append({"label": "Generation Seed", "value": generation_seed})
    if generated_at:
        items.append({"label": "Generated At", "value": generated_at})

    items.append(
        {
            "label": "Parser Notes",
            "value": len(getattr(instance, "parser_notes", []) or []),
        }
    )
    return items


def _group_feature_rows(features: dict[str, Any]) -> list[dict[str, Any]]:
    """Group extracted features according to the documented feature manifest."""

    grouped = grouped_feature_names()
    rows: list[dict[str, Any]] = []
    for group_name, feature_names in grouped.items():
        items = [
            {
                "name": feature_name,
                "value": _json_safe_value(features.get(feature_name)),
            }
            for feature_name in feature_names
            if feature_name in features
        ]
        if not items:
            continue
        rows.append(
            {
                "group": group_name,
                "label": _labelize(group_name),
                "items": items,
            }
        )
    return rows


def _resolve_xml_path(base_folder: Path, relative_path: str) -> Path:
    """Resolve one user-selected XML path safely within the requested folder."""

    candidate_text = str(relative_path or "").strip()
    if not candidate_text:
        raise ValueError("Please select an XML instance first.")

    base_resolved = base_folder.resolve()
    candidate = (base_folder / candidate_text).resolve()
    try:
        candidate.relative_to(base_resolved)
    except ValueError as exc:
        raise ValueError("The selected XML path is outside the allowed dashboard folder.") from exc

    if not candidate.exists():
        raise FileNotFoundError(f"Selected XML file does not exist: {candidate}")
    if not candidate.is_file() or candidate.suffix.lower() != ".xml":
        raise ValueError("The selected dashboard file must be an XML instance.")
    return candidate


def _normalize_synthetic_difficulty(value: object, *, fallback: str) -> str:
    """Normalize a dashboard synthetic difficulty value."""

    text = str(value or fallback).strip().casefold()
    if text not in SYNTHETIC_DIFFICULTIES:
        return fallback
    return text


def _empty_instance_inspector() -> dict[str, Any]:
    """Return the initial empty state for the instance inspector."""

    return {
        "mode": None,
        "mode_label": "Instance Inspector",
        "title": "No instance loaded",
        "source_kind": None,
        "source_badge": None,
        "source_description": (
            "Load a real XML instance or generate a synthetic preview to inspect "
            "structural features in the dashboard."
        ),
        "workspace_path": None,
        "summary_items": [],
        "feature_groups": [],
        "parser_notes": [],
        "loaded_at": None,
    }


def _build_instance_catalog(manifest: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Create a compact instance catalog from the demo manifest."""

    if not isinstance(manifest, dict):
        return []

    raw_instances = manifest.get("instances", [])
    if not isinstance(raw_instances, list):
        return []

    instances: list[dict[str, Any]] = []
    for item in raw_instances:
        if not isinstance(item, dict):
            continue
        instances.append(
            {
                "instance_name": item.get("instance_name"),
                "source_kind": "synthetic",
                "difficulty_level": item.get("difficulty_level") or item.get("profile_name"),
                "round_robin_mode": item.get("round_robin_mode"),
                "team_count": item.get("team_count"),
                "slot_count": item.get("slot_count"),
                "hard_constraint_count": item.get("hard_constraint_count"),
                "soft_constraint_count": item.get("soft_constraint_count"),
                "constraint_count": item.get("constraint_count"),
            }
        )
    return instances


def _build_solver_leaderboard(benchmarks: pd.DataFrame | None) -> list[dict[str, Any]]:
    """Create solver aggregate metrics for the dashboard."""

    if benchmarks is None or benchmarks.empty:
        return []

    from src.experiments.metrics import average_objective_by_solver, average_runtime_by_solver

    objective_summary = average_objective_by_solver(benchmarks)
    runtime_summary = average_runtime_by_solver(benchmarks)

    winners = (
        benchmarks.assign(
            objective_value=pd.to_numeric(benchmarks["objective_value"], errors="coerce"),
            runtime_seconds=pd.to_numeric(benchmarks["runtime_seconds"], errors="coerce"),
        )
        .sort_values(
            by=["instance_name", "objective_value", "runtime_seconds", "solver_name"],
            ascending=[True, True, True, True],
            na_position="last",
            kind="mergesort",
        )
        .dropna(subset=["objective_value"])
        .groupby("instance_name", as_index=False)
        .head(1)["solver_name"]
        .value_counts()
        .to_dict()
    )

    summary = objective_summary.merge(
        runtime_summary.loc[:, ["solver_name", "average_runtime", "num_runs", "num_feasible_runs"]],
        on="solver_name",
        how="outer",
    ).fillna({"num_instances_solved": 0, "num_runs": 0, "num_feasible_runs": 0})
    summary["wins"] = summary["solver_name"].map(lambda name: int(winners.get(name, 0)))
    summary = summary.sort_values(
        by=["wins", "average_objective", "average_runtime", "solver_name"],
        ascending=[False, True, True, True],
        kind="mergesort",
    )
    return _records(summary)


def _build_best_solver_distribution(selection_dataset: pd.DataFrame | None) -> list[dict[str, Any]]:
    """Summarize best-solver target frequencies for the dashboard."""

    if selection_dataset is None or selection_dataset.empty or "best_solver" not in selection_dataset.columns:
        return []

    counts = (
        selection_dataset["best_solver"]
        .dropna()
        .astype(str)
        .value_counts()
        .rename_axis("solver_name")
        .reset_index(name="count")
    )
    return _records(counts)


def _build_feature_importance_preview(feature_importance: pd.DataFrame | None) -> list[dict[str, Any]]:
    """Return the top feature importance rows for charting."""

    if feature_importance is None or feature_importance.empty:
        return []

    frame = feature_importance.copy()
    frame["importance"] = pd.to_numeric(frame["importance"], errors="coerce")
    frame = frame.dropna(subset=["importance"]).head(8)
    return _records(frame)


def _build_main_pipeline_state(paths: DashboardPaths) -> dict[str, Any]:
    """Build one dashboard section describing the latest core real-data pipeline run."""

    inventory = _safe_read_csv(paths.real_inventory_csv)
    features = _safe_read_csv(paths.main_features_csv)
    benchmarks = _safe_read_csv(paths.main_benchmark_csv)
    selection_dataset = _safe_read_csv(paths.main_selection_dataset_csv)
    evaluation = _safe_read_csv(paths.main_evaluation_csv)
    feature_importance = _safe_read_csv(paths.main_feature_importance_csv)
    training_summary = _extract_training_summary(_load_json_file(paths.main_training_run_summary_json))
    evaluation_summary = _extract_evaluation_summary(_load_json_file(paths.main_evaluation_run_summary_json))
    inventory_summary = _summarize_inventory(inventory)

    selected_solvers: list[str] = []
    if benchmarks is not None and not benchmarks.empty and "solver_name" in benchmarks.columns:
        selected_solvers = sorted(benchmarks["solver_name"].dropna().astype(str).unique().tolist())

    labeled_instances = 0
    distinct_best_solvers = 0
    if selection_dataset is not None and "best_solver" in selection_dataset.columns:
        labeled = selection_dataset["best_solver"].dropna().astype(str)
        labeled_instances = int(labeled.count())
        distinct_best_solvers = int(labeled.nunique())

    available = any(
        item is not None
        for item in (
            inventory,
            features,
            benchmarks,
            selection_dataset,
            evaluation,
            feature_importance,
        )
    )

    return {
        "available": available,
        "scope": {
            "title": "Main Thesis Pipeline",
            "description": (
                "Core CLI outputs produced from real benchmark XML files under data/raw/real. "
                "This section stays separate from synthetic dashboard demo artifacts."
            ),
        },
        "overview": {
            "parseable_real_files": inventory_summary["parseable_real_files"],
            "failed_real_files": inventory_summary["failed_real_files"],
            "inventory_rows": inventory_summary["inventory_rows"],
            "instance_count": len(features.index) if features is not None else 0,
            "feature_rows": len(features.index) if features is not None else 0,
            "benchmark_rows": len(benchmarks.index) if benchmarks is not None else 0,
            "selection_rows": len(selection_dataset.index) if selection_dataset is not None else 0,
            "labeled_instances": labeled_instances,
            "distinct_best_solvers": distinct_best_solvers,
            "solver_count": len(selected_solvers),
            "selected_solvers": selected_solvers,
            "pipeline_mode": "main_real_pipeline",
        },
        "training": training_summary,
        "evaluation": evaluation_summary,
        "solver_leaderboard": _build_solver_leaderboard(benchmarks),
        "best_solver_distribution": _build_best_solver_distribution(selection_dataset),
        "feature_importance": _build_feature_importance_preview(feature_importance),
        "artifacts": {
            "real_inventory": _describe_path(paths.workspace_root, paths.real_inventory_csv),
            "main_features": _describe_path(paths.workspace_root, paths.main_features_csv),
            "main_benchmarks": _describe_path(paths.workspace_root, paths.main_benchmark_csv),
            "main_selection_dataset": _describe_path(paths.workspace_root, paths.main_selection_dataset_csv),
            "main_model": _describe_path(paths.workspace_root, paths.main_model_output),
            "main_feature_importance": _describe_path(paths.workspace_root, paths.main_feature_importance_csv),
            "main_evaluation": _describe_path(paths.workspace_root, paths.main_evaluation_csv),
            "main_evaluation_summary_csv": _describe_path(paths.workspace_root, paths.main_evaluation_summary_csv),
            "main_evaluation_summary_markdown": _describe_path(
                paths.workspace_root,
                paths.main_evaluation_summary_markdown,
            ),
        },
        "previews": {
            "inventory": _frame_preview(inventory, limit=6),
            "features": _frame_preview(features, limit=6),
            "benchmarks": _frame_preview(benchmarks, limit=6),
            "selection_dataset": _frame_preview(selection_dataset, limit=6),
            "evaluation": _frame_preview(evaluation, limit=6),
        },
    }


def _build_thesis_pipeline_state(paths: DashboardPaths) -> dict[str, Any]:
    """Build a dashboard section for the synthetic thesis-mode pipeline outputs."""

    metadata = _safe_read_csv(paths.thesis_dataset_metadata_csv)
    features = _safe_read_csv(paths.thesis_features_csv)
    benchmarks = _safe_read_csv(paths.thesis_benchmark_csv)
    selection_dataset = _safe_read_csv(paths.thesis_selection_dataset_csv)
    evaluation = _safe_read_csv(paths.thesis_evaluation_csv)
    evaluation_summary_csv = _safe_read_csv(paths.thesis_evaluation_summary_csv)
    feature_importance = _safe_read_csv(paths.thesis_feature_importance_csv)
    training_summary = _extract_training_summary(_load_json_file(paths.thesis_training_run_summary_json))
    evaluation_summary = _extract_evaluation_summary(_load_json_file(paths.thesis_evaluation_run_summary_json))
    if not evaluation_summary:
        evaluation_summary = _extract_evaluation_summary_from_table(evaluation_summary_csv)
    pipeline_run_summary = _load_json_file(paths.thesis_pipeline_run_summary_json)

    selected_solvers = _solver_names_from_benchmarks(benchmarks)
    labeled_instances = _count_labeled_instances(selection_dataset)
    distinct_best_solvers = _count_distinct_best_solvers(selection_dataset)
    feasible_runs = _count_feasible_runs(benchmarks)
    support_counts = _column_value_counts(benchmarks, "solver_support_status")
    status_counts = _column_value_counts(benchmarks, "status")
    settings = pipeline_run_summary.get("settings", {}) if isinstance(pipeline_run_summary, dict) else {}
    pipeline_results = pipeline_run_summary.get("results", {}) if isinstance(pipeline_run_summary, dict) else {}
    solver_leaderboard = _build_solver_leaderboard(benchmarks)
    selector_comparison = _build_selector_comparison(evaluation_summary)
    feature_importance_preview = _frame_preview(feature_importance, limit=12)

    available = any(
        item is not None
        for item in (
            metadata,
            features,
            benchmarks,
            selection_dataset,
            evaluation,
            evaluation_summary_csv,
            feature_importance,
        )
    ) or paths.thesis_pipeline_summary_markdown.exists()

    return {
        "available": available,
        "empty_state": (
            "No thesis pipeline artifacts found yet. Run "
            "`python -m src.experiments.run_thesis_pipeline --dataset-size 30 --time-limit-seconds 5 --seed 42` "
            "and refresh this page."
        ),
        "scope": {
            "title": "Thesis Pipeline Results",
            "description": (
                "Outputs produced by the thesis-mode synthetic experiment pipeline. "
                "These artifacts are separate from the dashboard demo files and are never generated on page load."
            ),
            "source_folder": "data/results/thesis_pipeline",
        },
        "overview": {
            "dataset_rows": len(metadata.index) if metadata is not None else 0,
            "feature_rows": len(features.index) if features is not None else 0,
            "benchmark_rows": len(benchmarks.index) if benchmarks is not None else 0,
            "feasible_runs": feasible_runs,
            "solver_count": len(selected_solvers),
            "selected_solvers": selected_solvers,
            "selection_rows": len(selection_dataset.index) if selection_dataset is not None else 0,
            "labeled_instances": labeled_instances,
            "distinct_best_solvers": distinct_best_solvers,
            "time_limit_seconds": _json_safe_value(settings.get("time_limit_seconds")),
            "random_seed": _json_safe_value(settings.get("seed")),
            "generated_at": _json_safe_value(pipeline_run_summary.get("generated_at"))
            if isinstance(pipeline_run_summary, dict)
            else None,
            "dataset_generated": _json_safe_value(pipeline_results.get("dataset_generated")),
            "support_counts": support_counts,
            "status_counts": status_counts,
        },
        "training": training_summary,
        "evaluation": evaluation_summary,
        "selector_comparison": selector_comparison,
        "solver_leaderboard": solver_leaderboard,
        "feature_importance": feature_importance_preview,
        "charts": _build_thesis_chart_data(
            solver_leaderboard=solver_leaderboard,
            selector_comparison=selector_comparison,
            feature_importance=feature_importance_preview,
        ),
        "artifacts": _build_thesis_artifact_map(paths),
        "previews": {
            "metadata": _frame_preview(metadata, limit=6),
            "features": _frame_preview(features, limit=6),
            "benchmarks": _frame_preview(benchmarks, limit=6),
            "selection_dataset": _frame_preview(selection_dataset, limit=6),
            "evaluation": _frame_preview(evaluation, limit=6),
        },
    }


def _build_thesis_artifact_map(paths: DashboardPaths) -> dict[str, dict[str, Any]]:
    """Return generated thesis artifact paths for the dashboard file list."""

    return {
        "thesis_dataset_metadata": _describe_path(paths.workspace_root, paths.thesis_dataset_metadata_csv),
        "thesis_features": _describe_path(paths.workspace_root, paths.thesis_features_csv),
        "thesis_benchmark_results": _describe_path(paths.workspace_root, paths.thesis_benchmark_csv),
        "thesis_selection_dataset": _describe_path(paths.workspace_root, paths.thesis_selection_dataset_csv),
        "thesis_selector_model": _describe_path(paths.workspace_root, paths.thesis_model_output),
        "thesis_feature_importance": _describe_path(paths.workspace_root, paths.thesis_feature_importance_csv),
        "thesis_evaluation_report": _describe_path(paths.workspace_root, paths.thesis_evaluation_csv),
        "thesis_evaluation_summary_csv": _describe_path(paths.workspace_root, paths.thesis_evaluation_summary_csv),
        "thesis_evaluation_summary_markdown": _describe_path(
            paths.workspace_root,
            paths.thesis_evaluation_summary_markdown,
        ),
        "thesis_training_run_summary": _describe_path(paths.workspace_root, paths.thesis_training_run_summary_json),
        "thesis_evaluation_run_summary": _describe_path(paths.workspace_root, paths.thesis_evaluation_run_summary_json),
        "thesis_summary_report": _describe_path(paths.workspace_root, paths.thesis_pipeline_summary_markdown),
        "thesis_pipeline_run_summary": _describe_path(paths.workspace_root, paths.thesis_pipeline_run_summary_json),
    }


def _build_thesis_chart_data(
    *,
    solver_leaderboard: list[dict[str, Any]],
    selector_comparison: list[dict[str, Any]],
    feature_importance: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Build normalized chart rows for the thesis dashboard section."""

    return {
        "average_objective_per_solver": _metric_chart_rows(
            solver_leaderboard,
            label_key="solver_name",
            value_key="average_objective",
        ),
        "average_runtime_per_solver": _metric_chart_rows(
            solver_leaderboard,
            label_key="solver_name",
            value_key="average_runtime",
        ),
        "solver_win_counts": _metric_chart_rows(
            solver_leaderboard,
            label_key="solver_name",
            value_key="wins",
        ),
        "selector_baseline_comparison": _metric_chart_rows(
            selector_comparison,
            label_key="method",
            value_key="average_objective",
        ),
        "top_feature_importances": _metric_chart_rows(
            feature_importance,
            label_key="source_feature",
            value_key="importance",
        ),
    }


def _metric_chart_rows(
    rows: list[dict[str, Any]],
    *,
    label_key: str,
    value_key: str,
) -> list[dict[str, Any]]:
    """Convert generic records into simple label/value chart rows."""

    chart_rows: list[dict[str, Any]] = []
    for row in rows:
        label = row.get(label_key) or row.get("feature") or row.get("solver_name")
        value = _safe_float(row.get(value_key))
        if label is None or value is None:
            continue
        chart_rows.append(
            {
                "label": _json_safe_value(label),
                "value": value,
            }
        )
    return chart_rows


def _build_selector_comparison(evaluation_summary: dict[str, Any]) -> list[dict[str, Any]]:
    """Build selector, single-best, and virtual-best comparison rows."""

    selector_objective = _safe_float(evaluation_summary.get("average_selected_objective"))
    single_best_objective = _safe_float(evaluation_summary.get("average_single_best_objective"))
    virtual_best_objective = _safe_float(evaluation_summary.get("average_virtual_best_objective"))

    if selector_objective is None and single_best_objective is None and virtual_best_objective is None:
        return []

    return [
        {
            "method": "Selector",
            "average_objective": selector_objective,
            "delta_vs_virtual_best": _safe_float(evaluation_summary.get("regret_vs_virtual_best")),
            "note": "Predicted solver per instance",
        },
        {
            "method": "Single Best Solver",
            "average_objective": single_best_objective,
            "delta_vs_virtual_best": (
                single_best_objective - virtual_best_objective
                if single_best_objective is not None and virtual_best_objective is not None
                else None
            ),
            "note": evaluation_summary.get("single_best_solver_name") or "Best fixed solver from training split",
        },
        {
            "method": "Virtual Best Solver",
            "average_objective": virtual_best_objective,
            "delta_vs_virtual_best": 0.0 if virtual_best_objective is not None else None,
            "note": "Oracle lower bound",
        },
    ]


def _build_artifact_browser_state(paths: DashboardPaths) -> dict[str, Any]:
    """Build a read-only artifact browser state with explicit scope groups."""

    group_definitions = [
        {
            "scope": "thesis",
            "title": "Thesis Pipeline Artifacts",
            "description": (
                "Files produced by src.experiments.run_thesis_pipeline. "
                "These are the thesis-mode outputs under data/processed/thesis_pipeline and data/results/thesis_pipeline."
            ),
        },
        {
            "scope": "reports",
            "title": "Benchmark Report Artifacts",
            "description": (
                "Thesis-facing CSV and Markdown summaries produced by src.experiments.thesis_report "
                "under data/results/reports."
            ),
        },
        {
            "scope": "real_current",
            "title": "Refreshed Real Pipeline Artifacts",
            "description": (
                "Files produced by src.experiments.run_real_pipeline_current under "
                "data/processed/real_pipeline_current and data/results/real_pipeline_current."
            ),
        },
        {
            "scope": "synthetic_study",
            "title": "Synthetic Study Artifacts",
            "description": (
                "Files produced by the larger synthetic study under data/processed/synthetic_study "
                "and data/results/synthetic_study."
            ),
        },
        {
            "scope": "mixed",
            "title": "Mixed Dataset Artifacts",
            "description": (
                "Combined synthetic/real selector artifacts under data/processed/selection_dataset_full.csv "
                "and data/results/full_selection."
            ),
        },
        {
            "scope": "demo",
            "title": "Synthetic Demo Artifacts",
            "description": (
                "Files produced by dashboard demo actions. These stay in demo_* outputs and are separate from thesis results."
            ),
        },
    ]
    specs = _artifact_browser_specs(paths)
    groups: list[dict[str, Any]] = []
    for group in group_definitions:
        scope = str(group["scope"])
        scoped_specs = [spec for spec in specs if spec["scope"] == scope]
        available_specs = [
            spec for spec in scoped_specs if isinstance(spec["path"], Path) and spec["path"].exists()
        ]
        groups.append(
            {
                **group,
                "available_count": len(available_specs),
                "missing_count": len(scoped_specs) - len(available_specs),
                "artifacts": [
                    _browser_artifact_payload(
                        artifact_id=str(spec["artifact_id"]),
                        path=spec["path"],
                        workspace_root=paths.workspace_root,
                        artifact_type=str(spec["artifact_type"]),
                        scope=scope,
                        preview_kind=str(spec["preview_kind"]),
                    )
                    for spec in available_specs
                ],
            }
        )

    return {
        "title": "Artifacts Browser",
        "description": (
            "Browse generated CSV and Markdown artifacts from localhost. "
            "The browser uses a fixed whitelist and keeps thesis outputs separate from synthetic demo outputs."
        ),
        "groups": groups,
    }


def _artifact_browser_lookup(paths: DashboardPaths) -> dict[str, dict[str, Any]]:
    """Return browsable artifact specs keyed by stable artifact id."""

    return {str(spec["artifact_id"]): spec for spec in _artifact_browser_specs(paths)}


def _artifact_browser_specs(paths: DashboardPaths) -> list[dict[str, Any]]:
    """Return the fixed local artifact whitelist for browser previews."""

    specs = [
        _artifact_spec("thesis_benchmark_results", "thesis", "Benchmark Results", paths.thesis_benchmark_csv, "csv"),
        _artifact_spec("thesis_features", "thesis", "Feature Table", paths.thesis_features_csv, "csv"),
        _artifact_spec(
            "thesis_selection_dataset",
            "thesis",
            "Selection Dataset",
            paths.thesis_selection_dataset_csv,
            "csv",
        ),
        _artifact_spec(
            "thesis_selector_evaluation",
            "thesis",
            "Selector Evaluation",
            paths.thesis_evaluation_csv,
            "csv",
        ),
        _artifact_spec(
            "thesis_selector_evaluation_summary",
            "thesis",
            "Selector Evaluation Summary",
            paths.thesis_evaluation_summary_csv,
            "csv",
        ),
        _artifact_spec(
            "thesis_feature_importance",
            "thesis",
            "Feature Importance",
            paths.thesis_feature_importance_csv,
            "csv",
        ),
        _artifact_spec(
            "thesis_evaluation_markdown",
            "thesis",
            "Markdown Summary",
            paths.thesis_evaluation_summary_markdown,
            "markdown",
        ),
        _artifact_spec(
            "thesis_summary_report",
            "thesis",
            "Markdown Summary",
            paths.thesis_pipeline_summary_markdown,
            "markdown",
        ),
        _artifact_spec(
            "report_solver_comparison",
            "reports",
            "Solver Comparison",
            paths.report_solver_comparison_csv,
            "csv",
        ),
        _artifact_spec(
            "report_solver_comparison_markdown",
            "reports",
            "Markdown Report",
            paths.report_solver_comparison_markdown,
            "markdown",
        ),
        _artifact_spec(
            "report_win_counts",
            "reports",
            "Solver Win Counts",
            paths.report_win_counts_csv,
            "csv",
        ),
        _artifact_spec(
            "report_win_counts_markdown",
            "reports",
            "Markdown Report",
            paths.report_win_counts_markdown,
            "markdown",
        ),
        _artifact_spec(
            "report_average_objective",
            "reports",
            "Average Objective",
            paths.report_average_objective_csv,
            "csv",
        ),
        _artifact_spec(
            "report_average_objective_markdown",
            "reports",
            "Markdown Report",
            paths.report_average_objective_markdown,
            "markdown",
        ),
        _artifact_spec(
            "report_average_runtime",
            "reports",
            "Average Runtime",
            paths.report_average_runtime_csv,
            "csv",
        ),
        _artifact_spec(
            "report_average_runtime_markdown",
            "reports",
            "Markdown Report",
            paths.report_average_runtime_markdown,
            "markdown",
        ),
        _artifact_spec(
            "report_selector_vs_baselines",
            "reports",
            "Selector Vs Baselines",
            paths.report_selector_vs_baselines_csv,
            "csv",
        ),
        _artifact_spec(
            "report_selector_vs_baselines_markdown",
            "reports",
            "Markdown Report",
            paths.report_selector_vs_baselines_markdown,
            "markdown",
        ),
        _artifact_spec(
            "report_feature_importance_summary",
            "reports",
            "Feature Importance Summary",
            paths.report_feature_importance_summary_csv,
            "csv",
        ),
        _artifact_spec(
            "report_feature_importance_markdown",
            "reports",
            "Markdown Report",
            paths.report_feature_importance_summary_markdown,
            "markdown",
        ),
        _artifact_spec(
            "report_summary_markdown",
            "reports",
            "Benchmark Report Summary",
            paths.report_summary_markdown,
            "markdown",
        ),
        _artifact_spec("demo_benchmark_results", "demo", "Benchmark Results", paths.demo_benchmark_csv, "csv"),
        _artifact_spec("demo_features", "demo", "Feature Table", paths.demo_features_csv, "csv"),
        _artifact_spec(
            "demo_selection_dataset",
            "demo",
            "Selection Dataset",
            paths.demo_selection_dataset_csv,
            "csv",
        ),
        _artifact_spec(
            "demo_selector_evaluation",
            "demo",
            "Selector Evaluation",
            paths.demo_evaluation_csv,
            "csv",
        ),
        _artifact_spec(
            "demo_selector_evaluation_summary",
            "demo",
            "Selector Evaluation Summary",
            paths.demo_evaluation_summary_csv,
            "csv",
        ),
        _artifact_spec(
            "demo_feature_importance",
            "demo",
            "Feature Importance",
            paths.demo_feature_importance_csv,
            "csv",
        ),
        _artifact_spec(
            "demo_evaluation_markdown",
            "demo",
            "Markdown Summary",
            paths.demo_evaluation_summary_markdown,
            "markdown",
        ),
    ]
    specs.extend(build_report_artifact_specs(paths.workspace_root))
    return specs


def _artifact_spec(
    artifact_id: str,
    scope: str,
    artifact_type: str,
    path: Path,
    preview_kind: str,
) -> dict[str, Any]:
    """Build one artifact-browser whitelist entry."""

    return {
        "artifact_id": artifact_id,
        "scope": scope,
        "artifact_type": artifact_type,
        "path": path,
        "preview_kind": preview_kind,
    }


def _browser_artifact_payload(
    *,
    artifact_id: str,
    path: Path,
    workspace_root: Path,
    artifact_type: str,
    scope: str,
    preview_kind: str,
) -> dict[str, Any]:
    """Return dashboard metadata for one available artifact file."""

    stat = path.stat()
    return {
        "artifact_id": artifact_id,
        "scope": scope,
        "artifact_type": artifact_type,
        "file_name": path.name,
        "path": _relative_path(workspace_root, path),
        "last_modified": _format_timestamp(stat.st_mtime),
        "size_bytes": int(stat.st_size),
        "size": _format_file_size(stat.st_size),
        "preview_kind": preview_kind,
    }


def _preview_csv_artifact(path: Path) -> dict[str, Any]:
    """Return a compact CSV preview for the artifact browser."""

    try:
        frame = pd.read_csv(path)
    except pd.errors.EmptyDataError as exc:
        raise ValueError("CSV artifact is empty.") from exc

    preview_rows = frame.head(25)
    return {
        "columns": [str(column) for column in frame.columns],
        "rows": _records(preview_rows),
        "total_rows": int(len(frame.index)),
        "shown_rows": int(len(preview_rows.index)),
    }


def _preview_markdown_artifact(path: Path) -> dict[str, Any]:
    """Return a compact Markdown text preview for the artifact browser."""

    text = path.read_text(encoding="utf-8")
    max_chars = 12_000
    return {
        "text": text[:max_chars],
        "total_chars": len(text),
        "shown_chars": min(len(text), max_chars),
        "truncated": len(text) > max_chars,
    }


def _format_file_size(size_bytes: int) -> str:
    """Format a byte count for dashboard display."""

    size = float(max(0, size_bytes))
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024.0 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size_bytes} B"


def _extract_evaluation_summary_from_table(summary: pd.DataFrame | None) -> dict[str, Any]:
    """Extract aggregate selector metrics from the evaluation summary CSV."""

    if summary is None or summary.empty:
        return {}

    frame = summary.copy()
    if "summary_row_type" in frame.columns:
        aggregate_rows = frame[frame["summary_row_type"].astype(str) == "aggregate_mean"]
        if not aggregate_rows.empty:
            frame = aggregate_rows

    row = frame.iloc[0].to_dict()
    return {
        "single_best_solver_name": _json_safe_value(row.get("single_best_solver_name")),
        "classification_accuracy": _json_safe_value(row.get("classification_accuracy")),
        "balanced_accuracy": _json_safe_value(row.get("balanced_accuracy")),
        "average_selected_objective": _json_safe_value(row.get("average_selected_objective")),
        "average_virtual_best_objective": _json_safe_value(row.get("average_virtual_best_objective")),
        "average_single_best_objective": _json_safe_value(row.get("average_single_best_objective")),
        "regret_vs_virtual_best": _json_safe_value(row.get("regret_vs_virtual_best")),
        "delta_vs_single_best": _json_safe_value(row.get("delta_vs_single_best")),
        "improvement_vs_single_best": _json_safe_value(row.get("improvement_vs_single_best")),
        "num_test_instances": _json_safe_value(row.get("num_test_rows") or row.get("num_test_instances")),
        "num_validation_splits": int(len(summary.index)) if not summary.empty else 0,
        "split_strategy": _json_safe_value(row.get("split_strategy")),
    }


def _solver_names_from_benchmarks(benchmarks: pd.DataFrame | None) -> list[str]:
    """Return stable solver labels from a benchmark table."""

    if benchmarks is None or benchmarks.empty:
        return []

    column = "solver_registry_name" if "solver_registry_name" in benchmarks.columns else "solver_name"
    if column not in benchmarks.columns:
        return []
    return sorted(benchmarks[column].dropna().astype(str).unique().tolist())


def _count_labeled_instances(selection_dataset: pd.DataFrame | None) -> int:
    """Count labeled selector rows."""

    if selection_dataset is None or selection_dataset.empty or "best_solver" not in selection_dataset.columns:
        return 0
    return int(selection_dataset["best_solver"].dropna().count())


def _count_distinct_best_solvers(selection_dataset: pd.DataFrame | None) -> int:
    """Count distinct non-missing best-solver labels."""

    if selection_dataset is None or selection_dataset.empty or "best_solver" not in selection_dataset.columns:
        return 0
    return int(selection_dataset["best_solver"].dropna().astype(str).nunique())


def _count_feasible_runs(benchmarks: pd.DataFrame | None) -> int:
    """Count feasible benchmark rows."""

    if benchmarks is None or benchmarks.empty or "feasible" not in benchmarks.columns:
        return 0
    return int(benchmarks["feasible"].map(_coerce_bool).sum())


def _column_value_counts(frame: pd.DataFrame | None, column: str) -> dict[str, int]:
    """Return stable counts for one optional dataframe column."""

    if frame is None or frame.empty or column not in frame.columns:
        return {}
    counts = frame[column].fillna("missing").astype(str).value_counts().to_dict()
    return {str(key): int(value) for key, value in sorted(counts.items())}


def _summarize_inventory(inventory: pd.DataFrame | None) -> dict[str, int]:
    """Summarize parseable and failed counts from one inventory table."""

    if inventory is None or inventory.empty or "parseable" not in inventory.columns:
        return {
            "inventory_rows": 0,
            "parseable_real_files": 0,
            "failed_real_files": 0,
        }

    parseable = inventory["parseable"].fillna(False).astype(bool)
    parseable_count = int(parseable.sum())
    inventory_rows = int(len(inventory.index))
    return {
        "inventory_rows": inventory_rows,
        "parseable_real_files": parseable_count,
        "failed_real_files": inventory_rows - parseable_count,
    }


def _extract_training_summary(run_summary: dict[str, Any] | None) -> dict[str, Any]:
    """Extract a compact dashboard summary from a selector-training run summary."""

    if not isinstance(run_summary, dict):
        return {}

    results = run_summary.get("results", {})
    settings = run_summary.get("settings", {})
    outputs = run_summary.get("outputs", {})
    if not isinstance(results, dict) or not isinstance(settings, dict) or not isinstance(outputs, dict):
        return {}

    return {
        "accuracy": _json_safe_value(results.get("accuracy")),
        "balanced_accuracy": _json_safe_value(results.get("balanced_accuracy")),
        "num_train_rows": _json_safe_value(results.get("num_train_rows")),
        "num_test_rows": _json_safe_value(results.get("num_test_rows")),
        "num_labeled_rows": _json_safe_value(results.get("num_labeled_rows")),
        "num_validation_splits": _json_safe_value(results.get("num_validation_splits")),
        "split_strategy": _json_safe_value(settings.get("split_strategy")),
        "generated_at": _json_safe_value(run_summary.get("generated_at")),
        "model_output": _json_safe_value(outputs.get("model_output")),
    }


def _extract_evaluation_summary(run_summary: dict[str, Any] | None) -> dict[str, Any]:
    """Extract a compact dashboard summary from a selector-evaluation run summary."""

    if not isinstance(run_summary, dict):
        return {}

    results = run_summary.get("results", {})
    settings = run_summary.get("settings", {})
    outputs = run_summary.get("outputs", {})
    if not isinstance(results, dict) or not isinstance(settings, dict) or not isinstance(outputs, dict):
        return {}

    return {
        "single_best_solver_name": _json_safe_value(results.get("single_best_solver_name")),
        "classification_accuracy": _json_safe_value(results.get("classification_accuracy")),
        "balanced_accuracy": _json_safe_value(results.get("balanced_accuracy")),
        "average_selected_objective": _json_safe_value(results.get("average_selected_objective")),
        "average_virtual_best_objective": _json_safe_value(results.get("average_virtual_best_objective")),
        "average_single_best_objective": _json_safe_value(results.get("average_single_best_objective")),
        "regret_vs_virtual_best": _json_safe_value(results.get("regret_vs_virtual_best")),
        "delta_vs_single_best": _json_safe_value(results.get("delta_vs_single_best")),
        "improvement_vs_single_best": _json_safe_value(results.get("improvement_vs_single_best")),
        "num_test_instances": _json_safe_value(results.get("num_test_instances")),
        "num_validation_splits": _json_safe_value(results.get("num_validation_splits")),
        "split_strategy": _json_safe_value(settings.get("split_strategy")),
        "generated_at": _json_safe_value(run_summary.get("generated_at")),
        "summary_csv": _json_safe_value(outputs.get("evaluation_summary_csv")),
    }


def _count_best_solver_labels(selection_dataset_csv: Path) -> int:
    """Return the number of distinct non-missing solver labels in a dataset."""

    dataset = pd.read_csv(selection_dataset_csv)
    if "best_solver" not in dataset.columns:
        return 0
    return int(dataset["best_solver"].dropna().astype(str).nunique())


def _safe_read_csv(path: Path) -> pd.DataFrame | None:
    """Read one CSV file when it exists and is non-empty."""

    if not path.exists() or path.stat().st_size == 0:
        return None
    try:
        return pd.read_csv(path)
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return None


def _load_json_file(path: Path) -> dict[str, Any] | None:
    """Load one JSON file into a dictionary when available."""

    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _describe_path(workspace_root: Path, path: Path) -> dict[str, Any]:
    """Return metadata for one artifact path."""

    exists = path.exists()
    path_type = "directory" if exists and path.is_dir() else "file"
    entry_count = 0
    if exists and path.is_dir():
        entry_count = len([entry for entry in path.iterdir() if entry.is_file()])

    modified_at = _format_timestamp(path.stat().st_mtime) if exists else None
    return {
        "path": _relative_path(workspace_root, path),
        "exists": exists,
        "path_type": path_type,
        "entry_count": entry_count,
        "modified_at": modified_at,
    }


def _frame_preview(frame: pd.DataFrame | None, limit: int) -> list[dict[str, Any]]:
    """Return a small JSON-safe preview of a dataframe."""

    if frame is None or frame.empty:
        return []
    return _records(frame.head(limit))


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert a dataframe to JSON-safe records."""

    return [
        {column: _json_safe_value(value) for column, value in row.items()}
        for row in frame.to_dict(orient="records")
    ]


def _serialize_confusion_matrix(confusion_matrix: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert a confusion matrix dataframe into dashboard rows."""

    frame = confusion_matrix.copy()
    frame.index.name = "actual_label"
    return _records(frame.reset_index())


def _json_safe_value(value: object) -> object:
    """Convert pandas and numpy scalar values into JSON-safe values."""

    if value is None:
        return None
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return round(value, 6)
    if isinstance(value, int):
        return value

    item_method = getattr(value, "item", None)
    if callable(item_method):
        try:
            return _json_safe_value(item_method())
        except (TypeError, ValueError):
            pass

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return str(value) if not isinstance(value, str) else value


def _coerce_bool(value: object) -> bool:
    """Normalize bool-like CSV values."""

    if isinstance(value, bool):
        return value
    if value is None or pd.isna(value):
        return False
    return str(value).strip().casefold() in {"true", "1", "yes", "y"}


def _safe_float(value: object) -> float | None:
    """Convert a scalar value to a JSON-safe float."""

    if value is None or pd.isna(value):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(parsed) or math.isinf(parsed):
        return None
    return round(parsed, 6)


def _relative_path(workspace_root: Path, path: Path | None) -> str | None:
    """Convert an absolute path to a workspace-relative string when possible."""

    if path is None:
        return None

    try:
        return path.resolve().relative_to(workspace_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _labelize(value: str) -> str:
    """Convert one identifier-like string into a readable label."""

    return value.replace("_", " ").strip().title()


def _format_timestamp(timestamp: float) -> str:
    """Format a POSIX timestamp as an ISO string."""

    return datetime.fromtimestamp(timestamp, tz=timezone.utc).astimezone().isoformat(timespec="seconds")


def _timestamp_now() -> str:
    """Return the current timestamp as an ISO string."""

    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
