import uuid

def test_register_user(client):
    unique_email = f"test_{uuid.uuid4()}@example.com"
    response = client.post(
        "/auth/register",
        json={
            "email": unique_email,
            "full_name": "Test User",
            "role": "teacher",
            "password": "testpassword"
        }
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["email"] == unique_email
    assert "id" in data

def test_login_user(client):
    unique_email = f"test_{uuid.uuid4()}@example.com"
    # Register first
    client.post(
        "/auth/register",
        json={
            "email": unique_email,
            "full_name": "Test User",
            "role": "teacher",
            "password": "testpassword"
        }
    )
    
    # Login
    response = client.post(
        "/auth/login",
        data={
            "username": unique_email,
            "password": "testpassword"
        }
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_register_weak_password(client):
    unique_email = f"test_{uuid.uuid4()}@example.com"
    response = client.post(
        "/auth/register",
        json={
            "email": unique_email,
            "full_name": "Test User",
            "role": "student",
            "password": "123"
        }
    )
    assert response.status_code == 422

def test_get_me(client, test_student):
    response = client.get("/auth/me", headers=test_student["headers"])
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["id"] == test_student["id"]
    assert data["email"] == test_student["email"]
    assert "full_name" in data
    assert "role" in data
    assert "created_at" in data

def test_get_me_unauthorized(client):
    response = client.get("/auth/me")
    assert response.status_code == 401

