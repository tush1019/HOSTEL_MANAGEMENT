import os

import pytest

from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["DATABASE"] = os.path.join(app.root_path, "test_hostel.db")
    if os.path.exists(app.config["DATABASE"]):
        os.remove(app.config["DATABASE"])

    with app.app_context():
        from app import init_db

        init_db()

    with app.test_client() as client:
        yield client


def test_index_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Hostel Management" in response.data


def test_summary_endpoint(client):
    response = client.get("/api/summary")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["total_rooms"] >= 3
    assert "total_students" in payload


def test_room_creation(client):
    response = client.post(
        "/rooms/add",
        data={"room_number": "C-301", "capacity": "4", "rent": "7000"},
    )
    assert response.status_code == 302

    response = client.get("/rooms")
    assert b"C-301" in response.data


def test_student_creation(client):
    response = client.post(
        "/students/add",
        data={
            "name": "Rahul Verma",
            "phone": "9123456789",
            "room_id": "1",
            "check_in": "2026-02-01",
        },
    )
    assert response.status_code == 302

    response = client.get("/students")
    assert b"Rahul Verma" in response.data
