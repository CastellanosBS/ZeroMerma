from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from zeromerma_api.core.config import ApiSettings, get_settings
from zeromerma_api.modules.identity.domain.exceptions import AuthenticationError

PBKDF2_ALGORITHM = "sha256"
PBKDF2_ITERATIONS = 600_000


def _urlsafe_b64encode(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")


def _urlsafe_b64decode(payload: str) -> bytes:
    padding = "=" * (-len(payload) % 4)
    return base64.urlsafe_b64decode(payload + padding)


class PasswordHasher:
    def hash_password(self, password: str) -> str:
        salt = secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac(
            PBKDF2_ALGORITHM,
            password.encode("utf-8"),
            salt.encode("utf-8"),
            PBKDF2_ITERATIONS,
        )
        return (
            f"pbkdf2_{PBKDF2_ALGORITHM}$"
            f"{PBKDF2_ITERATIONS}$"
            f"{salt}$"
            f"{digest.hex()}"
        )

    def verify_password(self, password: str, password_hash: str) -> bool:
        try:
            algorithm, iterations, salt, expected_digest = password_hash.split("$", maxsplit=3)
        except ValueError:
            return False

        if algorithm != f"pbkdf2_{PBKDF2_ALGORITHM}":
            return False

        digest = hashlib.pbkdf2_hmac(
            PBKDF2_ALGORITHM,
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        )
        return hmac.compare_digest(digest.hex(), expected_digest)


class TokenService:
    def __init__(self, settings: ApiSettings | None = None) -> None:
        resolved_settings = settings or get_settings()
        self._secret = resolved_settings.auth_token_secret.encode("utf-8")
        self._ttl_minutes = resolved_settings.auth_token_ttl_minutes

    def issue_access_token(self, user_id: UUID) -> str:
        expires_at = datetime.now(tz=UTC) + timedelta(minutes=self._ttl_minutes)
        payload = {"sub": str(user_id), "exp": int(expires_at.timestamp())}
        payload_segment = _urlsafe_b64encode(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        )
        signature_segment = _urlsafe_b64encode(
            hmac.new(self._secret, payload_segment.encode("utf-8"), hashlib.sha256).digest()
        )
        return f"{payload_segment}.{signature_segment}"

    def read_user_id(self, token: str) -> UUID:
        try:
            payload_segment, signature_segment = token.split(".", maxsplit=1)
        except ValueError as error:
            raise AuthenticationError("Invalid bearer token.") from error

        expected_signature = _urlsafe_b64encode(
            hmac.new(self._secret, payload_segment.encode("utf-8"), hashlib.sha256).digest()
        )
        if not hmac.compare_digest(expected_signature, signature_segment):
            raise AuthenticationError("Invalid bearer token.")

        try:
            payload = json.loads(_urlsafe_b64decode(payload_segment))
            expires_at = int(payload["exp"])
            user_id = UUID(str(payload["sub"]))
        except (KeyError, ValueError, TypeError, json.JSONDecodeError) as error:
            raise AuthenticationError("Invalid bearer token.") from error

        if expires_at < int(datetime.now(tz=UTC).timestamp()):
            raise AuthenticationError("Bearer token has expired.")

        return user_id
