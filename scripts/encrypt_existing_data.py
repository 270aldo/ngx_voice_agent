"""
Script to encrypt existing PII data in the database.

This script should be run once to encrypt all existing PII data
after the encryption system is deployed.
"""

import asyncio
import logging
import os
import sys
from typing import List, Dict, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.encryption_service import get_encryption_service, PII_FIELDS
from src.integrations.supabase.client import get_supabase_client
from src.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataEncryptor:
    """Handles encryption of existing data in the database."""
    
    def __init__(self):
        """Initialize data encryptor."""
        self.encryption_service = get_encryption_service()
        self.supabase = None
        self.dry_run = False
        self.batch_size = 100
        
    async def initialize(self):
        """Initialize Supabase client."""
        self.supabase = await get_supabase_client()
        
    async def encrypt_customers_table(self) -> Dict[str, int]:
        """Encrypt PII fields in customers table."""
        logger.info("Starting encryption of customers table...")
        
        stats = {
            "total": 0,
            "encrypted": 0,
            "skipped": 0,
            "errors": 0
        }
        
        try:
            # Get all customers that aren't encrypted yet
            result = await self.supabase.table("customers").select("*").eq("is_encrypted", False).execute()
            
            if not result.data:
                logger.info("No unencrypted customers found")
                return stats
                
            stats["total"] = len(result.data)
            logger.info(f"Found {stats['total']} unencrypted customers")
            
            # Process in batches
            for i in range(0, len(result.data), self.batch_size):
                batch = result.data[i:i + self.batch_size]
                logger.info(f"Processing batch {i // self.batch_size + 1} ({len(batch)} records)")
                
                for customer in batch:
                    try:
                        # Encrypt PII fields
                        encrypted_data = self.encryption_service.encrypt_pii_fields(
                            customer,
                            PII_FIELDS["customers"]
                        )
                        
                        # Add email hash for searching
                        if customer.get("email"):
                            encrypted_data["email_hash"] = self.encryption_service.hash_identifier(
                                customer["email"]
                            )
                        
                        # Mark as encrypted
                        encrypted_data["is_encrypted"] = True
                        
                        if not self.dry_run:
                            # Update record
                            await self.supabase.table("customers").update(encrypted_data).eq(
                                "id", customer["id"]
                            ).execute()
                            
                        stats["encrypted"] += 1
                        
                    except Exception as e:
                        logger.error(f"Error encrypting customer {customer.get('id')}: {e}")
                        stats["errors"] += 1
                        
        except Exception as e:
            logger.error(f"Error processing customers table: {e}")
            
        return stats
    
    async def encrypt_conversations_table(self) -> Dict[str, int]:
        """Encrypt PII in conversations table (customer_data JSONB)."""
        logger.info("Starting encryption of conversations table...")
        
        stats = {
            "total": 0,
            "encrypted": 0,
            "skipped": 0,
            "errors": 0
        }
        
        try:
            # Get all conversations with unencrypted customer data
            result = await self.supabase.table("conversations").select("*").eq(
                "pii_encrypted", False
            ).execute()
            
            if not result.data:
                logger.info("No unencrypted conversations found")
                return stats
                
            stats["total"] = len(result.data)
            logger.info(f"Found {stats['total']} unencrypted conversations")
            
            # Process in batches
            for i in range(0, len(result.data), self.batch_size):
                batch = result.data[i:i + self.batch_size]
                logger.info(f"Processing batch {i // self.batch_size + 1} ({len(batch)} records)")
                
                for conversation in batch:
                    try:
                        customer_data = conversation.get("customer_data", {})
                        
                        if customer_data:
                            # Encrypt customer data fields
                            encrypted_customer_data = self.encryption_service.encrypt_pii_fields(
                                customer_data,
                                PII_FIELDS["customer_data"]
                            )
                            
                            update_data = {
                                "customer_data": encrypted_customer_data,
                                "pii_encrypted": True,
                                "encryption_version": 1
                            }
                            
                            if not self.dry_run:
                                # Update record
                                await self.supabase.table("conversations").update(update_data).eq(
                                    "id", conversation["id"]
                                ).execute()
                                
                            stats["encrypted"] += 1
                        else:
                            stats["skipped"] += 1
                            
                    except Exception as e:
                        logger.error(f"Error encrypting conversation {conversation.get('id')}: {e}")
                        stats["errors"] += 1
                        
        except Exception as e:
            logger.error(f"Error processing conversations table: {e}")
            
        return stats
    
    async def encrypt_trial_events_table(self) -> Dict[str, int]:
        """Encrypt PII fields in trial_events table."""
        logger.info("Starting encryption of trial_events table...")
        
        stats = {
            "total": 0,
            "encrypted": 0,
            "skipped": 0,
            "errors": 0
        }
        
        try:
            # Get all trial events that aren't encrypted yet
            result = await self.supabase.table("trial_events").select("*").eq(
                "is_encrypted", False
            ).execute()
            
            if not result.data:
                logger.info("No unencrypted trial events found")
                return stats
                
            stats["total"] = len(result.data)
            logger.info(f"Found {stats['total']} unencrypted trial events")
            
            # Process in batches
            for i in range(0, len(result.data), self.batch_size):
                batch = result.data[i:i + self.batch_size]
                logger.info(f"Processing batch {i // self.batch_size + 1} ({len(batch)} records)")
                
                for event in batch:
                    try:
                        update_data = {"is_encrypted": True}
                        
                        # Encrypt IP address
                        if event.get("ip_address"):
                            update_data["ip_address_encrypted"] = self.encryption_service.encrypt(
                                event["ip_address"]
                            )
                            update_data["ip_address"] = None  # Clear original
                            
                        # Encrypt user agent
                        if event.get("user_agent"):
                            update_data["user_agent_encrypted"] = self.encryption_service.encrypt(
                                event["user_agent"]
                            )
                            update_data["user_agent"] = None  # Clear original
                            
                        if not self.dry_run:
                            # Update record
                            await self.supabase.table("trial_events").update(update_data).eq(
                                "id", event["id"]
                            ).execute()
                            
                        stats["encrypted"] += 1
                        
                    except Exception as e:
                        logger.error(f"Error encrypting trial event {event.get('id')}: {e}")
                        stats["errors"] += 1
                        
        except Exception as e:
            logger.error(f"Error processing trial_events table: {e}")
            
        return stats
    
    async def log_encryption_audit(self, table_name: str, record_count: int, success: bool, error: str = None):
        """Log encryption operation to audit table."""
        try:
            audit_data = {
                "table_name": table_name,
                "record_id": "batch_encryption",
                "action": "encrypt",
                "field_names": PII_FIELDS.get(table_name, []),
                "success": success,
                "error_message": error
            }
            
            if not self.dry_run:
                await self.supabase.table("encryption_audit").insert(audit_data).execute()
                
        except Exception as e:
            logger.error(f"Error logging encryption audit: {e}")
    
    async def run_encryption(self, dry_run: bool = False, tables: List[str] = None):
        """
        Run encryption on all or specified tables.
        
        Args:
            dry_run: If True, don't actually update data
            tables: List of table names to encrypt (None = all)
        """
        self.dry_run = dry_run
        
        if dry_run:
            logger.info("Running in DRY RUN mode - no data will be modified")
            
        await self.initialize()
        
        all_stats = {}
        
        # Define tables to process
        tables_to_process = tables or ["customers", "conversations", "trial_events"]
        
        # Process each table
        if "customers" in tables_to_process:
            stats = await self.encrypt_customers_table()
            all_stats["customers"] = stats
            await self.log_encryption_audit(
                "customers", 
                stats["encrypted"], 
                stats["errors"] == 0,
                f"{stats['errors']} errors" if stats["errors"] > 0 else None
            )
            
        if "conversations" in tables_to_process:
            stats = await self.encrypt_conversations_table()
            all_stats["conversations"] = stats
            await self.log_encryption_audit(
                "conversations",
                stats["encrypted"],
                stats["errors"] == 0,
                f"{stats['errors']} errors" if stats["errors"] > 0 else None
            )
            
        if "trial_events" in tables_to_process:
            stats = await self.encrypt_trial_events_table()
            all_stats["trial_events"] = stats
            await self.log_encryption_audit(
                "trial_events",
                stats["encrypted"],
                stats["errors"] == 0,
                f"{stats['errors']} errors" if stats["errors"] > 0 else None
            )
            
        # Print summary
        logger.info("\n" + "=" * 50)
        logger.info("ENCRYPTION SUMMARY")
        logger.info("=" * 50)
        
        for table, stats in all_stats.items():
            logger.info(f"\n{table}:")
            logger.info(f"  Total records: {stats['total']}")
            logger.info(f"  Encrypted: {stats['encrypted']}")
            logger.info(f"  Skipped: {stats['skipped']}")
            logger.info(f"  Errors: {stats['errors']}")
            
        if dry_run:
            logger.info("\nDRY RUN COMPLETE - No data was modified")
        else:
            logger.info("\nENCRYPTION COMPLETE")


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Encrypt existing PII data in database")
    parser.add_argument("--dry-run", action="store_true", help="Run without modifying data")
    parser.add_argument("--tables", nargs="+", help="Specific tables to encrypt")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for processing")
    
    args = parser.parse_args()
    
    # Check environment
    if settings.environment == "production" and not args.dry_run:
        response = input("WARNING: Running in PRODUCTION. Are you sure? (yes/no): ")
        if response.lower() != "yes":
            logger.info("Aborted by user")
            return
            
    encryptor = DataEncryptor()
    encryptor.batch_size = args.batch_size
    
    await encryptor.run_encryption(
        dry_run=args.dry_run,
        tables=args.tables
    )


if __name__ == "__main__":
    asyncio.run(main())