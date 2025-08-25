from cryptography.fernet import Fernet
from django.conf import settings
import base64
import logging

logger = logging.getLogger(__name__)


def get_encryption_key():
    """获取加密密钥"""
    key = getattr(settings, 'ENCRYPTION_KEY', None)
    if not key:
        raise ValueError("ENCRYPTION_KEY not set in settings")
    
    # 如果密钥不是有效的Fernet密钥格式，则生成新的
    try:
        if isinstance(key, str):
            key = key.encode()
        # 验证密钥格式
        Fernet(key)
        return key
    except Exception:
        logger.warning("Invalid ENCRYPTION_KEY format, generating new key")
        return Fernet.generate_key()


def encrypt_data(data: str) -> str:
    """加密数据"""
    if not data:
        return ""
    
    try:
        key = get_encryption_key()
        f = Fernet(key)
        encrypted_data = f.encrypt(data.encode())
        return base64.b64encode(encrypted_data).decode()
    except Exception as e:
        logger.error(f"Failed to encrypt data: {e}")
        raise ValueError("Encryption failed")


def decrypt_data(encrypted_data: str) -> str:
    """解密数据"""
    if not encrypted_data:
        return ""
    
    try:
        key = get_encryption_key()
        f = Fernet(key)
        decoded_data = base64.b64decode(encrypted_data.encode())
        decrypted_data = f.decrypt(decoded_data)
        return decrypted_data.decode()
    except Exception as e:
        logger.error(f"Failed to decrypt data: {e}")
        raise ValueError("Decryption failed")