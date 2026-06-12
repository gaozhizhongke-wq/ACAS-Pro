# -*- coding: utf-8 -*-
"""Authentication routes for ACAS Pro Web - no cached refs, always read from source"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime, timezone

import jwt
import acas_pro.core.security as _sec
import acas_pro.core.config as _cfg_mod
import acas_pro.services.user_service as _us_mod
from acas_pro.core.logging import get_logger
from acas_pro.web.schemas import (
    RegisterRequest,
    LoginRequest,
    AuthResponse,
    AuthErrorResponse,
)
from pydantic import ValidationError

logger = get_logger(__name__)

# DO NOT cache refs here - conftest resets singletons between tests.
# Access _sec.rate_limiter etc. directly in each function.

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def generate_token(user_id: str, account: str) -> str:
    """Generate JWT using JWTManager (unified auth system)."""
    return _sec.JWTManager.generate_token(user_id, extra_claims={"account": account})


def verify_token(token: str) -> dict | None:
    """
    Verify JWT using JWTManager. Supports both:
    - New tokens (JWTManager, claim='sub')
    - Old tokens (legacy, claim='user_id') for backward compatibility
    """
    payload = _sec.JWTManager.verify_token(token, expected_type="access")
    if payload:
        return payload
    # Fallback: try legacy format (strict validation)
    try:
        JWT_SECRET = _sec.JWTManager._get_secret_key()
        alg = _cfg_mod.config.security.jwt_algorithm or "HS256"
        # Enforce algorithm whitelist to prevent "none" algorithm attack
        if alg not in (
            "HS256",
            "HS384",
            "HS512",
            "RS256",
            "RS384",
            "RS512",
            "ES256",
            "ES384",
            "ES512",
        ):
            logger.warning(f"Invalid JWT algorithm configured: {alg}")
            return None
        payload = jwt.decode(token, JWT_SECRET, algorithms=[alg])
        # Validate legacy token has required claims
        if not payload.get("user_id"):
            return None
        # Check expiration — legacy tokens must have valid exp
        exp = payload.get("exp")
        if exp is None:
            logger.warning("Legacy JWT token missing exp claim — rejecting")
            return None
        if datetime.now(timezone.utc) > datetime.fromtimestamp(exp, tz=timezone.utc):
            logger.warning("Legacy JWT token expired")
            return None
        # Check token is not revoked
        jti = payload.get("jti")
        if jti and _sec.TokenBlacklist.is_revoked(jti):
            logger.warning(f"Legacy JWT token revoked: jti={jti[:16]}...")
            return None
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Legacy JWT token expired")
    except jwt.InvalidTokenError as e:
        logger.warning(f"Legacy JWT token invalid: {e}")
    except (ValueError, KeyError) as e:
        logger.warning(f"JWT configuration error: {e}")
    except Exception as e:
        logger.warning(f"Unexpected JWT error: {e}")
    return None


@bp.route("/register", methods=["POST"])
def auth_register() -> tuple:
    """Register a new user account with Pydantic validation"""
    try:
        req = RegisterRequest.model_validate(request.json or {})
    except ValidationError as e:
        logger.warning(f"Registration validation failed: {e}")
        return jsonify(
            AuthErrorResponse(error=f"Validation error: {e}").model_dump(mode="json")
        ), 400

    # Enforce strong password policy
    is_valid, pw_msg = _sec.password_validator.validate(req.password)
    if not is_valid:
        return jsonify(AuthErrorResponse(error=pw_msg).model_dump(mode="json")), 400

    # Rate limit registration (10 per 10 minutes per account)
    rate_key = f"register:{req.account}"
    if not _sec.rate_limiter.is_allowed(rate_key, max_attempts=10, window_seconds=600):
        return jsonify(
            AuthErrorResponse(
                error="Too many registration attempts. Please try again later."
            ).model_dump(mode="json")
        ), 429
    _sec.rate_limiter.record_attempt(rate_key)

    ok, msg, profile = _us_mod.user_service.register(
        account=req.account, password=req.password, nickname=req.nickname or req.account
    )
    if not ok:
        return jsonify(AuthErrorResponse(error=msg).model_dump(mode="json")), 409

    token = generate_token(profile.id, req.account)
    return jsonify(
        AuthResponse(
            success=True,
            token=token,
            user={
                "user_id": profile.id,
                "account": profile.account,
                "nickname": profile.nickname,
            },
        ).model_dump(mode="json")
    ), 200


@bp.route("/login", methods=["POST"])
def auth_login() -> tuple:
    """Login with account and password with Pydantic validation"""
    try:
        req = LoginRequest.model_validate(request.json or {})
    except ValidationError as e:
        logger.warning(f"Login validation failed: {e}")
        return jsonify(
            AuthErrorResponse(error=f"Validation error: {e}").model_dump(mode="json")
        ), 400

    # Rate limit login attempts: 20 per 10 minutes per account
    rate_key = f"login:{req.account}"
    if not _sec.rate_limiter.is_allowed(rate_key, max_attempts=20, window_seconds=600):
        return jsonify(
            AuthErrorResponse(
                error="Too many login attempts. Please try again later."
            ).model_dump(mode="json")
        ), 429
    _sec.rate_limiter.record_attempt(rate_key)

    ok, msg, profile = _us_mod.user_service.login(
        account=req.account, password=req.password
    )
    if not ok:
        return jsonify(AuthErrorResponse(error=msg).model_dump(mode="json")), 401

    token = generate_token(profile.id, req.account)
    return jsonify(
        AuthResponse(
            success=True,
            token=token,
            user={
                "user_id": profile.id,
                "account": profile.account,
                "nickname": profile.nickname,
            },
        ).model_dump(mode="json")
    ), 200


@bp.route("/logout", methods=["POST"])
def auth_logout() -> tuple:
    """Logout and revoke current token"""
    # Extract token from Authorization header or cookie
    token = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    elif not token:
        token = request.cookies.get("access_token")

    if token:
        # Revoke the token
        _sec.JWTManager.revoke_token(token)

    response = jsonify({"success": True, "message": "Logged out successfully"})
    response.delete_cookie("access_token")
    return response, 200


@bp.route("/me", methods=["GET"])
def auth_me() -> tuple:
    """Get current user info (requires authentication)"""
    user: dict | None = g.get("user") if hasattr(g, "user") else None
    if not user:
        return jsonify({"error": "Authentication required"}), 401
    return jsonify({"user_id": user["user_id"], "account": user["account"]})
