import json
import time
import base64
import pytest
from fastapi.testclient import TestClient
from forecast_ai.config import ForecastConfig
from forecast_ai.api.server import ApiServer
from forecast_ai.pipelines.forecast import ForecastPipeline
from forecast_ai.services.balance_checker import BalanceChecker
from forecast_ai.services.badge_evaluator import BadgeEvaluator
from forecast_ai.db.supabase_store import SupabaseProfileStore

def create_mock_jwt(sub: str = "did:privy:test_user_123", email: str = "test@example.com", wallet: str = "0x1111111111111111111111111111111111111111", expired: bool = False) -> str:
    header = {"alg": "RS256", "typ": "JWT"}
    exp_time = time.time() - 3600 if expired else time.time() + 3600
    payload = {
        "sub": sub,
        "email": email,
        "wallet_address": wallet,
        "iss": "privy.io",
        "exp": exp_time
    }
    def _b64(d: dict) -> str:
        s = json.dumps(d).encode("utf-8")
        return base64.urlsafe_b64encode(s).decode("utf-8").rstrip("=")
    return f"{_b64(header)}.{_b64(payload)}.mock_signature"

def test_balance_checker_tier_mapping():
    cfg = ForecastConfig()
    checker = BalanceChecker(cfg.profile.tier)

    assert checker.evaluate_holder_tier(0.0) == "Free"
    assert checker.evaluate_holder_tier(150000.0) == "Free"
    assert checker.evaluate_holder_tier(200000.0) == "Holder"
    assert checker.evaluate_holder_tier(500000.0) == "Holder"
    assert checker.evaluate_holder_tier(1000000.0) == "Pro Holder"
    assert checker.evaluate_holder_tier(5000000.0) == "Pro Holder"

def test_badge_evaluator():
    evaluator = BadgeEvaluator(early_adopter_cutoff="2026-09-01T00:00:00Z")

    # Free tier, recent account
    badges1 = evaluator.evaluate_badges("Free", "2026-10-01T00:00:00Z")
    assert "holder" not in badges1
    assert "early_adopter" not in badges1

    # Holder tier, early account
    badges2 = evaluator.evaluate_badges("Holder", "2026-05-01T00:00:00Z")
    assert "holder" in badges2
    assert "early_adopter" in badges2
    assert "pro_holder" not in badges2

    # Pro Holder tier, early account
    badges3 = evaluator.evaluate_badges("Pro Holder", "2026-05-01T00:00:00Z")
    assert "holder" in badges3
    assert "pro_holder" in badges3
    assert "early_adopter" in badges3

@pytest.mark.asyncio
async def test_supabase_in_memory_fallback():
    cfg = ForecastConfig()
    store = SupabaseProfileStore(cfg.profile.supabase)

    p1 = await store.get_profile("non_existent_user")
    assert p1 is None

    new_profile = {
        "privy_user_id": "did:privy:user_999",
        "email": "user999@example.com",
        "holder_tier": "Holder",
        "forai_balance": 250000.0,
        "badges": ["holder"],
        "enabled_partner_features": ["facts_ai"]
    }
    saved = await store.upsert_profile(new_profile)
    assert saved["privy_user_id"] == "did:privy:user_999"

    p2 = await store.get_profile("did:privy:user_999")
    assert p2 is not None
    assert p2["email"] == "user999@example.com"
    assert p2["holder_tier"] == "Holder"
    assert p2["enabled_partner_features"] == ["facts_ai"]

def test_profile_endpoint_unauthenticated():
    cfg = ForecastConfig()
    pipeline = ForecastPipeline(cfg)
    server = ApiServer(cfg, pipeline)
    client = TestClient(server.app)

    # Request without Authorization header must fail with 401
    resp = client.get("/profile/me")
    assert resp.status_code == 401
    assert "Authentication required" in resp.json()["detail"]

def test_profile_endpoint_expired_token():
    cfg = ForecastConfig()
    pipeline = ForecastPipeline(cfg)
    server = ApiServer(cfg, pipeline)
    client = TestClient(server.app)

    expired_token = create_mock_jwt(expired=True)
    resp = client.get("/profile/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 401
    assert "expired" in resp.json()["detail"]

def test_profile_endpoint_success_and_partner_features():
    cfg = ForecastConfig()
    pipeline = ForecastPipeline(cfg)
    server = ApiServer(cfg, pipeline)
    client = TestClient(server.app)

    token = create_mock_jwt(sub="did:privy:test_user_777", email="privyuser@example.com")
    resp = client.get("/profile/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200

    data = resp.json()
    assert data["privy_user_id"] == "did:privy:test_user_777"
    assert data["email"] == "privyuser@example.com"
    assert data["holder_tier"] in ("Free", "Holder", "Pro Holder")
    assert isinstance(data["badges"], list)
    assert isinstance(data["enabled_partner_features"], list)
    assert data["track_record_status"] == "placeholder_active"

    # Test PATCH /profile/partner-features to enable facts_ai
    patch_resp = client.patch(
        "/profile/partner-features",
        json={"feature": "facts_ai", "enabled": True},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert patch_resp.status_code == 200
    assert "facts_ai" in patch_resp.json()["enabled_partner_features"]

    # Re-fetch profile to verify persistence
    resp2 = client.get("/profile/me", headers={"Authorization": f"Bearer {token}"})
    assert resp2.status_code == 200
    assert "facts_ai" in resp2.json()["enabled_partner_features"]

    # Test PATCH /profile/partner-features to disable facts_ai
    patch_resp2 = client.patch(
        "/profile/partner-features",
        json={"feature": "facts_ai", "enabled": False},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert patch_resp2.status_code == 200
    assert "facts_ai" not in patch_resp2.json()["enabled_partner_features"]

def test_agents_meta_endpoint():
    cfg = ForecastConfig()
    pipeline = ForecastPipeline(cfg)
    server = ApiServer(cfg, pipeline)
    client = TestClient(server.app)

    resp = client.get("/agents/meta")
    assert resp.status_code == 200
    meta = resp.json()
    assert len(meta) == 7
    agent_ids = [a["id"] for a in meta]
    assert "news" in agent_ids
    assert "research" in agent_ids
    assert "market" in agent_ids
    assert meta[0]["icon"].startswith("ti-")
    assert "color" in meta[0]
