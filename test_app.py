import os

os.environ["MOCK_AI"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///./test_fitbuddy.db"

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=True)


from app.database import init_db

init_db()


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_home():
    response = client.get("/")
    assert response.status_code == 200
    assert "Generate 7-Day Plan" in response.text


def test_generate_api():
    payload = {
        "user_id": "test001",
        "name": "Test User",
        "age": 22,
        "weight": 60,
        "goal": "general wellness",
        "intensity": "medium",
    }
    response = client.post("/api/plans", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == "test001"
    assert "Day 1" in body["workout_plan"]
    assert body["nutrition_tip"]


def test_feedback_api():
    payload = {
        "user_id": "test002",
        "name": "Feedback User",
        "age": 24,
        "weight": 65,
        "goal": "weight loss",
        "intensity": "low",
    }
    client.post("/api/plans", json=payload)
    response = client.post("/api/plans/test002/feedback", json={"user_id": "test002", "feedback": "Add more cardio"})
    assert response.status_code == 200
    assert "UPDATED FROM FEEDBACK" in response.json()["updated_plan"]


def test_users_api():
    response = client.get("/api/users")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
