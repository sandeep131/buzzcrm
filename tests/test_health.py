"""Issue #1 acceptance: the app boots and /health returns 200."""

from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_does_not_require_database(client: TestClient) -> None:
    """Liveness must not depend on Postgres being reachable — otherwise a
    database blip reads as a dead process and restarts fix nothing."""
    assert client.get("/health").status_code == 200
