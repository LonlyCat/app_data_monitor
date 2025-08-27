from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
import base64
import logging

logger = logging.getLogger(__name__)


def get_encryption_key():
    """获取并验证加密密钥"""
    key_str = getattr(settings, 'ENCRYPTION_KEY', None)
    if not key_str:
        raise ValueError(
            "ENCRYPTION_KEY is not set in your environment variables or settings. "
            "Please generate one using `python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'`"
        )
    
    try:
        key = key_str.encode()
        # The key must be a URL-safe base64-encoded 32-byte key.
        # Fernet's constructor will validate this.
        Fernet(key)
        return key
    except Exception as e:
        logger.error(f"Invalid ENCRYPTION_KEY: {e}")
        raise ValueError(
            "The provided ENCRYPTION_KEY is invalid. It must be a URL-safe base64-encoded 32-byte key."
        )


def encrypt_data(data: str) -> str:
    """Encrypts data using Fernet."""
    if not data:
        return ""
    
    try:
        key = get_encryption_key()
        f = Fernet(key)
        encrypted_token = f.encrypt(data.encode())
        # Fernet token is already bytes, just decode for storing in a text field.
        return encrypted_token.decode()
    except Exception as e:
        logger.error(f"Failed to encrypt data: {e}")
        raise ValueError("Encryption failed")


def decrypt_data(encrypted_data: str) -> str:
    """
    Decrypts data, handling both new (direct) and legacy (double-encoded) formats.
    """
    if not encrypted_data:
        return ""
    
    try:
        key = get_encryption_key()
        f = Fernet(key)

        # First, try to decrypt assuming the new, direct format.
        try:
            return f.decrypt(encrypted_data.encode()).decode()
        except InvalidToken:
            # If that fails, it might be the old, double-encoded format.
            logger.debug("Direct decryption failed, trying legacy format (double base64).")
            decoded_data = base64.b64decode(encrypted_data.encode())
            return f.decrypt(decoded_data).decode()

    except Exception as e:
        logger.error(f"Failed to decrypt data: {e}")
        # Add more context to the error.
        raise ValueError(
            f"Decryption failed. The credential may be corrupted or the ENCRYPTION_KEY may have changed. Error: {e}"
        )