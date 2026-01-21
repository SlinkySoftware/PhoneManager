# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

"""Encryption utilities for sensitive data storage.

Provides reversible encryption for passwords and other sensitive fields
using Fernet symmetric encryption (AES 128 CBC with HMAC).
"""

import base64
import logging
import os
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .config import config

logger = logging.getLogger(__name__)


class EncryptionManager:
    """Manages encryption and decryption of sensitive data."""
    
    _instance = None
    _cipher = None
    
    def __new__(cls):
        """Singleton pattern to ensure single cipher instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_cipher()
        return cls._instance
    
    def _initialize_cipher(self):
        """Initialize the Fernet cipher with key from config."""
        # Get encryption key from config or environment
        encryption_key = config.get(
            'ENCRYPTION_KEY',
            default=None,
            env_var='ENCRYPTION_KEY'
        )
        
        if not encryption_key:
            # Generate a default key for development (NOT FOR PRODUCTION)
            logger.warning(
                "No ENCRYPTION_KEY found in config.yaml or environment. "
                "Using default key. THIS IS NOT SECURE FOR PRODUCTION!"
            )
            encryption_key = "default-insecure-key-change-in-production"
        
        # Derive a proper Fernet key from the provided key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'phonemanager-salt',  # Static salt (could be in config too)
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(encryption_key.encode()))
        self._cipher = Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext string.
        
        Args:
            plaintext: The string to encrypt
            
        Returns:
            Base64-encoded encrypted string
        """
        if not plaintext:
            return plaintext
        
        try:
            encrypted_bytes = self._cipher.encrypt(plaintext.encode('utf-8'))
            return encrypted_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise
    
    def decrypt(self, encrypted: str) -> str:
        """Decrypt an encrypted string.
        
        Args:
            encrypted: Base64-encoded encrypted string
            
        Returns:
            Decrypted plaintext string
        """
        if not encrypted:
            return encrypted
        
        try:
            decrypted_bytes = self._cipher.decrypt(encrypted.encode('utf-8'))
            return decrypted_bytes.decode('utf-8')
        except InvalidToken:
            # Data might not be encrypted (legacy data)
            logger.warning(f"Failed to decrypt data - may be unencrypted legacy data")
            return encrypted
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise


# Global encryption manager instance
encryption_manager = EncryptionManager()


def encrypt_password(password: str) -> str:
    """Convenience function to encrypt a password.
    
    Args:
        password: Plaintext password
        
    Returns:
        Encrypted password string
    """
    return encryption_manager.encrypt(password)


def decrypt_password(encrypted_password: str) -> str:
    """Convenience function to decrypt a password.
    
    Args:
        encrypted_password: Encrypted password string
        
    Returns:
        Plaintext password
    """
    return encryption_manager.decrypt(encrypted_password)
