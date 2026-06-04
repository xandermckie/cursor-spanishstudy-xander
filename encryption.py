"""
Encryption utilities for user data at rest.

Uses Fernet (symmetric encryption with AES-128 CBC + HMAC) to encrypt
user JSON files and the email index.
"""

import json
import logging
import os
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

ENCRYPTION_VERSION = b"v1:"


def get_encryption_key() -> bytes:
    """
    Load encryption key from environment variable.
    
    Returns:
        Fernet key as bytes
        
    Raises:
        ValueError: If ENCRYPTION_KEY is not set or invalid
    """
    key_str = os.environ.get("ENCRYPTION_KEY")
    
    if not key_str:
        raise ValueError(
            "ENCRYPTION_KEY environment variable not set. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\""
        )
    
    try:
        key = key_str.encode() if isinstance(key_str, str) else key_str
        Fernet(key)
        return key
    except Exception as e:
        raise ValueError(f"Invalid ENCRYPTION_KEY format: {e}")


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
