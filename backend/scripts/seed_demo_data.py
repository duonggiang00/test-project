from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.core.config import settings
from app.core.file_storage import LocalFileStorage
from app.db.session import SessionLocal
from app.demo_data.fixture import DATASET_ID, DEFAULT_FIXTURE_ROOT, load_demo_fixture
from app.demo_data.loader import DemoDataError, DemoDataManager, DemoDataReport


def _print_report(report: DemoDataReport) -> None:
    print(f"DEMO_DATA action={report.action} dataset={report.dataset_id}")
    for item in report.items:
        print(
            "DEMO_DATA_PLAN "
            f"entity={item.entity} create={item.create} "
            f"unchanged={item.unchanged} conflict={item.conflict}"
        )
    for entity, count in sorted(report.counts.items()):
        print(f"DEMO_DATA_COUNT entity={entity} count={count}")
    if report.total_score_min is not None and report.total_score_max is not None:
        print(
            "DEMO_DATA_SCORE_RANGE "
            f"minimum={report.total_score_min:.1f} maximum={report.total_score_max:.1f}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage the guarded PlayStudy demo-standard-v1 dataset"
    )
    parser.add_argument("action", choices=("plan", "apply", "verify", "reset"))
    parser.add_argument("--confirm", default=None)
    parser.add_argument(
        "--fixture-root",
        type=Path,
        default=DEFAULT_FIXTURE_ROOT,
        help=argparse.SUPPRESS,
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.action == "reset" and args.confirm != DATASET_ID:
        print(
            f"DEMO_DATA_ERROR reset requires --confirm {DATASET_ID}",
            file=sys.stderr,
        )
        return 2

    try:
        fixture = load_demo_fixture(args.fixture_root)
        storage = LocalFileStorage(Path("uploads"), namespace=DATASET_ID)
        with SessionLocal() as session:
            manager = DemoDataManager(
                fixture,
                session,
                storage,
                database_url=settings.SQLALCHEMY_DATABASE_URL,
                environment=settings.ENV,
            )
            if args.action == "plan":
                report = manager.plan()
            elif args.action == "apply":
                report = manager.apply()
            elif args.action == "verify":
                report = manager.verify()
            else:
                report = manager.reset(args.confirm)
        _print_report(report)
        return 0
    except (DemoDataError, ValueError) as exc:
        print(f"DEMO_DATA_ERROR {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
