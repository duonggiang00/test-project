import pytest
import uuid

def test_topics_crud(client, test_teacher):
    # 1. Create topic
    res = client.post("/topics", json={"name": "Algebra", "description": "Basic Algebra"}, headers=test_teacher["headers"])
    assert res.status_code == 201
    topic = res.json()
    assert topic["name"] == "Algebra"
    topic_id = topic["id"]

    # 2. Get topics list
    res = client.get("/topics", headers=test_teacher["headers"])
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1

    # 3. Update topic
    res = client.put(f"/topics/{topic_id}", json={"name": "Linear Algebra", "description": "Advanced Algebra"}, headers=test_teacher["headers"])
    assert res.status_code == 200
    assert res.json()["name"] == "Linear Algebra"

    # 4. Get topic detail
    res = client.get(f"/topics/{topic_id}", headers=test_teacher["headers"])
    assert res.status_code == 200
    assert res.json()["name"] == "Linear Algebra"

    # 5. Delete topic
    res = client.delete(f"/topics/{topic_id}", headers=test_teacher["headers"])
    assert res.status_code == 200
    assert res.json()["id"] == topic_id

    # 6. Verify deleted
    res = client.get(f"/topics/{topic_id}", headers=test_teacher["headers"])
    assert res.status_code == 404

def test_questions_crud(client, test_teacher):
    # 1. Create question
    res = client.post("/questions", json={
        "content": "What is the capital of France?",
        "points": 2.0,
        "question_type": "MULTIPLE_CHOICE",
        "difficulty": "EASY",
        "options": [
            {"content": "Paris", "is_correct": True},
            {"content": "London", "is_correct": False}
        ]
    }, headers=test_teacher["headers"])
    assert res.status_code == 201
    question = res.json()
    q_id = question["id"]
    assert question["content"] == "What is the capital of France?"
    assert len(question["options"]) == 2

    # 2. Get questions list
    res = client.get("/questions", headers=test_teacher["headers"])
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1

    # 3. Get single question
    res = client.get(f"/questions/{q_id}", headers=test_teacher["headers"])
    assert res.status_code == 200
    assert res.json()["id"] == q_id

    # 4. Update question
    res = client.put(f"/questions/{q_id}", json={
        "content": "What is the capital of France? (Updated)",
        "points": 3.0
    }, headers=test_teacher["headers"])
    assert res.status_code == 200
    assert res.json()["content"] == "What is the capital of France? (Updated)"

    # 5. Delete question
    res = client.delete(f"/questions/{q_id}", headers=test_teacher["headers"])
    assert res.status_code == 200

    # 6. Verify deleted
    res = client.get(f"/questions/{q_id}", headers=test_teacher["headers"])
    assert res.status_code == 404

def test_analytics_endpoints(client, test_teacher):
    # Test /analytics/overview
    res = client.get("/analytics/overview", headers=test_teacher["headers"])
    assert res.status_code == 200
    data = res.json()
    assert "total_students" in data
    assert "total_exams" in data
    assert "completion_rate" in data

    # Test /analytics/score-stats
    res = client.get("/analytics/score-stats", headers=test_teacher["headers"])
    assert res.status_code == 200
    stats = res.json()
    assert "highest_score" in stats
    assert "distribution" in stats

    # Test /analytics/completion-status
    res = client.get("/analytics/completion-status", headers=test_teacher["headers"])
    assert res.status_code == 200
    comp = res.json()
    assert "completed" in comp
    assert "in_progress" in comp

    # Test /analytics/topic-performance
    res = client.get("/analytics/topic-performance", headers=test_teacher["headers"])
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_history_endpoints(client, test_teacher):
    # Test /history/submissions
    res = client.get("/history/submissions", headers=test_teacher["headers"])
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
