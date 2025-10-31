"""TopoKit Adapters for LLM providers, vector databases, and graph databases."""

from .framework import (
    BaseAdapter,
    AdapterConfig,
    AdapterHealth,
    AdapterRegistry,
    register_adapter,
    get_adapter,
    get_adapter_registry,
    ExecutionContext,
    ExecutionResult,
)

# Import adapters (optional dependencies)
try:
    from .openai import OpenAIAdapter
except ImportError:
    OpenAIAdapter = None

try:
    from .anthropic import AnthropicAdapter
except ImportError:
    AnthropicAdapter = None

try:
    from .langchain import LangChainAdapter
except ImportError:
    LangChainAdapter = None

try:
    from .llamaindex import LlamaIndexAdapter
except ImportError:
    LlamaIndexAdapter = None

try:
    from .huggingface import HuggingFaceAdapter
except ImportError:
    HuggingFaceAdapter = None

from .vectorstores import (
    BaseVectorStoreAdapter,
    PineconeAdapter,
    WeaviateAdapter,
    ChromaAdapter,
)

from .graphstores import (
    BaseGraphStoreAdapter,
    Neo4jAdapter,
    ArangoDBAdapter,
)

from .testing import (
    AdapterTester,
    TestScenario,
    TestResult,
    PerformanceBenchmark,
)

from .config import (
    AdapterManager,
    AdapterManagerConfig,
    load_adapter_configs,
    validate_adapter_config,
)

__all__ = [
    "BaseAdapter",
    "AdapterConfig",
    "AdapterHealth",
    "AdapterRegistry",
    "register_adapter",
    "get_adapter",
    "get_adapter_registry",
    "ExecutionContext",
    "ExecutionResult",
    # LLM Providers
    "OpenAIAdapter",
    "AnthropicAdapter",
    "LangChainAdapter",
    "LlamaIndexAdapter",
    "HuggingFaceAdapter",
    # Vector Stores
    "BaseVectorStoreAdapter",
    "PineconeAdapter",
    "WeaviateAdapter",
    "ChromaAdapter",
    # Graph Stores
    "BaseGraphStoreAdapter",
    "Neo4jAdapter",
    "ArangoDBAdapter",
    # Testing & Config
    "AdapterTester",
    "TestScenario",
    "TestResult",
    "PerformanceBenchmark",
    "AdapterManager",
    "AdapterManagerConfig",
    "load_adapter_configs",
    "validate_adapter_config",
]

