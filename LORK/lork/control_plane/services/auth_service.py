"""
Authentication & Authorization service.
Handles API key lifecycle and JWT token validation.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lork.config import get_settings
from lork.models import APIKey, Organization
from lork.schemas import APIKeyCreate, APIKeyResponse
from lork.observability.logging import get_logger

log = get_logger(__name__)

KEY_PREFIX_LENGTH = 8
KEY_ENTROPY_BYTES = 32


class AuthError(Exception):
    pass


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._settings = get_settings()

    async def create_api_key(self, organization_id: str, data: APIKeyCreate) -> APIKeyResponse:
        raw_key = self._generate_raw_key()
        prefix = raw_key[:KEY_PREFIX_LENGTH]
        key_hash = self._hash_key(raw_key)

        expires_at = None
        if data.expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=data.expires_in_days)

        api_key = APIKey(
            organization_id=organization_id,
            name=data.name,
            key_hash=key_hash,
            prefix=prefix,
            scopes=data.scopes,
            expires_at=expires_at,
        )

        self._db.add(api_key)
        await self._db.flush()

        log.info("auth.api_key.created", key_id=api_key.id)

        return APIKeyResponse(
            id=api_key.id,
            name=api_key.name,
            prefix=prefix,
            scopes=api_key.scopes,
            expires_at=expires_at,
            created_at=api_key.created_at,
            key=raw_key,
        )

    async def validate_api_key(self, raw_key: str):
        if len(raw_key) < KEY_PREFIX_LENGTH:
            return None

        prefix = raw_key[:KEY_PREFIX_LENGTH]

        result = await self._db.execute(
            select(APIKey).where(APIKey.prefix == prefix, APIKey.is_active.is_(True))
        )

        api_key = result.scalar_one_or_none()
        if api_key is None:
            return None

        expected_hash = self._hash_key(raw_key)
        if not hmac.compare_digest(api_key.key_hash, expected_hash):
            return None

        return api_key

    def create_access_token(self, subject: str, scopes: list[str]) -> str:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=self._settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )

        payload = {
            "sub": subject,
            "exp": expire,
            "scopes": scopes,
            "type": "access",
        }

        return jwt.encode(
            payload,
            self._settings.SECRET_KEY,
            algorithm=self._settings.JWT_ALGORITHM,
        )

    def decode_token(self, token: str):
        try:
            return jwt.decode(
                token,
                self._settings.SECRET_KEY,
                algorithms=[self._settings.JWT_ALGORITHM],
            )
        except JWTError as exc:
            raise AuthError(str(exc))

    @staticmethod
    def _generate_raw_key() -> str:
        return f"lork_{secrets.token_urlsafe(KEY_ENTROPY_BYTES)}"

    @staticmethod
    def _hash_key(raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode()).hexdigest()
