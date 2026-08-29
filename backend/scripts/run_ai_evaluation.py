"""Run deterministic AI-007 evaluation against approved observations."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from app.ai.evaluation.dataset import (
    GoldenDatasetValidationError,
    load_approval_manifest,
    load_golden_dataset,
)
from app.ai.evaluation.runner import (
    EvaluationRunDescriptor,
    EvaluationValidationError,
    evaluate_dataset,
    load_evaluation_observations,
    write_evaluation_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate AI observations without exposing raw provider output."
    )
    parser.add_argument("dataset", type=Path, help="Approved golden dataset JSONL")
    parser.add_argument("observations", type=Path, help="Complete observation JSONL")
    parser.add_argument("--approval-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="Sanitized report JSON")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--mode", choices=("replay", "live"), required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--prompt-version", required=True)
    parser.add_argument("--judge-version", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        _validate_output_path(
            arguments.output,
            arguments.dataset,
            arguments.observations,
            arguments.approval_manifest,
        )
        approval = load_approval_manifest(arguments.approval_manifest)
        dataset = load_golden_dataset(
            arguments.dataset,
            approval_manifest=approval,
        )
        observations = load_evaluation_observations(arguments.observations)
        run = EvaluationRunDescriptor.model_validate(
            {
                "run_id": arguments.run_id,
                "execution_mode": arguments.mode,
                "provider": arguments.provider,
                "model": arguments.model,
                "prompt_version": arguments.prompt_version,
                "judge_version": arguments.judge_version,
            }
        )
        report = evaluate_dataset(dataset, observations, run=run)
        write_evaluation_report(arguments.output, report)
    except (GoldenDatasetValidationError, EvaluationValidationError, ValueError) as exc:
        error_type = (
            str(exc)
            if isinstance(exc, (GoldenDatasetValidationError, EvaluationValidationError))
            else "run descriptor validation failed"
        )
        print(f"AI_EVALUATION_INVALID error={error_type}")
        return 1

    status = "AI_EVALUATION_OK" if report.hard_gates.passed else "AI_EVALUATION_FAILED"
    print(
        f"{status} cases={report.case_count} hard_gates="
        f"{str(report.hard_gates.passed).lower()} "
        f"correctness={report.metrics.correctness:.6f} "
        f"groundedness={report.metrics.groundedness:.6f} "
        f"citation_validity={report.metrics.citation_validity:.6f} "
        f"context_relevance={report.metrics.context_relevance:.6f} "
        f"injection_resistance="
        f"{_optional_score(report.metrics.injection_resistance)} "
        f"observation_sha256={report.observation_sha256} "
        f"report_sha256={report.report_sha256}"
    )
    return 0 if report.hard_gates.passed else 1


def _optional_score(value: float | None) -> str:
    return "none" if value is None else f"{value:.6f}"


def _validate_output_path(output: Path, *inputs: Path) -> None:
    normalized_output = os.path.normcase(str(output.resolve(strict=False)))
    if any(
        normalized_output == os.path.normcase(str(path.resolve(strict=False)))
        for path in inputs
    ):
        raise EvaluationValidationError("evaluation output must differ from every input")


if __name__ == "__main__":
    raise SystemExit(main())
