"""
TopoKit - Enterprise-grade topology-first contract system for LLM applications.

TopoKit transforms conceptual system networks (nodes, edges, contracts, guardrails) 
into enforceable runtime rules, code APIs, and CI evals—ensuring LLMs operate 
"on rails" instead of free-form guessing.
"""

__version__ = "0.1.0"
__author__ = "TopoKit Foundation"
__email__ = "hello@topokit.dev"

from .core.orchestrator import TopoOrchestrator
from .core.pack_parser import PackParser
from .core.schema_validator import SchemaValidator
from .core.guardrails import Guardrails
from .core.context_store import ContextStore
from .types.topology import TopologyPack, Node, EdgePolicy, Contract

__all__ = [
    "TopoOrchestrator",
    "PackParser", 
    "SchemaValidator",
    "Guardrails",
    "ContextStore",
    "TopologyPack",
    "Node",
    "EdgePolicy", 
    "Contract",
]
