"""Integration tests for TopoKit foundational components."""

import asyncio
import json
import pytest
from datetime import datetime, timezone
from typing import Dict, Any

from topokit.core.config import get_config, TopoKitConfig
from topokit.core.logging import get_logger, LoggingConfig
from topokit.core.pack_parser import EnhancedPackParser
from topokit.core.schema_validator import SchemaValidator
from topokit.core.context_store import EnhancedContextStore, MergeStrategy, ConflictResolutionStrategy
from topokit.core.guardrails import MultiStageGuardrails, PolicyEnvironment
from topokit.core.orchestrator import EnhancedTopoOrchestrator
from topokit.core.edge_enforcement import EdgeEnforcementEngine
from topokit.core.circuit_breaker import CircuitBreakerManager, CircuitBreakerLevel
from topokit.core.human_gates import HumanGateManager, GateType, GatePriority
from topokit.core.auth import get_auth_manager, User, UserRole, Permission
from topokit.core.api import get_api
from topokit.types.topology import TopologyPack, Node, EdgePolicy, Contract, GuardrailsConfig


class TestTopoKitIntegration:
    """Integration tests for TopoKit foundational components."""
    
    @pytest.fixture
    async def config(self):
        """Get TopoKit configuration."""
        return get_config()
    
    @pytest.fixture
    async def sample_topology_pack(self):
        """Create a sample topology pack for testing."""
        return TopologyPack(
            name="test-topology",
            version="1.0.0",
            description="Test topology for integration testing",
            nodes=[
                Node(
                    id="input_node",
                    name="Input Node",
                    kind="data",
                    description="Input data processing node"
                ),
                Node(
                    id="ai_node",
                    name="AI Node",
                    kind="ai",
                    description="AI processing node"
                ),
                Node(
                    id="output_node",
                    name="Output Node",
                    kind="data",
                    description="Output data processing node"
                )
            ],
            edges=[
                EdgePolicy(
                    id="input_to_ai",
                    from_node="input_node",
                    to_node="ai_node",
                    allow=True,
                    timeout_ms=5000
                ),
                EdgePolicy(
                    id="ai_to_output",
                    from_node="ai_node",
                    to_node="output_node",
                    allow=True,
                    timeout_ms=5000
                )
            ],
            contracts=[
                Contract(
                    id="input_contract",
                    name="Input Contract",
                    schema={
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "metadata": {"type": "object"}
                        },
                        "required": ["text"]
                    }
                )
            ],
            guardrails=GuardrailsConfig(
                enable_pre_processing=True,
                enable_post_processing=True,
                confidence_threshold=0.8
            )
        )
    
    @pytest.fixture
    async def pack_parser(self):
        """Create pack parser instance."""
        return EnhancedPackParser(max_parse_time_ms=100)
    
    @pytest.fixture
    async def schema_validator(self):
        """Create schema validator instance."""
        return SchemaValidator(
            lenient_parsing=True,
            auto_repair=True,
            schema_version="draft7"
        )
    
    @pytest.fixture
    async def context_store(self):
        """Create context store instance."""
        return EnhancedContextStore(
            merge_strategy=MergeStrategy.FIELD_LEVEL_CRDT,
            conflict_resolution=ConflictResolutionStrategy.AUTOMATIC
        )
    
    @pytest.fixture
    async def guardrails(self, sample_topology_pack):
        """Create guardrails instance."""
        return MultiStageGuardrails(
            sample_topology_pack.guardrails,
            PolicyEnvironment.DEVELOPMENT
        )
    
    @pytest.fixture
    async def orchestrator(self, sample_topology_pack, context_store, guardrails, schema_validator):
        """Create orchestrator instance."""
        return EnhancedTopoOrchestrator(
            pack=sample_topology_pack,
            context_store=context_store,
            guardrails=guardrails,
            schema_validator=schema_validator
        )
    
    @pytest.fixture
    async def edge_enforcement(self, schema_validator, guardrails):
        """Create edge enforcement engine."""
        return EdgeEnforcementEngine(
            schema_validator=schema_validator,
            guardrails=guardrails
        )
    
    @pytest.fixture
    async def circuit_breaker_manager(self):
        """Create circuit breaker manager."""
        return CircuitBreakerManager()
    
    @pytest.fixture
    async def human_gate_manager(self):
        """Create human gate manager."""
        return HumanGateManager()
    
    @pytest.fixture
    async def auth_manager(self):
        """Create authentication manager."""
        return get_auth_manager()
    
    @pytest.fixture
    async def api(self, config):
        """Create API instance."""
        return get_api(config)
    
    async def test_pack_parsing_integration(self, pack_parser, sample_topology_pack):
        """Test pack parsing integration."""
        # Convert topology pack to JSON
        pack_json = json.dumps(sample_topology_pack.dict(), indent=2)
        
        # Parse the pack
        result = await pack_parser.parse(pack_json)
        
        assert result.success, f"Pack parsing failed: {result.errors}"
        assert result.data is not None
        assert "nodes" in result.data
        assert "edges" in result.data
        assert "contracts" in result.data
    
    async def test_schema_validation_integration(self, schema_validator):
        """Test schema validation integration."""
        schema = {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1}
            },
            "required": ["text"]
        }
        
        # Test valid data
        valid_data = {"text": "Hello world", "confidence": 0.9}
        result = schema_validator.validate(valid_data, schema)
        assert result.success, f"Valid data validation failed: {result.errors}"
        
        # Test invalid data with auto-repair
        invalid_json = '{"text": "Hello world", "confidence": 0.9,}'  # Trailing comma
        result = schema_validator.validate(invalid_json, schema)
        assert result.success, f"Auto-repair failed: {result.errors}"
        assert result.repair_attempts > 0
    
    async def test_context_store_integration(self, context_store):
        """Test context store integration."""
        session_id = "test-session-123"
        
        # Store initial context
        await context_store.upsert(
            session_id=session_id,
            patch={"user_id": "user123", "input": "test input"},
            node_id="input_node",
            trace_id="trace-123"
        )
        
        # Retrieve context
        context = await context_store.get(session_id)
        assert context is not None
        assert context["user_id"] == "user123"
        assert context["input"] == "test input"
        
        # Update context with conflict
        await context_store.upsert(
            session_id=session_id,
            patch={"user_id": "user456", "status": "processing"},
            node_id="ai_node",
            trace_id="trace-124"
        )
        
        # Verify conflict resolution
        updated_context = await context_store.get(session_id)
        assert updated_context["user_id"] == "user456"  # Last write wins
        assert updated_context["status"] == "processing"
        assert updated_context["input"] == "test input"  # Preserved from previous
    
    async def test_guardrails_integration(self, guardrails, sample_topology_pack):
        """Test guardrails integration."""
        # Test pre-processing guardrails
        input_data = {"text": "This is a test input", "confidence": 0.9}
        node = sample_topology_pack.nodes[0]
        
        result = await guardrails.apply_pre_processing(
            data=input_data,
            node=node,
            trace_id="trace-123"
        )
        
        assert result.passed, f"Pre-processing guardrails failed: {result.message}"
        
        # Test post-processing guardrails
        output_data = {"response": "Test response", "confidence": 0.95}
        
        result = await guardrails.apply_post_processing(
            data=output_data,
            node=node,
            trace_id="trace-123"
        )
        
        assert result.passed, f"Post-processing guardrails failed: {result.message}"
    
    async def test_orchestrator_integration(self, orchestrator):
        """Test orchestrator integration."""
        session_id = "test-session-456"
        input_data = {"text": "Test input for orchestration"}
        
        # Execute topology
        result = await orchestrator.execute(
            session_id=session_id,
            input_data=input_data,
            timeout_seconds=30
        )
        
        assert result["success"], f"Orchestration failed: {result.get('error')}"
        assert "trace_id" in result
        assert "execution_time" in result
        assert "nodes_executed" in result
    
    async def test_edge_enforcement_integration(self, edge_enforcement, sample_topology_pack):
        """Test edge enforcement integration."""
        edge = sample_topology_pack.edges[0]
        from_node = sample_topology_pack.nodes[0]
        to_node = sample_topology_pack.nodes[1]
        
        data = {"text": "Test data for edge enforcement"}
        
        result = await edge_enforcement.enforce(
            edge=edge,
            from_node=from_node,
            to_node=to_node,
            data=data,
            session_id="test-session-789",
            trace_id="trace-789"
        )
        
        assert result.result.value == "success", f"Edge enforcement failed: {result.message}"
    
    async def test_circuit_breaker_integration(self, circuit_breaker_manager):
        """Test circuit breaker integration."""
        # Create circuit breaker
        cb = circuit_breaker_manager.create_circuit_breaker(
            identifier="test-cb",
            level=CircuitBreakerLevel.NODE
        )
        
        # Test successful call
        async def success_func():
            return "success"
        
        result = await cb.call(success_func)
        assert result == "success"
        
        # Test failed call
        async def fail_func():
            raise Exception("Test failure")
        
        with pytest.raises(Exception):
            await cb.call(fail_func)
        
        # Check circuit breaker state
        state = cb.get_state()
        assert state["state"] == "closed"  # Should still be closed for single failure
    
    async def test_human_gates_integration(self, human_gate_manager):
        """Test human gates integration."""
        # Create human gate
        gate = human_gate_manager.create_gate(
            identifier="test-gate",
            gate_type=GateType.APPROVAL,
            priority=GatePriority.MEDIUM,
            timeout_seconds=60
        )
        
        # Request approval
        request_id = await gate.request_approval(
            title="Test Approval Request",
            description="This is a test approval request",
            data={"action": "test_action"},
            created_by="user123"
        )
        
        assert request_id is not None
        
        # Get pending requests
        pending = gate.get_pending_requests()
        assert len(pending) == 1
        assert pending[0].id == request_id
        
        # Approve request
        success = await gate.approve_request(
            request_id=request_id,
            approved_by="admin",
            comments="Approved for testing"
        )
        
        assert success
        
        # Verify request is no longer pending
        pending = gate.get_pending_requests()
        assert len(pending) == 0
    
    async def test_auth_integration(self, auth_manager):
        """Test authentication integration."""
        # Create test user
        user = User(
            id="test-user-123",
            username="testuser",
            email="test@example.com",
            roles=[UserRole.DEVELOPER],
            permissions=[Permission.READ_TOPOLOGY, Permission.EXECUTE_TOPOLOGY]
        )
        
        # Create access token
        token = auth_manager.create_access_token(user)
        assert token is not None
        
        # Verify token
        payload = auth_manager.verify_token(token)
        assert payload is not None
        assert payload.user_id == user.id
        assert payload.username == user.username
        assert UserRole.DEVELOPER.value in payload.roles
    
    async def test_api_integration(self, api):
        """Test API integration."""
        # Test health check endpoint
        health_response = api.app.get("/health")
        assert health_response.status_code == 200
        
        # Test API structure
        assert hasattr(api, 'app')
        assert api.app is not None
    
    async def test_end_to_end_integration(self, 
                                        pack_parser, 
                                        schema_validator, 
                                        context_store, 
                                        guardrails, 
                                        orchestrator,
                                        edge_enforcement,
                                        circuit_breaker_manager,
                                        human_gate_manager):
        """Test end-to-end integration of all components."""
        # Create a complete topology pack
        topology_data = {
            "name": "integration-test-topology",
            "version": "1.0.0",
            "description": "End-to-end integration test",
            "nodes": [
                {
                    "id": "start",
                    "name": "Start Node",
                    "kind": "data",
                    "description": "Starting node"
                },
                {
                    "id": "process",
                    "name": "Process Node", 
                    "kind": "ai",
                    "description": "Processing node"
                },
                {
                    "id": "end",
                    "name": "End Node",
                    "kind": "data", 
                    "description": "Ending node"
                }
            ],
            "edges": [
                {
                    "id": "start_to_process",
                    "from_node": "start",
                    "to_node": "process",
                    "allow": True,
                    "timeout_ms": 5000
                },
                {
                    "id": "process_to_end",
                    "from_node": "process", 
                    "to_node": "end",
                    "allow": True,
                    "timeout_ms": 5000
                }
            ],
            "contracts": [
                {
                    "id": "data_contract",
                    "name": "Data Contract",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "message": {"type": "string"},
                            "timestamp": {"type": "string"}
                        },
                        "required": ["message"]
                    }
                }
            ],
            "guardrails": {
                "enable_pre_processing": True,
                "enable_post_processing": True,
                "confidence_threshold": 0.8
            }
        }
        
        # Parse topology pack
        pack_json = json.dumps(topology_data)
        parse_result = await pack_parser.parse(pack_json)
        assert parse_result.success, f"Pack parsing failed: {parse_result.errors}"
        
        # Validate data against schema
        schema = topology_data["contracts"][0]["schema"]
        test_data = {"message": "Hello TopoKit!", "timestamp": datetime.now(timezone.utc).isoformat()}
        
        validation_result = schema_validator.validate(test_data, schema)
        assert validation_result.success, f"Schema validation failed: {validation_result.errors}"
        
        # Store context
        session_id = "integration-test-session"
        await context_store.upsert(
            session_id=session_id,
            patch={"test_data": test_data},
            node_id="start",
            trace_id="integration-trace"
        )
        
        # Verify context storage
        stored_context = await context_store.get(session_id)
        assert stored_context["test_data"]["message"] == "Hello TopoKit!"
        
        # Test circuit breaker
        cb = circuit_breaker_manager.create_circuit_breaker(
            identifier="integration-cb",
            level=CircuitBreakerLevel.NODE
        )
        
        async def test_operation():
            return "operation_success"
        
        cb_result = await cb.call(test_operation)
        assert cb_result == "operation_success"
        
        # Test human gate
        gate = human_gate_manager.create_gate(
            identifier="integration-gate",
            gate_type=GateType.APPROVAL,
            priority=GatePriority.MEDIUM
        )
        
        request_id = await gate.request_approval(
            title="Integration Test Approval",
            description="Testing end-to-end integration",
            data={"operation": "integration_test"}
        )
        
        # Approve the request
        approval_success = await gate.approve_request(
            request_id=request_id,
            approved_by="integration_test",
            comments="Approved for integration testing"
        )
        
        assert approval_success
        
        # Verify all components are working together
        assert parse_result.success
        assert validation_result.success
        assert stored_context is not None
        assert cb_result == "operation_success"
        assert approval_success
        
        print("✅ All TopoKit foundational components integrated successfully!")


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v"])
