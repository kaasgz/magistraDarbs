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


LOGGER = logging.getLogger(__name__)
DEFAULT_SYNTHETIC_DIFFICULTY = "medium"
SYNTHETIC_DIFFICULTIES: tuple[str, ...] = ("easy", "medium", "hard")


@dataclass(frozen=True, slots=True)
class DashboardPaths:
    """Filesystem layout used by the local dashboard."""

    workspace_root: Path
    real_instance_folder: Path
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

    @classmethod
    def from_workspace(cls, workspace_root: str | Path) -> "DashboardPaths":
        """Build default dashboard paths anchored at one workspace root."""

        root = Path(workspace_root)
        return cls(
            workspace_root=root,
            real_instance_folder=root / "data" / "raw" / "real",
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
        except Exception:
            pass

    if pd.isna(value):
        return None
    return str(value) if not isinstance(value, str) else value


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
