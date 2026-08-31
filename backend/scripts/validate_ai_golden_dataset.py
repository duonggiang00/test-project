from __future__ import annotations

import argparse
import os
from pathlib import Path

from app.ai.evaluation.dataset import (
    GoldenDatasetValidationError,
    TRUST_ROOT_SHA256_ENV,
    load_golden_dataset,
    load_trusted_approvers,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate an owner/admin-approved AI golden dataset without provider calls."
    )
    parser.add_argument("dataset", type=Path, help="Path to the versioned JSONL dataset")
    parser.add_argument(
        "--trust-store",
        type=Path,
        help="Owner-controlled JSON trust store containing Ed25519 public keys",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Validate signed cases without enforcing the final 40-case distribution",
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
        trust_store = None
        if not arguments.structure_only:
            if arguments.trust_store is None:
                raise GoldenDatasetValidationError(
                    "--trust-store is required unless --structure-only is used"
                )
            trust_store = load_trusted_approvers(arguments.trust_store)
            trusted_root_sha256 = os.environ.get(TRUST_ROOT_SHA256_ENV)
            if trusted_root_sha256 is None:
                raise GoldenDatasetValidationError(
                    f"{TRUST_ROOT_SHA256_ENV} is required for approved validation"
                )
        else:
            trusted_root_sha256 = None
        dataset = load_golden_dataset(
            arguments.dataset,
            require_complete=not arguments.allow_partial,
            trust_store=trust_store,
            trusted_root_sha256=trusted_root_sha256,
            require_trusted_approval=not arguments.structure_only,
        )
    except GoldenDatasetValidationError as exc:
        print(f"AI_GOLDEN_DATASET_INVALID error={exc}")
        return 1

    distribution = " ".join(
        f"{use_case}={count}" for use_case, count in dataset.distribution.items()
    )
    status = (
        "AI_GOLDEN_DATASET_OK"
        if dataset.approvals_verified
        else "AI_GOLDEN_DATASET_STRUCTURE_OK"
    )
    print(
        f"{status} schema_version={dataset.schema_version} cases={len(dataset.cases)} "
        f"approvals_verified={str(dataset.approvals_verified).lower()} "
        f"trust_root_sha256={dataset.trust_root_sha256 or 'none'} "
        f"sha256={dataset.fingerprint_sha256} {distribution}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
