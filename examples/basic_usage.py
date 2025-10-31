"""Basic usage example for TopoKit platform."""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any

from topokit.core.config import get_config
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
from topokit.types.topology import TopologyPack, Node, EdgePolicy, Contract, GuardrailsConfig


async def main():
    """Main example function demonstrating TopoKit usage."""
    
    # Initialize logging
    logging_config = LoggingConfig(
        log_level="INFO",
        log_format="json",
        enable_console=True
    )
    logging_config.configure()
    
    logger = get_logger(__name__)
    logger.info("Starting TopoKit basic usage example")
    
    # 1. Configuration Management
    print("\n🔧 1. Configuration Management")
    config = get_config()
    print(f"Environment: {config.environment}")
    print(f"Debug mode: {config.debug}")
    print(f"Database URL: {config.database.url}")
    
    # 2. Create a Topology Pack
    print("\n📦 2. Creating Topology Pack")
    
    topology_pack = TopologyPack(
        name="chatbot-topology",
        version="1.0.0",
        description="A simple chatbot topology with input processing, AI response, and output formatting",
        nodes=[
            Node(
                id="input_processor",
                name="Input Processor",
                kind="data",
                description="Processes user input and validates format"
            ),
            Node(
                id="ai_responder",
                name="AI Responder", 
                kind="ai",
                description="Generates AI response using LLM"
            ),
            Node(
                id="output_formatter",
                name="Output Formatter",
                kind="data", 
                description="Formats AI response for user display"
            )
        ],
        edges=[
            EdgePolicy(
                id="input_to_ai",
                from_node="input_processor",
                to_node="ai_responder",
                allow=True,
                timeout_ms=10000,
                max_retries=3
            ),
            EdgePolicy(
                id="ai_to_output",
                from_node="ai_responder",
                to_node="output_formatter",
                allow=True,
                timeout_ms=5000,
                max_retries=2
            )
        ],
        contracts=[
            Contract(
                id="user_input_contract",
                name="User Input Contract",
                schema={
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "minLength": 1, "maxLength": 1000},
                        "user_id": {"type": "string"},
                        "session_id": {"type": "string"},
                        "metadata": {"type": "object"}
                    },
                    "required": ["message", "user_id", "session_id"]
                }
            ),
            Contract(
                id="ai_response_contract",
                name="AI Response Contract", 
                schema={
                    "type": "object",
                    "properties": {
                        "response": {"type": "string"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "tokens_used": {"type": "integer", "minimum": 0},
                        "processing_time_ms": {"type": "number", "minimum": 0}
                    },
                    "required": ["response", "confidence"]
                }
            )
        ],
        guardrails=GuardrailsConfig(
            enable_pre_processing=True,
            enable_post_processing=True,
            confidence_threshold=0.7,
            content_moderation=True,
            pii_detection=True
        )
    )
    
    print(f"Created topology pack: {topology_pack.name} v{topology_pack.version}")
    print(f"Nodes: {len(topology_pack.nodes)}")
    print(f"Edges: {len(topology_pack.edges)}")
    print(f"Contracts: {len(topology_pack.contracts)}")
    
    # 3. Pack Parsing
    print("\n📋 3. Pack Parsing")
    
    pack_parser = EnhancedPackParser(max_parse_time_ms=100)
    pack_json = json.dumps(topology_pack.dict(), indent=2)
    
    parse_result = await pack_parser.parse(pack_json)
    if parse_result.success:
        print("✅ Pack parsed successfully")
        print(f"Parse time: {parse_result.parse_time_ms:.2f}ms")
    else:
        print(f"❌ Pack parsing failed: {parse_result.errors}")
        return
    
    # 4. Schema Validation
    print("\n✅ 4. Schema Validation")
    
    schema_validator = SchemaValidator(
        lenient_parsing=True,
        auto_repair=True,
        schema_version="draft7"
    )
    
    # Test user input validation
    user_input = {
        "message": "Hello, how are you?",
        "user_id": "user123",
        "session_id": "session456",
        "metadata": {"source": "web", "timestamp": datetime.now(timezone.utc).isoformat()}
    }
    
    input_schema = topology_pack.contracts[0].schema
    validation_result = schema_validator.validate(user_input, input_schema)
    
    if validation_result.success:
        print("✅ User input validation passed")
    else:
        print(f"❌ User input validation failed: {validation_result.errors}")
        return
    
    # 5. Context Store
    print("\n💾 5. Context Store")
    
    context_store = EnhancedContextStore(
        merge_strategy=MergeStrategy.FIELD_LEVEL_CRDT,
        conflict_resolution=ConflictResolutionStrategy.AUTOMATIC
    )
    
    session_id = "example-session-123"
    
    # Store initial context
    await context_store.upsert(
        session_id=session_id,
        patch={
            "user_input": user_input,
            "start_time": datetime.now(timezone.utc).isoformat(),
            "status": "processing"
        },
        node_id="input_processor",
        trace_id="trace-001"
    )
    
    # Retrieve context
    stored_context = await context_store.get(session_id)
    print(f"✅ Context stored and retrieved: {len(stored_context)} fields")
    
    # 6. Guardrails
    print("\n🛡️ 6. Guardrails System")
    
    guardrails = MultiStageGuardrails(
        topology_pack.guardrails,
        PolicyEnvironment.DEVELOPMENT
    )
    
    # Test pre-processing guardrails
    pre_result = await guardrails.apply_pre_processing(
        data=user_input,
        node=topology_pack.nodes[0],  # input_processor
        trace_id="trace-001"
    )
    
    if pre_result.passed:
        print("✅ Pre-processing guardrails passed")
    else:
        print(f"❌ Pre-processing guardrails failed: {pre_result.message}")
        return
    
    # 7. Circuit Breakers
    print("\n⚡ 7. Circuit Breakers")
    
    circuit_breaker_manager = CircuitBreakerManager()
    
    # Create circuit breaker for AI node
    ai_circuit_breaker = circuit_breaker_manager.create_circuit_breaker(
        identifier="ai-responder-cb",
        level=CircuitBreakerLevel.NODE
    )
    
    print(f"✅ Circuit breaker created: {ai_circuit_breaker.identifier}")
    
    # 8. Human Gates
    print("\n👥 8. Human Gates")
    
    human_gate_manager = HumanGateManager()
    
    # Create approval gate for high-risk operations
    approval_gate = human_gate_manager.create_gate(
        identifier="high-risk-approval",
        gate_type=GateType.APPROVAL,
        priority=GatePriority.HIGH,
        timeout_seconds=300,  # 5 minutes
        escalation_chain=["admin1", "admin2", "supervisor"]
    )
    
    print(f"✅ Human gate created: {approval_gate.identifier}")
    
    # 9. Edge Enforcement
    print("\n🔗 9. Edge Enforcement")
    
    edge_enforcement = EdgeEnforcementEngine(
        schema_validator=schema_validator,
        guardrails=guardrails
    )
    
    # Test edge enforcement
    edge = topology_pack.edges[0]  # input_to_ai
    from_node = topology_pack.nodes[0]  # input_processor
    to_node = topology_pack.nodes[1]  # ai_responder
    
    enforcement_result = await edge_enforcement.enforce(
        edge=edge,
        from_node=from_node,
        to_node=to_node,
        data=user_input,
        session_id=session_id,
        trace_id="trace-001"
    )
    
    if enforcement_result.result.value == "success":
        print("✅ Edge enforcement passed")
    else:
        print(f"❌ Edge enforcement failed: {enforcement_result.message}")
        return
    
    # 10. Orchestrator Execution
    print("\n🎯 10. Orchestrator Execution")
    
    orchestrator = EnhancedTopoOrchestrator(
        pack=topology_pack,
        context_store=context_store,
        guardrails=guardrails,
        schema_validator=schema_validator
    )
    
    # Execute the topology
    execution_result = await orchestrator.execute(
        session_id=session_id,
        input_data=user_input,
        entry_node="input_processor",
        timeout_seconds=30
    )
    
    if execution_result["success"]:
        print("✅ Topology execution completed successfully")
        print(f"Execution time: {execution_result['execution_time']:.2f}s")
        print(f"Nodes executed: {execution_result['nodes_executed']}")
        print(f"Trace ID: {execution_result['trace_id']}")
    else:
        print(f"❌ Topology execution failed: {execution_result.get('error')}")
        return
    
    # 11. Authentication
    print("\n🔐 11. Authentication")
    
    auth_manager = get_auth_manager()
    
    # Create a test user
    test_user = User(
        id="example-user-123",
        username="example_user",
        email="user@example.com",
        roles=[UserRole.DEVELOPER],
        permissions=[Permission.READ_TOPOLOGY, Permission.EXECUTE_TOPOLOGY]
    )
    
    # Create access token
    access_token = auth_manager.create_access_token(test_user)
    refresh_token = auth_manager.create_refresh_token(test_user)
    
    print(f"✅ Access token created: {access_token[:20]}...")
    print(f"✅ Refresh token created: {refresh_token[:20]}...")
    
    # Verify token
    token_payload = auth_manager.verify_token(access_token)
    if token_payload:
        print(f"✅ Token verified for user: {token_payload.username}")
    else:
        print("❌ Token verification failed")
    
    # 12. Final Context and Results
    print("\n📊 12. Final Results")
    
    # Get final context
    final_context = await context_store.get(session_id)
    print(f"Final context fields: {len(final_context)}")
    
    # Get orchestrator metrics
    orchestrator_metrics = orchestrator.get_performance_metrics()
    print(f"Orchestrator metrics: {orchestrator_metrics}")
    
    # Get circuit breaker state
    cb_state = ai_circuit_breaker.get_state()
    print(f"Circuit breaker state: {cb_state['state']}")
    
    # Get human gate stats
    gate_stats = approval_gate.get_stats()
    print(f"Human gate stats: {gate_stats}")
    
    print("\n🎉 TopoKit basic usage example completed successfully!")
    print("\nKey Features Demonstrated:")
    print("✅ Configuration management")
    print("✅ Topology pack creation and parsing")
    print("✅ Schema validation with auto-repair")
    print("✅ Context store with CRDT conflict resolution")
    print("✅ Multi-stage guardrails system")
    print("✅ Circuit breaker protection")
    print("✅ Human-in-the-loop gates")
    print("✅ Edge enforcement engine")
    print("✅ DAG orchestration")
    print("✅ JWT authentication and authorization")
    print("✅ Comprehensive logging and observability")


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())
