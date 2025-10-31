# TopoKit Platform

**Enterprise-grade topology-first contract system for building reliable, testable, and explainable AI/LLM applications.**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Pydantic](https://img.shields.io/badge/Pydantic-2.0+-orange.svg)](https://pydantic.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🚀 **Quick Start**

### Using the CLI

```bash
# Install TopoKit CLI
npm install -g @topokit/cli

# Initialize a project with a template
topokit init --template=rag-system

# Navigate to your topology
cd topology

# Validate your configuration
topokit lint

# Generate visualization
topokit graph --format=mermaid

# Run tests
topokit eval
```

See the [Quick Start Guide](docs/quickstart.md) for more details.

### Using Python

```python
import asyncio
from topokit.core.orchestrator import EnhancedTopoOrchestrator
from topokit.types.topology import TopologyPack, Node, EdgePolicy

async def main():
    # Create a simple topology
    pack = TopologyPack(
        name="hello-world",
        version="1.0.0",
        nodes=[
            Node(id="input", name="Input", kind="data"),
            Node(id="process", name="Process", kind="ai"),
            Node(id="output", name="Output", kind="data")
        ],
        edges=[
            EdgePolicy(id="e1", from_node="input", to_node="process", allow=True),
            EdgePolicy(id="e2", from_node="process", to_node="output", allow=True)
        ]
    )
    
    # Execute the topology
    orchestrator = EnhancedTopoOrchestrator(pack)
    result = await orchestrator.execute(
        session_id="test-session",
        input_data={"message": "Hello TopoKit!"}
    )
    
    print(f"Execution result: {result}")

asyncio.run(main())
```

## 🏗️ **Architecture Overview**

TopoKit provides a comprehensive platform for building AI applications with:

- **🎯 Topology-First Design**: Define your AI workflows as directed acyclic graphs (DAGs)
- **📋 Contract-Based Validation**: JSON Schema validation for all data flows
- **🛡️ Multi-Stage Guardrails**: Pre/post processing, content moderation, confidence gating
- **⚡ Circuit Breakers**: Multi-tier failure protection and recovery
- **👥 Human-in-the-Loop**: Approval workflows and escalation chains
- **💾 CRDT Context Store**: Conflict-free replicated data types for distributed state
- **🔐 Enterprise Security**: JWT authentication, RBAC, audit logging
- **📊 Observability**: Comprehensive logging, metrics, and tracing

## 🔌 **Ecosystem Integrations**

TopoKit supports integration with popular AI/ML frameworks through adapters:

### LLM Providers
- ✅ **OpenAI** - GPT-3.5, GPT-4, GPT-4 Turbo
- ✅ **Anthropic** - Claude 3.5 Sonnet, Claude 3 Opus
- ✅ **LangChain** - Chain integration and RAG workflows
- ✅ **LlamaIndex** - Vector store integration
- ✅ **Hugging Face** - Local model inference

### Vector Databases
- ✅ **Pinecone** - Managed vector database
- ✅ **Weaviate** - Open-source vector search
- ✅ **Chroma** - Embedded vector database

### Graph Databases
- ✅ **Neo4j** - Graph database with Cypher queries
- ✅ **ArangoDB** - Multi-model database with AQL

### Creating Custom Adapters

```python
from topokit.adapters import BaseAdapter, AdapterType, ExecutionResult

class MyCustomAdapter(BaseAdapter):
    @property
    def adapter_type(self):
        return AdapterType.CUSTOM
    
    async def _execute_impl(self, context, profile):
        # Your implementation
        return ExecutionResult(success=True, output_data={...})
```

See the [Adapters Guide](docs/adapters.md) for complete documentation.

## 📦 **Core Components**

### **Topology Management**
- **Pack Parser**: <100ms parsing with streaming validation
- **Schema Validator**: JSON Schema validation with auto-repair
- **Orchestrator**: DAG execution with fallback systems

### **Safety & Reliability**
- **Guardrails**: Multi-stage safety controls
- **Circuit Breakers**: Failure protection and recovery
- **Human Gates**: Approval workflows and escalation
- **Edge Enforcement**: Real-time contract validation

### **Infrastructure**
- **Context Store**: CRDT-based state management
- **Authentication**: JWT with RBAC system
- **API Framework**: FastAPI with comprehensive middleware
- **Database**: PostgreSQL with automated migrations
- **Logging**: Structured logging with OpenTelemetry

## 🛠️ **Installation**

```bash
# Clone the repository
git clone https://github.com/your-org/topokit.git
cd topokit

# Install dependencies
pip install -r requirements.txt

# Run database migrations
python -m topokit.core.database migrate

# Start the API server
python -m topokit.core.api
```

## 📚 **Usage Examples**

### **Basic Topology**

```python
from topokit.types.topology import TopologyPack, Node, EdgePolicy

# Define your AI workflow as a topology
pack = TopologyPack(
    name="chatbot",
    version="1.0.0",
    nodes=[
        Node(id="input", name="User Input", kind="data"),
        Node(id="ai", name="AI Response", kind="ai"),
        Node(id="output", name="Formatted Output", kind="data")
    ],
    edges=[
        EdgePolicy(id="e1", from_node="input", to_node="ai", allow=True),
        EdgePolicy(id="e2", from_node="ai", to_node="output", allow=True)
    ]
)
```

### **Schema Validation**

```python
from topokit.core.schema_validator import SchemaValidator

validator = SchemaValidator(lenient_parsing=True, auto_repair=True)

schema = {
    "type": "object",
    "properties": {
        "message": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1}
    },
    "required": ["message"]
}

data = '{"message": "Hello", "confidence": 0.9,}'  # Note trailing comma
result = validator.validate(data, schema)

if result.success:
    print("✅ Validation passed with auto-repair")
    print(f"Repaired data: {result.data}")
```

### **Context Store with CRDT**

```python
from topokit.core.context_store import EnhancedContextStore, MergeStrategy

store = EnhancedContextStore(
    merge_strategy=MergeStrategy.FIELD_LEVEL_CRDT,
    conflict_resolution=ConflictResolutionStrategy.AUTOMATIC
)

# Store context
await store.upsert(
    session_id="session-123",
    patch={"user_id": "user456", "status": "processing"},
    node_id="input_node",
    trace_id="trace-789"
)

# Retrieve context
context = await store.get("session-123")
print(f"User: {context['user_id']}, Status: {context['status']}")
```

### **Guardrails System**

```python
from topokit.core.guardrails import MultiStageGuardrails, PolicyEnvironment

guardrails = MultiStageGuardrails(
    pack.guardrails,
    PolicyEnvironment.PRODUCTION
)

# Pre-processing validation
pre_result = await guardrails.apply_pre_processing(
    data=input_data,
    node=node,
    trace_id="trace-123"
)

if pre_result.passed:
    print("✅ Pre-processing passed")
else:
    print(f"❌ Pre-processing failed: {pre_result.message}")
```

### **Circuit Breakers**

```python
from topokit.core.circuit_breaker import CircuitBreakerManager, CircuitBreakerLevel

manager = CircuitBreakerManager()
cb = manager.create_circuit_breaker(
    identifier="ai-service-cb",
    level=CircuitBreakerLevel.NODE
)

# Protected function call
async def call_ai_service():
    return await ai_service.generate_response(prompt)

try:
    result = await cb.call(call_ai_service)
    print(f"AI response: {result}")
except CircuitBreakerOpenError:
    print("Circuit breaker is open - service unavailable")
```

### **Human-in-the-Loop Gates**

```python
from topokit.core.human_gates import HumanGateManager, GateType, GatePriority

gate_manager = HumanGateManager()
gate = gate_manager.create_gate(
    identifier="high-risk-approval",
    gate_type=GateType.APPROVAL,
    priority=GatePriority.HIGH,
    timeout_seconds=300
)

# Request approval
request_id = await gate.request_approval(
    title="High-Risk Operation",
    description="This operation requires human approval",
    data={"operation": "delete_user", "user_id": "user123"}
)

# Approve the request
await gate.approve_request(
    request_id=request_id,
    approved_by="admin",
    comments="Approved after review"
)
```

## 🔧 **Configuration**

TopoKit uses environment-based configuration:

```bash
# Environment
export TOPOKIT_ENVIRONMENT=production

# Database
export TOPOKIT_DATABASE_HOST=localhost
export TOPOKIT_DATABASE_PORT=5432
export TOPOKIT_DATABASE_NAME=topokit
export TOPOKIT_DATABASE_USER=topokit
export TOPOKIT_DATABASE_PASSWORD=your_password

# Security
export TOPOKIT_SECURITY_SECRET_KEY=your-secret-key-here

# LLM Provider
export TOPOKIT_LLM_PROVIDER=openai
export TOPOKIT_LLM_API_KEY=your-api-key
export TOPOKIT_LLM_MODEL=gpt-3.5-turbo

# Observability
export TOPOKIT_OBSERVABILITY_LOG_LEVEL=INFO
export TOPOKIT_OBSERVABILITY_METRICS_PORT=8080
```

## 🧪 **Testing**

```bash
# Run all tests
pytest

# Run integration tests
pytest packages/core/topokit/tests/test_integration.py -v

# Run with coverage
pytest --cov=topokit --cov-report=html
```

## 📊 **Monitoring & Observability**

TopoKit provides comprehensive observability:

- **Structured Logging**: JSON-formatted logs with context propagation
- **Metrics**: Performance metrics for all components
- **Tracing**: Distributed tracing with OpenTelemetry
- **Health Checks**: Built-in health check endpoints
- **Audit Logs**: Security and compliance event logging

## 🔐 **Security Features**

- **Authentication**: JWT-based authentication with refresh tokens
- **Authorization**: Role-based access control (RBAC)
- **Content Moderation**: Built-in content filtering and PII detection
- **Audit Logging**: Comprehensive security event logging
- **Rate Limiting**: Protection against abuse and DoS attacks
- **Data Encryption**: Encrypted data storage and transmission

## 🚀 **Performance**

- **Pack Parser**: <100ms for files up to 1MB
- **Context Store**: <10ms read/write operations
- **Schema Validation**: <10ms validation time
- **Edge Enforcement**: <5ms enforcement time
- **Orchestrator**: Supports concurrent executions with proper locking

## 🤝 **Contributing**

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 **Support**

- **Documentation**: [docs.topokit.dev](https://docs.topokit.dev)
- **Issues**: [GitHub Issues](https://github.com/your-org/topokit/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/topokit/discussions)
- **Email**: support@topokit.dev

## 📋 **Templates**

Get started quickly with pre-built templates:

```bash
# List available templates
topokit init --list-templates

# RAG System
topokit init --template=rag-system

# Multi-Agent System
topokit init --template=multi-agent

# LangChain Integration
topokit init --template=langchain-integration

# LlamaIndex Integration
topokit init --template=llamaindex-integration

# Travel Booking System
topokit init --template=travel-booking
```

## 📚 **Documentation**

- **[Quick Start](docs/quickstart.md)** - Get up and running in 5 minutes
- **[Architecture Guide](docs/architecture.md)** - System architecture and design
- **[Adapters Guide](docs/adapters.md)** - Using LLM and database adapters
- **[CLI Reference](docs/cli-reference.md)** - Complete CLI documentation
- **[Full Documentation](docs/index.md)** - All documentation

## 🗺️ **Roadmap**

- [x] **v1.0**: Core platform with orchestrator, guardrails, and context store
- [x] **v1.1**: LLM provider integrations (OpenAI, Anthropic, LangChain, LlamaIndex, Hugging Face)
- [x] **v1.2**: Vector and graph database support
- [ ] **v1.3**: Real-time collaboration features
- [ ] **v1.4**: Advanced analytics and insights
- [ ] **v2.0**: Multi-cloud deployment support

---

**Built with ❤️ by the TopoKit Team**