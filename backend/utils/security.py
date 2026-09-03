"""
Security utilities: rate limiting middleware and JWT-ready auth scaffolding.
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.config import get_settings
from backend.utils.logging_config import get_logger

logger = get_logger(__name__)

# ============================================
# Rate Limiting (in-memory for dev)
# ============================================

# Simple in-memory rate limiter
_rate_limit_store: dict[str, list[datetime]] = {}


async def rate_limit_middleware(request: Request) -> None:
    """
    Simple per-IP rate limiting middleware.
    In production, use Redis-backed rate limiting.
    """
    settings = get_settings()
    client_ip = request.client.host if request.client else "unknown"
    now = datetime.utcnow()
    window = timedelta(minutes=1)
    
    # Clean old entries
    if client_ip in _rate_limit_store:
        _rate_limit_store[client_ip] = [
            ts for ts in _rate_limit_store[client_ip]
            if now - ts < window
        ]
    else:
        _rate_limit_store[client_ip] = []
    
    # Check limit
    if len(_rate_limit_store[client_ip]) >= settings.rate_limit_per_minute:
        logger.warning("rate_limit_exceeded", client_ip=client_ip)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )
    
    _rate_limit_store[client_ip].append(now)


# ============================================
# JWT-Ready Authentication Scaffolding
# ============================================

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> Optional[dict]:
    """
    Optional JWT authentication. Returns None if no token provided.
    In production, validate JWT token and return user data.
    
    This is a scaffolding — currently allows all requests.
    """
    if credentials is None:
        return None
    
    # TODO: Implement JWT validation
    # try:
    #     payload = jwt.decode(credentials.credentials, settings.secret_key, algorithms=["HS256"])
    #     return {"user_id": payload.get("sub"), "email": payload.get("email")}
    # except JWTError:
    #     raise HTTPException(status_code=401, detail="Invalid token")
    
    return {"user_id": "demo-user", "token": credentials.credentials}


async def require_auth(
    user: Optional[dict] = Depends(get_current_user_optional),
) -> dict:
    """
    Require authentication. Use as a dependency for protected endpoints.
    Currently passes through for development.
    """
    # In production, uncomment the check below:
    # if user is None:
    #     raise HTTPException(status_code=401, detail="Authentication required")
    return user or {"user_id": "anonymous"}
