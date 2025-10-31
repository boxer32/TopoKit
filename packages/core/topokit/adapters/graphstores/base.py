"""
Module: base_graphstore_adapter
Purpose: Base class for graph database adapters
Inputs: Execution context, graph queries
Outputs: Execution results with graph query results
Dependencies: adapter.framework
Failure Modes: Connection failure → retry, query failure → error
Trace: page:adapters, build:20250127, spec-id:T100
"""

from abc import abstractmethod
from typing import Any, Dict, List, Optional
import logging

from ..framework import BaseAdapter, AdapterType, AdapterConfig, ExecutionContext, ExecutionResult


logger = logging.getLogger(__name__)


class BaseGraphStoreAdapter(BaseAdapter):
    """Base adapter for graph databases."""
    
    def __init__(self, config: AdapterConfig):
        """Initialize graph store adapter."""
        super().__init__(config)
    
    @property
    def adapter_type(self) -> AdapterType:
        """Get adapter type."""
        return AdapterType.GRAPH_DATABASE
    
    async def _execute_impl(
        self,
        context: ExecutionContext,
        execution_profile: Any,
    ) -> ExecutionResult:
        """Execute graph query."""
        # Extract query from input
        query = self._extract_query(context.input_data)
        
        # Execute graph query
        results = await self._execute_graph_query(query)
        
        return ExecutionResult(
            success=True,
            output_data={
                "results": results,
                "query": query,
                "num_results": len(results) if isinstance(results, list) else 1,
            },
            confidence=1.0,
            metadata={
                "query": query,
            },
        )
    
    @abstractmethod
    async def _execute_graph_query(self, query: str) -> Any:
        """Execute graph database query."""
        pass
    
    def _extract_query(self, input_data: Any) -> str:
        """Extract query from input data."""
        if isinstance(input_data, str):
            return input_data
        elif isinstance(input_data, dict):
            return input_data.get("query") or input_data.get("cypher") or str(input_data)
        else:
            return str(input_data)

