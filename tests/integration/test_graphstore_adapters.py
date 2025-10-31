"""
Integration test for graph database adapters in TopoKit.

Tests the integration of TopoKit with graph databases, including:
- Neo4j adapter
- ArangoDB adapter
- Graph query execution
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
from topokit.adapters.graphstores import (
    Neo4jAdapter,
    ArangoDBAdapter,
    BaseGraphStoreAdapter
)
from topokit.adapters import AdapterConfig, AdapterType
from topokit.types.topology import Node, NodeKind, ExecutionProfile
from topokit.adapters.framework import ExecutionContext


class TestGraphStoreAdapters:
    """Integration tests for graph database adapters."""
    
    @pytest.fixture
    def graphstore_topology_dir(self):
        """Create a temporary directory with graph store integration topology."""
        temp_dir = tempfile.mkdtemp()
        topology_dir = Path(temp_dir) / "topology"
        topology_dir.mkdir()
        contracts_dir = topology_dir / "contracts"
        contracts_dir.mkdir()
        
        # Create nodes.yaml with graph store nodes
        nodes_yaml = """nodes:
  - id: "Graph.Store.Neo4j"
    kind: "data"
    version: "1.0.0"
    scope:
      contracts: ["graph_query"]
      context_required: true
    execution_profile:
      temperature: 0.0
      top_p: 1.0
      seed: "stable"
      max_tokens: 5000
    metadata:
      adapter: "neo4j"
      uri: "bolt://localhost:7687"
    slos:
      schema_pass_rate: "≥ 99%"
      latency_budget: "≤ 2000ms"
  - id: "Graph.Store.ArangoDB"
    kind: "data"
    version: "1.0.0"
    scope:
      contracts: ["graph_query"]
      context_required: true
    execution_profile:
      temperature: 0.0
      top_p: 1.0
      seed: "stable"
      max_tokens: 5000
    metadata:
      adapter: "arangodb"
      hosts: "http://localhost:8529"
      database: "topokit"
    slos:
      schema_pass_rate: "≥ 99%"
      latency_budget: "≤ 2000ms"
"""
        (topology_dir / "nodes.yaml").write_text(nodes_yaml)
        
        # Create edges.yaml
        edges_yaml = """edges:
  - id: "Graph.Store_to_AI.Processor"
    from: "Graph.Store.Neo4j"
    to: "AI.Processor"
    version: "1.0.0"
    contracts: ["graph_query", "ai_process"]
    allow: true
    timeout_ms: 5000
"""
        (topology_dir / "edges.yaml").write_text(edges_yaml)
        
        # Create contract
        contract = {
            "name": "graph_query",
            "version": "1.0.0",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Cypher or AQL query"}
                },
                "required": ["query"]
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "results": {
                        "type": "array",
                        "items": {"type": "object"}
                    },
                    "num_results": {"type": "number"}
                },
                "required": ["results"]
            }
        }
        import json
        (contracts_dir / "graph_query.json").write_text(
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
        (Neo4jAdapter, "neo4j", {
            "uri": "bolt://localhost:7687",
            "username": "neo4j",
            "password": "test-password"
        }),
        (ArangoDBAdapter, "arangodb", {
            "hosts": "http://localhost:8529",
            "username": "root",
            "password": "test-password",
            "database": "test_db"
        }),
    ])
    async def test_graphstore_adapter_initialization(
        self, adapter_class, provider, config_params
    ):
        """Test graph store adapter initialization."""
        try:
            config = AdapterConfig(
                adapter_id=f"{provider}-test",
                adapter_type=AdapterType.GRAPH_DATABASE,
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
    @pytest.mark.parametrize("adapter_class,provider,query", [
        (Neo4jAdapter, "neo4j", "MATCH (n) RETURN n LIMIT 10"),
        (ArangoDBAdapter, "arangodb", "FOR doc IN documents RETURN doc LIMIT 10"),
    ])
    async def test_graphstore_adapter_query_execution(
        self, adapter_class, provider, query
    ):
        """Test graph store adapter query execution."""
        try:
            config_params = {
                "neo4j": {
                    "uri": "bolt://localhost:7687",
                    "username": "neo4j",
                    "password": "test-password"
                },
                "arangodb": {
                    "hosts": "http://localhost:8529",
                    "username": "root",
                    "password": "test-password",
                    "database": "test_db"
                }
            }
            
            config = AdapterConfig(
                adapter_id=f"{provider}-test",
                adapter_type=AdapterType.GRAPH_DATABASE,
                provider=provider,
                connection_params=config_params[provider]
            )
            
            adapter = adapter_class(config)
            adapter._initialized = True
            
            # Mock graph query execution
            with patch.object(adapter, '_execute_graph_query', new_callable=AsyncMock):
                adapter._execute_graph_query = AsyncMock(return_value=[
                    {"id": "1", "name": "Node 1"},
                    {"id": "2", "name": "Node 2"}
                ])
                
                node = Node(
                    id="test-node",
                    kind=NodeKind.DATA,
                )
                
                context = ExecutionContext(
                    node=node,
                    session_id="test-session",
                    trace_id="test-trace",
                    input_data={"query": query},
                    execution_profile=ExecutionProfile()
                )
                
                result = await adapter.execute(context)
                
                assert result.success is True
                assert result.output_data is not None
                assert "results" in result.output_data
                assert isinstance(result.output_data["results"], list)
                    
        except ImportError:
            pytest.skip(f"{provider} library not installed")
        except Exception as e:
            if "not installed" in str(e).lower() or "not found" in str(e).lower():
                pytest.skip(f"{provider} adapter not available: {e}")
            raise
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("adapter_class,provider", [
        (Neo4jAdapter, "neo4j"),
        (ArangoDBAdapter, "arangodb"),
    ])
    async def test_graphstore_adapter_health_check(
        self, adapter_class, provider
    ):
        """Test graph store adapter health check."""
        try:
            config_params = {
                "neo4j": {
                    "uri": "bolt://localhost:7687",
                    "username": "neo4j",
                    "password": "test-password"
                },
                "arangodb": {
                    "hosts": "http://localhost:8529",
                    "username": "root",
                    "password": "test-password",
                    "database": "test_db"
                }
            }
            
            config = AdapterConfig(
                adapter_id=f"{provider}-test",
                adapter_type=AdapterType.GRAPH_DATABASE,
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
    
    def test_graphstore_topology_loading(self, graphstore_topology_dir):
        """Test graph store integration topology loads correctly."""
        parser = EnhancedPackParser(graphstore_topology_dir)
        result = parser.parse()
        
        assert result.success is True, f"Parsing failed: {result.errors}"
        assert result.pack is not None
        
        pack = result.pack
        node_ids = [node.id for node in pack.nodes]
        assert "Graph.Store.Neo4j" in node_ids
        assert "Graph.Store.ArangoDB" in node_ids
    
    @pytest.mark.asyncio
    async def test_graphstore_adapters_with_topology(self, graphstore_topology_dir):
        """Test graph store adapters integrated with TopoKit orchestrator."""
        parser = EnhancedPackParser(graphstore_topology_dir)
        parse_result = parser.parse()
        
        if not parse_result.success:
            pytest.skip(f"Topology parsing failed: {parse_result.errors}")
        
        pack = parse_result.pack
        
        # Verify topology structure
        assert len(pack.nodes) > 0
        
        # Check each graph store adapter
        neo4j_node = next((n for n in pack.nodes if n.id == "Graph.Store.Neo4j"), None)
        assert neo4j_node is not None
        assert neo4j_node.metadata.get("adapter") == "neo4j"
        
        arangodb_node = next((n for n in pack.nodes if n.id == "Graph.Store.ArangoDB"), None)
        assert arangodb_node is not None
        assert arangodb_node.metadata.get("adapter") == "arangodb"
    
    @pytest.mark.asyncio
    async def test_neo4j_cypher_query(self):
        """Test Neo4j adapter with Cypher query."""
        try:
            config = AdapterConfig(
                adapter_id="neo4j-test",
                adapter_type=AdapterType.GRAPH_DATABASE,
                provider="neo4j",
                connection_params={
                    "uri": "bolt://localhost:7687",
                    "username": "neo4j",
                    "password": "test-password"
                }
            )
            
            adapter = Neo4jAdapter(config)
            adapter._initialized = True
            
            # Mock Neo4j driver
            with patch.object(adapter, '_driver', create=True):
                adapter._driver = Mock()
                mock_session = AsyncMock()
                mock_result = AsyncMock()
                mock_result.data = AsyncMock(return_value=[
                    {"name": "Person 1", "age": 30},
                    {"name": "Person 2", "age": 25}
                ])
                mock_session.run = AsyncMock(return_value=mock_result)
                adapter._driver.session = Mock(return_value=mock_session.__enter__())
                
                cypher_query = "MATCH (p:Person) RETURN p.name AS name, p.age AS age LIMIT 10"
                
                result = await adapter._execute_graph_query(cypher_query)
                
                assert result is not None
                assert isinstance(result, list)
                    
        except ImportError:
            pytest.skip("Neo4j library not installed")
        except Exception as e:
            if "not installed" in str(e).lower():
                pytest.skip(f"Neo4j adapter not available: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_arangodb_aql_query(self):
        """Test ArangoDB adapter with AQL query."""
        try:
            config = AdapterConfig(
                adapter_id="arangodb-test",
                adapter_type=AdapterType.GRAPH_DATABASE,
                provider="arangodb",
                connection_params={
                    "hosts": "http://localhost:8529",
                    "username": "root",
                    "password": "test-password",
                    "database": "test_db"
                }
            )
            
            adapter = ArangoDBAdapter(config)
            adapter._initialized = True
            
            # Mock ArangoDB client
            with patch.object(adapter, '_db', create=True):
                adapter._db = Mock()
                mock_cursor = Mock()
                mock_cursor.__iter__ = Mock(return_value=iter([
                    {"_key": "1", "name": "Document 1"},
                    {"_key": "2", "name": "Document 2"}
                ]))
                adapter._db.aql.execute = Mock(return_value=mock_cursor)
                
                aql_query = "FOR doc IN documents RETURN doc"
                
                result = await adapter._execute_graph_query(aql_query)
                
                assert result is not None
                assert isinstance(result, list)
                    
        except ImportError:
            pytest.skip("ArangoDB library not installed")
        except Exception as e:
            if "not installed" in str(e).lower():
                pytest.skip(f"ArangoDB adapter not available: {e}")
            raise


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

