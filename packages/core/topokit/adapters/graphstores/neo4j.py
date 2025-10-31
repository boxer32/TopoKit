"""
Module: neo4j_adapter
Purpose: Neo4j graph database adapter
Inputs: Execution context, Cypher queries
Outputs: Execution results with graph query results
Dependencies: neo4j library, adapter.graphstores.base
Failure Modes: Connection failure → retry, query failure → error
Trace: page:adapters, build:20250127, spec-id:T100
"""

from typing import Any, Dict, List, Optional
import logging

try:
    from neo4j import AsyncGraphDatabase, AsyncDriver
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False

from .base import BaseGraphStoreAdapter
from ..framework import AdapterConfig, register_adapter


logger = logging.getLogger(__name__)


class Neo4jAdapter(BaseGraphStoreAdapter):
    """Neo4j graph database adapter."""
    
    def __init__(self, config: AdapterConfig):
        """Initialize Neo4j adapter."""
        super().__init__(config)
        self._driver: Optional[AsyncDriver] = None
    
    @property
    def provider(self) -> str:
        """Get provider name."""
        return "neo4j"
    
    async def _initialize_impl(self) -> None:
        """Initialize Neo4j driver."""
        if not NEO4J_AVAILABLE:
            raise ImportError(
                "Neo4j library not installed. Install with: pip install neo4j"
            )
        
        uri = self.config.connection_params.get("uri", "bolt://localhost:7687")
        username = self.config.connection_params.get("username", "neo4j")
        password = self.config.connection_params.get("password")
        
        if not password:
            raise ValueError("Neo4j password required in connection_params")
        
        self._driver = AsyncGraphDatabase.driver(uri, auth=(username, password))
        
        # Test connection
        await self._driver.verify_connectivity()
        
        logger.info(f"Neo4j adapter initialized with URI: {uri}")
    
    async def _execute_graph_query(self, query: str) -> Any:
        """Execute Cypher query."""
        if not self._driver:
            raise RuntimeError("Neo4j driver not initialized")
        
        async with self._driver.session() as session:
            result = await session.run(query)
            records = await result.data()
            return records
    
    async def _health_check_impl(self) -> bool:
        """Check Neo4j health."""
        if not self._driver:
            return False
        
        try:
            await self._driver.verify_connectivity()
            return True
        except Exception as e:
            logger.error(f"Neo4j health check failed: {e}")
            return False
    
    async def _cleanup_impl(self) -> None:
        """Cleanup Neo4j driver."""
        if self._driver:
            await self._driver.close()
        self._driver = None


# Register adapter
if NEO4J_AVAILABLE:
    register_adapter("neo4j", Neo4jAdapter)

