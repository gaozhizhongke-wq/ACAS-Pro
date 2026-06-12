"""Pydantic schemas for ACAS Pro Web API input validation.

All request/response models for API endpoints.
Uses Pydantic v2 for strict type validation and clear error messages.
"""

from typing import Optional, List, Literal, Any
from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Auth schemas
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    """POST /api/auth/register"""

    account: str = Field(
        ..., min_length=3, max_length=50, description="User account name"
    )
    password: str = Field(
        ..., min_length=8, max_length=128, description="User password"
    )
    nickname: Optional[str] = Field(None, max_length=50, description="Display nickname")

    @field_validator("account")
    @classmethod
    def account_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("account cannot be empty")
        return v

    @field_validator("password")
    @classmethod
    def password_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("password cannot be empty")
        return v


class LoginRequest(BaseModel):
    """POST /api/auth/login"""

    account: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("account", "password")
    @classmethod
    def strip_and_check(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("field cannot be empty")
        return v


class AuthResponse(BaseModel):
    """Common auth success response"""

    success: bool
    token: Optional[str] = None
    user: Optional[dict] = None


class AuthErrorResponse(BaseModel):
    """Common auth error response"""

    error: str


# ---------------------------------------------------------------------------
# LLM schemas
# ---------------------------------------------------------------------------


class LLMChatMessage(BaseModel):
    """Single message in LLM chat"""

    role: Literal["user", "assistant", "system"] = Field(
        ..., description="Message role"
    )
    content: str = Field(
        ..., min_length=1, max_length=100000, description="Message content"
    )


class LLMChatRequest(BaseModel):
    """POST /api/llm/chat"""

    messages: List[LLMChatMessage] = Field(
        ..., min_length=1, description="Chat messages"
    )
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=32000)


class LLMChatResponse(BaseModel):
    """LLM chat success response"""

    success: bool
    content: Optional[str] = None
    usage: Optional[Any] = None


class LLMConfigRequest(BaseModel):
    """POST /api/llm/config"""

    provider: Literal[
        "openai",
        "anthropic",
        "kimi",
        "deepseek",
        "qwen",
        "lmstudio",
        "ollama",
        "custom",
    ] = Field(default="openai", description="LLM provider")
    api_key: Optional[str] = Field(default="", description="API key")
    api_base: Optional[str] = Field(None, description="Custom API base URL")
    model: Optional[str] = Field(None, description="Model name")

    @field_validator("api_key")
    @classmethod
    def api_key_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
        return v


class LLMConfigResponse(BaseModel):
    """LLM config save response"""

    success: bool
    message: str


# ---------------------------------------------------------------------------
# Dashboard schemas
# ---------------------------------------------------------------------------


class DashboardStatsResponse(BaseModel):
    """GET /api/dashboard/stats"""

    total_products: int = Field(..., ge=0)
    total_orders: int = Field(..., ge=0)
    total_revenue: float = Field(..., ge=0.0)
    active_users: int = Field(..., ge=0)
    conversion_rate: Optional[float] = Field(None, ge=0.0, le=1.0)
    recent_activity: Optional[List[dict]] = None


class HealthCheckResponse(BaseModel):
    """GET /api/health"""

    status: Literal["healthy", "degraded", "unhealthy"]
    timestamp: str
    version: str
    environment: str
    checks: Optional[List[dict]] = None


# ---------------------------------------------------------------------------
# Generic error schema
# ---------------------------------------------------------------------------


class ValidationErrorResponse(BaseModel):
    """Pydantic validation error response format"""

    error: str = "Validation error"
    details: List[dict] = Field(default_factory=list)
