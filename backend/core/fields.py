# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

"""Custom Django model fields for encrypted data storage."""

from django.db import models
from .encryption import encrypt_password, decrypt_password


class EncryptedCharField(models.CharField):
    """CharField that automatically encrypts/decrypts data on save/load.
    
    Stores encrypted data in the database but provides plaintext access
    in Python code. Transparent to application logic.
    """
    
    description = "Encrypted text field"
    
    def from_db_value(self, value, expression, connection):
        """Convert from database (encrypted) to Python (plaintext)."""
        if value is None:
            return value
        return decrypt_password(value)
    
    def get_prep_value(self, value):
        """Convert from Python (plaintext) to database (encrypted)."""
        if value is None or value == '':
            return value
        # Encrypt the value before storing
        return encrypt_password(value)
    
    def to_python(self, value):
        """Convert to Python representation (decrypted)."""
        if isinstance(value, str) or value is None:
            return value
        return str(value)
