"""Encryption utilities for secure storage of sensitive verification data."""
from __future__ import annotations

import logging
import hashlib
import base64
from typing import Optional

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
except ImportError:  # pragma: no cover
    Fernet = None
    hashes = None
    PBKDF2 = None

from django.conf import settings

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Raised when encryption/decryption operations fail."""
    pass


class DataEncryptor:
    """
    Encrypt and decrypt sensitive verification data.
    
    Uses Fernet (symmetric encryption) with a key derived from Django SECRET_KEY.
    """
    
    def __init__(self):
        """Initialize the encryptor."""
        if Fernet is None:
            raise ImportError(
                "cryptography is required for data encryption. "
                "Install with: pip install cryptography"
            )
        
        self._cipher = None
    
    @property
    def cipher(self):
        """Lazy-load the cipher with derived key."""
        if self._cipher is None:
            self._cipher = Fernet(self._derive_key())
        return self._cipher
    
    def _derive_key(self) -> bytes:
        """
        Derive encryption key from Django SECRET_KEY.
        
        Uses PBKDF2 to derive a Fernet-compatible key.
        """
        # Use Django's SECRET_KEY as the password
        password = settings.SECRET_KEY.encode('utf-8')
        
        # Use a fixed salt (in production, consider using a configurable salt)
        salt = b'trabaholink_philsys_verification_salt_v1'
        
        # Derive key using PBKDF2
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        
        return key
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string.
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            Base64-encoded encrypted string
        """
        try:
            if not plaintext:
                return ""
            
            plaintext_bytes = plaintext.encode('utf-8')
            encrypted_bytes = self.cipher.encrypt(plaintext_bytes)
            encrypted_str = base64.urlsafe_b64encode(encrypted_bytes).decode('utf-8')
            
            return encrypted_str
            
        except Exception as e:
            logger.exception(f"Encryption failed: {e}")
            raise EncryptionError(f"Failed to encrypt data: {str(e)}")
    
    def decrypt(self, encrypted_str: str) -> str:
        """
        Decrypt encrypted string.
        
        Args:
            encrypted_str: Base64-encoded encrypted string
            
        Returns:
            Decrypted plaintext string
        """
        try:
            if not encrypted_str:
                return ""
            
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_str.encode('utf-8'))
            plaintext_bytes = self.cipher.decrypt(encrypted_bytes)
            plaintext = plaintext_bytes.decode('utf-8')
            
            return plaintext
            
        except Exception as e:
            logger.exception(f"Decryption failed: {e}")
            raise EncryptionError(f"Failed to decrypt data: {str(e)}")
    
    def hash_data(self, data: str) -> str:
        """
        Create a SHA-256 hash of data for indexing/comparison.
        
        Args:
            data: String to hash
            
        Returns:
            Hexadecimal hash string
        """
        if not data:
            return ""
        
        hash_obj = hashlib.sha256(data.encode('utf-8'))
        return hash_obj.hexdigest()
    
    def mask_pcn(self, pcn: str) -> str:
        """
        Mask PhilSys Card Number for display purposes.
        
        Example: 1234-5678-9012-3456 -> 1234-****-****-3456
        
        Args:
            pcn: PhilSys Card Number
            
        Returns:
            Masked PCN string
        """
        if not pcn:
            return ""
        
        # Remove any existing dashes
        pcn_clean = pcn.replace('-', '').replace(' ', '')
        
        if len(pcn_clean) != 16:
            # If not standard format, mask middle portion
            if len(pcn_clean) <= 8:
                return pcn_clean[:2] + '*' * (len(pcn_clean) - 4) + pcn_clean[-2:]
            else:
                return pcn_clean[:4] + '*' * (len(pcn_clean) - 8) + pcn_clean[-4:]
        
        # Standard PhilSys format: 0000-0000-0000-0000
        return f"{pcn_clean[:4]}-****-****-{pcn_clean[-4:]}"


# Global encryptor instance
_encryptor: Optional[DataEncryptor] = None


def get_encryptor() -> DataEncryptor:
    """Get or create the global encryptor instance."""
    global _encryptor
    if _encryptor is None:
        _encryptor = DataEncryptor()
    return _encryptor


def encrypt_qr_payload(qr_data: str) -> str:
    """Convenience function to encrypt QR payload."""
    return get_encryptor().encrypt(qr_data)


def decrypt_qr_payload(encrypted_data: str) -> str:
    """Convenience function to decrypt QR payload."""
    return get_encryptor().decrypt(encrypted_data)


def hash_qr_payload(qr_data: str) -> str:
    """Convenience function to hash QR payload."""
    return get_encryptor().hash_data(qr_data)


def mask_pcn(pcn: str) -> str:
    """Convenience function to mask PCN."""
    return get_encryptor().mask_pcn(pcn)
