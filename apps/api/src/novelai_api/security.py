"""Only server-generated, 256-bit random opaque credentials are accepted."""

import hashlib
import secrets


SESSION_COOKIE = "__Host-nai_session"
SESSION_LIFETIME_SECONDS = 30 * 24 * 60 * 60


def new_secret() -> str:
    return secrets.token_urlsafe(32)


def digest_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()
