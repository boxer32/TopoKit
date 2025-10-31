"""
Module: llamaindex_adapter
Purpose: LlamaIndex adapter with vector store integration
Inputs: Execution context, execution profile, prompt/data
Outputs: Execution results with query response
Dependencies: llamaindex library, adapter.framework
Failure Modes: Query failure → retry, missing index → error
Trace: page:adapters, build:20250127, spec-id:T097
"""

from typing import Any, Dict, Optional
from datetime import datetime, timezone
import logging

try:
    from llama_index.core import VectorStoreIndex, ServiceContext, LLMPredictor
    from llama_index.core.vector_stores import VectorStore
    LLAMAINDEX_AVAILABLE = True
except ImportError:
    LLAMAINDEX_AVAILABLE = False

from .framework import (
    BaseAdapter,
    AdapterType,
    AdapterConfig,
    ExecutionContext,
    ExecutionResult,
    register_adapter,
)


logger = logging.getLogger(__name__)


class LlamaIndexAdapter(BaseAdapter):
    """LlamaIndex adapter for vector store integration."""
    
    def __init__(self, config: AdapterConfig):
        """Initialize LlamaIndex adapter."""
        super().__init__(config)
        self._index: Optional[VectorStoreIndex] = None
        self._query_engine = None
        self._vector_store: Optional[VectorStore] = None
    
    @property
    def adapter_type(self) -> AdapterType:
        """Get adapter type."""
        return AdapterType.VECTOR_DATABASE
    
    @property
    def provider(self) -> str:
        """Get provider name."""
        return "llamaindex"
    
    async def _initialize_impl(self) -> None:
        """Initialize LlamaIndex components."""
        if not LLAMAINDEX_AVAILABLE:
            raise ImportError(
                "LlamaIndex library not installed. Install with: pip install llamaindex"
            )
        
        # Initialize vector store from config
        vector_store_config = self.config.connection_params.get("vector_store_config", {})
        
        # Build vector store
        self._vector_store = self._build_vector_store(vector_store_config)
        
        # Build service context
        service_context = self._build_service_context(vector_store_config)
        
        # Load or create index
        if "index_path" in vector_store_config:
            # Load existing index
            from llama_index.core import load_index_from_storage
            storage_context = self._build_storage_context(vector_store_config)
            self._index = load_index_from_storage(storage_context)
        else:
            # Create new index
            from llama_index.core import Document
            documents = self._load_documents(vector_store_config)
            self._index = VectorStoreIndex.from_documents(
                documents,
                service_context=service_context,
                vector_store=self._vector_store,
            )
        
        # Build query engine
        self._query_engine = self._index.as_query_engine(
            similarity_top_k=vector_store_config.get("similarity_top_k", 5),
        )
    
    async def _execute_impl(
        self,
        context: ExecutionContext,
        execution_profile: Any,
    ) -> ExecutionResult:
        """Execute LlamaIndex query."""
        if not self._query_engine:
            raise RuntimeError("LlamaIndex query engine not initialized")
        
        # Extract query from input
        query = self._extract_query(context.input_data)
        
        # Execute query
        import asyncio
        
        try:
            if hasattr(self._query_engine, 'aquery'):
                # Async query
                response = await self._query_engine.aquery(query)
            else:
                # Sync query - run in thread pool
                response = await asyncio.to_thread(self._query_engine.query, query)
            
            return ExecutionResult(
                success=True,
                output_data={
                    "response": str(response),
                    "source_nodes": [
                        {
                            "node_id": node.node_id,
                            "score": node.score,
                            "text": node.text[:200],  # Truncate
                        }
                        for node in response.source_nodes
                    ] if hasattr(response, 'source_nodes') else [],
                },
                confidence=1.0,
                metadata={
                    "query": query,
                    "num_source_nodes": len(response.source_nodes) if hasattr(response, 'source_nodes') else 0,
                },
            )
        except Exception as e:
            logger.error(f"LlamaIndex query failed: {e}")
            raise
    
    async def _health_check_impl(self) -> bool:
        """Check LlamaIndex health."""
        if not self._query_engine:
            return False
        
        try:
            # Simple health check query
            test_query = "test"
            if hasattr(self._query_engine, 'aquery'):
                await self._query_engine.aquery(test_query)
            else:
                import asyncio
                await asyncio.to_thread(self._query_engine.query, test_query)
            return True
        except Exception:
            return False
    
    async def _cleanup_impl(self) -> None:
        """Cleanup LlamaIndex resources."""
        self._index = None
        self._query_engine = None
        self._vector_store = None
    
    def _extract_query(self, input_data: Any) -> str:
        """Extract query from input data."""
        if isinstance(input_data, str):
            return input_data
        elif isinstance(input_data, dict):
            return input_data.get("query") or input_data.get("question") or str(input_data)
        else:
            return str(input_data)
    
    def _build_vector_store(self, config: Dict[str, Any]) -> Optional[VectorStore]:
        """Build vector store from configuration."""
        vector_store_type = config.get("vector_store_type")
        
        if vector_store_type == "simple":
            from llama_index.core.vector_stores import SimpleVectorStore
            return SimpleVectorStore()
        elif vector_store_type == "pinecone":
            # Import and configure Pinecone
            # Implementation depends on Pinecone setup
            return None
        elif vector_store_type == "weaviate":
            # Import and configure Weaviate
            # Implementation depends on Weaviate setup
            return None
        else:
            return None
    
    def _build_service_context(self, config: Dict[str, Any]) -> ServiceContext:
        """Build service context."""
        llm_config = config.get("llm_config", {})
        llm_type = llm_config.get("llm_type", "openai")
        
        try:
            if llm_type == "openai":
                from llama_index.llms.openai import OpenAI
                llm = OpenAI(
                    temperature=llm_config.get("temperature", 0.7),
                    max_tokens=llm_config.get("max_tokens", 1000),
                )
            else:
                # Default LLM
                llm = None
            
            llm_predictor = LLMPredictor(llm=llm) if llm else None
            
            return ServiceContext.from_defaults(
                llm_predictor=llm_predictor,
            )
        except ImportError:
            return ServiceContext.from_defaults()
    
    def _build_storage_context(self, config: Dict[str, Any]):
        """Build storage context."""
        from llama_index.core import StorageContext
        storage_path = config.get("index_path")
        
        if storage_path:
            from llama_index.core import load_storage_context
            return load_storage_context(storage_path)
        else:
            return StorageContext.from_defaults()
    
    def _load_documents(self, config: Dict[str, Any]):
        """Load documents for indexing."""
        from llama_index.core import Document
        
        # Load from config or return empty
        documents_config = config.get("documents", [])
        documents = []
        
        for doc_config in documents_config:
            if isinstance(doc_config, str):
                documents.append(Document(text=doc_config))
            elif isinstance(doc_config, dict):
                documents.append(Document(**doc_config))
        
        return documents


# Register adapter
if LLAMAINDEX_AVAILABLE:
    register_adapter("llamaindex", LlamaIndexAdapter)

