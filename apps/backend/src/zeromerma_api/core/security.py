# apps/backend/src/zeromerma_api/core/security.py
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from zeromerma_api.core.settings import get_settings

# -------------------------------------------------------------------------
# JWT configuration (derived from settings)
# -------------------------------------------------------------------------
# IMPORTANT:
# - These are read once at import time (process start).
# - In production, AUTH_SECRET_KEY must be set to a strong value.
_settings = get_settings()
SECRET_KEY: str = _settings.auth_secret_key
ALGORITHM: str = _settings.auth_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES: int = _settings.auth_access_token_expires_minutes

# -------------------------------------------------------------------------
# Standard JWT claim names for application tokens
# -------------------------------------------------------------------------
JWT_CLAIM_SUBJECT = "sub"
JWT_CLAIM_ISSUED_AT = "iat"
JWT_CLAIM_EXPIRES_AT = "exp"
JWT_CLAIM_ROLE_CODE = "role_code"
JWT_CLAIM_BRANCH_ID = "branch_id"

# -------------------------------------------------------------------------
# Password hashing configuration (PBKDF2-HMAC-SHA256)
# -------------------------------------------------------------------------
PASSWORD_HASH_NAME = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 390_000
PASSWORD_SALT_BYTES = 16


class AuthTokenError(ValueError):
    """
    Raised when a JWT token is malformed, expired, or otherwise invalid.
    """


def _b64encode(raw: bytes) -> str:
    """
    Convert raw bytes to a URL-safe base64 string.
    """
    return base64.urlsafe_b64encode(raw).decode("utf-8")


def _b64decode(value: str) -> bytes:
    """
    Convert a URL-safe base64 string back to raw bytes.
    """
    return base64.urlsafe_b64decode(value.encode("utf-8"))


def _normalize_role_code_for_claim(role_code: str) -> str:
    """
    Normalize a role code before embedding it into a JWT.

    Current convention:
    - trim surrounding whitespace
    - uppercase for stability across routers/tests/UI callers
    """
    normalized = str(role_code).strip().upper()
    if not normalized:
        raise ValueError("role_code cannot be blank.")
    return normalized


def _normalize_branch_id_for_claim(branch_id: int) -> int:
    """
    Normalize and validate a branch id before embedding it into a JWT.
    """
    if isinstance(branch_id, bool):
        raise ValueError("branch_id must be an integer greater than zero.")

    normalized = int(branch_id)
    if normalized <= 0:
        raise ValueError("branch_id must be greater than zero.")

    return normalized


def build_standard_user_claims(
    *,
    role_code: str | None = None,
    branch_id: int | None = None,
) -> dict[str, object]:
    """
    Build the standard non-reserved JWT claims for an authenticated user.

    This helper exists so auth routers, tests, fixtures, and future clients
    can all use the same claim vocabulary.

    Returned claims may include:
    - role_code
    - branch_id
    """
    claims: dict[str, object] = {}

    if role_code is not None:
        claims[JWT_CLAIM_ROLE_CODE] = _normalize_role_code_for_claim(role_code)

    if branch_id is not None:
        claims[JWT_CLAIM_BRANCH_ID] = _normalize_branch_id_for_claim(branch_id)

    return claims


def hash_password(plain_password: str) -> str:
    """
    Hash a plain-text password using PBKDF2-HMAC-SHA256.

    Output format:
      pbkdf2_sha256$<iterations>$<salt_b64>$<hash_b64>
    """
    if not plain_password:
        raise ValueError("Password cannot be empty.")

    salt = secrets.token_bytes(PASSWORD_SALT_BYTES)

    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        plain_password.encode("utf-8"),
        salt,
        PASSWORD_HASH_ITERATIONS,
    )

    salt_b64 = _b64encode(salt)
    hash_b64 = _b64encode(derived_key)

    return f"{PASSWORD_HASH_NAME}${PASSWORD_HASH_ITERATIONS}${salt_b64}${hash_b64}"


def verify_password(plain_password: str, stored_hash: str | None) -> bool:
    """
    Verify a plain-text password against a stored PBKDF2 hash string.

    Returns:
      True if matches; False otherwise (including malformed stored hashes).
    """
    if not plain_password or not stored_hash:
        return False

    try:
        algorithm, iterations_str, salt_b64, hash_b64 = stored_hash.split("$", 3)
    except ValueError:
        return False

    if algorithm != PASSWORD_HASH_NAME:
        return False

    try:
        iterations = int(iterations_str)
        salt = _b64decode(salt_b64)
        expected_hash = _b64decode(hash_b64)
    except Exception:
        return False

    candidate_hash = hashlib.pbkdf2_hmac(
        "sha256",
        plain_password.encode("utf-8"),
        salt,
        iterations,
    )

    return hmac.compare_digest(candidate_hash, expected_hash)


def create_access_token(
    subject: str,
    *,
    extra_claims: dict[str, object] | None = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
      subject:
        Canonical user identifier stored in the `sub` claim (string).
      extra_claims:
        Optional additional claims to include (for example role_code,
        branch_id, or future user-context metadata).

    Returns:
      Encoded JWT as string.
    """
    now = datetime.now(tz=timezone.utc)
    payload: dict[str, object] = {
        JWT_CLAIM_SUBJECT: str(subject),
        JWT_CLAIM_ISSUED_AT: int(now.timestamp()),
        JWT_CLAIM_EXPIRES_AT: int(
            (now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()
        ),
    }

    if extra_claims:
        reserved_claims = {
            JWT_CLAIM_SUBJECT,
            JWT_CLAIM_ISSUED_AT,
            JWT_CLAIM_EXPIRES_AT,
        }
        for key in reserved_claims:
            if key in extra_claims:
                raise ValueError(f"extra_claims cannot override reserved claim '{key}'.")
        payload.update(extra_claims)

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_user_access_token(
    *,
    user_id: int | str,
    role_code: str | None = None,
    branch_id: int | None = None,
    extra_claims: dict[str, object] | None = None,
) -> str:
    """
    Create a standard application access token for a known user.

    This helper standardizes the most common authenticated-user token shape:
    - sub
    - optional role_code
    - optional branch_id

    Additional claims may still be appended, subject to the same reserved-claim
    protections enforced by `create_access_token()`.

    Compatibility:
    - If role_code/branch_id are omitted, the result is still a valid legacy
      subject-only token.
    """
    claims = build_standard_user_claims(
        role_code=role_code,
        branch_id=branch_id,
    )

    if extra_claims:
        claims.update(extra_claims)

    return create_access_token(
        subject=str(user_id),
        extra_claims=claims or None,
    )


def decode_access_token(token: str) -> dict[str, object]:
    """
    Decode and validate a JWT access token.

    Returns:
      The token payload as a dict.

    Raises:
      AuthTokenError for invalid/expired tokens.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if not isinstance(payload, dict):
            raise AuthTokenError("Invalid token payload type.")
        return payload
    except jwt.ExpiredSignatureError as e:
        raise AuthTokenError("Token expired.") from e
    except jwt.InvalidTokenError as e:
        raise AuthTokenError("Invalid token.") from e


def get_token_subject(token: str) -> str:
    """
    Convenience helper: decode the token and return only the `sub` claim.
    """
    payload = decode_access_token(token)

    subject = payload[JWT_CLAIM_SUBJECT]
    return str(subject)
