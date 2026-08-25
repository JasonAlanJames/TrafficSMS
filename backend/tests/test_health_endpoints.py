import pytest


@pytest.mark.parametrize("path, endpoint", [("/health", "health"), ("/live", "live"), ("/ready", "ready")])
def test_health_endpoints_are_public_and_safe(client, path: str, endpoint: str) -> None:
    response = client.get(path)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"status": "ok", "service": "trafficsms-api", "endpoint": endpoint}
