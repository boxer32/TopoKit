# TopoKit Adapters Guide

TopoKit supports integration with various LLM providers, vector databases, and graph databases through a flexible adapter system.

## Overview

Adapters allow TopoKit to integrate with external services while maintaining a consistent interface. All adapters implement the `BaseAdapter` interface and support:

- Health monitoring
- Error handling and retries
- Cost and token tracking
- Configuration management

## LLM Provider Adapters

### OpenAI

The OpenAI adapter supports GPT-3.5 and GPT-4 models.

#### Configuration

```yaml
# In nodes.yaml
metadata:
  adapter: "openai"
  model: "gpt-4-turbo-preview"  # or gpt-3.5-turbo, gpt-4, etc.
```

#### Environment Variables

```bash
export OPENAI_API_KEY=sk-your-api-key-here
```

#### Usage Example

```python
from topokit.adapters import OpenAIAdapter, AdapterConfig, AdapterType

config = AdapterConfig(
    adapter_id="openai-main",
    adapter_type=AdapterType.LLM_PROVIDER,
    provider="openai",
    connection_params={
        "api_key": "sk-...",
        "model": "gpt-4-turbo-preview"
    }
)

adapter = OpenAIAdapter(config)
await adapter.initialize()

# Execute
result = await adapter.execute(context)
print(f"Response: {result.output_data['response']}")
print(f"Tokens used: {result.tokens_used}")
print(f"Cost: ${result.cost_usd}")
```

### Anthropic Claude

The Anthropic adapter supports Claude models.

#### Configuration

```yaml
metadata:
  adapter: "anthropic"
  model: "claude-3-5-sonnet-20241022"
```

#### Environment Variables

```bash
export ANTHROPIC_API_KEY=sk-ant-your-api-key-here
```

### LangChain

The LangChain adapter integrates LangChain chains into TopoKit.

#### Configuration

```yaml
metadata:
  adapter: "langchain"
  chain_type: "retrieval_qa"
  llm_type: "openai"
  prompt_template: "Answer based on context: {context}\nQuestion: {question}"
```

#### Installation

```bash
pip install langchain openai
```

### LlamaIndex

The LlamaIndex adapter provides vector store integration.

#### Configuration

```yaml
metadata:
  adapter: "llamaindex"
  vector_store_type: "simple"
  similarity_top_k: 5
  llm_type: "openai"
```

#### Installation

```bash
pip install llamaindex
```

### Hugging Face

The Hugging Face adapter supports local model inference.

#### Configuration

```yaml
metadata:
  adapter: "huggingface"
  model_name: "gpt2"
  task: "text-generation"
```

#### Installation

```bash
pip install transformers torch
```

## Vector Database Adapters

### Pinecone

```yaml
metadata:
  adapter: "pinecone"
  index_name: "my-index"
```

#### Configuration

```python
config = AdapterConfig(
    adapter_id="pinecone-main",
    adapter_type=AdapterType.VECTOR_DATABASE,
    provider="pinecone",
    connection_params={
        "api_key": "your-pinecone-key",
        "index_name": "my-index",
        "openai_api_key": "sk-..."  # For embeddings
    }
)
```

### Weaviate

```yaml
metadata:
  adapter: "weaviate"
  url: "http://localhost:8080"
  class_name: "Document"
```

### Chroma

```yaml
metadata:
  adapter: "chroma"
  collection_name: "documents"
  persist_directory: "./chroma_db"
```

## Graph Database Adapters

### Neo4j

```yaml
metadata:
  adapter: "neo4j"
  uri: "bolt://localhost:7687"
  username: "neo4j"
```

#### Cypher Query Example

```python
# In your node execution
query = """
MATCH (n:Person)-[:KNOWS]->(m:Person)
WHERE n.name = $name
RETURN m.name AS friend
"""
result = await adapter.execute(context_with_query)
```

### ArangoDB

```yaml
metadata:
  adapter: "arangodb"
  hosts: "http://localhost:8529"
  database: "my_database"
```

#### AQL Query Example

```python
query = """
FOR doc IN documents
  FILTER doc.category == @category
  RETURN doc
"""
result = await adapter.execute(context_with_query)
```

## Adapter Management

### Adapter Manager

Use the `AdapterManager` to manage multiple adapters:

```python
from topokit.adapters import AdapterManager, AdapterManagerConfig, AdapterConfig, AdapterType

# Create manager configuration
manager_config = AdapterManagerConfig(
    adapters=[
        AdapterConfig(
            adapter_id="openai-main",
            adapter_type=AdapterType.LLM_PROVIDER,
            provider="openai",
            connection_params={"api_key": "sk-..."}
        ),
        AdapterConfig(
            adapter_id="pinecone-main",
            adapter_type=AdapterType.VECTOR_DATABASE,
            provider="pinecone",
            connection_params={"api_key": "...", "index_name": "my-index"}
        )
    ],
    health_check_interval_seconds=60,
    enable_health_monitoring=True
)

# Initialize manager
manager = AdapterManager(manager_config)
await manager.initialize()

# Check health
health = await manager.check_all_health()
for adapter_id, status in health.items():
    print(f"{adapter_id}: {'healthy' if status.healthy else 'unhealthy'}")

# Get adapter
adapter = manager.get_adapter("openai-main")
```

### Configuration File

You can also load adapters from a configuration file:

```yaml
# adapters.yaml
adapters:
  - adapter_id: "openai-main"
    adapter_type: "llm_provider"
    provider: "openai"
    version: "1.0.0"
    enabled: true
    timeout_ms: 30000
    max_retries: 3
    connection_params:
      api_key: "${OPENAI_API_KEY}"
      model: "gpt-4-turbo-preview"
    metadata:
      description: "Primary OpenAI adapter"

health_check_interval_seconds: 60
enable_health_monitoring: true
enable_auto_retry: true
max_retries: 3
```

```python
from topokit.adapters import load_adapter_configs

config = load_adapter_configs("adapters.yaml")
manager = AdapterManager(config)
await manager.initialize()
```

## Adapter Testing

Test your adapters using the testing framework:

```python
from topokit.adapters import AdapterTester, TestScenario

tester = AdapterTester()

# Define test scenarios
scenarios = [
    TestScenario(
        name="simple_query",
        description="Test simple query execution",
        input_data="What is TopoKit?",
        expected_pattern="topology",
        max_latency_ms=5000.0,
        min_confidence=0.8
    )
]

# Run validation tests
results = await tester.run_validation_tests(adapter, scenarios)

# Run performance benchmark
benchmark = await tester.run_performance_benchmark(
    adapter,
    scenarios[0],
    iterations=10,
    concurrent=5
)

print(f"Average latency: {benchmark.latency_ms}ms")
print(f"Throughput: {benchmark.throughput_rps} RPS")
```

## Best Practices

1. **Use Environment Variables**: Never hardcode API keys in configuration files
2. **Monitor Health**: Enable health monitoring for production deployments
3. **Handle Errors**: Implement proper error handling and retry logic
4. **Track Costs**: Monitor token usage and costs, especially for LLM providers
5. **Test Adapters**: Use the testing framework before deploying to production
6. **Cache When Possible**: Enable caching for frequently accessed data

## Troubleshooting

### Adapter Not Found

```python
# Register adapter manually
from topokit.adapters import register_adapter

register_adapter("my-adapter", MyCustomAdapter)
```

### Connection Failures

```python
# Check health status
health = await adapter.health_check()
if not health.healthy:
    print(f"Error: {health.error_message}")
```

### Cost Tracking

```python
# Monitor costs
result = await adapter.execute(context)
print(f"Cost: ${result.cost_usd}")
print(f"Tokens: {result.tokens_used}")
```

## Creating Custom Adapters

To create a custom adapter, extend `BaseAdapter`:

```python
from topokit.adapters import BaseAdapter, AdapterType, AdapterConfig, ExecutionContext, ExecutionResult

class MyCustomAdapter(BaseAdapter):
    @property
    def adapter_type(self) -> AdapterType:
        return AdapterType.CUSTOM
    
    @property
    def provider(self) -> str:
        return "my-custom-provider"
    
    async def _initialize_impl(self) -> None:
        # Initialize your adapter
        pass
    
    async def _execute_impl(self, context: ExecutionContext, execution_profile) -> ExecutionResult:
        # Implement execution logic
        return ExecutionResult(
            success=True,
            output_data={"result": "..."},
            confidence=1.0
        )
    
    async def _health_check_impl(self) -> bool:
        # Implement health check
        return True
```

Then register it:

```python
from topokit.adapters import register_adapter

register_adapter("my-custom", MyCustomAdapter)
```

## Additional Resources

- [Adapter Framework API Reference](../packages/core/topokit/adapters/framework.py)
- [Testing Framework](../packages/core/topokit/adapters/testing.py)
- [Configuration Management](../packages/core/topokit/adapters/config.py)

