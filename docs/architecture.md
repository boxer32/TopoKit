# TopoKit Architecture

This document describes the architecture of the TopoKit platform, including its core components, data flow, and design decisions.

## System Overview

TopoKit is built as a monorepo with multiple packages:

```
TopoKit/
├── packages/
│   ├── core/          # Python core library
│   ├── cli/            # TypeScript CLI
│   ├── dashboard/      # React dashboard
│   └── vscode-extension/  # VS Code extension
└── topology/           # Example topology packs
```

## Core Components

### 1. Orchestrator (`packages/core/topokit/core/orchestrator.py`)

The orchestrator is the heart of TopoKit, responsible for:

- **DAG Execution**: Executes topology as a directed acyclic graph
- **Dependency Resolution**: Resolves node dependencies and execution order
- **Cycle Detection**: Prevents circular dependencies
- **Fallback Strategies**: Multi-tier fallback handling
- **Confidence Gating**: Quality-based output filtering

```python
orchestrator = EnhancedTopoOrchestrator(
    pack=topology_pack,
    context_store=context_store,
    guardrails=guardrails,
    schema_validator=validator
)

result = await orchestrator.execute(
    session_id="session-123",
    input_data={"query": "..."},
    entry_node="Data.Retrieval"
)
```

### 2. Context Store (`packages/core/topokit/core/context_store.py`)

Manages versioned state with CRDT-based conflict resolution:

- **Versioned Writes**: Tracks context versions
- **CRDT Merge**: Multiple merge strategies (last-write-wins, field-level-CRDT, priority-based)
- **Conflict Resolution**: Automatic conflict resolution
- **Context Alignment**: Scoped retrieval and precision monitoring

### 3. Guardrails System (`packages/core/topokit/core/guardrails.py`)

Multi-stage safety constraint enforcement:

- **Pre-processing Guards**: Validate input before execution
- **Post-processing Guards**: Validate output after execution
- **Policy Templates**: Production, development, testing environments
- **Content Moderation**: Safety filters
- **Human Gates**: Approval workflows for high-risk actions

### 4. Schema Validator (`packages/core/topokit/core/schema_validator.py`)

JSON Schema validation with:

- **Streaming Validation**: Validates large payloads efficiently
- **Auto-repair**: Attempts to fix common LLM output issues
- **Lenient Parsing**: Handles malformed JSON gracefully
- **Performance**: <100ms parse time target

### 5. Policy Engine (`packages/core/topokit/core/policy_engine.py`)

Rego-based policy enforcement:

- **Rego Integration**: Uses Open Policy Agent (OPA)
- **Policy Validation**: Validates policies at compile time
- **Runtime Enforcement**: Enforces policies during execution
- **Environment Support**: Different policies for dev/test/prod

### 6. Adapter Framework (`packages/core/topokit/adapters/`)

Plugin-based adapter system:

- **Base Adapter Interface**: Consistent adapter API
- **Plugin System**: Register custom adapters
- **Health Monitoring**: Automatic health checks
- **Testing Framework**: Validation and benchmarking
- **Configuration Management**: YAML/JSON configuration

## Data Flow

### Execution Flow

```
User Input
    ↓
[Pre-processing Guardrails]
    ↓
[Orchestrator: DAG Execution]
    ├──→ [Node 1: Data.Retrieval]
    │       ↓
    │   [Adapter: Vector Store]
    │       ↓
    ├──→ [Node 2: AI.Answer]
    │       ↓
    │   [Adapter: OpenAI]
    │       ↓
    └──→ [Context Store Update]
            ↓
[Post-processing Guardrails]
    ↓
[Schema Validation]
    ↓
Output Result
```

### Adapter Execution

```
Node Request
    ↓
[Adapter Manager]
    ├──→ [Health Check]
    ├──→ [Load Adapter]
    └──→ [Execute]
            ↓
        [Adapter Implementation]
            ├──→ OpenAI API
            ├──→ Pinecone Query
            └──→ Neo4j Cypher
                ↓
        [Result Processing]
            ├──→ Token Counting
            ├──→ Cost Calculation
            └──→ Confidence Scoring
                ↓
        Execution Result
```

## Architecture Patterns

### 1. Topology-First Design

Topologies are defined as YAML files:
- `nodes.yaml` - Node definitions
- `edges.yaml` - Edge policies
- `guardrails.yaml` - Safety constraints
- `contracts/` - JSON Schema contracts

This enables:
- Version control for topologies
- Easy sharing and collaboration
- Visual representation
- Type safety

### 2. Contract-Based Communication

All data exchange uses JSON Schema contracts:
- Compile-time validation
- Runtime schema checking
- Type safety
- Clear API boundaries

### 3. Plugin Architecture

Adapters use a plugin system:
- Register adapters at runtime
- Health monitoring
- Configuration management
- Easy extension

### 4. Multi-Stage Processing

Requests go through multiple stages:
1. Pre-processing guardrails
2. Orchestrator execution
3. Adapter execution
4. Post-processing guardrails
5. Schema validation
6. Context update

## Storage Architecture

### Context Store

- **In-Memory**: Fast access for active sessions
- **Persistent**: PostgreSQL for production
- **Caching**: Redis for performance
- **Versioning**: Tracks all state changes

### Audit Logs

- **Database**: PostgreSQL with encryption
- **Tamper-Evident**: Cryptographic hashing
- **Retention**: Configurable retention policies
- **Compliance**: GDPR, CCPA, SOX, HIPAA

## Monitoring Architecture

### Metrics Collection

- **Performance**: Latency, throughput, error rates
- **Cost**: Token usage, cost per request
- **Quality**: Confidence scores, drift detection
- **Reliability**: Circuit breaker states, fallback usage

### Observability Stack

- **Traces**: Distributed tracing with spans
- **Logs**: Structured logging with correlation IDs
- **Metrics**: Time-series metrics
- **Alerts**: Multi-channel alerting (Slack, email, webhook)

## Security Architecture

### Authentication & Authorization

- **JWT**: Token-based authentication
- **RBAC**: Role-based access control
- **Multi-tenant**: Tenant isolation
- **Audit**: All actions logged

### Data Protection

- **PII Redaction**: Automatic PII detection and redaction
- **Encryption**: End-to-end encryption
- **Compliance**: Built-in compliance frameworks
- **Access Control**: Fine-grained permissions

## Scalability

### Horizontal Scaling

- **Stateless Orchestrator**: Can scale horizontally
- **Database**: PostgreSQL with read replicas
- **Caching**: Redis cluster
- **Load Balancing**: Multiple orchestrator instances

### Performance Optimization

- **Caching**: Multi-level caching strategy
- **Async Processing**: Asynchronous execution
- **Streaming**: Stream large payloads
- **Connection Pooling**: Efficient database connections

## Deployment Architecture

### Development

```
Developer
    ↓
[VS Code Extension]
    ↓
[Local Orchestrator]
    ↓
[Local Context Store]
```

### Production

```
Load Balancer
    ↓
[Orchestrator Instances]
    ├──→ [PostgreSQL]
    ├──→ [Redis]
    └──→ [Monitoring]
            ↓
    [TopoView Dashboard]
```

## Design Decisions

### Why Monorepo?

- Unified development experience
- Shared tooling and configuration
- Simplified CI/CD
- Version management

### Why Python + TypeScript?

- **Python**: Strong AI/ML ecosystem, Pydantic for validation
- **TypeScript**: Better developer tooling for CLI, web dashboard

### Why YAML for Topologies?

- Human-readable
- Version control friendly
- Easy to edit and share
- Tool support

### Why JSON Schema for Contracts?

- Industry standard
- Tool support
- Runtime validation
- Type generation

## Extension Points

### Custom Adapters

```python
class MyCustomAdapter(BaseAdapter):
    async def _execute_impl(self, context, profile):
        # Your implementation
        return ExecutionResult(...)
```

### Custom Guardrails

```python
class MyGuardrail(Guardrail):
    async def validate(self, data, node):
        # Your validation logic
        return GuardrailResult(...)
```

### Custom Policies

```rego
# policy.rego
package topokit

default allow = false

allow {
    input.action == "read"
    input.user.role == "admin"
}
```

## Performance Characteristics

### Latency Targets

- Parse time: <100ms
- Node execution: <2000ms (per node)
- End-to-end: <5000ms
- Monitoring refresh: <1000ms

### Throughput

- Target: 1,000+ RPS
- Concurrent sessions: 10,000+
- Database queries: Optimized with indexing

### Resource Usage

- Memory: <1GB per 1,000 sessions
- CPU: Efficient async processing
- Network: Connection pooling

## Future Enhancements

### Planned Features

- WebSocket support for real-time updates
- GraphQL API for flexible queries
- Multi-region deployment support
- Advanced caching strategies
- Machine learning-based drift detection

## Additional Resources

- [API Reference](./api-reference.md) - Detailed API documentation
- [Deployment Guide](./deployment.md) - Production deployment
- [Security Guide](./security.md) - Security best practices

