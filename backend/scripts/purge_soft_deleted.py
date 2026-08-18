"""Guarded CLI for DATA-005 permanent purge of soft-deleted study materials.

`plan` runs a read-only dry run and mutates nothing. `apply` requires an
explicit `--confirm PURGE-<UTC-date>` flag matching today's UTC date (fail
closed otherwise, exit code 2) before permanently purging eligible rows and
their quarantined files.

Purge is admin-only (`Permission.PURGE_DELETED_DATA`). This script runs
outside any authenticated HTTP session, so it establishes its own acting
identity for authorization and the audit trail by looking up a real admin
user in the target database (earliest-created by default, or a specific one
via `--actor-email`). It intentionally does not fabricate an admin identity
for a database with no admin user -- it fails closed instead, the same way
`seed_demo_data.py`'s `--confirm` guard fails closed on a mismatched flag.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.user import User
from app.services.purge_service import (
    DEFAULT_PURGE_BATCH_LIMIT,
    PurgeReport,
    apply_purge,
    plan_purge,
)


class PurgeCliError(Exception):
    pass


def _confirm_token() -> str:
    return f"PURGE-{datetime.now(timezone.utc).date().isoformat()}"


def _resolve_actor(session, actor_email: str | None) -> User:
    statement = select(User).where(User.role == "admin")
    if actor_email is not None:
        statement = statement.where(User.email == actor_email)
    else:
        statement = statement.order_by(User.created_at, User.id)
    actor = session.scalar(statement)
    if actor is None:
        detail = f" matching --actor-email {actor_email}" if actor_email else ""
        raise PurgeCliError(
            f"No admin user found{detail}; purge requires a real admin "
            "actor for authorization and the audit trail"
        )
    return actor


def _print_report(report: PurgeReport) -> None:
    if report.action == "plan":
        print(
            f"PURGE_PLAN entity={report.entity} "
            f"eligible={report.eligible_count} blocked={report.blocked_count}"
        )
    else:
        print(
            f"PURGE_APPLY entity={report.entity} "
            f"purged={report.purged_count} blocked={report.blocked_count} "
            f"eligible={report.eligible_count}"
        )
    for material_id in report.eligible_ids:
        print(f"PURGE_ELIGIBLE entity={report.entity} id={material_id}")
    for material_id in report.blocked_ids:
        print(
            f"PURGE_BLOCKED entity={report.entity} id={material_id} "
            "reason=retained_links"
        )
    for material_id in report.purged_ids:
        print(f"PURGE_PURGED entity={report.entity} id={material_id}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Preview or run the DATA-005 permanent purge of soft-deleted, "
            "past-retention-window study materials"
        )
    )
    parser.add_argument("action", choices=("plan", "apply"))
    parser.add_argument(
        "--confirm",
        default=None,
        help="Required for apply: PURGE-<UTC-date>, e.g. PURGE-2026-08-18",
    )
    parser.add_argument(
        "--actor-email",
        default=None,
        help="Admin user to act/audit as (defaults to the earliest-created admin)",
    )
    parser.add_argument(
        "--batch-limit",
        type=int,
        default=DEFAULT_PURGE_BATCH_LIMIT,
        help="Maximum number of materials to process in this run",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.action == "apply":
        expected = _confirm_token()
        if args.confirm != expected:
            print(
                f"PURGE_ERROR apply requires --confirm {expected}",
                file=sys.stderr,
            )
            return 2

    try:
        with SessionLocal() as session:
            if args.action == "plan":
                report = plan_purge(session, batch_limit=args.batch_limit)
            else:
                actor = _resolve_actor(session, args.actor_email)
                report = apply_purge(
                    session,
                    actor,
                    batch_limit=args.batch_limit,
                )
        _print_report(report)
        return 0
    except PurgeCliError as exc:
        print(f"PURGE_ERROR {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
