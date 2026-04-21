import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_ph = PasswordHasher()


def generate_api_key() -> str:
    return secrets.token_hex(32)  # 64-char hex string


def hash_api_key(api_key: str) -> str:
    return _ph.hash(api_key)


def verify_api_key(api_key: str, stored_hash: str) -> bool:
    try:
        return _ph.verify(stored_hash, api_key)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
