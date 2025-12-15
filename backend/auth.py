"""Clerk JWT verification for FastAPI."""

import os
import logging
import jwt
import httpx
from functools import lru_cache
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)
security = HTTPBearer()


@lru_cache(maxsize=1)
def get_clerk_jwks() -> dict:
    """
    Fetch Clerk's JWKS for JWT verification.
    Cached to avoid repeated network calls.
    """
    # Use instance-specific JWKS URL from CLERK_ISSUER
    clerk_issuer = os.getenv("CLERK_ISSUER", "").rstrip("/")
    if clerk_issuer:
        jwks_url = f"{clerk_issuer}/.well-known/jwks.json"
    else:
        # Fallback to global Clerk JWKS
        jwks_url = "https://api.clerk.com/v1/jwks"

    logger.info(f"Fetching JWKS from: {jwks_url}")

    try:
        response = httpx.get(jwks_url, timeout=10)
        response.raise_for_status()
        jwks = response.json()
        logger.info(f"Successfully fetched JWKS with {len(jwks.get('keys', []))} keys")
        return jwks
    except Exception as e:
        logger.error(f"Failed to fetch JWKS from {jwks_url}: {e}")
        raise ValueError(f"Failed to fetch JWKS from {jwks_url}: {e}")


def verify_clerk_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Verify Clerk JWT token and return decoded claims.

    Returns dict with:
    - sub: Clerk user ID (e.g., "user_2abc123...")
    - email: User's email (if available)
    - other standard JWT claims
    """
    token = credentials.credentials
    logger.info(f"Verifying token (first 50 chars): {token[:50]}...")

    try:
        # Get JWKS for verification
        jwks = get_clerk_jwks()

        # Decode token header to get key ID (kid)
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        logger.info(f"Token kid: {kid}")

        if not kid:
            logger.error("Token missing key ID")
            raise HTTPException(
                status_code=401,
                detail="Token missing key ID"
            )

        # Find matching key in JWKS
        key = None
        available_kids = [jwk.get("kid") for jwk in jwks.get("keys", [])]
        logger.info(f"Available JWKS kids: {available_kids}")

        for jwk in jwks.get("keys", []):
            if jwk.get("kid") == kid:
                key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
                break

        if not key:
            # Clear cache and retry once (key rotation scenario)
            logger.info("Key not found, clearing cache and retrying...")
            get_clerk_jwks.cache_clear()
            jwks = get_clerk_jwks()
            for jwk in jwks.get("keys", []):
                if jwk.get("kid") == kid:
                    key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
                    break

        if not key:
            logger.error(f"Token key {kid} not found in JWKS")
            raise HTTPException(
                status_code=401,
                detail="Token key not found in JWKS"
            )

        # Verify and decode token
        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            options={
                "verify_aud": False,  # Clerk doesn't always set audience
                "verify_iss": False,  # Skip issuer check for flexibility
            }
        )

        logger.info(f"Token verified successfully for user: {payload.get('sub')}")
        return payload

    except jwt.ExpiredSignatureError:
        logger.error("Token expired")
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid token: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {str(e)}"
        )


def get_current_user_id(claims: dict = Depends(verify_clerk_token)) -> str:
    """
    Extract user ID from verified token claims.
    Use this as a dependency in protected endpoints.
    """
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User ID not found in token"
        )
    return user_id


def get_current_user(claims: dict = Depends(verify_clerk_token)) -> dict:
    """
    Return full user info from token claims.
    """
    return {
        "user_id": claims.get("sub"),
        "email": claims.get("email"),
        "name": claims.get("name"),
        "image_url": claims.get("image_url"),
    }
