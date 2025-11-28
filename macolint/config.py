"""Configuration and key management for Macolint."""

import os
import keyring
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64


SERVICE_NAME = "macolint"
KEY_NAME = "master_key"
CONFIG_DIR = Path.home() / ".macolint"
DB_PATH = CONFIG_DIR / "snippets.db"
KEYRING_FALLBACK_FILE = CONFIG_DIR / "key.enc"


def ensure_config_dir():
    """Ensure the configuration directory exists."""
    CONFIG_DIR.mkdir(exist_ok=True, mode=0o700)


def generate_master_key() -> bytes:
    """Generate a new master encryption key."""
    return Fernet.generate_key()


def get_master_key() -> bytes:
    """
    Get the master encryption key from secure storage.
    Creates a new key if one doesn't exist.
    """
    ensure_config_dir()
    
    # Try to get key from keyring first
    try:
        stored_key = keyring.get_password(SERVICE_NAME, KEY_NAME)
        if stored_key:
            return stored_key.encode()
    except Exception:
        pass
    
    # If not in keyring, try fallback file
    if KEYRING_FALLBACK_FILE.exists():
        try:
            with open(KEYRING_FALLBACK_FILE, "rb") as f:
                encrypted_key = f.read()
            # For MVP, we'll use a simple approach: store base64 encoded key
            # In production, this should be encrypted with a user passphrase
            return base64.b64decode(encrypted_key)
        except Exception:
            pass
    
    # Generate new key if none exists
    new_key = generate_master_key()
    save_master_key(new_key)
    return new_key


def save_master_key(key: bytes):
    """Save the master key to secure storage."""
    ensure_config_dir()
    
    # Try to save to keyring first
    try:
        keyring.set_password(SERVICE_NAME, KEY_NAME, key.decode())
        return
    except Exception:
        pass
    
    # Fallback to encrypted file
    try:
        # For MVP, store as base64 encoded
        # In production, encrypt with user passphrase
        with open(KEYRING_FALLBACK_FILE, "wb") as f:
            f.write(base64.b64encode(key))
        KEYRING_FALLBACK_FILE.chmod(0o600)
    except Exception as e:
        raise RuntimeError(f"Failed to save master key: {e}")


def get_fernet() -> Fernet:
    """Get a Fernet instance with the master key."""
    key = get_master_key()
    return Fernet(key)


def get_db_path() -> Path:
    """Get the database path."""
    ensure_config_dir()
    return DB_PATH

