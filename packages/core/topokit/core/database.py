"""Database schema and migrations framework for TopoKit with PostgreSQL support."""

import asyncio
import json
from typing import Any, Dict, List, Optional, Union, Type
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
import logging

try:
    import asyncpg
    import sqlalchemy
    from sqlalchemy import create_engine, MetaData, Table, Column, String, Integer, DateTime, Text, JSON, Boolean, Float
    from sqlalchemy.dialects.postgresql import UUID, JSONB
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy.orm import declarative_base, sessionmaker
    from sqlalchemy.sql import text
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False

from .config import DatabaseConfig
from .logging import get_logger


class MigrationStatus(str, Enum):
    """Migration status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class Migration:
    """Database migration."""
    version: str
    name: str
    description: str
    up_sql: str
    down_sql: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: MigrationStatus = MigrationStatus.PENDING
    executed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class DatabaseManager:
    """Database manager with schema management and migrations."""
    
    def __init__(self, config: DatabaseConfig):
        """Initialize database manager.
        
        Args:
            config: Database configuration
        """
        if not DATABASE_AVAILABLE:
            raise ImportError("Database dependencies not available. Install asyncpg and sqlalchemy.")
        
        self.config = config
        self.logger = get_logger(__name__)
        
        # Create async engine
        self.engine = create_async_engine(
            config.url.replace("postgresql://", "postgresql+asyncpg://"),
            echo=config.echo,
            pool_size=config.pool_size,
            max_overflow=config.max_overflow
        )
        
        # Create session factory
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Base for models
        self.Base = declarative_base()
        
        # Initialize tables
        self._create_tables()
    
    def _create_tables(self):
        """Create SQLAlchemy table definitions."""
        
        # Migrations table
        self.migrations_table = Table(
            'topokit_migrations',
            self.Base.metadata,
            Column('version', String(50), primary_key=True),
            Column('name', String(255), nullable=False),
            Column('description', Text),
            Column('up_sql', Text, nullable=False),
            Column('down_sql', Text, nullable=False),
            Column('status', String(20), nullable=False, default=MigrationStatus.PENDING.value),
            Column('executed_at', DateTime(timezone=True)),
            Column('error_message', Text),
            Column('created_at', DateTime(timezone=True), nullable=False, default=datetime.utcnow)
        )
        
        # Topology packs table
        self.topology_packs_table = Table(
            'topology_packs',
            self.Base.metadata,
            Column('id', UUID(as_uuid=True), primary_key=True),
            Column('name', String(255), nullable=False),
            Column('version', String(50), nullable=False),
            Column('description', Text),
            Column('pack_data', JSONB, nullable=False),
            Column('created_at', DateTime(timezone=True), nullable=False, default=datetime.utcnow),
            Column('updated_at', DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
            Column('created_by', String(255)),
            Column('is_active', Boolean, default=True)
        )
        
        # Execution traces table
        self.execution_traces_table = Table(
            'execution_traces',
            self.Base.metadata,
            Column('id', UUID(as_uuid=True), primary_key=True),
            Column('session_id', String(255), nullable=False),
            Column('topology_pack_id', UUID(as_uuid=True), nullable=False),
            Column('start_time', DateTime(timezone=True), nullable=False),
            Column('end_time', DateTime(timezone=True)),
            Column('status', String(20), nullable=False),
            Column('input_data', JSONB),
            Column('output_data', JSONB),
            Column('error_message', Text),
            Column('performance_metrics', JSONB),
            Column('created_at', DateTime(timezone=True), nullable=False, default=datetime.utcnow)
        )
        
        # Node executions table
        self.node_executions_table = Table(
            'node_executions',
            self.Base.metadata,
            Column('id', UUID(as_uuid=True), primary_key=True),
            Column('trace_id', UUID(as_uuid=True), nullable=False),
            Column('node_id', String(255), nullable=False),
            Column('start_time', DateTime(timezone=True), nullable=False),
            Column('end_time', DateTime(timezone=True)),
            Column('status', String(20), nullable=False),
            Column('input_data', JSONB),
            Column('output_data', JSONB),
            Column('error_message', Text),
            Column('retry_count', Integer, default=0),
            Column('confidence_score', Float),
            Column('guardrail_results', JSONB),
            Column('created_at', DateTime(timezone=True), nullable=False, default=datetime.utcnow)
        )
        
        # Context store table
        self.context_store_table = Table(
            'context_store',
            self.Base.metadata,
            Column('session_id', String(255), primary_key=True),
            Column('data', JSONB, nullable=False),
            Column('version', Integer, nullable=False, default=1),
            Column('last_updated', DateTime(timezone=True), nullable=False, default=datetime.utcnow),
            Column('updated_by', String(255)),
            Column('metadata', JSONB)
        )
        
        # Audit logs table
        self.audit_logs_table = Table(
            'audit_logs',
            self.Base.metadata,
            Column('id', UUID(as_uuid=True), primary_key=True),
            Column('session_id', String(255)),
            Column('user_id', String(255)),
            Column('action', String(100), nullable=False),
            Column('resource_type', String(100), nullable=False),
            Column('resource_id', String(255)),
            Column('details', JSONB),
            Column('ip_address', String(45)),
            Column('user_agent', Text),
            Column('created_at', DateTime(timezone=True), nullable=False, default=datetime.utcnow)
        )
    
    async def initialize(self) -> None:
        """Initialize database and run migrations."""
        self.logger.info("Initializing database...")
        
        # Create all tables
        async with self.engine.begin() as conn:
            await conn.run_sync(self.Base.metadata.create_all)
        
        # Run migrations
        await self.run_migrations()
        
        self.logger.info("Database initialized successfully")
    
    async def close(self) -> None:
        """Close database connections."""
        await self.engine.dispose()
        self.logger.info("Database connections closed")
    
    async def run_migrations(self) -> None:
        """Run pending migrations."""
        self.logger.info("Running database migrations...")
        
        # Get pending migrations
        pending_migrations = self._get_pending_migrations()
        
        for migration in pending_migrations:
            try:
                await self._execute_migration(migration)
                self.logger.info(f"Migration {migration.version} completed successfully")
            except Exception as e:
                self.logger.error(f"Migration {migration.version} failed: {e}")
                migration.status = MigrationStatus.FAILED
                migration.error_message = str(e)
                await self._save_migration_status(migration)
                raise
    
    def _get_pending_migrations(self) -> List[Migration]:
        """Get pending migrations from migrations directory."""
        migrations_dir = Path(__file__).parent.parent / "migrations"
        if not migrations_dir.exists():
            return []
        
        migrations = []
        for migration_file in sorted(migrations_dir.glob("*.py")):
            try:
                migration = self._load_migration_from_file(migration_file)
                migrations.append(migration)
            except Exception as e:
                self.logger.error(f"Failed to load migration {migration_file}: {e}")
        
        return migrations
    
    def _load_migration_from_file(self, file_path: Path) -> Migration:
        """Load migration from Python file."""
        # This is a simplified implementation
        # In a full implementation, this would load the migration class and extract SQL
        version = file_path.stem
        name = f"migration_{version}"
        
        return Migration(
            version=version,
            name=name,
            description=f"Migration {version}",
            up_sql=f"-- Migration {version} UP\nSELECT 1;",
            down_sql=f"-- Migration {version} DOWN\nSELECT 1;"
        )
    
    async def _execute_migration(self, migration: Migration) -> None:
        """Execute a single migration."""
        migration.status = MigrationStatus.RUNNING
        await self._save_migration_status(migration)
        
        async with self.engine.begin() as conn:
            await conn.execute(text(migration.up_sql))
        
        migration.status = MigrationStatus.COMPLETED
        migration.executed_at = datetime.now(timezone.utc)
        await self._save_migration_status(migration)
    
    async def _save_migration_status(self, migration: Migration) -> None:
        """Save migration status to database."""
        async with self.engine.begin() as conn:
            await conn.execute(
                self.migrations_table.insert().values(
                    version=migration.version,
                    name=migration.name,
                    description=migration.description,
                    up_sql=migration.up_sql,
                    down_sql=migration.down_sql,
                    status=migration.status.value,
                    executed_at=migration.executed_at,
                    error_message=migration.error_message,
                    created_at=migration.created_at
                ).on_conflict_do_update(
                    index_elements=['version'],
                    set_={
                        'status': migration.status.value,
                        'executed_at': migration.executed_at,
                        'error_message': migration.error_message
                    }
                )
            )
    
    async def get_session(self) -> AsyncSession:
        """Get database session."""
        return self.session_factory()
    
    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute raw SQL query.
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            Query results
        """
        async with self.engine.begin() as conn:
            result = await conn.execute(text(query), params or {})
            return [dict(row) for row in result]
    
    async def health_check(self) -> bool:
        """Check database health.
        
        Returns:
            True if database is healthy
        """
        try:
            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            self.logger.error(f"Database health check failed: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        return {
            "engine_url": str(self.engine.url).replace(self.config.password, "***"),
            "pool_size": self.config.pool_size,
            "max_overflow": self.config.max_overflow,
            "echo": self.config.echo
        }


class TopologyPackRepository:
    """Repository for topology pack operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        """Initialize repository.
        
        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager
        self.logger = get_logger(__name__)
    
    async def save(self, pack_data: Dict[str, Any], created_by: Optional[str] = None) -> str:
        """Save topology pack.
        
        Args:
            pack_data: Topology pack data
            created_by: User who created the pack
            
        Returns:
            Pack ID
        """
        import uuid
        pack_id = str(uuid.uuid4())
        
        async with self.db.get_session() as session:
            await session.execute(
                self.db.topology_packs_table.insert().values(
                    id=pack_id,
                    name=pack_data.get('name', ''),
                    version=pack_data.get('version', '1.0.0'),
                    description=pack_data.get('description'),
                    pack_data=pack_data,
                    created_by=created_by
                )
            )
            await session.commit()
        
        self.logger.info(f"Saved topology pack {pack_id}")
        return pack_id
    
    async def get(self, pack_id: str) -> Optional[Dict[str, Any]]:
        """Get topology pack by ID.
        
        Args:
            pack_id: Pack ID
            
        Returns:
            Pack data or None if not found
        """
        async with self.db.get_session() as session:
            result = await session.execute(
                self.db.topology_packs_table.select().where(
                    self.db.topology_packs_table.c.id == pack_id
                )
            )
            row = result.fetchone()
            
            if row:
                return dict(row)
            return None
    
    async def list(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List topology packs.
        
        Args:
            limit: Maximum number of packs to return
            offset: Number of packs to skip
            
        Returns:
            List of pack data
        """
        async with self.db.get_session() as session:
            result = await session.execute(
                self.db.topology_packs_table.select()
                .where(self.db.topology_packs_table.c.is_active == True)
                .order_by(self.db.topology_packs_table.c.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            return [dict(row) for row in result]
    
    async def delete(self, pack_id: str) -> bool:
        """Delete topology pack.
        
        Args:
            pack_id: Pack ID
            
        Returns:
            True if deleted successfully
        """
        async with self.db.get_session() as session:
            result = await session.execute(
                self.db.topology_packs_table.update()
                .where(self.db.topology_packs_table.c.id == pack_id)
                .values(is_active=False)
            )
            await session.commit()
            
            return result.rowcount > 0


class ExecutionTraceRepository:
    """Repository for execution trace operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        """Initialize repository.
        
        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager
        self.logger = get_logger(__name__)
    
    async def save_trace(self, trace_data: Dict[str, Any]) -> str:
        """Save execution trace.
        
        Args:
            trace_data: Trace data
            
        Returns:
            Trace ID
        """
        import uuid
        trace_id = str(uuid.uuid4())
        
        async with self.db.get_session() as session:
            await session.execute(
                self.db.execution_traces_table.insert().values(
                    id=trace_id,
                    session_id=trace_data.get('session_id'),
                    topology_pack_id=trace_data.get('topology_pack_id'),
                    start_time=trace_data.get('start_time'),
                    end_time=trace_data.get('end_time'),
                    status=trace_data.get('status'),
                    input_data=trace_data.get('input_data'),
                    output_data=trace_data.get('output_data'),
                    error_message=trace_data.get('error_message'),
                    performance_metrics=trace_data.get('performance_metrics')
                )
            )
            await session.commit()
        
        return trace_id
    
    async def save_node_execution(self, node_execution_data: Dict[str, Any]) -> str:
        """Save node execution.
        
        Args:
            node_execution_data: Node execution data
            
        Returns:
            Node execution ID
        """
        import uuid
        execution_id = str(uuid.uuid4())
        
        async with self.db.get_session() as session:
            await session.execute(
                self.db.node_executions_table.insert().values(
                    id=execution_id,
                    trace_id=node_execution_data.get('trace_id'),
                    node_id=node_execution_data.get('node_id'),
                    start_time=node_execution_data.get('start_time'),
                    end_time=node_execution_data.get('end_time'),
                    status=node_execution_data.get('status'),
                    input_data=node_execution_data.get('input_data'),
                    output_data=node_execution_data.get('output_data'),
                    error_message=node_execution_data.get('error_message'),
                    retry_count=node_execution_data.get('retry_count', 0),
                    confidence_score=node_execution_data.get('confidence_score'),
                    guardrail_results=node_execution_data.get('guardrail_results')
                )
            )
            await session.commit()
        
        return execution_id
    
    async def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Get execution trace by ID.
        
        Args:
            trace_id: Trace ID
            
        Returns:
            Trace data or None if not found
        """
        async with self.db.get_session() as session:
            result = await session.execute(
                self.db.execution_traces_table.select().where(
                    self.db.execution_traces_table.c.id == trace_id
                )
            )
            row = result.fetchone()
            
            if row:
                return dict(row)
            return None
    
    async def get_node_executions(self, trace_id: str) -> List[Dict[str, Any]]:
        """Get node executions for trace.
        
        Args:
            trace_id: Trace ID
            
        Returns:
            List of node execution data
        """
        async with self.db.get_session() as session:
            result = await session.execute(
                self.db.node_executions_table.select().where(
                    self.db.node_executions_table.c.trace_id == trace_id
                ).order_by(self.db.node_executions_table.c.start_time)
            )
            return [dict(row) for row in result]


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_database_manager(config: Optional[DatabaseConfig] = None) -> DatabaseManager:
    """Get database manager instance.
    
    Args:
        config: Database configuration
        
    Returns:
        DatabaseManager instance
    """
    global _db_manager
    
    if _db_manager is None:
        if config is None:
            from .config import get_config
            config = get_config().database
        
        _db_manager = DatabaseManager(config)
    
    return _db_manager


async def initialize_database(config: Optional[DatabaseConfig] = None) -> DatabaseManager:
    """Initialize database with migrations.
    
    Args:
        config: Database configuration
        
    Returns:
        Initialized DatabaseManager instance
    """
    db_manager = get_database_manager(config)
    await db_manager.initialize()
    return db_manager
