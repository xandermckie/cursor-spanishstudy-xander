"""
Encryption utilities for user data at rest.

Uses Fernet (symmetric encryption with AES-128 CBC + HMAC) to encrypt
user JSON files and the email index.
"""

import base64
import hashlib
import json
import logging
import os
from functools import lru_cache
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

ENCRYPTION_VERSION = b"v1:"


def _derive_key_from_secret(secret: str) -> bytes:
    """Build a Fernet-compatible key from SECRET_KEY (stable across deploys)."""
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


@lru_cache(maxsize=1)
def get_encryption_key() -> bytes:
    """
    Load encryption key from ENCRYPTION_KEY, or derive from SECRET_KEY.

    Render's generateValue for ENCRYPTION_KEY is not Fernet-shaped; deriving
    from SECRET_KEY keeps production boots working when only SECRET_KEY is set.

    Returns:
        Fernet key as bytes

    Raises:
        ValueError: If no valid key source is available
    """
    key_str = os.environ.get("ENCRYPTION_KEY")
    if key_str:
        try:
            key = key_str.encode() if isinstance(key_str, str) else key_str
            Fernet(key)
            return key
        except Exception as exc:
            logger.warning(
                "ENCRYPTION_KEY invalid (%s); deriving from SECRET_KEY.", exc
            )

    secret = os.environ.get("SECRET_KEY", "").strip()
    if secret and secret != "dev-change-me":
        derived = _derive_key_from_secret(secret)
        Fernet(derived)
        return derived

    raise ValueError(
        "Set ENCRYPTION_KEY (Fernet.generate_key()) or SECRET_KEY for encryption. "
        "Generate: python -c \"from cryptography.fernet import Fernet; "
        "print(Fernet.generate_key().decode())\""
    )


def clear_encryption_key_cache() -> None:
    """Reset cached key so the next call re-reads environment."""
    get_encryption_key.cache_clear()


def encrypt_json(data: dict[str, Any]) -> bytes:
    """
    Serialize dict to JSON and encrypt it.
    
    Args:
        data: Dictionary to encrypt
        
    Returns:
        Encrypted bytes with version prefix
        
    Raises:
        ValueError: If encryption key is invalid
    """
    key = get_encryption_key()
    fernet = Fernet(key)
    
    json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    encrypted = fernet.encrypt(json_bytes)
    
    return ENCRYPTION_VERSION + encrypted


def decrypt_json(encrypted: bytes) -> dict[str, Any]:
    """
    Decrypt bytes and parse as JSON.
    
    Args:
        encrypted: Encrypted bytes (with or without version prefix)
        
    Returns:
        Decrypted dictionary
        
    Raises:
        InvalidToken: If decryption fails (wrong key or corrupted data)
        ValueError: If decrypted data is not valid JSON
    """
    key = get_encryption_key()
    fernet = Fernet(key)
    
    if encrypted.startswith(ENCRYPTION_VERSION):
        encrypted = encrypted[len(ENCRYPTION_VERSION):]
    
    try:
        decrypted_bytes = fernet.decrypt(encrypted)
        return json.loads(decrypted_bytes.decode("utf-8"))
    except InvalidToken:
        raise InvalidToken("Failed to decrypt data - invalid key or corrupted file")
    except json.JSONDecodeError as e:
        raise ValueError(f"Decrypted data is not valid JSON: {e}")


def is_encrypted(data: bytes) -> bool:
    """
    Check if data appears to be encrypted.
    
    Args:
        data: Raw file bytes
        
    Returns:
        True if data starts with version prefix or looks encrypted
    """
    if data.startswith(ENCRYPTION_VERSION):
        return True
    
    try:
        data.decode("utf-8")
        json.loads(data)
        return False
    except (UnicodeDecodeError, json.JSONDecodeError):
        return True
