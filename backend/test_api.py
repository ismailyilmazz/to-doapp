import os
import pytest
import io
from datetime import datetime

os.environ["TESTING"] = "1" 

from fastapi.testclient import TestClient
from main import app
import database

client = TestClient(app)

task_id_with_file = None
uploaded_file_id = None


def promote_user_to_admin(email):
    """Test kullanıcısını veritabanında manuel olarak Admin yapar."""
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET role = 'admin' WHERE email = %s", (email,))
    conn.commit()
    cursor.close()
    conn.close()

@pytest.fixture(scope="module")
def user_auth():
    """Standart bir kullanıcı oluşturur ve token döner."""
    email = "user_test@example.com"
    password = "password123"
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE email = %s", (email,))
    conn.commit()
    cursor.close()
    conn.close()

    client.post("/api/auth/register", json={
        "name": "Standard User",
        "email": email,
        "password": password
    })

    response = client.post("/api/auth/login", json={
        "email": email,
        "password": password
    })
    return {"Authorization": f"Bearer {response.json()['access_token']}", "email": email}

@pytest.fixture(scope="module")
def admin_auth():
    """Admin kullanıcısı oluşturur ve token döner."""
    email = "admin_test@example.com"
    password = "password123"
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE email = %s", (email,))
    conn.commit()
    cursor.close()
    conn.close()

    client.post("/api/auth/register", json={
        "name": "Admin User",
        "email": email,
        "password": password
    })

    promote_user_to_admin(email)

    response = client.post("/api/auth/login", json={
        "email": email,
        "password": password
    })
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_create_task(user_auth):
    """Kullanıcının görev oluşturmasını test eder."""
    global task_id_with_file
    response = client.post("/api/tasks/", json={
        "title": "File Upload Task",
        "description": "Task for testing files",
        "category": "Testing",
        "status": "pending",
        "dueDate": "2025-12-31",
        "dueTime": "12:00:00"
    }, headers=user_auth)
    
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "File Upload Task"
    task_id_with_file = data["id"]

def test_upload_file(user_auth):
    """Oluşturulan göreve dosya yüklemeyi test eder."""
    global uploaded_file_id
    assert task_id_with_file is not None
    
    file_content = b"fake image content"
    file = io.BytesIO(file_content)
    
    response = client.post(
        f"/api/files/upload/{task_id_with_file}",
        files={"file": ("test_image.png", file, "image/png")},
        headers=user_auth
    )
    
    assert response.status_code == 201
    assert response.json()["info"] == "File uploaded successfully"

    get_res = client.get("/api/tasks/", headers=user_auth)
    tasks = get_res.json()
    my_task = next((t for t in tasks if t["id"] == task_id_with_file), None)
    assert my_task is not None
    assert len(my_task["attachments"]) > 0
    uploaded_file_id = my_task["attachments"][0]["id"]

def test_download_file(user_auth):
    """Yüklenen dosyayı indirmeyi test eder."""
    assert uploaded_file_id is not None
    
    response = client.get(f"/api/files/download/{uploaded_file_id}", headers=user_auth)
    assert response.status_code == 200
    assert response.content == b"fake image content" # İçerik eşleşmeli

def test_admin_can_see_users(admin_auth):
    """Admin kullanıcısının kullanıcı listesini çekebildiğini test eder."""
    response = client.get("/api/auth/users", headers=admin_auth)
    assert response.status_code == 200
    users = response.json()
    assert isinstance(users, list)
    assert len(users) >= 2 # En azından user ve admin olmalı

def test_user_cannot_see_users(user_auth):
    """Normal kullanıcının kullanıcı listesini ÇEKEMEDİĞİNİ test eder."""
    response = client.get("/api/auth/users", headers=user_auth)
    assert response.status_code == 403 

def test_admin_can_see_all_tasks(admin_auth):
    """Adminin tüm görevleri görebildiğini test eder."""
    response = client.get("/api/tasks/", headers=admin_auth)
    assert response.status_code == 200
    tasks = response.json()
    ids = [t["id"] for t in tasks]
    assert task_id_with_file in ids

def test_delete_file(user_auth):
    """Dosya silmeyi test eder."""
    assert uploaded_file_id is not None
    response = client.delete(f"/api/files/{uploaded_file_id}", headers=user_auth)
    assert response.status_code == 200

def test_delete_task_cascades(user_auth):
    """Görev silinince her şeyin temizlendiğini test eder."""
    assert task_id_with_file is not None
    response = client.delete(f"/api/tasks/{task_id_with_file}", headers=user_auth)
    assert response.status_code == 204
    
    # Task silinmiş olmalı
    get_res = client.get("/api/tasks/", headers=user_auth)
    tasks = get_res.json()
    ids = [t["id"] for t in tasks]
    assert task_id_with_file not in ids