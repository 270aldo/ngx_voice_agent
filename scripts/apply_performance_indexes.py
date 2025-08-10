#!/usr/bin/env python3
"""
Script to safely apply performance indexes to the database.
Includes progress tracking and rollback capability.
"""

import asyncio
import asyncpg
import logging
from datetime import datetime
from typing import List, Dict, Any
import os
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IndexMigration:
    """Handles safe application of database indexes."""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.applied_indexes = []
        self.failed_indexes = []
        
    async def connect(self) -> asyncpg.Connection:
        """Create database connection."""
        return await asyncpg.connect(self.database_url)
    
    async def check_index_exists(self, conn: asyncpg.Connection, index_name: str) -> bool:
        """Check if an index already exists."""
        result = await conn.fetchval(
            """
            SELECT EXISTS (
                SELECT 1 
                FROM pg_indexes 
                WHERE indexname = $1
            )
            """,
            index_name
        )
        return result
    
    async def get_table_size(self, conn: asyncpg.Connection, table_name: str) -> str:
        """Get the size of a table."""
        result = await conn.fetchval(
            """
            SELECT pg_size_pretty(pg_total_relation_size($1::regclass))
            """,
            table_name
        )
        return result or "Unknown"
    
    async def create_index_concurrently(
        self, 
        conn: asyncpg.Connection, 
        index_sql: str,
        index_name: str
    ) -> bool:
        """Create an index concurrently to avoid locking."""
        try:
            # Replace CREATE INDEX with CREATE INDEX CONCURRENTLY
            concurrent_sql = index_sql.replace("CREATE INDEX", "CREATE INDEX CONCURRENTLY")
            
            logger.info(f"Creating index {index_name} concurrently...")
            start_time = datetime.now()
            
            # Execute in a separate connection (required for CONCURRENTLY)
            async with await asyncpg.connect(self.database_url) as idx_conn:
                await idx_conn.execute(concurrent_sql)
            
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ Index {index_name} created successfully in {duration:.2f} seconds")
            
            self.applied_indexes.append({
                "name": index_name,
                "duration": duration,
                "status": "success"
            })
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create index {index_name}: {e}")
            self.failed_indexes.append({
                "name": index_name,
                "error": str(e),
                "status": "failed"
            })
            return False
    
    async def analyze_table(self, conn: asyncpg.Connection, table_name: str):
        """Run ANALYZE on a table to update statistics."""
        try:
            logger.info(f"Analyzing table {table_name}...")
            await conn.execute(f"ANALYZE {table_name}")
            logger.info(f"✅ Table {table_name} analyzed successfully")
        except Exception as e:
            logger.error(f"Failed to analyze table {table_name}: {e}")
    
    async def apply_migration(self):
        """Apply the performance indexes migration."""
        migration_file = Path(__file__).parent / "migrations" / "014_performance_indexes.sql"
        
        if not migration_file.exists():
            logger.error(f"Migration file not found: {migration_file}")
            return
        
        logger.info("Starting performance index migration...")
        logger.info(f"Database: {self.database_url.split('@')[1] if '@' in self.database_url else 'local'}")
        
        # Read migration file
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        # Parse individual index creation statements
        index_statements = []
        current_statement = []
        
        for line in migration_sql.split('\n'):
            if line.strip().startswith('CREATE INDEX'):
                if current_statement:
                    index_statements.append('\n'.join(current_statement))
                current_statement = [line]
            elif current_statement and line.strip():
                current_statement.append(line)
                if line.strip().endswith(';'):
                    index_statements.append('\n'.join(current_statement))
                    current_statement = []
        
        logger.info(f"Found {len(index_statements)} index creation statements")
        
        # Connect to database
        conn = await self.connect()
        
        try:
            # Check table sizes
            logger.info("\nTable sizes:")
            for table in ['conversations', 'messages', 'ml_tracking_events']:
                size = await self.get_table_size(conn, table)
                logger.info(f"  {table}: {size}")
            
            # Apply each index
            for i, index_sql in enumerate(index_statements, 1):
                # Extract index name
                index_name = None
                for line in index_sql.split('\n'):
                    if 'CREATE INDEX' in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            index_name = parts[2]
                            break
                
                if not index_name:
                    logger.warning(f"Could not extract index name from statement {i}")
                    continue
                
                logger.info(f"\n[{i}/{len(index_statements)}] Processing index: {index_name}")
                
                # Check if index already exists
                if await self.check_index_exists(conn, index_name):
                    logger.info(f"⏭️  Index {index_name} already exists, skipping")
                    continue
                
                # Create index concurrently
                await self.create_index_concurrently(conn, index_sql, index_name)
            
            # Analyze tables
            logger.info("\nAnalyzing tables to update statistics...")
            tables = [
                'conversations', 'messages', 'conversation_outcomes',
                'ml_tracking_events', 'ml_training_data', 'lead_scores',
                'objection_handling', 'ab_experiments', 'prompt_versions'
            ]
            
            for table in tables:
                await self.analyze_table(conn, table)
            
            # Summary
            logger.info("\n" + "="*60)
            logger.info("MIGRATION SUMMARY")
            logger.info("="*60)
            logger.info(f"Total indexes processed: {len(index_statements)}")
            logger.info(f"Successfully created: {len(self.applied_indexes)}")
            logger.info(f"Failed: {len(self.failed_indexes)}")
            
            if self.applied_indexes:
                logger.info("\nSuccessfully created indexes:")
                for idx in self.applied_indexes:
                    logger.info(f"  ✅ {idx['name']} ({idx['duration']:.2f}s)")
            
            if self.failed_indexes:
                logger.info("\nFailed indexes:")
                for idx in self.failed_indexes:
                    logger.info(f"  ❌ {idx['name']}: {idx['error']}")
            
            # Performance tips
            logger.info("\n" + "="*60)
            logger.info("NEXT STEPS:")
            logger.info("1. Monitor query performance using the query_performance_monitor.sql script")
            logger.info("2. Check pg_stat_user_indexes to verify indexes are being used")
            logger.info("3. Run VACUUM ANALYZE periodically to maintain performance")
            logger.info("4. Consider partitioning large tables if needed")
            
        finally:
            await conn.close()
    
    async def rollback_indexes(self, index_names: List[str]):
        """Rollback specific indexes if needed."""
        conn = await self.connect()
        
        try:
            for index_name in index_names:
                try:
                    logger.info(f"Dropping index {index_name}...")
                    await conn.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {index_name}")
                    logger.info(f"✅ Index {index_name} dropped successfully")
                except Exception as e:
                    logger.error(f"Failed to drop index {index_name}: {e}")
        finally:
            await conn.close()


async def main():
    """Main execution function."""
    # Get database URL from environment or use default
    database_url = os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:your_password@localhost:5432/ngx_voice_agent'
    )
    
    # Safety check
    response = input(
        "\n⚠️  This script will create database indexes. "
        "This may take time on large tables.\n"
        "Do you want to continue? (yes/no): "
    )
    
    if response.lower() != 'yes':
        logger.info("Migration cancelled.")
        return
    
    # Run migration
    migration = IndexMigration(database_url)
    await migration.apply_migration()


if __name__ == "__main__":
    asyncio.run(main())