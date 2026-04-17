from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from app.core.config import settings

PASSWORD_ALGORITHM = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 210_000
PASSWORD_SALT_BYTES = 16


class TokenError(ValueError):
    """Raised when access token payload is invalid or expired."""


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(PASSWORD_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    )
    return (
        f"{PASSWORD_ALGORITHM}${PASSWORD_ITERATIONS}$"
        f"{_b64url_encode(salt)}${_b64url_encode(digest)}"
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, digest_text = password_hash.split("$")
        if algorithm != PASSWORD_ALGORITHM:
            return False
        iterations = int(iterations_text)
        salt = _b64url_decode(salt_text)
        expected_digest = _b64url_decode(digest_text)
    except Exception:
        return False

    computed_digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    return hmac.compare_digest(computed_digest, expected_digest)


def create_access_token(user_id: str, email: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {
        "sub": user_id,
        "email": email,
        "iat": now,
        "exp": now + settings.AUTH_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }

    header_segment = _b64url_encode(
        json.dumps(header, separators=(",", ":")).encode("utf-8")
    )
    payload_segment = _b64url_encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    )
    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    signature = hmac.new(
        settings.AUTH_JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256
    ).digest()
    return f"{header_segment}.{payload_segment}.{_b64url_encode(signature)}"


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        header_segment, payload_segment, signature_segment = token.split(".")
    except ValueError as exc:
        raise TokenError("Token format is invalid") from exc

    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    expected_signature = hmac.new(
        settings.AUTH_JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256
    ).digest()

    try:
        received_signature = _b64url_decode(signature_segment)
    except Exception as exc:
        raise TokenError("Token signature encoding is invalid") from exc

    if not hmac.compare_digest(received_signature, expected_signature):
        raise TokenError("Token signature is invalid")

    try:
        payload_raw = _b64url_decode(payload_segment)
        payload = json.loads(payload_raw)
    except Exception as exc:
        raise TokenError("Token payload is invalid") from exc

    if not isinstance(payload, dict):
        raise TokenError("Token payload type is invalid")

    exp = payload.get("exp")
    if not isinstance(exp, int):
        raise TokenError("Token expiration is invalid")
    if exp < int(time.time()):
        raise TokenError("Token has expired")

    sub = payload.get("sub")
    if not isinstance(sub, str) or not sub:
        raise TokenError("Token subject is invalid")

    email = payload.get("email")
    if not isinstance(email, str) or not email:
        raise TokenError("Token email is invalid")

    return payload
