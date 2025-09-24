from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.main import create_app


@pytest.fixture
def test_db():
    """Create a test database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session


@pytest.fixture
def client(test_db: Session):
    """Create a test client with test database."""
    app = create_app()

    # Override the database dependency
    def get_test_session():
        yield test_db

    # Import the actual get_session function and override it
    from app.db import get_session

    app.dependency_overrides[get_session] = get_test_session

    return TestClient(app)


def test_list_teams_empty(client: TestClient):
    """Test listing teams when none exist."""
    response = client.get("/api/teams/")
    assert response.status_code == 200
    assert response.json() == []


def test_create_team_success(client: TestClient):
    """Test creating a team successfully."""
    team_data = {"name": "Test Team", "season": "2024-25"}

    response = client.post("/api/teams/", json=team_data)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == "Test Team"
    assert data["season"] == "2024-25"
    assert "id" in data
    assert "created_at" in data


def test_create_team_duplicate(client: TestClient):
    """Test creating a duplicate team returns 409."""
    team_data = {"name": "Test Team", "season": "2024-25"}

    # Create first team
    response1 = client.post("/api/teams/", json=team_data)
    assert response1.status_code == 201

    # Try to create duplicate
    response2 = client.post("/api/teams/", json=team_data)
    assert response2.status_code == 409
    assert "already exists" in response2.json()["detail"]


def test_get_team_success(client: TestClient):
    """Test getting a team by ID."""
    # Create a team first
    team_data = {"name": "Test Team", "season": "2024-25"}
    create_response = client.post("/api/teams/", json=team_data)
    team_id = create_response.json()["id"]

    # Get the team
    response = client.get(f"/api/teams/{team_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == team_id
    assert data["name"] == "Test Team"
    assert data["season"] == "2024-25"


def test_get_team_not_found(client: TestClient):
    """Test getting a non-existent team returns 404."""
    response = client.get("/api/teams/999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_list_teams_with_data(client: TestClient):
    """Test listing teams when data exists."""
    # Create multiple teams
    teams_data = [
        {"name": "Team A", "season": "2024-25"},
        {"name": "Team B", "season": "2024-25"},
        {"name": "Team A", "season": "2023-24"},  # Same name, different season
    ]

    for team_data in teams_data:
        response = client.post("/api/teams/", json=team_data)
        assert response.status_code == 201

    # List teams
    response = client.get("/api/teams/")
    assert response.status_code == 200

    teams = response.json()
    assert len(teams) == 3

    # Should be ordered by name, then season
    assert teams[0]["name"] == "Team A"
    assert teams[0]["season"] == "2023-24"
    assert teams[1]["name"] == "Team A"
    assert teams[1]["season"] == "2024-25"
    assert teams[2]["name"] == "Team B"
    assert teams[2]["season"] == "2024-25"
