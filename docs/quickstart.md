# TopoKit Quickstart Guide

Get up and running with TopoKit in minutes. This guide will walk you through installing TopoKit, creating your first topology, and deploying it.

## Prerequisites

- **Node.js** 18+ and npm/pnpm
- **Python** 3.11+ (for core library)
- **Git** (for version control)

## Installation

### Install TopoKit CLI

```bash
npm install -g @topokit/cli
# or using pnpm
pnpm add -g @topokit/cli
```

### Verify Installation

```bash
topokit --version
topokit help
```

## Quick Start (5 Minutes)

### Step 1: Initialize a Project

Create a new TopoKit project using a template:

```bash
# List available templates
topokit init --list-templates

# Create a RAG system
topokit init --template=rag-system --output=my-rag-project

# Or create a multi-agent system
topokit init --template=multi-agent --output=my-agents

# Or integrate with LangChain
topokit init --template=langchain-integration --output=my-langchain-app
```

### Step 2: Explore Your Project

```bash
cd my-rag-project/topology
ls -la
```

You'll see:
- `nodes.yaml` - Node definitions
- `edges.yaml` - Edge policies
- `guardrails.yaml` - Safety constraints
- `contracts/` - JSON Schema contracts
- `README.md` - Project documentation

### Step 3: Validate Your Topology

```bash
# Lint your topology configuration
topokit lint

# Generate a visual graph
topokit graph --format=mermaid --output=topology.mmd

# View the graph (if you have a Mermaid viewer)
open topology.mmd
```

### Step 4: Run Tests

```bash
# Run evaluation tests
topokit eval

# Run unit tests with coverage
topokit test --coverage
```

### Step 5: Start Development

```bash
# Start development server with hot reload
topokit dev --watch

# The server will be available at http://localhost:3000
```

## Working with Templates

### Available Templates

TopoKit comes with several pre-built templates:

1. **rag-system** - Basic RAG (Retrieval-Augmented Generation) system
   - Document retrieval
   - AI answer generation
   - Vector store integration

2. **qa-system** - Question-answering system
   - Document processing
   - Question analysis
   - Answer generation

3. **multi-agent** - Multi-agent coordination
   - Research agent
   - Analysis agent
   - Synthesis agent
   - Validation agent

4. **langchain-integration** - LangChain integration
   - LangChain chains
   - Vector store integration
   - RAG workflows

5. **llamaindex-integration** - LlamaIndex integration
   - LlamaIndex query engine
   - Document indexing
   - Vector store RAG

6. **travel-booking** - Travel booking system
   - Flight search
   - Hotel search
   - Booking coordination
   - Payment processing

### Customizing Templates

Templates are just YAML files. You can customize them:

```bash
# Edit nodes
nano topology/nodes.yaml

# Edit edges
nano topology/edges.yaml

# Add custom contracts
nano topology/contracts/my-contract.json
```

## Using Adapters

TopoKit supports various LLM providers and databases through adapters.

### Configure OpenAI

```yaml
# In nodes.yaml, add metadata:
metadata:
  adapter: "openai"
  model: "gpt-4-turbo-preview"
```

Set environment variable:
```bash
export OPENAI_API_KEY=your-api-key
```

### Configure Anthropic Claude

```yaml
metadata:
  adapter: "anthropic"
  model: "claude-3-5-sonnet-20241022"
```

Set environment variable:
```bash
export ANTHROPIC_API_KEY=your-api-key
```

### Use Vector Databases

```yaml
metadata:
  adapter: "pinecone"
  index_name: "my-index"
```

## Common Workflows

### Analyze Costs

```bash
# Analyze topology costs
topokit cost --model=gpt-4 --tokens=1000 --requests=1000

# Get optimization recommendations
topokit cost --optimize --budget=100
```

### Detect Drift

```bash
# Create baseline
topokit drift --create-baseline --output=baseline.json

# Detect drift against baseline
topokit drift --baseline=baseline.json --threshold=10
```

### Monitor Execution

```bash
# Start monitoring dashboard
topokit monitor --watch

# View metrics
topokit monitor --metrics=latency,cost,quality
```

### Manage Policies

```bash
# Validate policies
topokit policy --validate

# Generate policy templates
topokit policy --generate-templates
```

## Next Steps

1. **Read the Documentation**
   - [Architecture Guide](./architecture.md) - Understand system design
   - [API Reference](./api-reference.md) - Complete API docs
   - [Adapters Guide](./adapters.md) - Using LLM and database adapters

2. **Customize Your Topology**
   - Add custom nodes
   - Define custom contracts
   - Configure guardrails

3. **Deploy to Production**
   ```bash
   topokit deploy --env=production
   ```

4. **Join the Community**
   - GitHub: [https://github.com/topokit/topokit](https://github.com/topokit/topokit)
   - Discord: [Join our Discord](https://discord.gg/topokit)

## Troubleshooting

### Common Issues

**Problem**: `topokit: command not found`
```bash
# Solution: Ensure npm global bin is in your PATH
npm config get prefix
export PATH="$(npm config get prefix)/bin:$PATH"
```

**Problem**: Template not found
```bash
# Solution: List available templates
topokit init --list-templates
```

**Problem**: Adapter initialization fails
```bash
# Solution: Check environment variables
echo $OPENAI_API_KEY
echo $ANTHROPIC_API_KEY
```

For more help, see:
- `topokit help --troubleshooting`
- [Troubleshooting Guide](./troubleshooting.md)

## Example: Complete Workflow

Here's a complete example of building and deploying a RAG system:

```bash
# 1. Initialize project
topokit init --template=rag-system --output=my-rag

# 2. Configure API keys
export OPENAI_API_KEY=sk-...

# 3. Validate
cd my-rag/topology
topokit lint

# 4. Visualize
topokit graph --format=mermaid --show-contracts

# 5. Test
topokit eval
topokit test

# 6. Analyze costs
topokit cost --model=gpt-4 --optimize

# 7. Develop
topokit dev --watch

# 8. Deploy
topokit deploy --env=production
```

## Getting Help

- **Documentation**: [Full Documentation](./index.md)
- **CLI Help**: `topokit help`
- **Examples**: `topokit help --examples`
- **GitHub Issues**: Report bugs and request features
- **Community**: Join discussions and get support

---

**Congratulations!** You're now ready to build AI/ML applications with TopoKit. 🚀

