from __future__ import annotations

import argparse
from pathlib import Path

from app.ai.evaluation.dataset import (
    GoldenDatasetValidationError,
    load_approval_manifest,
    load_golden_dataset,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate an AI golden dataset and its owner/admin approval manifest."
    )
    parser.add_argument("dataset", type=Path, help="Path to the versioned JSONL dataset")
    parser.add_argument(
        "--approval-manifest",
        type=Path,
        help="JSON approval record bound to the reviewed dataset SHA-256",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Validate cases without enforcing the final 40-case distribution",
    )
    parser.add_argument(
        "--structure-only",
        action="store_true",
        help="Check draft structure without claiming owner/admin approval",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        if arguments.allow_partial and not arguments.structure_only:
            raise GoldenDatasetValidationError(
                "--allow-partial is valid only with --structure-only"
            )
        approval_manifest = None
        if not arguments.structure_only:
            if arguments.approval_manifest is None:
                raise GoldenDatasetValidationError(
                    "--approval-manifest is required unless --structure-only is used"
                )
            approval_manifest = load_approval_manifest(arguments.approval_manifest)
        dataset = load_golden_dataset(
            arguments.dataset,
            require_complete=not arguments.allow_partial,
            approval_manifest=approval_manifest,
            require_approval=not arguments.structure_only,
        )
    except GoldenDatasetValidationError as exc:
        print(f"AI_GOLDEN_DATASET_INVALID error={exc}")
        return 1

    distribution = " ".join(
        f"{use_case}={count}" for use_case, count in dataset.distribution.items()
    )
    status = (
        "AI_GOLDEN_DATASET_OK"
        if dataset.approval_verified
        else "AI_GOLDEN_DATASET_STRUCTURE_OK"
    )
    print(
        f"{status} schema_version={dataset.schema_version} cases={len(dataset.cases)} "
        f"approval_record_matched={str(dataset.approval_verified).lower()} "
        f"sha256={dataset.fingerprint_sha256} {distribution}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
