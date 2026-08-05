def test_start_exam(client, sample_exam, test_student):
    exam_id = sample_exam["exam"]["id"]
    res = client.get(f"/student/exams/{exam_id}/start", headers=test_student["headers"])
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == exam_id
    assert len(data["questions"]) == 2
    
    # Verify is_correct is NOT exposed
    for q in data["questions"]:
        for opt in q["options"]:
            assert "is_correct" not in opt

def test_submit_exam(client, sample_exam, test_student):
    exam_id = sample_exam["exam"]["id"]
    # Must start the exam first
    client.get(f"/student/exams/{exam_id}/start", headers=test_student["headers"])
    
    q1 = sample_exam["questions"][0]
    q2 = sample_exam["questions"][1]
    
    # We know the correct options from the mock data
    q1_correct_opt = next(opt["id"] for opt in q1["options"] if opt["is_correct"])
    q2_wrong_opt = next(opt["id"] for opt in q2["options"] if not opt["is_correct"])
    
    # New schema: answers use answer_data dict (supports multiple question types)
    res = client.post(f"/student/exams/{exam_id}/submit", json={
        "answers": [
            {"question_id": q1["id"], "answer_data": {"selected_option_id": q1_correct_opt}}, # 5 points
            {"question_id": q2["id"], "answer_data": {"selected_option_id": q2_wrong_opt}}  # 0 points
        ]
    }, headers=test_student["headers"])
    
    assert res.status_code == 200
    data = res.json()
    assert data["total_score"] == 5
    assert data["max_score"] == 10
    
def test_submit_without_start(client, sample_exam, test_student):
    # Using a fresh student who hasn't started
    import uuid
    email = f"student2_{uuid.uuid4()}@example.com"
    client.post("/auth/register", json={"email": email, "full_name": "Student", "role": "student", "password": "testpassword"})
    res = client.post("/auth/login", data={"username": email, "password": "testpassword"})
    token = res.json()["access_token"]
    
    exam_id = sample_exam["exam"]["id"]
    res = client.post(f"/student/exams/{exam_id}/submit", json={"answers": []}, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 400
    assert res.json()["error_code"] == "NOT_STARTED_YET"
