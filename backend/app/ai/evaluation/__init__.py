"""Versioned AI evaluation contracts and deterministic dataset validation."""

from app.ai.evaluation.dataset import (
    GOLDEN_DATASET_SCHEMA_VERSION,
    GoldenDataset,
    GoldenDatasetApprovalManifest,
    GoldenDatasetCase,
    GoldenDatasetValidationError,
    golden_dataset_fingerprint,
    load_approval_manifest,
    load_golden_dataset,
)
from app.ai.evaluation.runner import (
    EVALUATION_SCHEMA_VERSION,
    EvaluationObservation,
    EvaluationReport,
    EvaluationRunDescriptor,
    EvaluationValidationError,
    evaluate_dataset,
    load_evaluation_observations,
    write_evaluation_report,
)

__all__ = [
    "GOLDEN_DATASET_SCHEMA_VERSION",
    "GoldenDataset",
    "GoldenDatasetApprovalManifest",
    "GoldenDatasetCase",
    "GoldenDatasetValidationError",
    "golden_dataset_fingerprint",
    "EVALUATION_SCHEMA_VERSION",
    "EvaluationObservation",
    "EvaluationReport",
    "EvaluationRunDescriptor",
    "EvaluationValidationError",
    "evaluate_dataset",
    "load_approval_manifest",
    "load_evaluation_observations",
    "load_golden_dataset",
    "write_evaluation_report",
]
