from datetime import datetime, timezone

from sqlalchemy import select


def load_record(session, model, record_id):
    now = datetime.now(timezone.utc)
    return now, session.scalar(select(model).where(model.id == record_id))
