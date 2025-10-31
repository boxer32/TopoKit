# TopoKit Documentation

Welcome to the TopoKit documentation! TopoKit is an enterprise-grade topology-first contract system for building reliable, testable, and explainable AI/LLM applications.

## What is TopoKit?

TopoKit transforms conceptual system networks into enforceable runtime rules, code APIs, and CI evals through a comprehensive DAG-based orchestration system with enterprise-grade safety, observability, and compliance features.

## Quick Navigation

### Getting Started
- **[Quick Start Guide](./quickstart.md)** - Get up and running in 5 minutes
- **[Installation Guide](./installation.md)** - Detailed installation instructions
- **[Architecture Overview](./architecture.md)** - Understand the system design

### Core Concepts
- **[Topology Pack Format](./topology-pack.md)** - Understanding topology packs
- **[Nodes and Edges](./nodes-edges.md)** - Building your topology graph
- **[Contracts](./contracts.md)** - Type-safe data exchange
- **[Guardrails](./guardrails.md)** - Safety and compliance constraints

### Integration
- **[Adapters Guide](./adapters.md)** - LLM providers and database adapters
- **[LangChain Integration](./langchain-integration.md)** - Using LangChain with TopoKit
- **[LlamaIndex Integration](./llamaindex-integration.md)** - Using LlamaIndex with TopoKit

### Development
- **[CLI Reference](./cli-reference.md)** - Command-line interface commands
- **[API Reference](./api-reference.md)** - Python API documentation
- **[Testing Guide](./testing.md)** - Writing and running tests
- **[Deployment Guide](./deployment.md)** - Production deployment

### Operations
- **[Monitoring](./monitoring.md)** - Observability and monitoring
- **[Cost Optimization](./cost-optimization.md)** - Managing and reducing costs
- **[Drift Detection](./drift-detection.md)** - Detecting and handling drift
- **[Troubleshooting](./troubleshooting.md)** - Common issues and solutions

### Enterprise Features
- **[Security](./security.md)** - Security features and best practices
- **[Compliance](./compliance.md)** - GDPR, CCPA, SOX, HIPAA compliance
- **[Audit Logging](./audit-logging.md)** - Audit trails and compliance reporting

## Key Features

### 🎯 Topology-First Design
Define workflows as directed acyclic graphs with nodes and edges. Each node represents a capability boundary, and edges define communication policies.

### 📋 Contract-Based Communication
Type-safe data exchange using JSON Schema contracts. Ensure data consistency and catch errors at design time.

### 🛡️ Enterprise Safety
- Multi-stage guardrails (pre/post processing)
- Circuit breakers at multiple levels
- Human-in-the-loop gates
- Confidence gating and quality scoring

### 📊 Observability
- Real-time monitoring (<1s refresh)
- Performance metrics dashboard
- Execution timeline visualization
- Drift detection with statistical analysis
- Cost tracking and optimization

### ✅ Compliance Ready
- Audit trail generation
- GDPR, CCPA, SOX, HIPAA support
- PII redaction
- Data retention policies
- Tamper-evident logging

### 🔌 Ecosystem Integration
- LLM providers: OpenAI, Anthropic, LangChain, LlamaIndex, Hugging Face
- Vector databases: Pinecone, Weaviate, Chroma
- Graph databases: Neo4j, ArangoDB
- Plugin system for custom adapters

## Templates

Get started quickly with pre-built templates:

- **rag-system** - Basic RAG with document retrieval and AI answers
- **qa-system** - Question-answering with document processing
- **multi-agent** - Multi-agent coordination system
- **langchain-integration** - LangChain chain integration
- **llamaindex-integration** - LlamaIndex vector store integration
- **travel-booking** - Complete travel booking system

## CLI Commands

TopoKit provides a rich command-line interface:

```bash
# Initialize a new project
topokit init --template=rag-system

# Validate topology
topokit lint

# Generate visualization
topokit graph --format=mermaid

# Run tests
topokit test

# Monitor execution
topokit monitor

# Cost analysis
topokit cost --optimize

# Detect drift
topokit drift --detect
```

See the [CLI Reference](./cli-reference.md) for complete command documentation.

## Examples

### Basic RAG System

```bash
# Initialize
topokit init --template=rag-system

# Configure
export OPENAI_API_KEY=sk-...

# Validate
cd topology
topokit lint

# Visualize
topokit graph --format=mermaid

# Test
topokit eval
```

### Multi-Agent Workflow

```bash
# Initialize
topokit init --template=multi-agent

# Customize nodes
nano nodes.yaml

# Deploy
topokit deploy --env=production
```

## Community

- **GitHub**: [github.com/topokit/topokit](https://github.com/topokit/topokit)
- **Discord**: [Join our Discord](https://discord.gg/topokit)
- **Issues**: [Report bugs](https://github.com/topokit/topokit/issues)
- **Discussions**: [Ask questions](https://github.com/topokit/topokit/discussions)

## Contributing

We welcome contributions! See our [Contributing Guide](./contributing.md) for details.

## License

TopoKit is open source. See [LICENSE](../LICENSE) for details.

---

**Ready to get started?** Check out the [Quick Start Guide](./quickstart.md)!

