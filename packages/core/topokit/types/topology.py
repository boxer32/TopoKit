"""Topology type definitions for TopoKit."""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from enum import Enum


class ContextScope(BaseModel):
    """Context scope definition for nodes."""
    contracts: List[str] = Field(default_factory=list, description="Required contracts")
    permissions: List[str] = Field(default_factory=list, description="Required permissions")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class NodeKind(str, Enum):
    """Types of nodes in the topology."""
    UX = "ux"
    AI = "ai" 
    DATA = "data"
    OPS = "ops"


class NodeScope(BaseModel):
    """Node scope configuration."""
    contracts: List[str] = Field(default_factory=list)
    context_required: bool = False
    retrieval_scope: Optional[List[str]] = None


class ExecutionProfile(BaseModel):
    """Node execution profile for deterministic behavior."""
    temperature: float = Field(ge=0.0, le=2.0, default=0.2)
    top_p: float = Field(ge=0.0, le=1.0, default=0.9)
    seed: Optional[Union[str, int]] = "stable"
    max_tokens: int = Field(gt=0, default=1000)
    deterministic_reranker: bool = True


class SLOs(BaseModel):
    """Service Level Objectives for a node."""
    schema_pass_rate: str = "≥ 99%"
    drift_threshold: str = "≤ 10%"
    latency_budget: str = "≤ 1000ms"
    context_precision: str = "≥ 0.9"
    consistency_rate: str = "≥ 95%"
    cost_budget: str = "≤ 100 tokens/run"


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration."""
    failure_threshold: int = Field(gt=0, default=3)
    timeout_ms: int = Field(gt=0, default=2000)
    fallback_node: Optional[str] = None


class CachingConfig(BaseModel):
    """Caching configuration."""
    enabled: bool = True
    ttl_seconds: int = Field(gt=0, default=3600)
    key_template: str = "prompt_hash+ctx_hash+model+profile"


class ProvenanceConfig(BaseModel):
    """Provenance tracking configuration."""
    track_prompt_hash: bool = True
    track_model_params: bool = True
    track_retrieval_sources: bool = True


class Node(BaseModel):
    """A node in the topology representing a capability boundary."""
    id: str = Field(..., description="Unique node identifier")
    kind: NodeKind
    version: str = Field(default="1.0.0")
    scope: NodeScope = Field(default_factory=NodeScope)
    execution_profile: ExecutionProfile = Field(default_factory=ExecutionProfile)
    slos: SLOs = Field(default_factory=SLOs)
    circuit_breaker: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)
    caching: CachingConfig = Field(default_factory=CachingConfig)
    provenance: ProvenanceConfig = Field(default_factory=ProvenanceConfig)


class EdgePolicy(BaseModel):
    """Edge policy defining communication between nodes."""
    id: str = Field(..., description="Unique edge identifier")
    from_node: str = Field(..., alias="from")
    to_node: str = Field(..., alias="to")
    version: str = Field(default="1.0.0")
    contracts: List[str] = Field(default_factory=list)
    allow: bool = True
    timeout_ms: int = Field(gt=0, default=4000)
    max_retries: int = Field(ge=0, default=0)
    circuit_breaker: Optional[CircuitBreakerConfig] = None


class Contract(BaseModel):
    """JSON Schema contract for data exchange."""
    name: str
    version: str = Field(default="1.0.0")
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    description: Optional[str] = None


class GuardrailsConfig(BaseModel):
    """Guardrails configuration for safety and determinism."""
    determinism: Dict[str, Any] = Field(default_factory=dict)
    confidence: Dict[str, Any] = Field(default_factory=dict)
    fallback: Dict[str, Any] = Field(default_factory=dict)
    ranking: Dict[str, Any] = Field(default_factory=dict)
    context_alignment: Dict[str, Any] = Field(default_factory=dict)
    human_gates: Dict[str, Any] = Field(default_factory=dict)
    circuit_breakers: Dict[str, Any] = Field(default_factory=dict)
    policy_engine: Dict[str, Any] = Field(default_factory=dict)
    observability: Dict[str, Any] = Field(default_factory=dict)


class TopologyPack(BaseModel):
    """Complete topology pack containing all configuration."""
    version: str = Field(default="1.0.0")
    name: str
    description: Optional[str] = None
    nodes: List[Node] = Field(default_factory=list)
    edges: List[EdgePolicy] = Field(default_factory=list)
    contracts: List[Contract] = Field(default_factory=list)
    guardrails: GuardrailsConfig = Field(default_factory=GuardrailsConfig)
    context_schema: Optional[Dict[str, Any]] = None


# Type aliases for backward compatibility and task requirements
Topology = TopologyPack  # Runtime topology model (alias for TopologyPack)
Edge = EdgePolicy  # Edge model (alias for EdgePolicy)
