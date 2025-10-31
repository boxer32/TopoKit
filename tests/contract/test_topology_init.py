"""Contract test for topology initialization in TopoKit."""

import pytest
import tempfile
import shutil
from pathlib import Path
from topokit.core.pack_parser import EnhancedPackParser, PackParseError, PackParseResult
from topokit.core.orchestrator import EnhancedTopoOrchestrator
from topokit.types.topology import TopologyPack, Node, EdgePolicy, Contract, GuardrailsConfig, NodeScope
from topokit.types.validation import ValidationError as TopoValidationError


class TestTopologyInitialization:
    """Contract tests for topology initialization."""
    
    @pytest.fixture
    def sample_topology_dir(self):
        """Create a temporary directory with sample topology files."""
        temp_dir = tempfile.mkdtemp()
        topology_dir = Path(temp_dir) / "topology"
        topology_dir.mkdir()
        
        # Create nodes.yaml
        nodes_yaml = """nodes:
  - id: "Test.Node1"
    kind: "data"
    version: "1.0.0"
    scope:
      contracts: ["test_contract"]
      context_required: false
    execution_profile:
      temperature: 0.2
      top_p: 0.9
      seed: "stable"
      max_tokens: 1000
      deterministic_reranker: true
    slos:
      schema_pass_rate: "≥ 99%"
      drift_threshold: "≤ 10%"
      latency_budget: "≤ 1000ms"
    circuit_breaker:
      failure_threshold: 3
      timeout_ms: 2000
    caching:
      enabled: true
      ttl_seconds: 3600
    provenance:
      track_prompt_hash: true
  - id: "Test.Node2"
    kind: "ai"
    version: "1.0.0"
    scope:
      contracts: ["test_contract"]
      context_required: false
    execution_profile:
      temperature: 0.2
      top_p: 0.9
      seed: "stable"
      max_tokens: 1000
      deterministic_reranker: true
    slos:
      schema_pass_rate: "≥ 99%"
      drift_threshold: "≤ 10%"
      latency_budget: "≤ 1000ms"
    circuit_breaker:
      failure_threshold: 3
      timeout_ms: 2000
    caching:
      enabled: true
      ttl_seconds: 3600
    provenance:
      track_prompt_hash: true
"""
        (topology_dir / "nodes.yaml").write_text(nodes_yaml)
        
        # Create edges.yaml
        edges_yaml = """edges:
  - id: "Test.Node1_to_Test.Node2"
    from: "Test.Node1"
    to: "Test.Node2"
    version: "1.0.0"
    contracts: ["test_contract"]
    allow: true
    timeout_ms: 4000
    max_retries: 0
"""
        (topology_dir / "edges.yaml").write_text(edges_yaml)
        
        # Create contracts directory and contract file
        contracts_dir = topology_dir / "contracts"
        contracts_dir.mkdir()
        
        contract_json = """{
  "name": "test_contract",
  "version": "1.0.0",
  "input_schema": {
    "type": "object",
    "properties": {
      "data": {
        "type": "string",
        "description": "Input data"
      }
    },
    "required": ["data"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "result": {
        "type": "string",
        "description": "Output result"
      }
    },
    "required": ["result"]
  },
  "description": "Test contract for topology initialization"
}
"""
        (contracts_dir / "test_contract.json").write_text(contract_json)
        
        # Create guardrails.yaml
        guardrails_yaml = """determinism:
  temperature: 0.2
  seed: "session-hash"
  canonical_sort: true

confidence:
  threshold: 0.6

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
"""
        (topology_dir / "guardrails.yaml").write_text(guardrails_yaml)
        
        yield str(topology_dir)
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    def test_topology_initialization_contract(self, sample_topology_dir):
        """Contract test: Topology initialization must parse all required components."""
        parser = EnhancedPackParser(sample_topology_dir, max_parse_time_ms=100)
        result = parser.parse()
        
        # Contract: Must return a PackParseResult
        assert isinstance(result, PackParseResult)
        assert result.success is True
        assert isinstance(result.pack, TopologyPack)
        
        # Contract: Must parse nodes
        assert len(result.pack.nodes) > 0
        assert all(isinstance(node, Node) for node in result.pack.nodes)
        
        # Contract: Must parse edges
        assert len(result.pack.edges) > 0
        assert all(isinstance(edge, EdgePolicy) for edge in result.pack.edges)
        
        # Contract: Must parse contracts
        assert len(result.pack.contracts) > 0
        assert all(isinstance(contract, Contract) for contract in result.pack.contracts)
        
        # Contract: Must parse guardrails
        assert isinstance(result.pack.guardrails, GuardrailsConfig)
        
        # Contract: Must complete within parse time limit
        assert result.parse_time_ms < 100, f"Parse time {result.parse_time_ms}ms exceeds limit"
    
    def test_topology_initialization_structure(self, sample_topology_dir):
        """Contract test: Initialized topology must have valid structure."""
        parser = EnhancedPackParser(sample_topology_dir)
        result = parser.parse()
        
        pack = result.pack
        
        # Contract: Must have name
        assert pack.name is not None
        assert isinstance(pack.name, str)
        
        # Contract: All nodes must have required fields
        for node in pack.nodes:
            assert node.id is not None
            assert node.kind is not None
            assert isinstance(node.scope, NodeScope)
        
        # Contract: All edges must have from/to nodes that exist
        node_ids = {node.id for node in pack.nodes}
        for edge in pack.edges:
            assert edge.from_node in node_ids, f"Edge references non-existent node: {edge.from_node}"
            assert edge.to_node in node_ids, f"Edge references non-existent node: {edge.to_node}"
        
        # Contract: All contracts must have valid schemas
        for contract in pack.contracts:
            assert contract.name is not None
            assert contract.input_schema is not None
            assert contract.output_schema is not None
            assert isinstance(contract.input_schema, dict)
            assert isinstance(contract.output_schema, dict)
    
    def test_topology_initialization_orchestrator_compatibility(self, sample_topology_dir):
        """Contract test: Initialized topology must be compatible with orchestrator."""
        parser = EnhancedPackParser(sample_topology_dir)
        result = parser.parse()
        
        pack = result.pack
        
        # Contract: Must be able to create orchestrator from pack
        orchestrator = EnhancedTopoOrchestrator(pack)
        
        # Contract: Orchestrator must build execution graph successfully
        assert orchestrator.pack == pack
        assert len(orchestrator._node_map) == len(pack.nodes)
        assert len(orchestrator._edge_map) == len(pack.edges)
        
        # Contract: Must identify entry points
        assert len(orchestrator._entry_points) > 0
        
        # Contract: Must identify exit points
        assert len(orchestrator._exit_points) > 0
        
        # Contract: Graph must be a valid DAG (no cycles)
        # This is validated by orchestrator initialization
    
    def test_topology_initialization_validation(self, sample_topology_dir):
        """Contract test: Initialized topology must pass validation."""
        parser = EnhancedPackParser(sample_topology_dir)
        result = parser.parse()
        
        # Contract: Must have no errors
        assert len(result.errors) == 0, f"Topology has validation errors: {result.errors}"
        
        # Contract: Must pass pack validation
        validation_errors = parser.validate_pack(result.pack)
        assert len(validation_errors) == 0, f"Pack validation failed: {validation_errors}"
    
    def test_topology_initialization_performance(self, sample_topology_dir):
        """Contract test: Topology initialization must meet performance requirements."""
        parser = EnhancedPackParser(sample_topology_dir, max_parse_time_ms=100)
        result = parser.parse()
        
        # Contract: Must parse within time limit (<100ms per spec)
        assert result.parse_time_ms < 100, \
            f"Parse time {result.parse_time_ms}ms exceeds <100ms requirement"
        
        # Contract: Must have parse time tracked
        assert result.parse_time_ms > 0
    
    def test_topology_initialization_error_handling(self):
        """Contract test: Topology initialization must handle errors gracefully."""
        # Contract: Must raise PackParseError for invalid directory
        with pytest.raises(PackParseError, match="Pack directory does not exist"):
            parser = EnhancedPackParser("/nonexistent/directory")
            parser.parse()
        
        # Contract: Must handle missing files gracefully
        temp_dir = tempfile.mkdtemp()
        try:
            topology_dir = Path(temp_dir) / "topology"
            topology_dir.mkdir()
            
            parser = EnhancedPackParser(str(topology_dir))
            result = parser.parse()
            
            # Should still create a pack with empty components
            assert isinstance(result.pack, TopologyPack)
        finally:
            shutil.rmtree(temp_dir)
    
    def test_topology_initialization_contract_compliance(self, sample_topology_dir):
        """Contract test: Initialized topology must comply with contract requirements."""
        parser = EnhancedPackParser(sample_topology_dir)
        result = parser.parse()
        
        pack = result.pack
        
        # Contract: Nodes must reference valid contracts
        contract_names = {contract.name for contract in pack.contracts}
        for node in pack.nodes:
            for contract_ref in node.scope.contracts:
                assert contract_ref in contract_names or contract_ref == "", \
                    f"Node {node.id} references non-existent contract: {contract_ref}"
        
        # Contract: Edges must reference valid contracts
        for edge in pack.edges:
            for contract_ref in edge.contracts:
                assert contract_ref in contract_names or contract_ref == "", \
                    f"Edge {edge.id} references non-existent contract: {contract_ref}"

