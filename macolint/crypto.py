"""Cryptography utilities for end-to-end encryption."""

import os
import base64
from typing import Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def derive_key(passphrase: str, salt: bytes, iterations: int = 200_000) -> bytes:
    """
    Derive an encryption key from a passphrase using PBKDF2.
    
    Args:
        passphrase: User-provided passphrase
        salt: Random salt (16 bytes recommended)
        iterations: Number of PBKDF2 iterations (default: 200,000)
    
    Returns:
        32-byte encryption key suitable for AES-256
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
    )
    return kdf.derive(passphrase.encode())


def encrypt(plaintext: bytes, key: bytes) -> Tuple[bytes, bytes]:
    """
    Encrypt plaintext using AES-GCM.
    
    Args:
        plaintext: Data to encrypt
        key: 32-byte encryption key
    
    Returns:
        Tuple of (ciphertext_with_tag, nonce)
    """
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 12 bytes for GCM
    ct = aesgcm.encrypt(nonce, plaintext, None)
    return ct, nonce


def decrypt(ciphertext: bytes, nonce: bytes, key: bytes) -> bytes:
    """
    Decrypt ciphertext using AES-GCM.
    
    Args:
        ciphertext: Encrypted data (includes authentication tag)
        nonce: Nonce used during encryption
        key: 32-byte encryption key
    
    Returns:
        Decrypted plaintext
    
    Raises:
        cryptography.exceptions.InvalidTag: If decryption fails (wrong key or corrupted data)
    """
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)


def gen_salt() -> bytes:
    """
    Generate a random salt for key derivation.
    
    Returns:
        16-byte random salt
    """
    return os.urandom(16)


def b64(x: bytes) -> str:
    """
    Encode bytes to base64 string.
    
    Args:
        x: Bytes to encode
    
    Returns:
        Base64-encoded string
    """
    return base64.b64encode(x).decode()


def ub64(s: str) -> bytes:
    """
    Decode base64 string to bytes.
    
    Args:
        s: Base64-encoded string
    
    Returns:
        Decoded bytes
    """
    return base64.b64decode(s.encode())

