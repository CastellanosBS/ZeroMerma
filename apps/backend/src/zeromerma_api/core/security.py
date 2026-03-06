# apps/backend/src/zeromerma_api/core/security.py
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from zeromerma_api.core.settings import get_settings

# -------------------------------------------------------------------------
# Password hashing configuration
# -------------------------------------------------------------------------
# We use PBKDF2-HMAC-SHA256 from Python's standard library.
#
# Why this choice:
# - No extra hashing dependency required for the MVP.
# - Battle-tested primitive from the standard library.
# - Good enough for a learning-oriented backend if configured correctly.
#
# Later, in a more mature production setup, you may migrate to argon2 or bcrypt.
PASSWORD_HASH_NAME = "pbkdf2_sha256"

# Number of PBKDF2 iterations.
# Higher = slower for attackers, but also slower for login.
# This value is intentionally non-trivial for modern hardware.
PASSWORD_HASH_ITERATIONS = 390_000

# Salt length in bytes before base64 encoding.
# A per-password random salt prevents rainbow-table reuse.
PASSWORD_SALT_BYTES = 16


class AuthTokenError(ValueError):
    """
    Raised when a JWT token is malformed, expired, or otherwise invalid.

    Why define our own exception:
    - Keeps auth-specific errors explicit.
    - Lets routers/services translate this into 401 consistently later.
    """


def _utc_now() -> datetime:
    """
    Return the current UTC time as a timezone-aware datetime.

    Why this helper exists:
    - JWT claims like `exp`, `iat`, and `nbf` are time-based.
    - Using timezone-aware UTC avoids ambiguous local time handling.
    """
    return datetime.now(timezone.utc)


def _b64encode(raw: bytes) -> str:
    """
    Convert raw bytes to a URL-safe base64 string.

    Why this helper exists:
    - We need to store salt and hash as text inside the database.
    - URL-safe base64 avoids weird characters and is easy to transport.
    """
    return base64.urlsafe_b64encode(raw).decode("utf-8")


def _b64decode(value: str) -> bytes:
    """
    Convert a URL-safe base64 string back to raw bytes.
    """
    return base64.urlsafe_b64decode(value.encode("utf-8"))


def hash_password(plain_password: str) -> str:
    """
    Hash a plain-text password using PBKDF2-HMAC-SHA256.

    Output format:
      pbkdf2_sha256$<iterations>$<salt_b64>$<hash_b64>

    Why this string format:
    - Self-describing: we can see algorithm and iteration count.
    - Flexible for future migrations.
    - Easy to verify later without extra metadata columns.

    Parameters:
    - plain_password: the raw password entered by the user.

    Returns:
    - A structured password-hash string safe to store in the DB.

    Important:
    - We never store plain passwords.
    - We always generate a random salt per password.
    """
    if not plain_password:
        raise ValueError("Password cannot be empty.")

    # Generate a cryptographically secure random salt.
    salt = secrets.token_bytes(PASSWORD_SALT_BYTES)

    # Derive a strong hash from the password + salt.
    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        plain_password.encode("utf-8"),
        salt,
        PASSWORD_HASH_ITERATIONS,
    )

    # Convert binary pieces to text so they can be stored in a VARCHAR/TEXT column.
    salt_b64 = _b64encode(salt)
    hash_b64 = _b64encode(derived_key)

    # Return a single portable string that contains all verification metadata.
    return f"{PASSWORD_HASH_NAME}${PASSWORD_HASH_ITERATIONS}${salt_b64}${hash_b64}"


def verify_password(plain_password: str, stored_hash: str | None) -> bool:
    """
    Verify a plain-text password against a stored PBKDF2 hash string.

    Parameters:
    - plain_password: password provided by the user at login.
    - stored_hash: hash stored in the database.

    Returns:
    - True if the password matches.
    - False if it does not match or if the stored value is malformed.

    Security notes:
    - We use `hmac.compare_digest()` to reduce timing-attack leakage.
    - We do not raise on malformed stored data; returning False is safer for auth flow.
    """
    if not plain_password or not stored_hash:
        return False

    try:
        algorithm, iterations_str, salt_b64, hash_b64 = stored_hash.split("$", 3)
    except ValueError:
        # Stored format is invalid.
        return False

    if algorithm != PASSWORD_HASH_NAME:
        # Unknown hash scheme for this verifier.
        return False

    try:
        iterations = int(iterations_str)
        salt = _b64decode(salt_b64)
        expected_hash = _b64decode(hash_b64)
    except Exception:
        # Any decoding/parsing problem means the stored value is not usable.
        return False

    # Re-derive the hash using the same parameters.
    candidate_hash = hashlib.pbkdf2_hmac(
        "sha256",
        plain_password.encode("utf-8"),
        salt,
        iterations,
    )

    # Constant-time comparison to avoid leaking information through timing.
    return hmac.compare_digest(candidate_hash, expected_hash)


def create_access_token(
    *,
    subject: str,
    extra_claims: dict[str, Any] | None = None,
    expires_minutes: int | None = None,
) -> str:
    """
    Create a signed JWT access token.

    Parameters:
    - subject: principal identity for the token.
      For this project, this will typically be the user id as a string.
    - extra_claims: optional extra claims (e.g., role, email, branch_id).
    - expires_minutes: optional override for token lifetime.
      If omitted, we use the default from settings.

    Standard claims we set:
    - sub: subject (who the token represents)
    - iat: issued-at time
    - nbf: not-before time
    - exp: expiration time

    Returns:
    - A JWT string signed with the app's configured secret.
    """
    settings = get_settings()

    now = _utc_now()
    ttl_minutes = (
        expires_minutes
        if expires_minutes is not None
        else settings.auth_access_token_expires_minutes
    )
    expires_at = now + timedelta(minutes=ttl_minutes)

    # Start with the standard claims.
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }

    # Merge optional application-specific claims.
    # Example later:
    #   {"role": "ADMIN", "email": "admin@zeromerma.local", "branch_id": 1}
    if extra_claims:
        payload.update(extra_claims)

    # Sign the token using the configured secret and algorithm.
    token = jwt.encode(
        payload,
        settings.auth_secret_key,
        algorithm=settings.auth_algorithm,
    )

    # Depending on library version, jwt.encode may return str already.
    # We explicitly return it as str for a stable contract.
    return str(token)


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT access token.

    What this does:
    - Verifies signature
    - Verifies expiration (`exp`)
    - Verifies not-before (`nbf`) if present
    - Returns the decoded claims if valid

    Parameters:
    - token: raw JWT string from the Authorization header.

    Returns:
    - A dict of claims if the token is valid.

    Raises:
    - AuthTokenError if token is missing, invalid, expired, or has no usable subject.
    """
    if not token:
        raise AuthTokenError("Missing token.")

    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.auth_secret_key,
            algorithms=[settings.auth_algorithm],
        )
    except jwt.InvalidTokenError as exc:
        # Collapse library-specific token errors into our domain-specific exception.
        raise AuthTokenError("Invalid or expired token.") from exc

    # `sub` is the canonical principal identifier in JWT.
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        raise AuthTokenError("Token subject is missing or invalid.")

    return payload


def get_token_subject(token: str) -> str:
    """
    Convenience helper: decode the token and return only the `sub` claim.

    Why this helper exists:
    - Many auth dependencies only need the principal id, not the full payload.
    - It keeps later router/dependency code cleaner.
    """
    payload = decode_access_token(token)

    subject = payload["sub"]
    # At this point decode_access_token() already guaranteed it is a non-empty str.
    return str(subject)
