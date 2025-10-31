"""Integration test for RAG system template in TopoKit."""

import pytest
import tempfile
import shutil
from pathlib import Path
import asyncio
import yaml
import json
from topokit.core.pack_parser import EnhancedPackParser, PackParseResult
from topokit.core.orchestrator import EnhancedTopoOrchestrator
from topokit.types.topology import TopologyPack, Node, EdgePolicy


class TestRAGSystemTemplate:
    """Integration tests for RAG system template."""
    
    @pytest.fixture
    def rag_template_dir(self):
        """Get the path to the RAG system template."""
        # Template is in packages/cli/src/templates/rag-system.yaml
        template_path = Path(__file__).parent.parent.parent / "packages" / "cli" / "src" / "templates" / "rag-system.yaml"
        assert template_path.exists(), f"RAG template not found at {template_path}"
        return template_path
    
    @pytest.fixture
    def generated_topology_dir(self, rag_template_dir):
        """Generate a topology from the RAG template for testing."""
        temp_dir = tempfile.mkdtemp()
        topology_dir = Path(temp_dir) / "topology"
        topology_dir.mkdir()
        
        # Read and parse the template
        template_data = yaml.safe_load(rag_template_dir.read_text())
        
        # Generate topology structure from template
        nodes_file = topology_dir / "nodes.yaml"
        edges_file = topology_dir / "edges.yaml"
        guardrails_file = topology_dir / "guardrails.yaml"
        contracts_dir = topology_dir / "contracts"
        contracts_dir.mkdir()
        
        # Write nodes.yaml
        nodes_content = {"nodes": template_data["nodes"]}
        nodes_file.write_text(yaml.dump(nodes_content))
        
        # Write edges.yaml
        edges_content = {"edges": template_data["edges"]}
        edges_file.write_text(yaml.dump(edges_content))
        
        # Write guardrails.yaml
        guardrails_file.write_text(yaml.dump(template_data["guardrails"]))
        
        # Write contract files (parser expects 'input' and 'output' keys, not 'input_schema'/'output_schema')
        for contract in template_data["contracts"]:
            contract_file = contracts_dir / f"{contract['name']}.json"
            # Convert to parser-expected format
            contract_data = {
                "name": contract["name"],
                "version": contract.get("version", "1.0.0"),
                "input": contract.get("input_schema", {}),
                "output": contract.get("output_schema", {}),
                "description": contract.get("description")
            }
            contract_file.write_text(json.dumps(contract_data, indent=2))
        
        yield str(topology_dir)
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    def test_rag_template_loading(self, rag_template_dir):
        """Integration test: RAG template must load correctly."""
        
        # Test: Template file must exist
        assert rag_template_dir.exists(), "RAG template file does not exist"
        
        # Test: Template must be valid YAML
        template_data = yaml.safe_load(rag_template_dir.read_text())
        assert template_data is not None, "RAG template is not valid YAML"
        
        # Test: Template must have required fields
        required_fields = ["name", "description", "version", "nodes", "edges", "contracts", "guardrails"]
        for field in required_fields:
            assert field in template_data, f"RAG template missing required field: {field}"
        
        # Test: Template must be RAG system template
        assert template_data["name"] == "rag-system", "Template is not RAG system template"
    
    def test_rag_template_structure(self, rag_template_dir):
        """Integration test: RAG template must have correct structure."""
        template_data = yaml.safe_load(rag_template_dir.read_text())
        
        # Test: Must have at least 2 nodes (Data.Retrieval and AI.Answer)
        assert len(template_data["nodes"]) >= 2, "RAG template must have at least 2 nodes"
        
        node_ids = [node["id"] for node in template_data["nodes"]]
        assert "Data.Retrieval" in node_ids, "RAG template must have Data.Retrieval node"
        assert "AI.Answer" in node_ids, "RAG template must have AI.Answer node"
        
        # Test: Must have at least 1 edge connecting nodes
        assert len(template_data["edges"]) > 0, "RAG template must have edges"
        
        # Test: Must have contracts for retrieve and answer
        contract_names = [contract["name"] for contract in template_data["contracts"]]
        assert "retrieve" in contract_names, "RAG template must have retrieve contract"
        assert "answer" in contract_names, "RAG template must have answer contract"
        
        # Test: Must have guardrails configuration
        assert "guardrails" in template_data, "RAG template must have guardrails"
        assert isinstance(template_data["guardrails"], dict), "Guardrails must be a dictionary"
    
    def test_rag_template_topology_generation(self, generated_topology_dir):
        """Integration test: RAG template must generate valid topology."""
        parser = EnhancedPackParser(generated_topology_dir)
        result = parser.parse()
        
        # Test: Must successfully parse generated topology
        assert isinstance(result, PackParseResult), "Parsing must return PackParseResult"
        assert result.success is True, f"Parsing failed: {result.errors}"
        assert isinstance(result.pack, TopologyPack), "Must return TopologyPack"
        
        pack = result.pack
        
        # Test: Must have RAG system nodes
        node_ids = [node.id for node in pack.nodes]
        assert "Data.Retrieval" in node_ids, "Topology must have Data.Retrieval node"
        assert "AI.Answer" in node_ids, "Topology must have AI.Answer node"
        
        # Test: Must have edge connecting Data.Retrieval to AI.Answer
        edge_found = False
        for edge in pack.edges:
            if edge.from_node == "Data.Retrieval" and edge.to_node == "AI.Answer":
                edge_found = True
                break
        assert edge_found, "Topology must have edge from Data.Retrieval to AI.Answer"
        
        # Test: Must have retrieve and answer contracts
        contract_names = [contract.name for contract in pack.contracts]
        assert "retrieve" in contract_names, "Topology must have retrieve contract"
        assert "answer" in contract_names, "Topology must have answer contract"
    
    def test_rag_template_orchestrator_execution(self, generated_topology_dir):
        """Integration test: Generated RAG topology must be executable by orchestrator."""
        parser = EnhancedPackParser(generated_topology_dir)
        result = parser.parse()
        pack = result.pack
        
        # Test: Must create orchestrator successfully
        orchestrator = EnhancedTopoOrchestrator(pack)
        assert orchestrator.pack == pack
        
        # Test: Must identify entry point (Data.Retrieval)
        assert "Data.Retrieval" in orchestrator._entry_points, \
            "Data.Retrieval must be an entry point"
        
        # Test: Must identify exit point (AI.Answer)
        assert "AI.Answer" in orchestrator._exit_points, \
            "AI.Answer must be an exit point"
        
        # Test: Must have valid execution graph
        assert len(orchestrator._graph) == len(pack.nodes), \
            "Graph must include all nodes"
        assert len(orchestrator._node_map) == len(pack.nodes), \
            "Node map must include all nodes"
    
    @pytest.mark.asyncio
    async def test_rag_template_end_to_end_execution(self, generated_topology_dir):
        """Integration test: RAG template topology must execute end-to-end."""
        parser = EnhancedPackParser(generated_topology_dir)
        result = parser.parse()
        pack = result.pack
        
        orchestrator = EnhancedTopoOrchestrator(pack)
        
        # Test: Must execute successfully with valid input
        input_data = {
            "query": "What is the capital of France?",
            "limit": 10
        }
        
        execution_result = await orchestrator.execute(
            session_id="test_session",
            input_data=input_data,
            entry_node="Data.Retrieval",
            timeout_seconds=30
        )
        
        # Test: Must return successful result
        assert execution_result["success"] is True, \
            f"Execution failed: {execution_result.get('error', 'Unknown error')}"
        
        # Test: Must execute nodes in correct order
        nodes_executed = execution_result["nodes_executed"]
        assert "Data.Retrieval" in nodes_executed, \
            "Data.Retrieval must be executed"
        assert "AI.Answer" in nodes_executed, \
            "AI.Answer must be executed"
        
        # Test: Must have execution time
        assert "execution_time" in execution_result, \
            "Result must include execution time"
        assert execution_result["execution_time"] > 0, \
            "Execution time must be positive"
    
    def test_rag_template_visualization_generation(self, generated_topology_dir):
        """Integration test: RAG template topology must support graph generation."""
        parser = EnhancedPackParser(generated_topology_dir)
        result = parser.parse()
        pack = result.pack
        
        # Test: Topology must have enough nodes for visualization
        assert len(pack.nodes) >= 2, "Must have at least 2 nodes for visualization"
        
        # Test: Topology must have edges for visualization
        assert len(pack.edges) > 0, "Must have edges for visualization"
        
        # Test: Must be able to generate basic graph structure
        node_ids = [node.id for node in pack.nodes]
        edge_pairs = [(edge.from_node, edge.to_node) for edge in pack.edges]
        
        # Verify graph structure is valid
        assert len(node_ids) > 0, "Must have nodes"
        assert len(edge_pairs) > 0, "Must have edges"
        assert all(from_node in node_ids and to_node in node_ids 
                  for from_node, to_node in edge_pairs), \
            "All edges must connect valid nodes"
    
    def test_rag_template_schema_validation(self, generated_topology_dir):
        """Integration test: RAG template topology must pass schema validation."""
        parser = EnhancedPackParser(generated_topology_dir)
        result = parser.parse()
        pack = result.pack
        
        # Test: All contracts must have valid JSON schemas
        for contract in pack.contracts:
            assert contract.input_schema is not None, \
                f"Contract {contract.name} must have input schema"
            assert contract.output_schema is not None, \
                f"Contract {contract.name} must have output schema"
            assert isinstance(contract.input_schema, dict), \
                f"Contract {contract.name} input schema must be a dictionary"
            assert isinstance(contract.output_schema, dict), \
                f"Contract {contract.name} output schema must be a dictionary"
            
            # Validate schema structure (only if schema is not empty)
            if contract.input_schema:  # Empty dict is acceptable for parser fallback
                assert "type" in contract.input_schema, \
                    f"Contract {contract.name} input schema must have type"
            if contract.output_schema:  # Empty dict is acceptable for parser fallback
                assert "type" in contract.output_schema, \
                    f"Contract {contract.name} output schema must have type"
    
    def test_rag_template_acceptance_criteria(self, generated_topology_dir):
        """Integration test: RAG template must meet acceptance criteria from spec."""
        parser = EnhancedPackParser(generated_topology_dir)
        result = parser.parse()
        
        # Acceptance Criteria 1: Can generate a visual graph
        pack = result.pack
        assert len(pack.nodes) > 0 and len(pack.edges) > 0, \
            "Topology must support graph generation"
        
        # Acceptance Criteria 2: Can validate schema
        assert len(pack.contracts) > 0, \
            "Topology must have contracts for schema validation"
        for contract in pack.contracts:
            assert contract.input_schema and contract.output_schema, \
                "Contracts must have schemas for validation"
        
        # Acceptance Criteria 3: Can run basic evaluation
        orchestrator = EnhancedTopoOrchestrator(pack)
        assert orchestrator is not None, \
            "Topology must be executable for evaluation"
        
        # Must have entry and exit points for evaluation
        assert len(orchestrator._entry_points) > 0, \
            "Topology must have entry points for evaluation"
        assert len(orchestrator._exit_points) > 0, \
            "Topology must have exit points for evaluation"
    
    def test_rag_template_performance(self, generated_topology_dir):
        """Integration test: RAG template topology must meet performance requirements."""
        parser = EnhancedPackParser(generated_topology_dir, max_parse_time_ms=100)
        result = parser.parse()
        
        # Test: Must parse within time limit (<100ms per spec)
        assert result.parse_time_ms < 100, \
            f"Parse time {result.parse_time_ms}ms exceeds <100ms requirement"
        
        # Test: Must be efficient for initialization
        assert result.success is True, \
            "Parsing must succeed for performance test"
    
    def test_rag_template_completeness(self, rag_template_dir, generated_topology_dir):
        """Integration test: RAG template must generate complete, working topology."""
        
        template_data = yaml.safe_load(rag_template_dir.read_text())
        parser = EnhancedPackParser(generated_topology_dir)
        result = parser.parse()
        pack = result.pack
        
        # Test: Generated topology must match template structure
        assert len(pack.nodes) == len(template_data["nodes"]), \
            "Generated topology must have same number of nodes as template"
        
        assert len(pack.edges) == len(template_data["edges"]), \
            "Generated topology must have same number of edges as template"
        
        assert len(pack.contracts) == len(template_data["contracts"]), \
            "Generated topology must have same number of contracts as template"
        
        # Test: Generated topology must be executable
        orchestrator = EnhancedTopoOrchestrator(pack)
        assert orchestrator is not None, \
            "Generated topology must create orchestrator"
        
        # Test: Must have valid DAG structure
        assert len(orchestrator._entry_points) > 0, \
            "Generated topology must have entry points"
        assert len(orchestrator._exit_points) > 0, \
            "Generated topology must have exit points"

