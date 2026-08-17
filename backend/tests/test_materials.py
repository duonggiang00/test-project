def test_upload_material(client, test_teacher):
    files = {"file": ("test.txt", b"Mock Document Content", "text/plain")}
    res = client.post("/materials/upload", files=files, headers=test_teacher["headers"])
    assert res.status_code == 200
    data = res.json()
    assert "id" in data
    assert data["title"] == "test.txt"
    assert data["ai_status"] == "pending"
    assert "file_path" not in data

    download_res = client.get(
        f"/materials/{data['id']}/download",
        headers=test_teacher["headers"],
    )
    assert download_res.status_code == 200
    assert download_res.content == b"Mock Document Content"
    assert client.get("/uploads/materials/canary.txt").status_code == 404

    delete_res = client.delete(
        f"/materials/{data['id']}?cascade=true",
        headers=test_teacher["headers"],
    )
    assert delete_res.status_code == 200
    assert (
        client.get(
            f"/materials/{data['id']}/download",
            headers=test_teacher["headers"],
        ).status_code
        == 404
    )

def test_get_materials(client, test_teacher):
    res = client.get("/materials/", headers=test_teacher["headers"])
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)

def test_get_material_questions(client, test_teacher):
    # Upload first
    files = {"file": ("test.txt", b"Mock", "text/plain")}
    upload_res = client.post("/materials/upload", files=files, headers=test_teacher["headers"])
    mat_id = upload_res.json()["id"]
    
    # Get questions (will be empty initially because background task takes 10s)
    res = client.get(f"/materials/{mat_id}/questions", headers=test_teacher["headers"])
    assert res.status_code == 200
    assert isinstance(res.json(), list)
