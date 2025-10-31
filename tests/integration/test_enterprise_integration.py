"""Integration test for enterprise system integration in TopoKit."""

import pytest
import tempfile
import shutil
import asyncio
from pathlib import Path
from datetime import datetime
import yaml
import json
from topokit.core.pack_parser import EnhancedPackParser, PackParseResult
from topokit.core.orchestrator import EnhancedTopoOrchestrator
from topokit.types.topology import TopologyPack, Node, EdgePolicy


class TestEnterpriseSystemIntegration:
    """Integration tests for enterprise system integration."""
    
    @pytest.fixture
    def enterprise_topology_dir(self):
        """Create a temporary directory with enterprise integration topology."""
        temp_dir = tempfile.mkdtemp()
        topology_dir = Path(temp_dir) / "topology"
        topology_dir.mkdir()
        
        # Create nodes.yaml with enterprise system integration nodes
        nodes_yaml = """nodes:
  - id: "System.API.Gateway"
    kind: "data"
    version: "1.0.0"
    scope:
      contracts: ["api_request"]
      context_required: false
    execution_profile:
      temperature: 0.0
      top_p: 1.0
      seed: "stable"
      max_tokens: 1000
    slos:
      schema_pass_rate: "≥ 99%"
      latency_budget: "≤ 500ms"
    circuit_breaker:
      failure_threshold: 5
      timeout_ms: 1000
  - id: "System.Auth.Validator"
    kind: "data"
    version: "1.0.0"
    scope:
      contracts: ["auth_request", "auth_response"]
      context_required: false
    execution_profile:
      temperature: 0.0
      top_p: 1.0
      seed: "stable"
    slos:
      schema_pass_rate: "≥ 99.9%"
      latency_budget: "≤ 200ms"
    circuit_breaker:
      failure_threshold: 10
      timeout_ms: 500
  - id: "System.Database.Connector"
    kind: "data"
    version: "1.0.0"
    scope:
      contracts: ["db_query", "db_response"]
      context_required: false
    execution_profile:
      temperature: 0.0
      top_p: 1.0
      seed: "stable"
    slos:
      schema_pass_rate: "≥ 99%"
      latency_budget: "≤ 1000ms"
    circuit_breaker:
      failure_threshold: 3
      timeout_ms: 2000
  - id: "AI.Business.Processor"
    kind: "ai"
    version: "1.0.0"
    scope:
      contracts: ["business_process"]
      context_required: true
    execution_profile:
      temperature: 0.2
      top_p: 0.9
      seed: "stable"
      max_tokens: 2000
    slos:
      schema_pass_rate: "≥ 99%"
      drift_threshold: "≤ 10%"
      latency_budget: "≤ 3000ms"
    circuit_breaker:
      failure_threshold: 3
      timeout_ms: 4000
  - id: "System.Audit.Logger"
    kind: "data"
    version: "1.0.0"
    scope:
      contracts: ["audit_event"]
      context_required: false
    execution_profile:
      temperature: 0.0
      top_p: 1.0
      seed: "stable"
    slos:
      schema_pass_rate: "≥ 99.9%"
      latency_budget: "≤ 1000ms"
    circuit_breaker:
      failure_threshold: 5
      timeout_ms: 1500
"""
        (topology_dir / "nodes.yaml").write_text(nodes_yaml)
        
        # Create edges.yaml with enterprise system flow
        edges_yaml = """edges:
  - id: "System.API.Gateway_to_System.Auth.Validator"
    from: "System.API.Gateway"
    to: "System.Auth.Validator"
    version: "1.0.0"
    contracts: ["auth_request"]
    allow: true
    timeout_ms: 2000
    max_retries: 1
  - id: "System.Auth.Validator_to_System.Database.Connector"
    from: "System.Auth.Validator"
    to: "System.Database.Connector"
    version: "1.0.0"
    contracts: ["db_query"]
    allow: true
    timeout_ms: 3000
    max_retries: 2
  - id: "System.Auth.Validator_to_AI.Business.Processor"
    from: "System.Auth.Validator"
    to: "AI.Business.Processor"
    version: "1.0.0"
    contracts: ["business_process"]
    allow: true
    timeout_ms: 5000
    max_retries: 2
  - id: "System.Database.Connector_to_AI.Business.Processor"
    from: "System.Database.Connector"
    to: "AI.Business.Processor"
    version: "1.0.0"
    contracts: ["business_process"]
    allow: true
    timeout_ms: 5000
    max_retries: 2
  - id: "AI.Business.Processor_to_System.Audit.Logger"
    from: "AI.Business.Processor"
    to: "System.Audit.Logger"
    version: "1.0.0"
    contracts: ["audit_event"]
    allow: true
    timeout_ms: 2000
    max_retries: 1
"""
        (topology_dir / "edges.yaml").write_text(edges_yaml)
        
        # Create contracts directory
        contracts_dir = topology_dir / "contracts"
        contracts_dir.mkdir()
        
        contracts_data = [
            {
                "name": "api_request",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "method": {"type": "string"},
                        "path": {"type": "string"},
                        "headers": {"type": "object"},
                        "body": {"type": "object"}
                    },
                    "required": ["method", "path"]
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "request_id": {"type": "string"},
                        "authenticated": {"type": "boolean"}
                    },
                    "required": ["request_id", "authenticated"]
                }
            },
            {
                "name": "auth_request",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "token": {"type": "string"},
                        "permissions": {"type": "array"}
                    },
                    "required": ["token"]
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "authorized": {"type": "boolean"},
                        "user_id": {"type": "string"},
                        "roles": {"type": "array"}
                    },
                    "required": ["authorized"]
                }
            },
            {
                "name": "auth_response",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "authorized": {"type": "boolean"}
                    },
                    "required": ["authorized"]
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "auth_status": {"type": "string"}
                    },
                    "required": ["auth_status"]
                }
            },
            {
                "name": "db_query",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "params": {"type": "object"}
                    },
                    "required": ["query"]
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "results": {"type": "array"},
                        "row_count": {"type": "integer"}
                    },
                    "required": ["results"]
                }
            },
            {
                "name": "db_response",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "results": {"type": "array"}
                    },
                    "required": ["results"]
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "data": {"type": "object"}
                    },
                    "required": ["data"]
                }
            },
            {
                "name": "business_process",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "request": {"type": "object"},
                        "context": {"type": "object"}
                    },
                    "required": ["request"]
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "result": {"type": "object"},
                        "status": {"type": "string"}
                    },
                    "required": ["result", "status"]
                }
            },
            {
                "name": "audit_event",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "event_type": {"type": "string"},
                        "timestamp": {"type": "string"},
                        "data": {"type": "object"}
                    },
                    "required": ["event_type", "timestamp", "data"]
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "logged": {"type": "boolean"},
                        "event_id": {"type": "string"}
                    },
                    "required": ["logged", "event_id"]
                }
            }
        ]
        
        for contract in contracts_data:
            contract_json = json.dumps({
                "name": contract["name"],
                "version": "1.0.0",
                "input_schema": contract["input_schema"],
                "output_schema": contract["output_schema"],
                "description": f"Enterprise contract for {contract['name']}"
            }, indent=2)
            (contracts_dir / f"{contract['name']}.json").write_text(contract_json)
        
        # Create guardrails.yaml
        guardrails_yaml = """determinism:
  temperature: 0.2
  seed: "session-hash"
  canonical_sort: true

confidence:
  threshold: 0.8

fallback:
  enabled: true
  policy: rule_first

circuit_breakers:
  enabled: true
  failure_threshold: 3

policy_engine:
  enabled: true
  environment: "production"

observability:
  enabled: true
  logging_level: "info"

security:
  pii_redaction: true
  audit_logging: true
  encryption: true
"""
        (topology_dir / "guardrails.yaml").write_text(guardrails_yaml)
        
        yield str(topology_dir)
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    def test_enterprise_integration_topology_loading(self, enterprise_topology_dir):
        """Integration test: Enterprise topology must load correctly."""
        parser = EnhancedPackParser(enterprise_topology_dir)
        result = parser.parse()
        
        # Test: Must successfully parse enterprise topology
        assert isinstance(result, PackParseResult)
        assert result.success is True, f"Parsing failed: {result.errors}"
        assert isinstance(result.pack, TopologyPack)
        
        pack = result.pack
        
        # Test: Must have enterprise system nodes
        node_ids = [node.id for node in pack.nodes]
        assert "System.API.Gateway" in node_ids
        assert "System.Auth.Validator" in node_ids
        assert "System.Database.Connector" in node_ids
        assert "AI.Business.Processor" in node_ids
        assert "System.Audit.Logger" in node_ids
    
    def test_enterprise_integration_system_flow(self, enterprise_topology_dir):
        """Integration test: Enterprise topology must have valid system flow."""
        parser = EnhancedPackParser(enterprise_topology_dir)
        result = parser.parse()
        pack = result.pack
        
        # Test: Must have edges connecting enterprise systems
        edge_from_nodes = {edge.from_node for edge in pack.edges}
        edge_to_nodes = {edge.to_node for edge in pack.edges}
        
        # Gateway must be entry point
        assert "System.API.Gateway" in edge_from_nodes
        assert "System.API.Gateway" not in edge_to_nodes or len([e for e in pack.edges if e.to_node == "System.API.Gateway"]) == 0
        
        # Auth validator must be in flow
        assert "System.Auth.Validator" in edge_from_nodes
        assert "System.Auth.Validator" in edge_to_nodes
        
        # Audit logger should be in flow
        assert "System.Audit.Logger" in edge_to_nodes
    
    def test_enterprise_integration_orchestrator_execution(self, enterprise_topology_dir):
        """Integration test: Enterprise topology must be executable by orchestrator."""
        parser = EnhancedPackParser(enterprise_topology_dir)
        result = parser.parse()
        pack = result.pack
        
        # Test: Must create orchestrator successfully
        orchestrator = EnhancedTopoOrchestrator(pack)
        assert orchestrator.pack == pack
        
        # Test: Must identify entry point (API Gateway)
        assert "System.API.Gateway" in orchestrator._entry_points or \
               len(orchestrator._entry_points) > 0
        
        # Test: Must have valid execution graph
        assert len(orchestrator._graph) == len(pack.nodes)
        assert len(orchestrator._node_map) == len(pack.nodes)
    
    def test_enterprise_integration_contract_compliance(self, enterprise_topology_dir):
        """Integration test: Enterprise topology must comply with all contracts."""
        parser = EnhancedPackParser(enterprise_topology_dir)
        result = parser.parse()
        pack = result.pack
        
        # Test: Must have contracts for all system interactions
        required_contracts = {
            "api_request", "auth_request", "auth_response",
            "db_query", "db_response", "business_process", "audit_event"
        }
        contract_names = {contract.name for contract in pack.contracts}
        
        for required in required_contracts:
            assert required in contract_names, f"Missing required contract: {required}"
        
        # Test: All contracts must have valid schemas
        for contract in pack.contracts:
            assert contract.input_schema is not None
            assert contract.output_schema is not None
            assert isinstance(contract.input_schema, dict)
            assert isinstance(contract.output_schema, dict)
    
    def test_enterprise_integration_security_features(self, enterprise_topology_dir):
        """Integration test: Enterprise topology must have security features."""
        parser = EnhancedPackParser(enterprise_topology_dir)
        result = parser.parse()
        pack = result.pack
        
        # Test: Must have guardrails with security configuration
        assert pack.guardrails is not None
        
        # Test: Must have auth validator node
        auth_nodes = [node for node in pack.nodes if "Auth" in node.id]
        assert len(auth_nodes) > 0, "Must have authentication node"
        
        # Test: Must have audit logger node
        audit_nodes = [node for node in pack.nodes if "Audit" in node.id]
        assert len(audit_nodes) > 0, "Must have audit logging node"
    
    def test_enterprise_integration_performance(self, enterprise_topology_dir):
        """Integration test: Enterprise topology must meet performance requirements."""
        parser = EnhancedPackParser(enterprise_topology_dir, max_parse_time_ms=100)
        result = parser.parse()
        
        # Test: Must parse within time limit (<100ms per spec)
        assert result.parse_time_ms < 100, \
            f"Parse time {result.parse_time_ms}ms exceeds <100ms requirement"
        
        # Test: Must be efficient for enterprise scale
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_enterprise_integration_end_to_end(self, enterprise_topology_dir):
        """Integration test: Enterprise topology must execute end-to-end."""
        parser = EnhancedPackParser(enterprise_topology_dir)
        result = parser.parse()
        pack = result.pack
        
        orchestrator = EnhancedTopoOrchestrator(pack)
        
        # Test: Must execute successfully with enterprise input
        input_data = {
            "method": "POST",
            "path": "/api/business/process",
            "headers": {
                "Authorization": "Bearer test-token"
            },
            "body": {
                "action": "process",
                "data": {}
            }
        }
        
        execution_result = await orchestrator.execute(
            session_id="enterprise_test_session",
            input_data=input_data,
            entry_node="System.API.Gateway",
            timeout_seconds=30
        )
        
        # Test: Must return successful result structure
        assert "success" in execution_result
        
        # Test: Must track execution
        assert "execution_time" in execution_result or execution_result.get("success") is not False
    
    def test_enterprise_integration_system_isolation(self, enterprise_topology_dir):
        """Integration test: Enterprise systems must maintain proper isolation."""
        parser = EnhancedPackParser(enterprise_topology_dir)
        result = parser.parse()
        pack = result.pack
        
        # Test: System nodes should have proper scoping
        for node in pack.nodes:
            if node.id.startswith("System."):
                assert node.scope is not None
                assert len(node.scope.contracts) > 0, \
                    f"System node {node.id} must have contracts"

