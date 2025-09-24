"""Integration tests for health endpoint."""

import sys
from pathlib import Path

from fastapi.testclient import TestClient

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Test that the health endpoint returns 200 OK with correct response."""
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
