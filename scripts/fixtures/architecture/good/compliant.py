from datetime import datetime, timezone

from sqlalchemy import select


def load_record(session, model, record_id):
    now = datetime.now(timezone.utc)
    return now, session.scalar(select(model).where(model.id == record_id))


def delete_in_fixed_dependency_order(session, statements):
    for statement in statements:
        session.execute(statement)  # architecture-guard: allow backend.query-in-loop ANTI-PG-SEC-001 -- fixed dependency-order teardown
