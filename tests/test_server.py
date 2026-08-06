import pytest
from fastapi.testclient import TestClient
import os
import sys
from types import SimpleNamespace

from fastapi import HTTPException, Request

# Ensure forecast_ai is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_server_starts_without_env_vars():
    # Remove potentially set env vars
    for k in list(os.environ.keys()):
        if 'SUPABASE' in k or 'PRIVY' in k:
            del os.environ[k]
            
    # Now import app (this will load config and instantiate the server)
    from forecast_ai.api.server import app
    
    client = TestClient(app)
    
    # Test healthz
    resp = client.get('/healthz')
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "message": "Forecast AI API Server active."}

    # Test agents meta
    resp = client.get('/agents/meta')
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def _request(headers=None):
    encoded_headers = [
        (name.lower().encode("latin-1"), value.encode("latin-1"))
        for name, value in (headers or {}).items()
    ]
    return Request({
        "type": "http",
        "method": "GET",
        "path": "/markets/search",
        "headers": encoded_headers,
        "client": ("127.0.0.1", 12345),
    })


def test_authenticated_service_calls_skip_shared_ip_limit(monkeypatch):
    from forecast_ai.api import routes

    pipeline = SimpleNamespace(config=SimpleNamespace(server=SimpleNamespace(api_key="service-secret")))
    monkeypatch.setattr(routes, "_pipeline", pipeline)
    routes._IP_RATE_LIMITS.clear()

    for _ in range(60):
        assert routes.enforce_request_access(
            _request({"x-api-key": "service-secret"})
        ) is True

    assert routes._IP_RATE_LIMITS == {}


def test_public_calls_remain_rate_limited(monkeypatch):
    from forecast_ai.api import routes

    pipeline = SimpleNamespace(config=SimpleNamespace(server=SimpleNamespace(api_key="")))
    monkeypatch.setattr(routes, "_pipeline", pipeline)
    monkeypatch.setattr(routes, "MAX_PER_HOUR", 2)
    routes._IP_RATE_LIMITS.clear()

    assert routes.enforce_request_access(_request()) is False
    assert routes.enforce_request_access(_request()) is False
    with pytest.raises(HTTPException) as exc:
        routes.enforce_request_access(_request())

    assert exc.value.status_code == 429


def test_private_endpoints_require_a_configured_server_key(monkeypatch):
    from forecast_ai.api import routes

    pipeline = SimpleNamespace(config=SimpleNamespace(server=SimpleNamespace(api_key="")))
    monkeypatch.setattr(routes, "_pipeline", pipeline)

    with pytest.raises(HTTPException) as exc:
        routes.require_private_access(_request())

    assert exc.value.status_code == 503
