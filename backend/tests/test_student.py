def test_start_exam(client, sample_exam, test_student):
    exam_id = sample_exam["exam"]["id"]
    res = client.get(f"/student/exams/{exam_id}/start", headers=test_student["headers"])
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == exam_id
    assert len(data["questions"]) == 2
    assert 0 < data["remaining_seconds"] <= data["duration_minutes"] * 60
    
    # Verify is_correct is NOT exposed
    for q in data["questions"]:
        for opt in q["options"]:
            assert "is_correct" not in opt


def test_start_exam_returns_only_safe_interaction_metadata(
    client,
    sample_exam,
    test_student,
):
    exam_id = sample_exam["exam"]["id"]
    teacher_headers = sample_exam["teacher"]["headers"]

    fill_response = client.post(
        f"/exams/{exam_id}/questions",
        json={
            "content": "Complete this legacy blank: ___.",
            "points": 2,
            "question_type": "FILL_IN_BLANK",
            "metadata_json": {
                "blanks": [
                    {
                        "blank_index": 0,
                        "acceptable_answers": ["secret fill answer"],
                    }
                ]
            },
            "options": [],
        },
        headers=teacher_headers,
    )
    assert fill_response.status_code == 200

    matching_response = client.post(
        f"/exams/{exam_id}/questions",
        json={
            "content": "Match each concept.",
            "points": 2,
            "question_type": "MATCHING",
            "metadata_json": {
                "pairs": [
                    {"left": "One", "right": "secret first answer"},
                    {"left": "Two", "right": "secret second answer"},
                    {"left": "Three", "right": "secret third answer"},
                ]
            },
            "options": [],
        },
        headers=teacher_headers,
    )
    assert matching_response.status_code == 200

    start_response = client.get(
        f"/student/exams/{exam_id}/start",
        headers=test_student["headers"],
    )
    assert start_response.status_code == 200
    questions = {question["id"]: question for question in start_response.json()["questions"]}

    fill_question = questions[fill_response.json()["id"]]
    assert fill_question["metadata_json"] == {"blank_count": 1}
    assert "acceptable_answers" not in str(fill_question)

    matching_question = questions[matching_response.json()["id"]]
    matching_metadata = matching_question["metadata_json"]
    assert set(matching_metadata["left_options"]) == {"One", "Two", "Three"}
    assert set(matching_metadata["right_options"]) == {
        "secret first answer",
        "secret second answer",
        "secret third answer",
    }
    assert "pairs" not in matching_metadata


def test_available_exam_metadata_is_derived_from_the_exam(
    client,
    sample_exam,
    test_student,
):
    res = client.get(
        "/student/exams?size=100",
        headers=test_student["headers"],
    )

    assert res.status_code == 200
    exam = next(
        item
        for item in res.json()["items"]
        if item["id"] == sample_exam["exam"]["id"]
    )
    assert exam["topic_name"] is None
    assert exam["question_count"] == 2
    assert exam["max_score"] == 10.0

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


def test_submit_rejects_duplicate_question_answers(
    client,
    sample_exam,
    test_student,
):
    exam_id = sample_exam["exam"]["id"]
    question_id = sample_exam["questions"][0]["id"]
    client.get(
        f"/student/exams/{exam_id}/start",
        headers=test_student["headers"],
    )

    response = client.post(
        f"/student/exams/{exam_id}/submit",
        json={
            "answers": [
                {"question_id": question_id, "answer_data": {}},
                {"question_id": question_id, "answer_data": {}},
            ]
        },
        headers=test_student["headers"],
    )

    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_ERROR"


def test_result_counts_and_returns_an_unanswered_question(
    client,
    sample_exam,
    test_student,
):
    exam_id = sample_exam["exam"]["id"]
    client.get(
        f"/student/exams/{exam_id}/start",
        headers=test_student["headers"],
    )
    answered_question = sample_exam["questions"][0]
    correct_option_id = next(
        option["id"]
        for option in answered_question["options"]
        if option["is_correct"]
    )

    submit_response = client.post(
        f"/student/exams/{exam_id}/submit",
        json={
            "answers": [
                {
                    "question_id": answered_question["id"],
                    "answer_data": {"selected_option_id": correct_option_id},
                }
            ]
        },
        headers=test_student["headers"],
    )
    assert submit_response.status_code == 200

    result_response = client.get(
        f"/student/exams/{exam_id}/result",
        headers=test_student["headers"],
    )
    assert result_response.status_code == 200
    result = result_response.json()
    assert result["correct_count"] == 1
    assert result["incorrect_count"] == 1
    assert len(result["answers"]) == 2

    unanswered = next(
        answer
        for answer in result["answers"]
        if answer["question_id"] != answered_question["id"]
    )
    assert unanswered["answer_data"] is None
    assert unanswered["is_correct"] is False
    assert unanswered["points_awarded"] == 0.0

    answered = next(
        answer
        for answer in result["answers"]
        if answer["question_id"] == answered_question["id"]
    )
    assert any(option["is_correct"] for option in answered["options"])
