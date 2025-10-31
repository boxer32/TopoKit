"""
Integration test for vector database adapters in TopoKit.

Tests the integration of TopoKit with vector databases, including:
- Pinecone adapter
- Weaviate adapter
- Chroma adapter
- Vector search functionality
- Integration with TopoKit orchestrator
"""

import pytest
import tempfile
import shutil
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import os

from topokit.core.pack_parser import EnhancedPackParser
from topokit.core.orchestrator import EnhancedTopoOrchestrator
from topokit.adapters.vectorstores import (
    PineconeAdapter,
    WeaviateAdapter,
    ChromaAdapter,
    BaseVectorStoreAdapter
)
from topokit.adapters import AdapterConfig, AdapterType
from topokit.types.topology import Node, NodeKind, ExecutionProfile
from topokit.adapters.framework import ExecutionContext


class TestVectorStoreAdapters:
    """Integration tests for vector database adapters."""
    
    @pytest.fixture
    def vectorstore_topology_dir(self):
        """Create a temporary directory with vector store integration topology."""
        temp_dir = tempfile.mkdtemp()
        topology_dir = Path(temp_dir) / "topology"
        topology_dir.mkdir()
        contracts_dir = topology_dir / "contracts"
        contracts_dir.mkdir()
        
        # Create nodes.yaml with vector store nodes
        nodes_yaml = """nodes:
  - id: "Vector.Store.Pinecone"
    kind: "data"
    version: "1.0.0"
    scope:
      contracts: ["vector_search"]
      retrieval_scope: ["vec:documents"]
      context_required: true
    execution_profile:
      temperature: 0.0
      top_p: 1.0
      seed: "stable"
      max_tokens: 1000
    metadata:
      adapter: "pinecone"
      index_name: "test-index"
    slos:
      schema_pass_rate: "≥ 99%"
      latency_budget: "≤ 1000ms"
  - id: "Vector.Store.Weaviate"
    kind: "data"
    version: "1.0.0"
    scope:
      contracts: ["vector_search"]
      retrieval_scope: ["vec:documents"]
      context_required: true
    execution_profile:
      temperature: 0.0
      top_p: 1.0
      seed: "stable"
      max_tokens: 1000
    metadata:
      adapter: "weaviate"
      url: "http://localhost:8080"
      class_name: "Document"
    slos:
      schema_pass_rate: "≥ 99%"
      latency_budget: "≤ 1000ms"
  - id: "Vector.Store.Chroma"
    kind: "data"
    version: "1.0.0"
    scope:
      contracts: ["vector_search"]
      retrieval_scope: ["vec:documents"]
      context_required: true
    execution_profile:
      temperature: 0.0
      top_p: 1.0
      seed: "stable"
      max_tokens: 1000
    metadata:
      adapter: "chroma"
      collection_name: "documents"
    slos:
      schema_pass_rate: "≥ 99%"
      latency_budget: "≤ 1000ms"
"""
        (topology_dir / "nodes.yaml").write_text(nodes_yaml)
        
        # Create edges.yaml
        edges_yaml = """edges:
  - id: "Vector.Store_to_AI.Processor"
    from: "Vector.Store.Pinecone"
    to: "AI.Processor"
    version: "1.0.0"
    contracts: ["vector_search", "ai_process"]
    allow: true
    timeout_ms: 3000
"""
        (topology_dir / "edges.yaml").write_text(edges_yaml)
        
        # Create contract
        contract = {
            "name": "vector_search",
            "version": "1.0.0",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "top_k": {"type": "number", "default": 5},
                    "filters": {"type": "object"}
                },
                "required": ["query"]
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "documents": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string"},
                                "score": {"type": "number"},
                                "metadata": {"type": "object"}
                            }
                        }
                    },
                    "total_found": {"type": "number"}
                },
                "required": ["documents"]
            }
        }
        import json
        (contracts_dir / "vector_search.json").write_text(
            json.dumps(contract, indent=2)
        )
        
        # Create guardrails.yaml
        guardrails_yaml = """determinism:
  temperature: 0.0
  seed: "stable"
  canonical_sort: true

confidence:
  threshold: 0.8

fallback:
  enabled: true
  policy: rule_first

circuit_breakers:
  enabled: true
  failure_threshold: 3
"""
        (topology_dir / "guardrails.yaml").write_text(guardrails_yaml)
        
        yield str(topology_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("adapter_class,provider,config_params", [
        (PineconeAdapter, "pinecone", {
            "api_key": "test-key",
            "index_name": "test-index"
        }),
        (WeaviateAdapter, "weaviate", {
            "url": "http://localhost:8080",
            "class_name": "Document"
        }),
        (ChromaAdapter, "chroma", {
            "collection_name": "test-collection",
            "persist_directory": None
        }),
    ])
    async def test_vectorstore_adapter_initialization(
        self, adapter_class, provider, config_params
    ):
        """Test vector store adapter initialization."""
        try:
            config = AdapterConfig(
                adapter_id=f"{provider}-test",
                adapter_type=AdapterType.VECTOR_DATABASE,
                provider=provider,
                connection_params=config_params
            )
            
            adapter = adapter_class(config)
            
            # Test initialization (may fail if library not installed)
            try:
                await adapter.initialize()
                assert adapter._initialized is True
            except ImportError:
                pytest.skip(f"{provider} library not installed")
            except Exception as e:
                # For adapters that require actual connections, skip if connection fails
                if "connection" in str(e).lower() or "connect" in str(e).lower():
                    pytest.skip(f"{provider} connection not available: {e}")
                raise
            
        except Exception as e:
            if "not installed" in str(e).lower() or "not found" in str(e).lower():
                pytest.skip(f"{provider} adapter not available: {e}")
            raise
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("adapter_class,provider", [
        (PineconeAdapter, "pinecone"),
        (WeaviateAdapter, "weaviate"),
        (ChromaAdapter, "chroma"),
    ])
    async def test_vectorstore_adapter_query(
        self, adapter_class, provider
    ):
        """Test vector store adapter query execution."""
        try:
            config_params = {
                "pinecone": {"api_key": "test-key", "index_name": "test-index"},
                "weaviate": {"url": "http://localhost:8080", "class_name": "Document"},
                "chroma": {"collection_name": "test-collection"},
            }
            
            config = AdapterConfig(
                adapter_id=f"{provider}-test",
                adapter_type=AdapterType.VECTOR_DATABASE,
                provider=provider,
                connection_params=config_params[provider]
            )
            
            adapter = adapter_class(config)
            adapter._initialized = True
            
            # Mock similarity search
            with patch.object(adapter, '_similarity_search', new_callable=AsyncMock):
                adapter._similarity_search = AsyncMock(return_value=[
                    {
                        "id": "doc1",
                        "score": 0.95,
                        "text": "Test document content",
                        "metadata": {}
                    }
                ])
                
                # Mock embed query
                with patch.object(adapter, '_embed_query', new_callable=AsyncMock):
                    adapter._embed_query = AsyncMock(return_value=[0.1] * 384)
                    
                    node = Node(
                        id="test-node",
                        kind=NodeKind.DATA,
                    )
                    
                    context = ExecutionContext(
                        node=node,
                        session_id="test-session",
                        trace_id="test-trace",
                        input_data={"query": "test query"},
                        execution_profile=ExecutionProfile()
                    )
                    
                    result = await adapter.execute(context)
                    
                    assert result.success is True
                    assert result.output_data is not None
                    assert "results" in result.output_data or "documents" in result.output_data
                    
        except ImportError:
            pytest.skip(f"{provider} library not installed")
        except Exception as e:
            if "not installed" in str(e).lower() or "not found" in str(e).lower():
                pytest.skip(f"{provider} adapter not available: {e}")
            raise
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("adapter_class,provider", [
        (PineconeAdapter, "pinecone"),
        (WeaviateAdapter, "weaviate"),
        (ChromaAdapter, "chroma"),
    ])
    async def test_vectorstore_adapter_health_check(
        self, adapter_class, provider
    ):
        """Test vector store adapter health check."""
        try:
            config_params = {
                "pinecone": {"api_key": "test-key", "index_name": "test-index"},
                "weaviate": {"url": "http://localhost:8080"},
                "chroma": {"collection_name": "test-collection"},
            }
            
            config = AdapterConfig(
                adapter_id=f"{provider}-test",
                adapter_type=AdapterType.VECTOR_DATABASE,
                provider=provider,
                connection_params=config_params[provider]
            )
            
            adapter = adapter_class(config)
            adapter._initialized = True
            
            # Mock health check
            try:
                health = await adapter.health_check()
                assert health is not None
                assert hasattr(health, 'healthy')
                assert hasattr(health, 'last_check')
            except Exception as e:
                # If health check requires actual connection, skip
                if "connection" in str(e).lower() or "connect" in str(e).lower():
                    pytest.skip(f"{provider} connection not available for health check")
                raise
                    
        except ImportError:
            pytest.skip(f"{provider} library not installed")
        except Exception as e:
            if "not installed" in str(e).lower():
                pytest.skip(f"{provider} adapter not available: {e}")
            raise
    
    def test_vectorstore_topology_loading(self, vectorstore_topology_dir):
        """Test vector store integration topology loads correctly."""
        parser = EnhancedPackParser(vectorstore_topology_dir)
        result = parser.parse()
        
        assert result.success is True, f"Parsing failed: {result.errors}"
        assert result.pack is not None
        
        pack = result.pack
        node_ids = [node.id for node in pack.nodes]
        assert "Vector.Store.Pinecone" in node_ids
        assert "Vector.Store.Weaviate" in node_ids
        assert "Vector.Store.Chroma" in node_ids
    
    @pytest.mark.asyncio
    async def test_vectorstore_adapters_with_topology(self, vectorstore_topology_dir):
        """Test vector store adapters integrated with TopoKit orchestrator."""
        parser = EnhancedPackParser(vectorstore_topology_dir)
        parse_result = parser.parse()
        
        if not parse_result.success:
            pytest.skip(f"Topology parsing failed: {parse_result.errors}")
        
        pack = parse_result.pack
        
        # Verify topology structure
        assert len(pack.nodes) > 0
        
        # Check each vector store adapter
        pinecone_node = next((n for n in pack.nodes if n.id == "Vector.Store.Pinecone"), None)
        assert pinecone_node is not None
        assert pinecone_node.metadata.get("adapter") == "pinecone"
        
        weaviate_node = next((n for n in pack.nodes if n.id == "Vector.Store.Weaviate"), None)
        assert weaviate_node is not None
        assert weaviate_node.metadata.get("adapter") == "weaviate"
        
        chroma_node = next((n for n in pack.nodes if n.id == "Vector.Store.Chroma"), None)
        assert chroma_node is not None
        assert chroma_node.metadata.get("adapter") == "chroma"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

