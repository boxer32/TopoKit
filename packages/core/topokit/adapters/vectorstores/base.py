"""
Module: base_vectorstore_adapter
Purpose: Base class for vector database adapters
Inputs: Execution context, embeddings, queries
Outputs: Execution results with retrieved documents
Dependencies: adapter.framework
Failure Modes: Connection failure → retry, query failure → error
Trace: page:adapters, build:20250127, spec-id:T099
"""

from abc import abstractmethod
from typing import Any, Dict, List, Optional
import logging

from ..framework import BaseAdapter, AdapterType, AdapterConfig, ExecutionContext, ExecutionResult


logger = logging.getLogger(__name__)


class BaseVectorStoreAdapter(BaseAdapter):
    """Base adapter for vector databases."""
    
    def __init__(self, config: AdapterConfig):
        """Initialize vector store adapter."""
        super().__init__(config)
    
    @property
    def adapter_type(self) -> AdapterType:
        """Get adapter type."""
        return AdapterType.VECTOR_DATABASE
    
    async def _execute_impl(
        self,
        context: ExecutionContext,
        execution_profile: Any,
    ) -> ExecutionResult:
        """Execute vector store query."""
        # Extract query from input
        query = self._extract_query(context.input_data)
        query_embeddings = await self._embed_query(query)
        
        # Execute similarity search
        results = await self._similarity_search(
            query_embeddings=query_embeddings,
            top_k=execution_profile.max_tokens if hasattr(execution_profile, 'max_tokens') else 5,
        )
        
        return ExecutionResult(
            success=True,
            output_data={
                "results": results,
                "query": query,
                "num_results": len(results),
            },
            confidence=1.0,
            metadata={
                "query": query,
            },
        )
    
    @abstractmethod
    async def _embed_query(self, query: str) -> List[float]:
        """Generate embeddings for query."""
        pass
    
    @abstractmethod
    async def _similarity_search(
        self,
        query_embeddings: List[float],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Perform similarity search."""
        pass
    
    def _extract_query(self, input_data: Any) -> str:
        """Extract query from input data."""
        if isinstance(input_data, str):
            return input_data
        elif isinstance(input_data, dict):
            return input_data.get("query") or input_data.get("question") or str(input_data)
        else:
            return str(input_data)

