import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.core.config import settings
from app.core.rate_limit import limiter
from scripts.test_database import validate_test_database_target

engine = create_engine(settings.SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def pytest_collection_modifyitems(items):
    for item in items:
        if "unit" in item.path.parts:
            item.add_marker(pytest.mark.unit)
        elif "contract" in item.path.parts:
            item.add_marker(pytest.mark.contract)
        else:
            item.add_marker(pytest.mark.integration)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    limiter.reset()
    yield
    limiter.reset()

@pytest.fixture(scope="session")
def db():
    if settings.ENV.casefold() != "test":
        raise RuntimeError(
            "Integration tests require ENV=test and the guarded integration runner"
        )
    validate_test_database_target(
        settings.BASE_DATABASE_URL,
        settings.SQLALCHEMY_DATABASE_URL,
    )
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()

from sqlalchemy import event

@pytest.fixture
def assert_num_queries():
    def _assert_num_queries(expected_count):
        class QueryCounter:
            count = 0

        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            QueryCounter.count += 1

        event.listen(engine, "before_cursor_execute", before_cursor_execute)

        class Asserter:
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc_val, exc_tb):
                event.remove(engine, "before_cursor_execute", before_cursor_execute)
                if exc_type is None:
                    assert QueryCounter.count <= expected_count, f"Anti-Pattern Detected: N+1 Query. Expected at most {expected_count} queries, but got {QueryCounter.count}. Please use selectinload()."

        return Asserter()

    return _assert_num_queries

@pytest.fixture(scope="module")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass
            
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c

@pytest.fixture
def test_admin(client, db):
    email = f"admin_{uuid.uuid4()}@example.com"
    client.post("/auth/register", json={"email": email, "full_name": "Admin", "role": "admin", "password": "testpassword"})
    
    # Fix role directly in DB since register forces student
    from app.models.user import User
    user = db.query(User).filter(User.email == email).first()
    if user:
        user.role = "admin"
        db.commit()

    res = client.post("/auth/login", data={"username": email, "password": "testpassword"})
    token = res.json()["access_token"]
    return {"email": email, "token": token, "headers": {"Authorization": f"Bearer {token}"}}

@pytest.fixture
def test_teacher(client, db):
    email = f"teacher_{uuid.uuid4()}@example.com"
    client.post("/auth/register", json={"email": email, "full_name": "Teacher", "role": "teacher", "password": "testpassword"})
    
    # Fix role directly in DB since register forces student
    from app.models.user import User
    user = db.query(User).filter(User.email == email).first()
    if user:
        user.role = "teacher"
        db.commit()

    res = client.post("/auth/login", data={"username": email, "password": "testpassword"})
    token = res.json()["access_token"]
    return {"email": email, "token": token, "headers": {"Authorization": f"Bearer {token}"}}

@pytest.fixture
def test_student(client):
    email = f"student_{uuid.uuid4()}@example.com"
    res = client.post("/auth/register", json={"email": email, "full_name": "Student", "role": "student", "password": "testpassword"})
    user_id = res.json()["id"]
    res = client.post("/auth/login", data={"username": email, "password": "testpassword"})
    token = res.json()["access_token"]
    return {"id": user_id, "email": email, "token": token, "headers": {"Authorization": f"Bearer {token}"}}

@pytest.fixture
def sample_exam(client, test_teacher):
    res = client.post("/exams/", json={"title": "Mock Exam", "duration_minutes": 30, "is_published": True}, headers=test_teacher["headers"])
    exam = res.json()
    
    q1 = client.post(f"/exams/{exam['id']}/questions", json={
        "content": "What is 2+2?",
        "points": 5,
        "options": [
            {"content": "3", "is_correct": False},
            {"content": "4", "is_correct": True}
        ]
    }, headers=test_teacher["headers"]).json()
    
    q2 = client.post(f"/exams/{exam['id']}/questions", json={
        "content": "Is the sky blue?",
        "points": 5,
        "options": [
            {"content": "Yes", "is_correct": True},
            {"content": "No", "is_correct": False}
        ]
    }, headers=test_teacher["headers"]).json()
    
    return {"exam": exam, "questions": [q1, q2], "teacher": test_teacher}
