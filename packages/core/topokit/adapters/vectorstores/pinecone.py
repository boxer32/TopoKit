"""
Module: pinecone_adapter
Purpose: Pinecone vector database adapter
Inputs: Execution context, embeddings, queries
Outputs: Execution results with retrieved documents
Dependencies: pinecone-client library, adapter.vectorstores.base
Failure Modes: Connection failure → retry, query failure → error
Trace: page:adapters, build:20250127, spec-id:T099
"""

from typing import Any, Dict, List, Optional
import logging

try:
    from pinecone import Pinecone, ServerlessSpec
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False

try:
    from openai import OpenAI as OpenAIClient
    OPENAI_EMBEDDINGS_AVAILABLE = True
except ImportError:
    OPENAI_EMBEDDINGS_AVAILABLE = False

from .base import BaseVectorStoreAdapter
from ..framework import AdapterConfig, register_adapter


logger = logging.getLogger(__name__)


class PineconeAdapter(BaseVectorStoreAdapter):
    """Pinecone vector database adapter."""
    
    def __init__(self, config: AdapterConfig):
        """Initialize Pinecone adapter."""
        super().__init__(config)
        self._client: Optional[Pinecone] = None
        self._index = None
        self._embedding_client = None
    
    @property
    def provider(self) -> str:
        """Get provider name."""
        return "pinecone"
    
    async def _initialize_impl(self) -> None:
        """Initialize Pinecone client."""
        if not PINECONE_AVAILABLE:
            raise ImportError(
                "Pinecone library not installed. Install with: pip install pinecone-client"
            )
        
        api_key = self.config.connection_params.get("api_key")
        if not api_key:
            raise ValueError("Pinecone API key required in connection_params")
        
        index_name = self.config.connection_params.get("index_name", "topokit-index")
        environment = self.config.connection_params.get("environment", "us-west1-gcp")
        
        self._client = Pinecone(api_key=api_key)
        self._index = self._client.Index(index_name)
        
        # Initialize embedding client if OpenAI available
        if OPENAI_EMBEDDINGS_AVAILABLE:
            openai_key = self.config.connection_params.get("openai_api_key")
            if openai_key:
                self._embedding_client = OpenAIClient(api_key=openai_key)
        
        logger.info(f"Pinecone adapter initialized with index: {index_name}")
    
    async def _embed_query(self, query: str) -> List[float]:
        """Generate embeddings for query."""
        if self._embedding_client:
            # Use OpenAI embeddings
            response = self._embedding_client.embeddings.create(
                model="text-embedding-3-small",
                input=query,
            )
            return response.data[0].embedding
        else:
            # Use simple token-based embedding (placeholder)
            # In production, use a proper embedding model
            import hashlib
            hash_obj = hashlib.md5(query.encode())
            hash_int = int(hash_obj.hexdigest(), 16)
            # Return 384-dim vector (Pinecone default)
            return [(hash_int % 1000) / 1000.0 for _ in range(384)]
    
    async def _similarity_search(
        self,
        query_embeddings: List[float],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Perform similarity search."""
        if not self._index:
            raise RuntimeError("Pinecone index not initialized")
        
        # Query Pinecone
        results = self._index.query(
            vector=query_embeddings,
            top_k=top_k,
            include_metadata=True,
        )
        
        # Format results
        formatted_results = []
        for match in results.matches:
            formatted_results.append({
                "id": match.id,
                "score": match.score,
                "metadata": match.metadata or {},
                "text": match.metadata.get("text", "") if match.metadata else "",
            })
        
        return formatted_results
    
    async def _health_check_impl(self) -> bool:
        """Check Pinecone health."""
        if not self._index:
            return False
        
        try:
            # Simple health check - query with empty vector
            self._index.query(
                vector=[0.0] * 384,  # Default dimension
                top_k=1,
            )
            return True
        except Exception as e:
            logger.error(f"Pinecone health check failed: {e}")
            return False
    
    async def _cleanup_impl(self) -> None:
        """Cleanup Pinecone resources."""
        self._index = None
        self._client = None
        self._embedding_client = None


# Register adapter
if PINECONE_AVAILABLE:
    register_adapter("pinecone", PineconeAdapter)

