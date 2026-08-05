def test_get_users(client, test_admin):
    res = client.get("/admin/users", headers=test_admin["headers"])
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) >= 1

def test_update_user_role(client, test_admin, test_student):
    res = client.put(f"/admin/users/{test_student['id']}/role?new_role=teacher", headers=test_admin["headers"])
    assert res.status_code == 200
    assert res.json()["role"] == "teacher"

def test_delete_user(client, test_admin, test_student):
    res = client.delete(f"/admin/users/{test_student['id']}", headers=test_admin["headers"])
    assert res.status_code == 200
    assert res.json()["message"] == "User deleted successfully"
