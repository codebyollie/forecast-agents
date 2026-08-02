import pytest
from fastapi.testclient import TestClient
import os
import sys

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
