"""
Module: arangodb_adapter
Purpose: ArangoDB graph database adapter
Inputs: Execution context, AQL queries
Outputs: Execution results with graph query results
Dependencies: python-arango library, adapter.graphstores.base
Failure Modes: Connection failure → retry, query failure → error
Trace: page:adapters, build:20250127, spec-id:T100
"""

from typing import Any, Dict, List, Optional
import logging

try:
    from arango import ArangoClient
    ARANGODB_AVAILABLE = True
except ImportError:
    ARANGODB_AVAILABLE = False

from .base import BaseGraphStoreAdapter
from ..framework import AdapterConfig, register_adapter


logger = logging.getLogger(__name__)


class ArangoDBAdapter(BaseGraphStoreAdapter):
    """ArangoDB graph database adapter."""
    
    def __init__(self, config: AdapterConfig):
        """Initialize ArangoDB adapter."""
        super().__init__(config)
        self._client = None
        self._db = None
    
    @property
    def provider(self) -> str:
        """Get provider name."""
        return "arangodb"
    
    async def _initialize_impl(self) -> None:
        """Initialize ArangoDB client."""
        if not ARANGODB_AVAILABLE:
            raise ImportError(
                "ArangoDB library not installed. Install with: pip install python-arango"
            )
        
        hosts = self.config.connection_params.get("hosts", "http://localhost:8529")
        username = self.config.connection_params.get("username", "root")
        password = self.config.connection_params.get("password", "")
        database = self.config.connection_params.get("database", "_system")
        
        self._client = ArangoClient(hosts=hosts)
        sys_db = self._client.db("_system", username=username, password=password)
        
        # Connect to database
        try:
            self._db = self._client.db(database, username=username, password=password)
        except Exception:
            # Create database if it doesn't exist
            sys_db.create_database(database)
            self._db = self._client.db(database, username=username, password=password)
        
        logger.info(f"ArangoDB adapter initialized with database: {database}")
    
    async def _execute_graph_query(self, query: str) -> Any:
        """Execute AQL query."""
        if not self._db:
            raise RuntimeError("ArangoDB database not initialized")
        
        # Execute AQL query
        cursor = self._db.aql.execute(query)
        results = list(cursor)
        return results
    
    async def _health_check_impl(self) -> bool:
        """Check ArangoDB health."""
        if not self._db:
            return False
        
        try:
            # Simple health check - query version
            self._db.version()
            return True
        except Exception as e:
            logger.error(f"ArangoDB health check failed: {e}")
            return False
    
    async def _cleanup_impl(self) -> None:
        """Cleanup ArangoDB client."""
        self._db = None
        self._client = None


# Register adapter
if ARANGODB_AVAILABLE:
    register_adapter("arangodb", ArangoDBAdapter)

