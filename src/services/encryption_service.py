"""
Encryption service for protecting PII (Personal Identifiable Information).

This module provides AES-256-GCM encryption for sensitive data fields
in the database, ensuring GDPR compliance and data protection.
"""

import base64
import os
import json
from typing import Any, Dict, Optional, Union
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

from src.config import settings

logger = logging.getLogger(__name__)


class EncryptionService:
    """Service for encrypting and decrypting PII data."""
    
    def __init__(self):
        """Initialize encryption service with key derivation."""
        self._master_key = self._get_or_create_master_key()
        self._salt = self._get_or_create_salt()
        self._key = self._derive_key()
        
    def _get_or_create_master_key(self) -> bytes:
        """Get or create master encryption key from environment."""
        master_key = os.environ.get('ENCRYPTION_MASTER_KEY')
        
        if not master_key:
            if settings.environment == "production":
                raise ValueError("ENCRYPTION_MASTER_KEY must be set in production")
            else:
                # Generate a test key for development
                master_key = base64.b64encode(os.urandom(32)).decode('utf-8')
                logger.warning("Using generated encryption key for development")
                
        return base64.b64decode(master_key.encode('utf-8'))
    
    def _get_or_create_salt(self) -> bytes:
        """Get or create salt for key derivation."""
        salt = os.environ.get('ENCRYPTION_SALT')
        
        if not salt:
            if settings.environment == "production":
                raise ValueError("ENCRYPTION_SALT must be set in production")
            else:
                # Generate a test salt for development
                salt = base64.b64encode(os.urandom(16)).decode('utf-8')
                logger.warning("Using generated salt for development")
                
        return base64.b64decode(salt.encode('utf-8'))
    
    def _derive_key(self) -> bytes:
        """Derive encryption key from master key using PBKDF2."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._salt,
            iterations=100000,
            backend=default_backend()
        )
        return kdf.derive(self._master_key)
    
    def encrypt(self, plaintext: Union[str, Dict, Any]) -> str:
        """
        Encrypt data using AES-256-GCM.
        
        Args:
            plaintext: Data to encrypt (string or JSON-serializable object)
            
        Returns:
            Base64-encoded encrypted data with nonce prepended
        """
        if plaintext is None:
            return None
            
        # Convert to string if necessary
        if isinstance(plaintext, dict):
            plaintext = json.dumps(plaintext)
        elif not isinstance(plaintext, str):
            plaintext = str(plaintext)
            
        # Generate random nonce (12 bytes for GCM)
        nonce = os.urandom(12)
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(self._key),
            modes.GCM(nonce),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        # Encrypt data
        ciphertext = encryptor.update(plaintext.encode('utf-8')) + encryptor.finalize()
        
        # Combine nonce + ciphertext + tag
        encrypted_data = nonce + ciphertext + encryptor.tag
        
        # Return base64-encoded result
        return base64.b64encode(encrypted_data).decode('utf-8')
    
    def decrypt(self, ciphertext: str) -> Union[str, None]:
        """
        Decrypt data encrypted with AES-256-GCM.
        
        Args:
            ciphertext: Base64-encoded encrypted data
            
        Returns:
            Decrypted string or None if decryption fails
        """
        if not ciphertext:
            return None
            
        try:
            # Decode from base64
            encrypted_data = base64.b64decode(ciphertext.encode('utf-8'))
            
            # Extract components
            nonce = encrypted_data[:12]
            tag = encrypted_data[-16:]
            ciphertext_bytes = encrypted_data[12:-16]
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(self._key),
                modes.GCM(nonce, tag),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            
            # Decrypt data
            plaintext = decryptor.update(ciphertext_bytes) + decryptor.finalize()
            
            return plaintext.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return None
    
    def encrypt_pii_fields(self, data: Dict[str, Any], pii_fields: list) -> Dict[str, Any]:
        """
        Encrypt specific PII fields in a dictionary.
        
        Args:
            data: Dictionary containing data
            pii_fields: List of field names to encrypt
            
        Returns:
            Dictionary with encrypted PII fields
        """
        encrypted_data = data.copy()
        
        for field in pii_fields:
            if field in encrypted_data and encrypted_data[field] is not None:
                encrypted_data[field] = self.encrypt(encrypted_data[field])
                
        return encrypted_data
    
    def decrypt_pii_fields(self, data: Dict[str, Any], pii_fields: list) -> Dict[str, Any]:
        """
        Decrypt specific PII fields in a dictionary.
        
        Args:
            data: Dictionary containing encrypted data
            pii_fields: List of field names to decrypt
            
        Returns:
            Dictionary with decrypted PII fields
        """
        decrypted_data = data.copy()
        
        for field in pii_fields:
            if field in decrypted_data and decrypted_data[field] is not None:
                decrypted_value = self.decrypt(decrypted_data[field])
                if decrypted_value is not None:
                    # Try to parse as JSON if it looks like JSON
                    if decrypted_value.startswith(('{', '[')):
                        try:
                            decrypted_data[field] = json.loads(decrypted_value)
                        except json.JSONDecodeError:
                            decrypted_data[field] = decrypted_value
                    else:
                        decrypted_data[field] = decrypted_value
                        
        return decrypted_data
    
    def hash_identifier(self, identifier: str) -> str:
        """
        Create a one-way hash of an identifier for indexing.
        
        Args:
            identifier: String to hash (e.g., email)
            
        Returns:
            Hexadecimal hash string
        """
        if not identifier:
            return None
            
        # Use SHA-256 with salt for consistent hashing
        hasher = hashes.Hash(hashes.SHA256(), backend=default_backend())
        hasher.update(self._salt)
        hasher.update(identifier.encode('utf-8'))
        
        return hasher.finalize().hex()
    
    def tokenize_pii(self, pii_value: str, token_prefix: str = "tok") -> str:
        """
        Create a reversible token for PII that can be used in logs.
        
        Args:
            pii_value: PII value to tokenize
            token_prefix: Prefix for the token
            
        Returns:
            Token string like "tok_1234abcd"
        """
        if not pii_value:
            return None
            
        # Create a short hash for the token
        hasher = hashes.Hash(hashes.SHA256(), backend=default_backend())
        hasher.update(pii_value.encode('utf-8'))
        hash_bytes = hasher.finalize()
        
        # Use first 8 characters of hex for token
        token = f"{token_prefix}_{hash_bytes.hex()[:8]}"
        
        return token


# Singleton instance
_encryption_service = None


def get_encryption_service() -> EncryptionService:
    """Get or create encryption service singleton."""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


# PII field definitions by model/table
PII_FIELDS = {
    "customers": ["name", "email", "phone", "age", "gender", "occupation"],
    "conversations": ["customer_data"],  # JSONB field containing PII
    "trial_events": ["ip_address", "user_agent"],
    "customer_data": ["name", "email", "phone", "age", "gender", "occupation"],
}


def encrypt_customer_data(customer_data: Dict[str, Any]) -> Dict[str, Any]:
    """Encrypt customer data fields."""
    service = get_encryption_service()
    return service.encrypt_pii_fields(customer_data, PII_FIELDS["customer_data"])


def decrypt_customer_data(encrypted_data: Dict[str, Any]) -> Dict[str, Any]:
    """Decrypt customer data fields."""
    service = get_encryption_service()
    return service.decrypt_pii_fields(encrypted_data, PII_FIELDS["customer_data"])