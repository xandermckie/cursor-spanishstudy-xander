"""Tests for encryption utilities."""

import json
import os
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet, InvalidToken

import encryption


@pytest.fixture
def test_encryption_key():
    """Generate a test encryption key."""
    return Fernet.generate_key()


@pytest.fixture
def set_test_key(test_encryption_key):
    """Set test encryption key in environment."""
    with patch.dict(os.environ, {"ENCRYPTION_KEY": test_encryption_key.decode()}):
        yield test_encryption_key


def test_get_encryption_key_from_env(set_test_key):
    """Test loading encryption key from environment variable."""
    key = encryption.get_encryption_key()
    assert key == set_test_key
    assert isinstance(key, bytes)


def test_get_encryption_key_missing():
    """Test error when neither ENCRYPTION_KEY nor SECRET_KEY is usable."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="ENCRYPTION_KEY|SECRET_KEY"):
            encryption.get_encryption_key()


def test_get_encryption_key_derives_from_secret():
    """Invalid ENCRYPTION_KEY falls back to a Fernet key derived from SECRET_KEY."""
    with patch.dict(
        os.environ,
        {"ENCRYPTION_KEY": "not-fernet", "SECRET_KEY": "render-production-secret"},
        clear=True,
    ):
        key = encryption.get_encryption_key()
        Fernet(key)
        assert key == encryption._derive_key_from_secret("render-production-secret")


def test_get_encryption_key_invalid_without_secret():
    """Test error when ENCRYPTION_KEY invalid and SECRET_KEY missing."""
    with patch.dict(os.environ, {"ENCRYPTION_KEY": "invalid-key"}, clear=True):
        with pytest.raises(ValueError, match="ENCRYPTION_KEY|SECRET_KEY"):
            encryption.get_encryption_key()


def test_encrypt_decrypt_json_round_trip(set_test_key):
    """Test encrypting and decrypting JSON data."""
    test_data = {
        "email": "test@example.com",
        "password_hash": "hashed_password",
        "profile": {"avatar_ext": "jpg"},
        "phrasebook": ["hola", "adiós"],
        "user_stats": {"xp_total": 100, "level": 2},
    }
    
    encrypted = encryption.encrypt_json(test_data)
    
    assert isinstance(encrypted, bytes)
    assert encrypted.startswith(encryption.ENCRYPTION_VERSION)
    assert encrypted != json.dumps(test_data).encode()
    
    decrypted = encryption.decrypt_json(encrypted)
    
    assert decrypted == test_data
    assert isinstance(decrypted, dict)


def test_encrypt_json_with_unicode(set_test_key):
    """Test encrypting JSON with unicode characters."""
    test_data = {
        "phrases": ["¡Hola!", "¿Cómo estás?", "Años", "Niño"],
        "emoji": "🎉",
    }
    
    encrypted = encryption.encrypt_json(test_data)
    decrypted = encryption.decrypt_json(encrypted)
    
    assert decrypted == test_data


def test_decrypt_json_without_version_prefix(set_test_key):
    """Test decrypting data without version prefix (backward compatibility)."""
    test_data = {"key": "value"}
    key = encryption.get_encryption_key()
    fernet = Fernet(key)
    
    json_bytes = json.dumps(test_data).encode("utf-8")
    encrypted = fernet.encrypt(json_bytes)
    
    decrypted = encryption.decrypt_json(encrypted)
    assert decrypted == test_data


def test_decrypt_json_invalid_token():
    """Test error when decrypting with wrong key."""
    test_data = {"key": "value"}
    
    key1 = Fernet.generate_key()
    with patch.dict(os.environ, {"ENCRYPTION_KEY": key1.decode()}):
        encrypted = encryption.encrypt_json(test_data)
    
    key2 = Fernet.generate_key()
    with patch.dict(os.environ, {"ENCRYPTION_KEY": key2.decode()}):
        with pytest.raises(InvalidToken, match="Failed to decrypt data"):
            encryption.decrypt_json(encrypted)


def test_decrypt_json_corrupted_data(set_test_key):
    """Test error when decrypting corrupted data."""
    corrupted = b"v1:corrupted_data_that_is_not_valid_fernet"
    
    with pytest.raises(InvalidToken):
        encryption.decrypt_json(corrupted)


def test_decrypt_json_invalid_json(set_test_key):
    """Test error when decrypted data is not valid JSON."""
    key = encryption.get_encryption_key()
    fernet = Fernet(key)
    
    invalid_json = b"not valid json {{"
    encrypted = fernet.encrypt(invalid_json)
    
    with pytest.raises(ValueError, match="not valid JSON"):
        encryption.decrypt_json(encrypted)


def test_is_encrypted_with_version_prefix(set_test_key):
    """Test detecting encrypted data with version prefix."""
    test_data = {"key": "value"}
    encrypted = encryption.encrypt_json(test_data)
    
    assert encryption.is_encrypted(encrypted) is True


def test_is_encrypted_plaintext_json():
    """Test detecting plaintext JSON data."""
    plaintext = json.dumps({"key": "value"}).encode("utf-8")
    
    assert encryption.is_encrypted(plaintext) is False


def test_is_encrypted_binary_data():
    """Test detecting binary (non-JSON) data as encrypted."""
    binary_data = b"\xff\xfe\xfd\xfc\x00\x01\x02\x03"
    
    assert encryption.is_encrypted(binary_data) is True


def test_encrypt_empty_dict(set_test_key):
    """Test encrypting empty dictionary."""
    test_data = {}
    
    encrypted = encryption.encrypt_json(test_data)
    decrypted = encryption.decrypt_json(encrypted)
    
    assert decrypted == test_data


def test_encrypt_nested_dict(set_test_key):
    """Test encrypting deeply nested dictionary."""
    test_data = {
        "level1": {
            "level2": {
                "level3": {
                    "level4": ["value1", "value2"],
                },
            },
        },
    }
    
    encrypted = encryption.encrypt_json(test_data)
    decrypted = encryption.decrypt_json(encrypted)
    
    assert decrypted == test_data


def test_encrypt_large_data(set_test_key):
    """Test encrypting large data structure."""
    test_data = {
        "phrasebook": [f"phrase_{i}" for i in range(1000)],
        "weak_words": {f"word_{i}": i for i in range(500)},
        "user_stats": {"xp_total": 999999},
    }
    
    encrypted = encryption.encrypt_json(test_data)
    decrypted = encryption.decrypt_json(encrypted)
    
    assert decrypted == test_data
    assert len(decrypted["phrasebook"]) == 1000
    assert len(decrypted["weak_words"]) == 500
