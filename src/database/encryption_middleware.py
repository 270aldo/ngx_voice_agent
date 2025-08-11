"""
Database encryption middleware for automatic PII protection.

This module provides middleware that automatically encrypts PII fields
when writing to the database and decrypts them when reading.
"""

import json
from typing import Any, Dict, List, Optional, Union
import logging

from src.services.encryption_service import get_encryption_service, PII_FIELDS

logger = logging.getLogger(__name__)


class DatabaseEncryptionMiddleware:
    """Middleware for automatic PII encryption/decryption in database operations."""
    
    def __init__(self):
        """Initialize the encryption middleware."""
        self.encryption_service = get_encryption_service()
        self._enabled = True
        
    def disable(self):
        """Temporarily disable encryption (for migrations, etc.)."""
        self._enabled = False
        
    def enable(self):
        """Re-enable encryption."""
        self._enabled = True
        
    def encrypt_for_insert(self, table_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Encrypt PII fields before inserting into database.
        
        Args:
            table_name: Name of the database table
            data: Data to be inserted
            
        Returns:
            Data with PII fields encrypted
        """
        if not self._enabled:
            return data
            
        # Get PII fields for this table
        pii_fields = PII_FIELDS.get(table_name, [])
        if not pii_fields:
            return data
            
        encrypted_data = data.copy()
        
        for field in pii_fields:
            if field in encrypted_data and encrypted_data[field] is not None:
                # Special handling for JSONB fields
                if field == "customer_data" and isinstance(encrypted_data[field], dict):
                    # Encrypt individual fields within customer_data
                    encrypted_customer_data = self.encryption_service.encrypt_pii_fields(
                        encrypted_data[field],
                        PII_FIELDS.get("customer_data", [])
                    )
                    encrypted_data[field] = encrypted_customer_data
                else:
                    # Regular field encryption
                    encrypted_data[field] = self.encryption_service.encrypt(encrypted_data[field])
                    
        return encrypted_data
    
    def decrypt_from_select(self, table_name: str, data: Union[Dict, List]) -> Union[Dict, List]:
        """
        Decrypt PII fields after selecting from database.
        
        Args:
            table_name: Name of the database table
            data: Data retrieved from database
            
        Returns:
            Data with PII fields decrypted
        """
        if not self._enabled:
            return data
            
        # Handle list of records
        if isinstance(data, list):
            return [self.decrypt_from_select(table_name, record) for record in data]
            
        # Get PII fields for this table
        pii_fields = PII_FIELDS.get(table_name, [])
        if not pii_fields:
            return data
            
        decrypted_data = data.copy()
        
        for field in pii_fields:
            if field in decrypted_data and decrypted_data[field] is not None:
                # Special handling for JSONB fields
                if field == "customer_data" and isinstance(decrypted_data[field], dict):
                    # Check if the data is already encrypted
                    if any(isinstance(v, str) and v.startswith('gAAAAA') for v in decrypted_data[field].values()):
                        # Decrypt individual fields within customer_data
                        decrypted_customer_data = self.encryption_service.decrypt_pii_fields(
                            decrypted_data[field],
                            PII_FIELDS.get("customer_data", [])
                        )
                        decrypted_data[field] = decrypted_customer_data
                else:
                    # Regular field decryption
                    if isinstance(decrypted_data[field], str):
                        decrypted_value = self.encryption_service.decrypt(decrypted_data[field])
                        if decrypted_value is not None:
                            decrypted_data[field] = decrypted_value
                            
        return decrypted_data
    
    def create_search_token(self, field_name: str, search_value: str) -> str:
        """
        Create an encrypted search token for PII fields.
        
        For exact match searches on encrypted fields.
        
        Args:
            field_name: Name of the field
            search_value: Value to search for
            
        Returns:
            Encrypted search token
        """
        if not self._enabled:
            return search_value
            
        return self.encryption_service.encrypt(search_value)
    
    def create_search_hash(self, field_name: str, search_value: str) -> str:
        """
        Create a hash for indexed PII field searches.
        
        Args:
            field_name: Name of the field
            search_value: Value to search for
            
        Returns:
            Hash value for searching
        """
        if not self._enabled:
            return search_value
            
        return self.encryption_service.hash_identifier(search_value)


# Global middleware instance
_encryption_middleware = None


def get_encryption_middleware() -> DatabaseEncryptionMiddleware:
    """Get or create encryption middleware singleton."""
    global _encryption_middleware
    if _encryption_middleware is None:
        _encryption_middleware = DatabaseEncryptionMiddleware()
    return _encryption_middleware


class EncryptedSupabaseClient:
    """Wrapper for Supabase client with automatic encryption/decryption."""
    
    def __init__(self, supabase_client):
        """Initialize with a Supabase client instance."""
        self._client = supabase_client
        self._middleware = get_encryption_middleware()
        
    def table(self, table_name: str):
        """Get an encrypted table interface."""
        return EncryptedTable(self._client.table(table_name), table_name, self._middleware)
        
    # Proxy other methods to the underlying client
    def __getattr__(self, name):
        return getattr(self._client, name)


class EncryptedTable:
    """Wrapper for Supabase table with automatic encryption/decryption."""
    
    def __init__(self, table, table_name: str, middleware: DatabaseEncryptionMiddleware):
        """Initialize encrypted table wrapper."""
        self._table = table
        self._table_name = table_name
        self._middleware = middleware
        
    def insert(self, data: Union[Dict, List[Dict]]):
        """Insert data with automatic PII encryption."""
        if isinstance(data, list):
            encrypted_data = [self._middleware.encrypt_for_insert(self._table_name, record) for record in data]
        else:
            encrypted_data = self._middleware.encrypt_for_insert(self._table_name, data)
            
        return EncryptedQuery(self._table.insert(encrypted_data), self._table_name, self._middleware)
    
    def upsert(self, data: Union[Dict, List[Dict]]):
        """Upsert data with automatic PII encryption."""
        if isinstance(data, list):
            encrypted_data = [self._middleware.encrypt_for_insert(self._table_name, record) for record in data]
        else:
            encrypted_data = self._middleware.encrypt_for_insert(self._table_name, data)
            
        return EncryptedQuery(self._table.upsert(encrypted_data), self._table_name, self._middleware)
    
    def update(self, data: Dict):
        """Update data with automatic PII encryption."""
        encrypted_data = self._middleware.encrypt_for_insert(self._table_name, data)
        return EncryptedQuery(self._table.update(encrypted_data), self._table_name, self._middleware)
    
    def select(self, *args, **kwargs):
        """Select data with automatic PII decryption."""
        return EncryptedQuery(self._table.select(*args, **kwargs), self._table_name, self._middleware)
    
    def delete(self):
        """Delete operations don't need encryption."""
        return self._table.delete()
    
    # Proxy other methods
    def __getattr__(self, name):
        result = getattr(self._table, name)
        if callable(result):
            return lambda *args, **kwargs: EncryptedQuery(
                result(*args, **kwargs), 
                self._table_name, 
                self._middleware
            )
        return result


class EncryptedQuery:
    """Wrapper for Supabase query with automatic encryption/decryption."""
    
    def __init__(self, query, table_name: str, middleware: DatabaseEncryptionMiddleware):
        """Initialize encrypted query wrapper."""
        self._query = query
        self._table_name = table_name
        self._middleware = middleware
        
    async def execute(self):
        """Execute query and decrypt results."""
        result = await self._query.execute()
        
        # Decrypt the data if present
        if hasattr(result, 'data') and result.data:
            result.data = self._middleware.decrypt_from_select(self._table_name, result.data)
            
        return result
    
    def eq(self, column: str, value: Any):
        """Equal filter with encryption support for PII fields."""
        # Check if this column needs encryption
        pii_fields = PII_FIELDS.get(self._table_name, [])
        if column in pii_fields and value is not None:
            # For searching encrypted fields, we need to encrypt the search value
            encrypted_value = self._middleware.create_search_token(column, value)
            return EncryptedQuery(self._query.eq(column, encrypted_value), self._table_name, self._middleware)
        
        return EncryptedQuery(self._query.eq(column, value), self._table_name, self._middleware)
    
    # Proxy other query methods
    def __getattr__(self, name):
        result = getattr(self._query, name)
        if callable(result):
            return lambda *args, **kwargs: EncryptedQuery(
                result(*args, **kwargs),
                self._table_name,
                self._middleware
            )
        return result