def test_get_exams(client, sample_exam):
    res = client.get("/exams/", headers=sample_exam["teacher"]["headers"])
    assert res.status_code == 200
    assert len(res.json()) >= 1

def test_update_exam(client, sample_exam):
    exam_id = sample_exam["exam"]["id"]
    res = client.put(f"/exams/{exam_id}", json={
        "title": "Updated Mock Exam",
        "description": "Updated desc",
        "duration_minutes": 60,
        "is_published": True
    }, headers=sample_exam["teacher"]["headers"])
    assert res.status_code == 200
    assert res.json()["title"] == "Updated Mock Exam"

def test_get_exam_detail(client, sample_exam, assert_num_queries):
    exam_id = sample_exam["exam"]["id"]
    with assert_num_queries(4):
        res = client.get(f"/exams/{exam_id}", headers=sample_exam["teacher"]["headers"])
    assert res.status_code == 200
    data = res.json()
    assert len(data["questions"]) == 2
    assert "options" in data["questions"][0]

def test_bulk_add_questions(client, sample_exam):
    exam_id = sample_exam["exam"]["id"]
    # Assuming we have question IDs to bulk add. For this test, we can just re-add the same questions
    # to see if the endpoint works (even though it's the same exam, just testing the bulk logic).
    q_ids = [q["id"] for q in sample_exam["questions"]]
    res = client.post(f"/exams/{exam_id}/questions/bulk", json={
        "question_ids": q_ids
    }, headers=sample_exam["teacher"]["headers"])
    assert res.status_code == 200
    assert "Added 2 questions" in res.json()["message"]
