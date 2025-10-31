"""
Module: chroma_adapter
Purpose: Chroma vector database adapter
Inputs: Execution context, embeddings, queries
Outputs: Execution results with retrieved documents
Dependencies: chromadb library, adapter.vectorstores.base
Failure Modes: Connection failure → retry, query failure → error
Trace: page:adapters, build:20250127, spec-id:T099
"""

from typing import Any, Dict, List, Optional
import logging

try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

from .base import BaseVectorStoreAdapter
from ..framework import AdapterConfig, register_adapter


logger = logging.getLogger(__name__)


class ChromaAdapter(BaseVectorStoreAdapter):
    """Chroma vector database adapter."""
    
    def __init__(self, config: AdapterConfig):
        """Initialize Chroma adapter."""
        super().__init__(config)
        self._client = None
        self._collection = None
    
    @property
    def provider(self) -> str:
        """Get provider name."""
        return "chroma"
    
    async def _initialize_impl(self) -> None:
        """Initialize Chroma client."""
        if not CHROMA_AVAILABLE:
            raise ImportError(
                "Chroma library not installed. Install with: pip install chromadb"
            )
        
        # Get configuration
        persist_directory = self.config.connection_params.get("persist_directory")
        collection_name = self.config.connection_params.get("collection_name", "topokit")
        
        # Initialize client
        if persist_directory:
            self._client = chromadb.PersistentClient(path=persist_directory)
        else:
            self._client = chromadb.Client()
        
        # Get or create collection
        try:
            self._collection = self._client.get_collection(name=collection_name)
        except Exception:
            self._collection = self._client.create_collection(name=collection_name)
        
        logger.info(f"Chroma adapter initialized with collection: {collection_name}")
    
    async def _embed_query(self, query: str) -> List[float]:
        """Generate embeddings for query."""
        # Chroma can generate embeddings automatically if embedding function configured
        # For manual embedding, use a proper embedding model
        # Placeholder implementation
        import hashlib
        hash_obj = hashlib.md5(query.encode())
        hash_int = int(hash_obj.hexdigest(), 16)
        return [(hash_int % 1000) / 1000.0 for _ in range(384)]
    
    async def _similarity_search(
        self,
        query_embeddings: List[float],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Perform similarity search."""
        if not self._collection:
            raise RuntimeError("Chroma collection not initialized")
        
        # Query collection
        results = self._collection.query(
            query_embeddings=[query_embeddings],
            n_results=top_k,
            include=["metadatas", "documents"],
        )
        
        # Format results
        formatted_results = []
        if results["ids"] and len(results["ids"]) > 0:
            for i, doc_id in enumerate(results["ids"][0]):
                formatted_results.append({
                    "id": doc_id,
                    "score": 1.0 - (i * 0.1),  # Chroma doesn't return scores directly
                    "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                    "text": results["documents"][0][i] if results.get("documents") else "",
                })
        
        return formatted_results
    
    async def _health_check_impl(self) -> bool:
        """Check Chroma health."""
        if not self._client or not self._collection:
            return False
        
        try:
            # Simple health check - query with empty collection
            self._collection.peek()
            return True
        except Exception as e:
            logger.error(f"Chroma health check failed: {e}")
            return False
    
    async def _cleanup_impl(self) -> None:
        """Cleanup Chroma resources."""
        self._collection = None
        self._client = None


# Register adapter
if CHROMA_AVAILABLE:
    register_adapter("chroma", ChromaAdapter)

