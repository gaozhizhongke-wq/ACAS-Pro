#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - User Service
Enterprise user management with security controls
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass, asdict

from acas_pro.core.database import db
from acas_pro.core.security import (
    password_validator, password_hasher, 
    session_manager, rate_limiter
)
from acas_pro.core.logging import get_logger, audit_logger

logger = get_logger(__name__)


@dataclass
class UserProfile:
    """User profile data"""
    id: str
    account: str
    nickname: str
    email: str
    phone: str
    role: str
    status: str
    region: str
    language: str
    timezone: str
    created_at: str
    last_login: Optional[str]
    wallet_balance: float
    wallet_currency: str
    model_preference: str


class UserService:
    """
    Enterprise user service
    - Secure authentication
    - Account lockout protection
    - Session management
    - Audit logging
    """
    
    def __init__(self):
        self._current_user: Optional[UserProfile] = None
    
    def register(self, account: str, password: str, nickname: str = "",
                 email: str = "", phone: str = "", region: str = "global") -> Tuple[bool, str, Optional[UserProfile]]:
        """
        Register new user
        
        Returns: (success, message, user_profile)
        """
        # Validate account
        if not account or len(account) < 3:
            return False, "Account must be at least 3 characters", None
        
        # Validate password
        is_valid, error_msg = password_validator.validate(password)
        if not is_valid:
            return False, error_msg, None
        
        # Check if account exists
        existing = db.fetchone("SELECT id FROM users WHERE account = ?", (account,))
        if existing:
            return False, "Account already exists", None
        
        # Create user
        user_id = f"U{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')[:-3]}"
        password_hash = password_hasher.hash(password)
        now = datetime.now(timezone.utc).isoformat()
        
        # Determine language from region
        language = "zh"
        if region in ["mena"]:
            language = "ar"
        elif region in ["ssa"]:
            language = "en"
        elif region in ["sea"]:
            language = "en"
        
        try:
            db.insert("users", {
                "id": user_id,
                "account_type": "email" if "@" in account else "phone",
                "account": account,
                "password_hash": password_hash,
                "nickname": nickname or account,
                "email": email,
                "phone": phone,
                "role": "user",
                "status": "active",
                "region": region,
                "language": language,
                "timezone": "Asia/Shanghai" if region == "cn_northwest" else "UTC",
                "created_at": now,
                "last_login": None,
                "login_count": 0,
                "failed_login_count": 0,
                "wallet_balance": 0.0,
                "wallet_currency": "USD",
                "model_preference": "auto"
            })
            
            audit_logger.log(
                "USER_REGISTERED",
                user_id,
                {"account": account, "region": region},
                severity="info"
            )
            
            profile = self._get_profile(user_id)
            return True, "Registration successful", profile
            
        except Exception as e:
            logger.error(f"Registration failed: {e}")
            return False, "Registration failed, please try again", None
    
    def login(self, account: str, password: str, ip_address: str = None) -> Tuple[bool, str, Optional[UserProfile]]:
        """
        Authenticate user
        
        Returns: (success, message, user_profile)
        """
        # Rate limiting
        rate_key = f"login:{account}"
        if not rate_limiter.is_allowed(rate_key, max_attempts=5, window_seconds=300):
            audit_logger.log(
                "LOGIN_RATE_LIMITED",
                account,
                {"ip_address": ip_address},
                ip_address=ip_address,
                severity="warning"
            )
            return False, "Too many login attempts. Please try again later.", None
        
        # Find user
        user = db.fetchone("SELECT * FROM users WHERE account = ?", (account,))
        if not user:
            rate_limiter.record_attempt(rate_key)
            audit_logger.log(
                "LOGIN_FAILED",
                account,
                {"reason": "account_not_found", "ip_address": ip_address},
                ip_address=ip_address,
                severity="warning"
            )
            return False, "Invalid account or password", None
        
        # Check if locked
        if user.get("locked_until"):
            locked_until = datetime.fromisoformat(user["locked_until"])
            if datetime.now(timezone.utc) < locked_until:
                remaining = (locked_until - datetime.now(timezone.utc)).seconds // 60
                return False, f"Account is locked. Try again in {remaining} minutes.", None
        
        # Check status
        if user.get("status") != "active":
            return False, "Account is inactive", None
        
        # Verify password
        if not password_hasher.verify(password, user["password_hash"]):
            # Increment failed login count
            failed_count = user.get("failed_login_count", 0) + 1
            
            if failed_count >= 5:
                # Lock account
                lock_until = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
                db.update("users", 
                    {"failed_login_count": failed_count, "locked_until": lock_until},
                    "id = ?", (user["id"],)
                )
                audit_logger.log(
                    "ACCOUNT_LOCKED",
                    user["id"],
                    {"failed_attempts": failed_count, "ip_address": ip_address},
                    ip_address=ip_address,
                    severity="warning"
                )
                return False, "Account locked due to too many failed attempts. Try again in 30 minutes.", None
            else:
                db.update("users", 
                    {"failed_login_count": failed_count},
                    "id = ?", (user["id"],)
                )
            
            rate_limiter.record_attempt(rate_key)
            audit_logger.log(
                "LOGIN_FAILED",
                user["id"],
                {"reason": "invalid_password", "ip_address": ip_address},
                ip_address=ip_address,
                severity="warning"
            )
            return False, "Invalid account or password", None
        
        # Successful login
        now = datetime.now(timezone.utc).isoformat()
        db.update("users", {
            "last_login": now,
            "login_count": user.get("login_count", 0) + 1,
            "failed_login_count": 0,
            "locked_until": None
        }, "id = ?", (user["id"],))
        
        rate_limiter.reset(rate_key)
        
        audit_logger.log(
            "LOGIN_SUCCESS",
            user["id"],
            {"account": account, "ip_address": ip_address},
            ip_address=ip_address,
            severity="info"
        )
        
        profile = self._get_profile(user["id"])
        self._current_user = profile
        return True, "Login successful", profile
    
    def login_guest(self) -> UserProfile:
        """Create guest session"""
        guest_id = f"G{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')[:-3]}"
        now = datetime.now(timezone.utc).isoformat()
        
        db.insert("users", {
            "id": guest_id,
            "account_type": "guest",
            "account": guest_id,
            "password_hash": "",
            "nickname": "Guest",
            "role": "guest",
            "status": "active",
            "region": "global",
            "language": "zh",
            "timezone": "UTC",
            "created_at": now,
            "last_login": now,
            "login_count": 1,
            "wallet_balance": 1000.0,
            "wallet_currency": "USD"
        })
        
        audit_logger.log("GUEST_LOGIN", guest_id, {})
        
        profile = self._get_profile(guest_id)
        self._current_user = profile
        return profile
    
    def logout(self) -> None:
        """Logout current user"""
        if self._current_user:
            audit_logger.log("LOGOUT", self._current_user.id, {})
            self._current_user = None
    
    def _get_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile by ID"""
        user = db.fetchone("SELECT * FROM users WHERE id = ?", (user_id,))
        if not user:
            return None
        
        return UserProfile(
            id=user["id"],
            account=user["account"],
            nickname=user["nickname"],
            email=user["email"],
            phone=user["phone"],
            role=user["role"],
            status=user["status"],
            region=user["region"],
            language=user["language"],
            timezone=user["timezone"],
            created_at=user["created_at"],
            last_login=user["last_login"],
            wallet_balance=user["wallet_balance"],
            wallet_currency=user["wallet_currency"],
            model_preference=user["model_preference"]
        )
    
    def get_current(self) -> Optional[UserProfile]:
        """Get current logged-in user"""
        return self._current_user
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated (not guest)"""
        return self._current_user is not None and self._current_user.role != "guest"
    
    def update_profile(self, user_id: str, updates: Dict[str, Any]) -> Tuple[bool, str]:
        """Update user profile"""
        allowed_fields = {"nickname", "email", "phone", "language", "timezone", "model_preference"}
        
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
        if not filtered_updates:
            return False, "No valid fields to update"
        
        try:
            count = db.update("users", filtered_updates, "id = ?", (user_id,))
            if count > 0:
                audit_logger.log("PROFILE_UPDATED", user_id, {"fields": list(filtered_updates.keys())})
                return True, "Profile updated successfully"
            return False, "User not found"
        except Exception as e:
            logger.error(f"Profile update failed: {e}")
            return False, "Update failed"
    
    def change_password(self, user_id: str, old_password: str, new_password: str) -> Tuple[bool, str]:
        """Change user password"""
        # Validate new password
        is_valid, error_msg = password_validator.validate(new_password)
        if not is_valid:
            return False, error_msg
        
        # Get user
        user = db.fetchone("SELECT password_hash FROM users WHERE id = ?", (user_id,))
        if not user:
            return False, "User not found"
        
        # Verify old password
        if not password_hasher.verify(old_password, user["password_hash"]):
            return False, "Current password is incorrect"
        
        # Update password
        new_hash = password_hasher.hash(new_password)
        db.update("users", {"password_hash": new_hash}, "id = ?", (user_id,))
        
        audit_logger.log("PASSWORD_CHANGED", user_id, {})
        return True, "Password changed successfully"


# Global instance
user_service = UserService()
