from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import jwt
from passlib.context import CryptContext
from app.core.config import get_settings

settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class SecurityUtils:
    """Security utilities for password hashing and verification"""

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """Generate password hash"""
        return pwd_context.hash(password)


class JWTManager:
    """JWT token management using PyJWT"""

    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    @staticmethod
    def decode_token(token: str) -> Optional[Dict[str, Any]]:
        """Decode and verify JWT token"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            # Token hết hạn
            return None
        except jwt.InvalidTokenError:
            # Token không hợp lệ
            return None

    @staticmethod
    def create_verification_token(user_id: int) -> str:
        """Create email verification token"""
        data = {"user_id": user_id, "type": "verification"}
        expire = datetime.now(timezone.utc) + timedelta(hours=24)
        data.update({"exp": expire})
        return jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    def create_reset_password_token(user_id: int) -> str:
        """Create password reset token"""
        data = {"user_id": user_id, "type": "reset_password"}
        expire = datetime.now(timezone.utc) + timedelta(hours=1)
        data.update({"exp": expire})
        return jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    def get_user_id_from_token(token: str) -> Optional[int]:
        """Extract user_id from token"""
        payload = JWTManager.decode_token(token)
        if payload and payload.get("user_id"):
            return payload.get("user_id")
        return None

    @staticmethod
    def get_token_type(token: str) -> Optional[str]:
        """Get token type"""
        payload = JWTManager.decode_token(token)
        if payload:
            return payload.get("type")
        return None


# Create instances for easy import
security_utils = SecurityUtils()
jwt_manager = JWTManager()