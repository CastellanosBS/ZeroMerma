from __future__ import annotations

import hashlib
import hmac
import secrets

PBKDF2_ALGORITHM = "sha256"
PBKDF2_ITERATIONS = 600_000


class PasswordHasher:
    def hash_password(self, password: str) -> str:
        salt = secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac(
            PBKDF2_ALGORITHM, password.encode(), salt.encode(), PBKDF2_ITERATIONS
        )
        return f"pbkdf2_{PBKDF2_ALGORITHM}${PBKDF2_ITERATIONS}${salt}${digest.hex()}"

    def verify_password(self, password: str, password_hash: str) -> bool:
        try:
            algorithm, iterations, salt, expected_digest = password_hash.split("$", maxsplit=3)
            iteration_count = int(iterations)
        except ValueError:
            return False
        if algorithm != f"pbkdf2_{PBKDF2_ALGORITHM}" or iteration_count != PBKDF2_ITERATIONS:
            return False
        digest = hashlib.pbkdf2_hmac(
            PBKDF2_ALGORITHM, password.encode(), salt.encode(), iteration_count
        )
        return hmac.compare_digest(digest.hex(), expected_digest)


def secret_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def csrf_for_credential(credential: str) -> str:
    return hmac.new(credential.encode("ascii"), b"zeromerma-csrf-v1", hashlib.sha256).hexdigest()


def new_session_secrets() -> tuple[str, str]:
    credential = secrets.token_urlsafe(32)
    return credential, csrf_for_credential(credential)
