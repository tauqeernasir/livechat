"""Simple credential encryption using Fernet symmetric encryption.

In production, consider replacing with KMS-backed envelope encryption.
"""

import base64
import hashlib
from typing import Optional

from cryptography.fernet import Fernet

from app.core.config import settings
from app.core.logging import logger


def _get_fernet() -> Fernet:
    """Derive a Fernet key from the app SECRET_KEY."""
    # Fernet requires a 32-byte url-safe base64-encoded key.
    raw = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    key = base64.urlsafe_b64encode(raw)
    return Fernet(key)


def encrypt_credential(plaintext: str) -> str:
    """Encrypt a credential string. Returns base64-encoded ciphertext."""
    if not plaintext:
        return ""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_credential(ciphertext: str) -> Optional[str]:
    """Decrypt a credential string. Returns None on failure."""
    if not ciphertext:
        return None
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except Exception:
        logger.error("credential_decryption_failed")
        return None
