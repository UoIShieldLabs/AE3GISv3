"""Password hashing and the random strings accounts hand out (stdlib only).

Hashes are scrypt, stored as ``scrypt$<n>$<r>$<p>$<salt b64>$<hash b64>`` so the
cost can be raised later without breaking existing rows: ``needs_rehash`` tells
a sign-in to upgrade one.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

_N, _R, _P = 2**14, 8, 1
_DKLEN = 32
# scrypt needs 128 * r * n bytes; give OpenSSL room above its 32 MiB default.
_MAXMEM = 64 * 1024 * 1024

# Join codes and temporary passwords avoid look-alike characters (0/O, 1/l/I)
# since they are read off a projector or typed from a note.
_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _scrypt(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=_DKLEN, maxmem=_MAXMEM
    )


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = _scrypt(password, salt, _N, _R, _P)
    return f"scrypt${_N}${_R}${_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
        if scheme != "scrypt":
            return False
        expected = base64.b64decode(digest)
        actual = _scrypt(password, base64.b64decode(salt), int(n), int(r), int(p))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def needs_rehash(stored: str) -> bool:
    return not stored.startswith(f"scrypt${_N}${_R}${_P}$")


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    """What a session row stores: a token is never kept in the clear."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _random_string(length: int) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


def new_join_code() -> str:
    """A class join code, e.g. ``kq7m-x3fa``."""
    raw = _random_string(8)
    return f"{raw[:4]}-{raw[4:]}"


def normalize_join_code(code: str) -> str:
    return "".join(ch for ch in code.lower() if ch.isalnum())


def new_temporary_password() -> str:
    return _random_string(10)
