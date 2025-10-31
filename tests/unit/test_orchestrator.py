"""Unit tests for TopoOrchestrator."""

import pytest
import asyncio
from datetime import datetime, timezone
from topokit.core.orchestrator import EnhancedTopoOrchestrator, ExecutionState
from topokit.types.topology import TopologyPack, Node, EdgePolicy, Contract, GuardrailsConfig, NodeScope


class TestTopoOrchestrator:
    """Test cases for TopoOrchestrator."""
    
    @pytest.fixture
    def sample_pack(self):
        """Create a sample topology pack for testing."""
        nodes = [
            Node(
                id="input",
                kind="data",
                name="Input Processor",
                description="Process input data",
                scope=NodeScope(contracts=["input"])
            ),
            Node(
                id="ai_node",
                kind="ai",
                name="AI Processor",
                description="AI processing node",
                scope=NodeScope(contracts=["ai_output"])
            ),
            Node(
                id="output",
                kind="data",
                name="Output Processor",
                description="Process output data",
                scope=NodeScope(contracts=["output"])
            )
        ]
        
        edges = [
            EdgePolicy(
                id="input_to_ai",
                **{"from": "input", "to": "ai_node"},
                contracts=["input", "ai_output"]
            ),
            EdgePolicy(
                id="ai_to_output",
                **{"from": "ai_node", "to": "output"},
                contracts=["ai_output", "output"]
            )
        ]
        
        contracts = [
            Contract(
                name="input",
                input_schema={"type": "object", "properties": {"data": {"type": "string"}}},
                output_schema={"type": "object", "properties": {"data": {"type": "string"}}}
            ),
            Contract(
                name="ai_output",
                input_schema={"type": "object", "properties": {"data": {"type": "string"}}},
                output_schema={"type": "object", "properties": {"response": {"type": "string"}}}
            ),
            Contract(
                name="output",
                input_schema={"type": "object", "properties": {"response": {"type": "string"}}},
                output_schema={"type": "object", "properties": {"result": {"type": "string"}}}
            )
        ]
        
        return TopologyPack(
            name="test_pack",
            description="Test topology pack",
            nodes=nodes,
            edges=edges,
            contracts=contracts,
            guardrails=GuardrailsConfig()
        )
    
    def test_orchestrator_initialization(self, sample_pack):
        """Test orchestrator initialization."""
        orchestrator = EnhancedTopoOrchestrator(sample_pack)
        
        assert orchestrator.pack == sample_pack
        assert len(orchestrator._node_map) == 3
        assert len(orchestrator._graph) == 3
        assert "input" in orchestrator._entry_points
        assert "output" in orchestrator._exit_points
    
    def test_dag_validation_valid(self, sample_pack):
        """Test DAG validation with valid topology."""
        orchestrator = EnhancedTopoOrchestrator(sample_pack)
        # Should not raise any exception
        assert orchestrator._entry_points == ["input"]
        assert orchestrator._exit_points == ["output"]
    
    def test_dag_validation_cycle_detection(self):
        """Test DAG validation detects cycles."""
        # Create a pack with a cycle
        nodes = [
            Node(id="A", kind="data", name="Node A", scope=NodeScope()),
            Node(id="B", kind="data", name="Node B", scope=NodeScope()),
            Node(id="C", kind="data", name="Node C", scope=NodeScope())
        ]
        
        edges = [
            EdgePolicy(id="A_to_B", **{"from": "A", "to": "B"}, contracts=[]),
            EdgePolicy(id="B_to_C", **{"from": "B", "to": "C"}, contracts=[]),
            EdgePolicy(id="C_to_A", **{"from": "C", "to": "A"}, contracts=[])  # Cycle!
        ]
        
        pack = TopologyPack(
            name="cyclic_pack",
            nodes=nodes,
            edges=edges,
            contracts=[],
            guardrails=GuardrailsConfig()
        )
        
        with pytest.raises(ValueError, match="Cycle detected"):
            EnhancedTopoOrchestrator(pack)
    
    def test_topological_sort(self, sample_pack):
        """Test topological sorting."""
        orchestrator = EnhancedTopoOrchestrator(sample_pack)
        order = orchestrator._topological_sort("input")
        
        # Should be in dependency order
        assert order[0] == "input"  # No dependencies
        assert "ai_node" in order[1:]  # Depends on input
        assert order[-1] == "output"  # Depends on ai_node
    
    @pytest.mark.asyncio
    async def test_execute_success(self, sample_pack):
        """Test successful execution."""
        orchestrator = EnhancedTopoOrchestrator(sample_pack)
        
        result = await orchestrator.execute(
            session_id="test_session",
            input_data={"data": "test input"}
        )
        
        assert result["success"] is True
        assert "trace_id" in result
        assert "result" in result
        assert "execution_time" in result
        assert "nodes_executed" in result
    
    @pytest.mark.asyncio
    async def test_execute_with_entry_node(self, sample_pack):
        """Test execution with specific entry node."""
        orchestrator = EnhancedTopoOrchestrator(sample_pack)
        
        result = await orchestrator.execute(
            session_id="test_session",
            input_data={"data": "test input"},
            entry_node="input"
        )
        
        assert result["success"] is True
        assert "input" in result["nodes_executed"]
    
    def test_get_execution_status(self, sample_pack):
        """Test getting execution status."""
        orchestrator = EnhancedTopoOrchestrator(sample_pack)
        
        # No active executions initially
        status = orchestrator.get_execution_status("nonexistent")
        assert status is None
    
    def test_get_node_status(self, sample_pack):
        """Test getting node status."""
        orchestrator = EnhancedTopoOrchestrator(sample_pack)
        
        # No node executions initially
        status = orchestrator.get_node_status("nonexistent", "input")
        assert status is None
    
    @pytest.mark.asyncio
    async def test_cancel_execution(self, sample_pack):
        """Test execution cancellation."""
        orchestrator = EnhancedTopoOrchestrator(sample_pack)
        
        # Try to cancel non-existent execution
        result = await orchestrator.cancel_execution("nonexistent")
        assert result is False
