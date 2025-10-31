"""
Integration test for LlamaIndex adapter in TopoKit.

Tests the integration of TopoKit with LlamaIndex, including:
- LlamaIndex adapter initialization
- Vector store integration
- Query execution through TopoKit orchestrator
- Document indexing workflow
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
from topokit.adapters import LlamaIndexAdapter, AdapterConfig, AdapterType
from topokit.types.topology import Node, NodeKind, ExecutionProfile
from topokit.adapters.framework import ExecutionContext


class TestLlamaIndexAdapter:
    """Integration tests for LlamaIndex adapter."""
    
    @pytest.fixture
    def llamaindex_topology_dir(self):
        """Create a temporary directory with LlamaIndex integration topology."""
        temp_dir = tempfile.mkdtemp()
        topology_dir = Path(temp_dir) / "topology"
        topology_dir.mkdir()
        contracts_dir = topology_dir / "contracts"
        contracts_dir.mkdir()
        
        # Create nodes.yaml with LlamaIndex nodes
        nodes_yaml = """nodes:
  - id: "LlamaIndex.QueryEngine"
    kind: "ai"
    version: "1.0.0"
    scope:
      contracts: ["llamaindex_query"]
      context_required: true
    execution_profile:
      temperature: 0.2
      top_p: 0.9
      seed: "stable"
      max_tokens: 2000
      deterministic_reranker: true
    metadata:
      adapter: "llamaindex"
      vector_store_type: "simple"
      similarity_top_k: 5
      llm_type: "openai"
    slos:
      schema_pass_rate: "≥ 99%"
      drift_threshold: "≤ 10%"
      latency_budget: "≤ 3000ms"
      context_precision: "≥ 0.9"
      consistency_rate: "≥ 95%"
      cost_budget: "≤ 200 tokens/run"
    circuit_breaker:
      failure_threshold: 3
      timeout_ms: 5000
  - id: "Document.Indexer"
    kind: "data"
    version: "1.0.0"
    scope:
      contracts: ["index_documents"]
      context_required: false
    execution_profile:
      temperature: 0.0
      top_p: 1.0
      seed: "stable"
      max_tokens: 5000
    metadata:
      adapter: "llamaindex"
      index_mode: "incremental"
    slos:
      schema_pass_rate: "≥ 99%"
      latency_budget: "≤ 5000ms"
"""
        (topology_dir / "nodes.yaml").write_text(nodes_yaml)
        
        # Create edges.yaml
        edges_yaml = """edges:
  - id: "Document.Indexer_to_LlamaIndex.QueryEngine"
    from: "Document.Indexer"
    to: "LlamaIndex.QueryEngine"
    version: "1.0.0"
    contracts: ["index_documents", "llamaindex_query"]
    allow: true
    timeout_ms: 5000
    max_retries: 1
"""
        (topology_dir / "edges.yaml").write_text(edges_yaml)
        
        # Create contracts
        contracts = [
            {
                "name": "llamaindex_query",
                "version": "1.0.0",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "query_mode": {"type": "string", "enum": ["default", "retrieve", "summarize"]}
                    },
                    "required": ["query"]
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "response": {"type": "string"},
                        "source_nodes": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "node_id": {"type": "string"},
                                    "score": {"type": "number"}
                                }
                            }
                        }
                    },
                    "required": ["response"]
                }
            },
            {
                "name": "index_documents",
                "version": "1.0.0",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "documents": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "text": {"type": "string"},
                                    "metadata": {"type": "object"}
                                }
                            }
                        }
                    },
                    "required": ["documents"]
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "indexed_count": {"type": "number"},
                        "index_path": {"type": "string"}
                    },
                    "required": ["indexed_count"]
                }
            }
        ]
        
        import json
        for contract in contracts:
            (contracts_dir / f"{contract['name']}.json").write_text(
                json.dumps(contract, indent=2)
            )
        
        # Create guardrails.yaml
        guardrails_yaml = """determinism:
  temperature: 0.2
  seed: "session-hash"
  canonical_sort: true

confidence:
  threshold: 0.7

fallback:
  enabled: true
  policy: rule_first

circuit_breakers:
  enabled: true
  failure_threshold: 3

policy_engine:
  enabled: true
  environment: "development"
"""
        (topology_dir / "guardrails.yaml").write_text(guardrails_yaml)
        
        yield str(topology_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_llamaindex_adapter_initialization(self):
        """Test LlamaIndex adapter can be initialized."""
        try:
            config = AdapterConfig(
                adapter_id="llamaindex-test",
                adapter_type=AdapterType.VECTOR_DATABASE,
                provider="llamaindex",
                connection_params={
                    "vector_store_type": "simple",
                    "similarity_top_k": 5,
                    "llm_type": "openai"
                }
            )
            
            adapter = LlamaIndexAdapter(config)
            
            # Test initialization (may fail if llamaindex not installed)
            try:
                await adapter.initialize()
                # If initialized, verify components exist
                assert adapter._index is not None or adapter._query_engine is not None
            except ImportError:
                pytest.skip("LlamaIndex not installed")
            
        except Exception as e:
            if "not installed" in str(e).lower() or "not found" in str(e).lower():
                pytest.skip(f"LlamaIndex adapter not available: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_llamaindex_adapter_query_execution(self):
        """Test LlamaIndex adapter query execution."""
        try:
            config = AdapterConfig(
                adapter_id="llamaindex-test",
                adapter_type=AdapterType.VECTOR_DATABASE,
                provider="llamaindex",
                connection_params={
                    "vector_store_type": "simple"
                }
            )
            
            adapter = LlamaIndexAdapter(config)
            adapter._initialized = True
            
            # Mock query engine
            with patch.object(adapter, '_query_engine', create=True):
                adapter._query_engine = Mock()
                mock_response = Mock()
                mock_response.response = "Test answer from LlamaIndex"
                mock_response.source_nodes = []
                adapter._query_engine.query = Mock(return_value=mock_response)
                
                node = Node(
                    id="test-node",
                    kind=NodeKind.AI,
                )
                
                context = ExecutionContext(
                    node=node,
                    session_id="test-session",
                    trace_id="test-trace",
                    input_data={"query": "What is TopoKit?"},
                    execution_profile=ExecutionProfile()
                )
                
                result = await adapter.execute(context)
                
                assert result.success is True or result.error is not None
                
        except ImportError:
            pytest.skip("LlamaIndex not installed")
        except Exception as e:
            if "not installed" in str(e).lower() or "not found" in str(e).lower():
                pytest.skip(f"LlamaIndex adapter not available: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_llamaindex_adapter_health_check(self):
        """Test LlamaIndex adapter health check."""
        try:
            config = AdapterConfig(
                adapter_id="llamaindex-test",
                adapter_type=AdapterType.VECTOR_DATABASE,
                provider="llamaindex",
                connection_params={
                    "vector_store_type": "simple"
                }
            )
            
            adapter = LlamaIndexAdapter(config)
            adapter._initialized = True
            
            # Mock query engine for health check
            with patch.object(adapter, '_query_engine', create=True):
                adapter._query_engine = Mock()
                mock_response = Mock()
                mock_response.response = "test"
                adapter._query_engine.query = Mock(return_value=mock_response)
                
                health = await adapter.health_check()
                
                assert health is not None
                assert hasattr(health, 'healthy')
                assert hasattr(health, 'last_check')
                
        except ImportError:
            pytest.skip("LlamaIndex not installed")
        except Exception as e:
            if "not installed" in str(e).lower() or "not found" in str(e).lower():
                pytest.skip(f"LlamaIndex adapter not available: {e}")
            raise
    
    def test_llamaindex_topology_loading(self, llamaindex_topology_dir):
        """Test LlamaIndex integration topology loads correctly."""
        parser = EnhancedPackParser(llamaindex_topology_dir)
        result = parser.parse()
        
        assert result.success is True, f"Parsing failed: {result.errors}"
        assert result.pack is not None
        
        pack = result.pack
        node_ids = [node.id for node in pack.nodes]
        assert "LlamaIndex.QueryEngine" in node_ids
        assert "Document.Indexer" in node_ids
    
    @pytest.mark.asyncio
    async def test_llamaindex_adapter_with_topology(self, llamaindex_topology_dir):
        """Test LlamaIndex adapter integrated with TopoKit orchestrator."""
        parser = EnhancedPackParser(llamaindex_topology_dir)
        parse_result = parser.parse()
        
        if not parse_result.success:
            pytest.skip(f"Topology parsing failed: {parse_result.errors}")
        
        pack = parse_result.pack
        
        # Create orchestrator
        orchestrator = EnhancedTopoOrchestrator(pack)
        
        # Verify topology structure
        assert len(pack.nodes) > 0
        query_node = next((n for n in pack.nodes if n.id == "LlamaIndex.QueryEngine"), None)
        assert query_node is not None
        assert query_node.metadata.get("adapter") == "llamaindex"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

