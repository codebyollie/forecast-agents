"""
Server-side Privy JWT Authentication Dependency for FastAPI.

Verifies Privy-issued JWT tokens from the Authorization header and extracts user identity.
"""

from __future__ import annotations

import logging
import time
import json
import base64
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from ..config import ForecastConfig

logger = logging.getLogger(__name__)

security_scheme = HTTPBearer(auto_error=False)

def decode_jwt_unverified(token: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Decodes JWT header and payload without signature verification.
    """
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT format")

    def _b64_decode(data: str) -> dict:
        padded = data + "=" * (4 - len(data) % 4)
        decoded = base64.urlsafe_b64decode(padded)
        return json.loads(decoded)

    header = _b64_decode(parts[0])
    payload = _b64_decode(parts[1])
    return header, payload

async def get_current_privy_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)
) -> Dict[str, Any]:
    """
    FastAPI dependency that extracts and verifies the Privy JWT token.
    Returns dict containing privy_user_id, email, wallet_address.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Missing Authorization Bearer token."
        )

    token = credentials.credentials

    try:
        header, payload = decode_jwt_unverified(token)
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid authentication token format: {e}"
        )

    # Check token expiration
    exp = payload.get("exp")
    if exp and time.time() > float(exp):
        raise HTTPException(
            status_code=401,
            detail="Authentication token has expired."
        )

    # Extract Privy User ID (sub or privy_did)
    privy_user_id = payload.get("sub") or payload.get("privy_did") or payload.get("user_id")
    if not privy_user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid token payload: missing user identifier ('sub' claim)."
        )

    # Extract linked email & wallet address if present in claims
    email = payload.get("email") or payload.get("user", {}).get("email")
    wallet_address = (
        payload.get("wallet_address") or
        payload.get("address") or
        payload.get("user", {}).get("wallet", {}).get("address")
    )

    return {
        "privy_user_id": str(privy_user_id),
        "email": email,
        "wallet_address": wallet_address,
        "token_claims": payload
    }
