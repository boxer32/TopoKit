"""Contract test for multi-agent workflows in TopoKit."""

import pytest
import tempfile
import shutil
from pathlib import Path
from topokit.core.pack_parser import EnhancedPackParser, PackParseError, PackParseResult
from topokit.core.orchestrator import EnhancedTopoOrchestrator
from topokit.types.topology import TopologyPack, Node, EdgePolicy, Contract, GuardrailsConfig, NodeScope


class TestMultiAgentWorkflows:
    """Contract tests for multi-agent workflows."""
    
    @pytest.fixture
    def multi_agent_topology_dir(self):
        """Create a temporary directory with multi-agent topology files."""
        temp_dir = tempfile.mkdtemp()
        topology_dir = Path(temp_dir) / "topology"
        topology_dir.mkdir()
        
        # Create nodes.yaml with multiple agent nodes
        nodes_yaml = """nodes:
  - id: "Agent.Orchestrator"
    kind: "ai"
    version: "1.0.0"
    scope:
      contracts: ["coordinate"]
      context_required: true
    execution_profile:
      temperature: 0.3
      top_p: 0.9
      seed: "stable"
      max_tokens: 2000
      deterministic_reranker: true
    slos:
      schema_pass_rate: "≥ 99%"
      drift_threshold: "≤ 10%"
      latency_budget: "≤ 2000ms"
    circuit_breaker:
      failure_threshold: 3
      timeout_ms: 3000
  - id: "Agent.Researcher"
    kind: "ai"
    version: "1.0.0"
    scope:
      contracts: ["research"]
      context_required: true
    execution_profile:
      temperature: 0.2
      top_p: 0.9
      seed: "stable"
      max_tokens: 1500
      deterministic_reranker: true
    slos:
      schema_pass_rate: "≥ 99%"
      drift_threshold: "≤ 10%"
      latency_budget: "≤ 1500ms"
    circuit_breaker:
      failure_threshold: 3
      timeout_ms: 2000
  - id: "Agent.Analyst"
    kind: "ai"
    version: "1.0.0"
    scope:
      contracts: ["analyze"]
      context_required: true
    execution_profile:
      temperature: 0.2
      top_p: 0.9
      seed: "stable"
      max_tokens: 1500
      deterministic_reranker: true
    slos:
      schema_pass_rate: "≥ 99%"
      drift_threshold: "≤ 10%"
      latency_budget: "≤ 1500ms"
    circuit_breaker:
      failure_threshold: 3
      timeout_ms: 2000
  - id: "Agent.Synthesizer"
    kind: "ai"
    version: "1.0.0"
    scope:
      contracts: ["synthesize"]
      context_required: true
    execution_profile:
      temperature: 0.3
      top_p: 0.9
      seed: "stable"
      max_tokens: 2000
      deterministic_reranker: true
    slos:
      schema_pass_rate: "≥ 99%"
      drift_threshold: "≤ 10%"
      latency_budget: "≤ 2000ms"
    circuit_breaker:
      failure_threshold: 3
      timeout_ms: 3000
"""
        (topology_dir / "nodes.yaml").write_text(nodes_yaml)
        
        # Create edges.yaml with multi-agent coordination edges
        edges_yaml = """edges:
  - id: "Agent.Orchestrator_to_Agent.Researcher"
    from: "Agent.Orchestrator"
    to: "Agent.Researcher"
    version: "1.0.0"
    contracts: ["research"]
    allow: true
    timeout_ms: 5000
    max_retries: 2
  - id: "Agent.Orchestrator_to_Agent.Analyst"
    from: "Agent.Orchestrator"
    to: "Agent.Analyst"
    version: "1.0.0"
    contracts: ["analyze"]
    allow: true
    timeout_ms: 5000
    max_retries: 2
  - id: "Agent.Researcher_to_Agent.Synthesizer"
    from: "Agent.Researcher"
    to: "Agent.Synthesizer"
    version: "1.0.0"
    contracts: ["synthesize"]
    allow: true
    timeout_ms: 5000
    max_retries: 2
  - id: "Agent.Analyst_to_Agent.Synthesizer"
    from: "Agent.Analyst"
    to: "Agent.Synthesizer"
    version: "1.0.0"
    contracts: ["synthesize"]
    allow: true
    timeout_ms: 5000
    max_retries: 2
"""
        (topology_dir / "edges.yaml").write_text(edges_yaml)
        
        # Create contracts directory and contract files
        contracts_dir = topology_dir / "contracts"
        contracts_dir.mkdir()
        
        contracts = [
            {
                "name": "coordinate",
                "description": "Contract for orchestrator coordination",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string"},
                        "agents": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["task", "agents"]
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "coordination": {"type": "object"},
                        "agent_tasks": {"type": "array"}
                    },
                    "required": ["coordination", "agent_tasks"]
                }
            },
            {
                "name": "research",
                "description": "Contract for research agent",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string"},
                        "scope": {"type": "string"}
                    },
                    "required": ["topic", "scope"]
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "findings": {"type": "array"},
                        "sources": {"type": "array"}
                    },
                    "required": ["findings", "sources"]
                }
            },
            {
                "name": "analyze",
                "description": "Contract for analysis agent",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "data": {"type": "object"},
                        "criteria": {"type": "array"}
                    },
                    "required": ["data", "criteria"]
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "analysis": {"type": "object"},
                        "insights": {"type": "array"}
                    },
                    "required": ["analysis", "insights"]
                }
            },
            {
                "name": "synthesize",
                "description": "Contract for synthesis agent",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "research": {"type": "object"},
                        "analysis": {"type": "object"}
                    },
                    "required": ["research", "analysis"]
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "synthesis": {"type": "object"},
                        "conclusions": {"type": "array"}
                    },
                    "required": ["synthesis", "conclusions"]
                }
            }
        ]
        
        for contract_data in contracts:
            contract_json = f"""{{
  "name": "{contract_data['name']}",
  "version": "1.0.0",
  "input_schema": {str(contract_data['input_schema']).replace("'", '"')},
  "output_schema": {str(contract_data['output_schema']).replace("'", '"')},
  "description": "{contract_data['description']}"
}}
"""
            (contracts_dir / f"{contract_data['name']}.json").write_text(contract_json)
        
        # Create guardrails.yaml
        guardrails_yaml = """determinism:
  temperature: 0.3
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

observability:
  enabled: true
  logging_level: "info"
"""
        (topology_dir / "guardrails.yaml").write_text(guardrails_yaml)
        
        yield str(topology_dir)
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    def test_multi_agent_workflow_contract(self, multi_agent_topology_dir):
        """Contract test: Multi-agent workflow must parse all required components."""
        parser = EnhancedPackParser(multi_agent_topology_dir, max_parse_time_ms=100)
        result = parser.parse()
        
        # Contract: Must return a PackParseResult
        assert isinstance(result, PackParseResult)
        assert result.success is True
        assert isinstance(result.pack, TopologyPack)
        
        # Contract: Must parse multiple agent nodes
        assert len(result.pack.nodes) >= 3, "Multi-agent workflow must have at least 3 agent nodes"
        
        agent_nodes = [node for node in result.pack.nodes if node.kind == "ai"]
        assert len(agent_nodes) >= 3, "Must have at least 3 AI agent nodes"
        
        # Contract: Must parse coordination edges
        assert len(result.pack.edges) > 0, "Multi-agent workflow must have edges"
        
        # Contract: Must parse contracts for all agents
        assert len(result.pack.contracts) >= 3, "Multi-agent workflow must have contracts"
        
        # Contract: Must complete within parse time limit
        assert result.parse_time_ms < 100, f"Parse time {result.parse_time_ms}ms exceeds limit"
    
    def test_multi_agent_workflow_structure(self, multi_agent_topology_dir):
        """Contract test: Multi-agent workflow must have valid structure."""
        parser = EnhancedPackParser(multi_agent_topology_dir)
        result = parser.parse()
        
        pack = result.pack
        
        # Contract: Must have orchestrator agent
        node_ids = {node.id for node in pack.nodes}
        assert "Agent.Orchestrator" in node_ids, "Must have orchestrator agent"
        
        # Contract: All agent nodes must have context_required: true
        for node in pack.nodes:
            if node.kind == "ai":
                assert node.scope.context_required is True, \
                    f"Agent node {node.id} must require context"
        
        # Contract: Must have edges connecting agents
        agent_edges = [edge for edge in pack.edges 
                      if edge.from_node.startswith("Agent.") and edge.to_node.startswith("Agent.")]
        assert len(agent_edges) > 0, "Must have edges between agents"
        
        # Contract: All edges must reference valid contracts
        contract_names = {contract.name for contract in pack.contracts}
        for edge in pack.edges:
            for contract_ref in edge.contracts:
                assert contract_ref in contract_names or contract_ref == "", \
                    f"Edge {edge.id} references non-existent contract: {contract_ref}"
    
    def test_multi_agent_workflow_orchestrator_compatibility(self, multi_agent_topology_dir):
        """Contract test: Multi-agent workflow must be compatible with orchestrator."""
        parser = EnhancedPackParser(multi_agent_topology_dir)
        result = parser.parse()
        
        pack = result.pack
        
        # Contract: Must be able to create orchestrator from pack
        orchestrator = EnhancedTopoOrchestrator(pack)
        
        # Contract: Orchestrator must build execution graph successfully
        assert orchestrator.pack == pack
        assert len(orchestrator._node_map) == len(pack.nodes)
        assert len(orchestrator._edge_map) == len(pack.edges)
        
        # Contract: Must identify entry points (orchestrator should be entry)
        assert len(orchestrator._entry_points) > 0, "Must have entry points"
        
        # Contract: Must identify exit points (synthesizer should be exit)
        assert len(orchestrator._exit_points) > 0, "Must have exit points"
        
        # Contract: Graph must be a valid DAG (no cycles)
        # This is validated by orchestrator initialization
    
    def test_multi_agent_workflow_coordination(self, multi_agent_topology_dir):
        """Contract test: Multi-agent workflow must support agent coordination."""
        parser = EnhancedPackParser(multi_agent_topology_dir)
        result = parser.parse()
        
        pack = result.pack
        
        # Contract: Must have orchestrator node that coordinates other agents
        orchestrator_node = None
        for node in pack.nodes:
            if node.id == "Agent.Orchestrator":
                orchestrator_node = node
                break
        
        assert orchestrator_node is not None, "Must have orchestrator node"
        assert "coordinate" in orchestrator_node.scope.contracts, \
            "Orchestrator must have coordinate contract"
        
        # Contract: Must have edges from orchestrator to worker agents
        orchestrator_edges = [edge for edge in pack.edges 
                             if edge.from_node == "Agent.Orchestrator"]
        assert len(orchestrator_edges) >= 2, \
            "Orchestrator must coordinate at least 2 worker agents"
        
        # Contract: Must have path from worker agents to synthesizer
        synthesizer_edges = [edge for edge in pack.edges 
                           if edge.to_node == "Agent.Synthesizer"]
        assert len(synthesizer_edges) >= 1, \
            "Must have paths from worker agents to synthesizer"
    
    def test_multi_agent_workflow_contract_validation(self, multi_agent_topology_dir):
        """Contract test: Multi-agent workflow contracts must be valid."""
        parser = EnhancedPackParser(multi_agent_topology_dir)
        result = parser.parse()
        
        pack = result.pack
        
        # Contract: Must have contracts for all agent interactions
        required_contracts = {"coordinate", "research", "analyze", "synthesize"}
        contract_names = {contract.name for contract in pack.contracts}
        
        for required in required_contracts:
            assert required in contract_names, \
                f"Missing required contract: {required}"
        
        # Contract: All contracts must have valid schemas
        for contract in pack.contracts:
            assert contract.input_schema is not None
            assert contract.output_schema is not None
            assert isinstance(contract.input_schema, dict)
            assert isinstance(contract.output_schema, dict)
    
    def test_multi_agent_workflow_performance(self, multi_agent_topology_dir):
        """Contract test: Multi-agent workflow must meet performance requirements."""
        parser = EnhancedPackParser(multi_agent_topology_dir, max_parse_time_ms=100)
        result = parser.parse()
        
        # Contract: Must parse within time limit (<100ms per spec)
        assert result.parse_time_ms < 100, \
            f"Parse time {result.parse_time_ms}ms exceeds <100ms requirement"
        
        # Contract: Must have parse time tracked
        assert result.parse_time_ms > 0

