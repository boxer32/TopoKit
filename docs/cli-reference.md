# TopoKit CLI Reference

Complete reference for all TopoKit CLI commands.

## Installation

```bash
npm install -g @topokit/cli
# or
pnpm add -g @topokit/cli
```

## Commands Overview

```bash
topokit <command> [options]
```

## Commands

### `init`

Initialize a new TopoKit project from a template.

```bash
topokit init [options]
```

**Options:**
- `-t, --template <template>` - Template to use (default: rag-system)
- `-l, --language <language>` - Programming language (default: typescript)
- `-o, --output <output>` - Output directory (default: .)
- `--list-templates` - List all available templates

**Examples:**
```bash
topokit init --template=rag-system
topokit init --template=multi-agent --output=my-agents
topokit init --list-templates
```

**Templates:**
- `rag-system` - Basic RAG with data retrieval and AI answers
- `qa-system` - Question-answering with document processing
- `multi-agent` - Multi-agent coordination system
- `langchain-integration` - LangChain chain integration
- `llamaindex-integration` - LlamaIndex vector store integration
- `travel-booking` - Travel booking system

---

### `lint`

Lint and validate topology pack configuration.

```bash
topokit lint [options]
```

**Options:**
- `-d, --pack-dir <dir>` - Topology pack directory (default: ./topology)
- `--strict` - Enable strict validation
- `--fix` - Auto-fix issues where possible

**Examples:**
```bash
topokit lint
topokit lint --strict --fix
topokit lint --pack-dir=./my-topology
```

**Validates:**
- Node definitions (required fields, valid types)
- Edge policies (valid references, contracts)
- Contracts (valid JSON Schema)
- Guardrails configuration
- Schema consistency

---

### `graph`

Generate topology visualization.

```bash
topokit graph [options]
```

**Options:**
- `-d, --pack-dir <dir>` - Topology pack directory (default: ./topology)
- `-o, --output <file>` - Output file (default: stdout)
- `-f, --format <format>` - Output format: mermaid, svg, png, dot (default: mermaid)
- `--theme <theme>` - Graph theme: light, dark, colorblind (default: light)
- `--layout <layout>` - Layout algorithm: top-down, left-right, circular (default: top-down)
- `--show-contracts` - Show contract information on edges
- `--show-slos` - Show SLO information on nodes
- `--show-execution-profile` - Show execution profile details

**Examples:**
```bash
topokit graph --format=mermaid
topokit graph --format=svg --show-contracts --show-slos
topokit graph --format=dot --theme=dark --layout=left-right
topokit graph --output=topology.mmd
```

---

### `eval`

Run evaluation tests on topology pack.

```bash
topokit eval [options]
```

**Options:**
- `-d, --pack-dir <dir>` - Topology pack directory (default: ./topology)
- `-t, --test-dir <dir>` - Test directory (default: ./topology/eval)
- `--verbose` - Verbose output

**Examples:**
```bash
topokit eval
topokit eval --verbose
topokit eval --test-dir=./custom-tests
```

**Evaluates:**
- Semantic similarity
- Factual consistency
- Coherence assessment
- Pass@k metrics
- Drift detection
- Cost efficiency
- Latency and throughput

---

### `test`

Run unit and integration tests.

```bash
topokit test [options]
```

**Options:**
- `-d, --pack-dir <dir>` - Topology pack directory (default: ./topology)
- `--coverage` - Generate coverage report
- `--watch` - Watch mode for development
- `--verbose` - Verbose output

**Examples:**
```bash
topokit test
topokit test --coverage
topokit test --watch
```

---

### `replay`

Replay execution with deterministic testing.

```bash
topokit replay [options]
```

**Options:**
- `-d, --pack-dir <dir>` - Topology pack directory
- `--session-id <id>` - Session ID to replay
- `--trace-id <id>` - Trace ID to replay
- `--seed <seed>` - Random seed for deterministic execution
- `--compare` - Compare with golden case

**Examples:**
```bash
topokit replay --session-id=session-123
topokit replay --trace-id=trace-456 --seed=stable
topokit replay --compare
```

---

### `monitor`

Monitor topology execution in real-time.

```bash
topokit monitor [options]
```

**Options:**
- `--watch` - Watch mode with auto-refresh
- `--metrics <metrics>` - Comma-separated metrics to display
- `--format <format>` - Output format: table, json (default: table)
- `--interval <seconds>` - Refresh interval in seconds (default: 1)

**Examples:**
```bash
topokit monitor --watch
topokit monitor --metrics=latency,cost,quality
topokit monitor --format=json --interval=5
```

**Metrics Available:**
- `latency` - Execution latency
- `throughput` - Requests per second
- `cost` - Cost per request
- `quality` - Quality scores
- `errors` - Error rates
- `drift` - Drift detection

---

### `cost`

Analyze topology costs and optimization opportunities.

```bash
topokit cost [options]
```

**Options:**
- `-d, --pack-dir <dir>` - Topology pack directory (default: ./topology)
- `-m, --model <model>` - LLM model to analyze (default: gpt-4)
- `--tokens <tokens>` - Estimated tokens per request (default: 1000)
- `--requests <requests>` - Number of requests to analyze (default: 1000)
- `--optimize` - Show optimization recommendations
- `--budget <budget>` - Budget limit in USD (default: 100)

**Examples:**
```bash
topokit cost --model=gpt-4
topokit cost --tokens=2000 --requests=5000
topokit cost --optimize --budget=50
```

**Output:**
- Total cost breakdown
- Cost by node
- Cost by model
- Cost by operation
- Optimization recommendations

---

### `drift`

Detect drift in topology execution.

```bash
topokit drift [options]
```

**Options:**
- `-d, --pack-dir <dir>` - Topology pack directory
- `--create-baseline` - Create baseline metrics
- `--baseline <file>` - Baseline file path
- `--detect` - Detect drift against baseline
- `--threshold <percentage>` - Drift threshold percentage (default: 10)
- `--output <file>` - Output file for results

**Examples:**
```bash
topokit drift --create-baseline --output=baseline.json
topokit drift --baseline=baseline.json --detect
topokit drift --threshold=15
```

**Drift Detection:**
- Statistical anomaly detection (z-score)
- Percentage-based drift calculation
- Baseline comparison
- Alert generation

---

### `policy`

Manage and validate policies.

```bash
topokit policy [options]
```

**Options:**
- `-d, --pack-dir <dir>` - Topology pack directory
- `--validate` - Validate policies
- `--test` - Run policy tests
- `--generate-templates` - Generate policy templates

**Examples:**
```bash
topokit policy --validate
topokit policy --test
topokit policy --generate-templates
```

---

### `migrate`

Migrate topology between versions.

```bash
topokit migrate [options]
```

**Options:**
- `--from-version <version>` - Source version
- `--to-version <version>` - Target version
- `--dry-run` - Show what would be migrated without applying
- `--backup` - Create backup before migration

**Examples:**
```bash
topokit migrate --from-version=1.0.0 --to-version=2.0.0
topokit migrate --dry-run
```

---

### `dev`

Start development server with hot reload.

```bash
topokit dev [options]
```

**Options:**
- `--watch` - Watch mode (default: true)
- `--port <port>` - Server port (default: 3000)
- `--open` - Open browser automatically

**Examples:**
```bash
topokit dev
topokit dev --port=8080
topokit dev --open
```

---

### `generate`

Generate code components.

```bash
topokit generate [options]
```

**Options:**
- `--type <type>` - Component type: node, contract, edge
- `--name <name>` - Component name
- `--template <template>` - Template to use

**Examples:**
```bash
topokit generate --type=node --name=MyNode --template=ai
topokit generate --type=contract --name=my-contract
```

---

### `docs`

Generate documentation.

```bash
topokit docs [options]
```

**Options:**
- `-d, --pack-dir <dir>` - Topology pack directory
- `--output <dir>` - Output directory
- `--format <format>` - Documentation format: markdown, html (default: markdown)

**Examples:**
```bash
topokit docs
topokit docs --output=./docs --format=html
```

---

### `help`

Show help information.

```bash
topokit help [command]
topokit help --examples
topokit help --troubleshooting
```

**Options:**
- `<command>` - Show help for specific command
- `--examples` - Show detailed examples
- `--troubleshooting` - Show troubleshooting guide

**Examples:**
```bash
topokit help
topokit help init
topokit help --examples
```

---

## Global Options

All commands support these global options:

- `--version` - Show version number
- `-h, --help` - Show help for command
- `--verbose` - Verbose output
- `--quiet` - Quiet mode (errors only)

## Configuration

TopoKit can be configured via:

1. **Command-line options** (highest priority)
2. **Configuration file** (`topokit.config.json`)
3. **Environment variables**
4. **Defaults** (lowest priority)

### Configuration File

Create `topokit.config.json`:

```json
{
  "packDir": "./topology",
  "defaultTemplate": "rag-system",
  "logging": {
    "level": "info",
    "format": "json"
  },
  "monitoring": {
    "enabled": true,
    "interval": 1000
  }
}
```

### Environment Variables

```bash
export TOPOKIT_PACK_DIR=./topology
export TOPOKIT_LOG_LEVEL=debug
export TOPOKIT_API_KEY=your-key
```

## Exit Codes

- `0` - Success
- `1` - General error
- `2` - Invalid command or option
- `3` - Validation error
- `4` - Execution error

## Examples

### Complete Workflow

```bash
# 1. Initialize project
topokit init --template=rag-system --output=my-project

# 2. Navigate to topology
cd my-project/topology

# 3. Validate
topokit lint

# 4. Visualize
topokit graph --format=mermaid --show-contracts

# 5. Test
topokit test --coverage

# 6. Evaluate
topokit eval

# 7. Analyze costs
topokit cost --optimize

# 8. Start development
topokit dev --watch
```

## See Also

- [Quick Start Guide](./quickstart.md)
- [Architecture Documentation](./architecture.md)
- [API Reference](./api-reference.md)

