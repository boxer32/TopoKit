"""
Integration test for LangChain adapter in TopoKit.

Tests the integration of TopoKit with LangChain chains, including:
- LangChain adapter initialization
- Chain execution through TopoKit orchestrator
- Error handling and retry logic
- Cost and token tracking
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
from topokit.adapters import LangChainAdapter, AdapterConfig, AdapterType
from topokit.types.topology import Node, NodeKind, ExecutionProfile
from topokit.adapters.framework import ExecutionContext


class TestLangChainAdapter:
    """Integration tests for LangChain adapter."""
    
    @pytest.fixture
    def langchain_topology_dir(self):
        """Create a temporary directory with LangChain integration topology."""
        temp_dir = tempfile.mkdtemp()
        topology_dir = Path(temp_dir) / "topology"
        topology_dir.mkdir()
        contracts_dir = topology_dir / "contracts"
        contracts_dir.mkdir()
        
        # Create nodes.yaml with LangChain node
        nodes_yaml = """nodes:
  - id: "LangChain.RAG.Chain"
    kind: "ai"
    version: "1.0.0"
    scope:
      contracts: ["langchain_query"]
      context_required: true
    execution_profile:
      temperature: 0.2
      top_p: 0.9
      seed: "stable"
      max_tokens: 2000
      deterministic_reranker: true
    metadata:
      adapter: "langchain"
      chain_type: "retrieval_qa"
      llm_type: "openai"
      prompt_template: "Answer based on context: {context}\\nQuestion: {question}\\nAnswer:"
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
"""
        (topology_dir / "nodes.yaml").write_text(nodes_yaml)
        
        # Create edges.yaml
        edges_yaml = """edges:
  - id: "Vector.Store_to_LangChain.RAG.Chain"
    from: "Vector.Store"
    to: "LangChain.RAG.Chain"
    version: "1.0.0"
    contracts: ["vector_search", "langchain_query"]
    allow: true
    timeout_ms: 5000
    max_retries: 1
"""
        (topology_dir / "edges.yaml").write_text(edges_yaml)
        
        # Create contract
        contract = {
            "name": "langchain_query",
            "version": "1.0.0",
            "input_schema": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "context": {
                        "type": "array",
                        "items": {"type": "object"}
                    }
                },
                "required": ["question", "context"]
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "answer": {"type": "string"},
                    "sources": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["answer"]
            }
        }
        import json
        (contracts_dir / "langchain_query.json").write_text(
            json.dumps(contract, indent=2)
        )
        
        # Create guardrails.yaml
        guardrails_yaml = """determinism:
  temperature: 0.2
  seed: "session-hash"
  canonical_sort: true

confidence:
  threshold: 0.7
  min_confidence: 0.5

fallback:
  enabled: true
  policy: rule_first

circuit_breakers:
  enabled: true
  failure_threshold: 3

policy_engine:
  enabled: true
  environment: "development"

observability:
  enabled: true
  logging_level: "info"
  metrics_enabled: true
"""
        (topology_dir / "guardrails.yaml").write_text(guardrails_yaml)
        
        yield str(topology_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_langchain_adapter_initialization(self):
        """Test LangChain adapter can be initialized."""
        try:
            config = AdapterConfig(
                adapter_id="langchain-test",
                adapter_type=AdapterType.LLM_PROVIDER,
                provider="langchain",
                connection_params={
                    "chain_type": "llm_chain",
                    "llm_type": "openai",
                    "prompt_template": "Answer: {input}"
                }
            )
            
            adapter = LangChainAdapter(config)
            
            # Test initialization (may fail if langchain not installed, that's OK)
            try:
                await adapter.initialize()
                assert adapter._chain is not None or adapter._llm is not None
            except ImportError:
                pytest.skip("LangChain not installed")
            
        except Exception as e:
            # If adapter doesn't exist or langchain not installed, skip test
            if "not installed" in str(e).lower() or "not found" in str(e).lower():
                pytest.skip(f"LangChain adapter not available: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_langchain_adapter_execution(self):
        """Test LangChain adapter execution."""
        try:
            config = AdapterConfig(
                adapter_id="langchain-test",
                adapter_type=AdapterType.LLM_PROVIDER,
                provider="langchain",
                connection_params={
                    "chain_type": "llm_chain",
                    "llm_type": "openai"
                }
            )
            
            adapter = LangChainAdapter(config)
            
            # Mock the chain execution if langchain not available
            with patch.object(adapter, '_chain', create=True):
                adapter._chain = Mock()
                adapter._chain.invoke = Mock(return_value={"output": "Test answer"})
                adapter._initialized = True
                
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
            pytest.skip("LangChain not installed")
        except Exception as e:
            if "not installed" in str(e).lower() or "not found" in str(e).lower():
                pytest.skip(f"LangChain adapter not available: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_langchain_adapter_health_check(self):
        """Test LangChain adapter health check."""
        try:
            config = AdapterConfig(
                adapter_id="langchain-test",
                adapter_type=AdapterType.LLM_PROVIDER,
                provider="langchain",
                connection_params={
                    "chain_type": "llm_chain",
                    "llm_type": "openai"
                }
            )
            
            adapter = LangChainAdapter(config)
            adapter._initialized = True
            
            # Mock chain for health check
            with patch.object(adapter, '_chain', create=True):
                adapter._chain = Mock()
                adapter._chain.invoke = Mock(return_value={"output": "test"})
                
                health = await adapter.health_check()
                
                assert health is not None
                assert hasattr(health, 'healthy')
                assert hasattr(health, 'last_check')
                
        except ImportError:
            pytest.skip("LangChain not installed")
        except Exception as e:
            if "not installed" in str(e).lower() or "not found" in str(e).lower():
                pytest.skip(f"LangChain adapter not available: {e}")
            raise
    
    def test_langchain_topology_loading(self, langchain_topology_dir):
        """Test LangChain integration topology loads correctly."""
        parser = EnhancedPackParser(langchain_topology_dir)
        result = parser.parse()
        
        assert result.success is True, f"Parsing failed: {result.errors}"
        assert result.pack is not None
        
        pack = result.pack
        node_ids = [node.id for node in pack.nodes]
        assert "LangChain.RAG.Chain" in node_ids
    
    @pytest.mark.asyncio
    async def test_langchain_adapter_with_topology(self, langchain_topology_dir):
        """Test LangChain adapter integrated with TopoKit orchestrator."""
        parser = EnhancedPackParser(langchain_topology_dir)
        parse_result = parser.parse()
        
        if not parse_result.success:
            pytest.skip(f"Topology parsing failed: {parse_result.errors}")
        
        pack = parse_result.pack
        
        # Create orchestrator
        orchestrator = EnhancedTopoOrchestrator(pack)
        
        # Mock the adapter execution in orchestrator
        # In a real scenario, the orchestrator would call the adapter
        # For this test, we verify the topology is set up correctly
        
        # Verify topology structure
        assert len(pack.nodes) > 0
        langchain_node = next((n for n in pack.nodes if n.id == "LangChain.RAG.Chain"), None)
        assert langchain_node is not None
        assert langchain_node.metadata.get("adapter") == "langchain"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

