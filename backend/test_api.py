import os
import pytest
os.environ["TESTING"] = "1" 

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_register_user():
    response = client.post("/api/auth/register", json={
        "name": "TestUser",
        "email": "testuser@example.com",
        "password": "password123"
    })
    assert response.status_code in (201, 400)
    print(response.json())

def test_login_user():
    response = client.post("/api/auth/login", data={
        "username": "testuser@example.com",
        "password": "password123"
    })
    assert response.status_code in (200, 401)
    print(response.json())

@pytest.fixture(scope="session")
def test_user():
    """Register (or ensure) a user and get a valid token."""
    email = "apitest@example.com"
    password = "testpassword123"

    # Try to register the user
    client.post("/api/auth/register", json={
        "name": "API Tester",
        "email": email,
        "password": password
    })

    # Then log in
    login_response = client.post("/api/auth/login", data={
        "username": email,
        "password": password
    })
    assert login_response.status_code == 200, login_response.text
    token = login_response.json()["access_token"]
    return {"email": email, "token": token}


@pytest.fixture
def auth_header(test_user):
    """Return Authorization header for the test user."""
    return {"Authorization": f"Bearer {test_user['token']}"}


# --- Tests ---

def test_create_task(auth_header):
    response = client.post("/api/tasks/", json={
        "title": "Test Task",
        "description": "A task created by pytest",
        "category": "Testing",
        "status": "pending",
        "dueDate": "2025-10-24",
        "dueTime": "10:00:00"
    }, headers=auth_header)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["title"] == "Test Task"
    global created_task_id
    created_task_id = data["id"]


def test_get_tasks(auth_header):
    response = client.get("/api/tasks/", headers=auth_header)
    assert response.status_code == 200, response.text
    tasks = response.json()
    assert isinstance(tasks, list)
    if tasks:
        assert "title" in tasks[0]


def test_update_task(auth_header):
    # We use the global task created before
    response = client.get("/api/tasks/", headers=auth_header)
    task_id = response.json()[0]["id"]

    response = client.put(f"/api/tasks/{task_id}", json={
        "title": "Updated Task",
        "description": "Now updated",
        "category": "UpdatedCat",
        "status": "completed",
        "dueDate": "2025-10-25",
        "dueTime": "11:00:00"
    }, headers=auth_header)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["title"] == "Updated Task"
    assert data["status"] == "completed"


def test_get_stats(auth_header):
    response = client.get("/api/tasks/stats", headers=auth_header)
    assert response.status_code == 200, response.text
    stats = response.json()
    assert isinstance(stats, dict)
    assert any(k in stats for k in ["Testing", "UpdatedCat", "Uncategorized"])


def test_delete_task(auth_header):
    # Get a task to delete
    response = client.get("/api/tasks/", headers=auth_header)
    task_id = response.json()[0]["id"]

    response = client.delete(f"/api/tasks/{task_id}", headers=auth_header)
    assert response.status_code in (204, 404), response.text  # 404 if already deleted
