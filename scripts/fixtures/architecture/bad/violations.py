from datetime import datetime

from openai import OpenAI

from app.models.user import User


@router.get("/legacy/")
def broken(db, background_tasks):
    now = datetime.utcnow()
    try:
        for item in range(2):
            db.query(User).filter(User.id == item).first()
        background_tasks.add_task(run_later, db)
    except:
        raise AppException(message=str(error))
    return now
