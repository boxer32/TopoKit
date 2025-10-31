"""Enhanced TopoOrchestrator for TopoKit with DAG execution, fallback systems, and confidence gating."""

import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from collections import defaultdict, deque

from ..types.topology import TopologyPack, Node, EdgePolicy, Contract
from ..types.context import ContextVersion
from .context_store import EnhancedContextStore, MergeStrategy, ConflictResolutionStrategy
from .guardrails import MultiStageGuardrails, GuardrailResult, PolicyEnvironment
from .schema_validator import SchemaValidator


class ExecutionState(str, Enum):
    """Execution states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class FallbackStrategy(str, Enum):
    """Fallback strategies."""
    RETRY = "retry"
    FALLBACK_NODE = "fallback_node"
    CACHED_RESPONSE = "cached_response"
    DEFAULT_RESPONSE = "default_response"
    HUMAN_INTERVENTION = "human_intervention"


@dataclass
class ExecutionTrace:
    """Execution trace for debugging and monitoring."""
    trace_id: str
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    nodes_executed: List[str] = field(default_factory=list)
    edges_traversed: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    context_versions: List[ContextVersion] = field(default_factory=list)


@dataclass
class NodeExecution:
    """Node execution details."""
    node_id: str
    state: ExecutionState
    start_time: datetime
    end_time: Optional[datetime] = None
    input_data: Any = None
    output_data: Any = None
    error: Optional[str] = None
    retry_count: int = 0
    fallback_strategy: Optional[FallbackStrategy] = None
    confidence_score: float = 1.0
    guardrail_results: List[GuardrailResult] = field(default_factory=list)


class EnhancedTopoOrchestrator:
    """Enhanced orchestrator for topology execution with DAG execution, fallback systems, and confidence gating."""
    
    def __init__(self, pack: TopologyPack, 
                 context_store: Optional[EnhancedContextStore] = None,
                 guardrails: Optional[MultiStageGuardrails] = None,
                 schema_validator: Optional[SchemaValidator] = None):
        """Initialize enhanced orchestrator.
        
        Args:
            pack: Topology pack to orchestrate
            context_store: Context store for state management
            guardrails: Guardrails system for safety
            schema_validator: Schema validator for contracts
        """
        self.pack = pack
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.context_store = context_store or EnhancedContextStore(
            merge_strategy=MergeStrategy.FIELD_LEVEL_CRDT,
            conflict_resolution=ConflictResolutionStrategy.AUTOMATIC
        )
        self.guardrails = guardrails or MultiStageGuardrails(
            pack.guardrails, 
            PolicyEnvironment.DEVELOPMENT
        )
        self.schema_validator = schema_validator or SchemaValidator()
        
        # Build execution graph
        self._build_execution_graph()
        
        # Execution state
        self._active_executions: Dict[str, ExecutionTrace] = {}
        self._node_executions: Dict[str, Dict[str, NodeExecution]] = defaultdict(dict)
        self._execution_lock = asyncio.Lock()
        
        # Performance tracking
        self._performance_metrics = defaultdict(list)
    
    def _build_execution_graph(self):
        """Build execution graph from topology pack."""
        # Build adjacency list for DAG traversal
        self._graph: Dict[str, List[str]] = defaultdict(list)
        self._reverse_graph: Dict[str, List[str]] = defaultdict(list)
        self._node_map: Dict[str, Node] = {}
        self._edge_map: Dict[str, EdgePolicy] = {}
        
        # Map nodes
        for node in self.pack.nodes:
            self._node_map[node.id] = node
            self._graph[node.id] = []
            self._reverse_graph[node.id] = []
        
        # Map edges and build graph
        for edge in self.pack.edges:
            self._edge_map[edge.id] = edge
            self._graph[edge.from_node].append(edge.to_node)
            self._reverse_graph[edge.to_node].append(edge.from_node)
        
        # Find entry points (nodes with no incoming edges)
        self._entry_points = [
            node_id for node_id in self._node_map.keys()
            if not self._reverse_graph[node_id]
        ]
        
        # Find exit points (nodes with no outgoing edges)
        self._exit_points = [
            node_id for node_id in self._node_map.keys()
            if not self._graph[node_id]
        ]
        
        # Validate DAG structure (no cycles)
        self._validate_dag_structure()
    
    def _validate_dag_structure(self):
        """Validate that the topology forms a valid DAG."""
        # Detect cycles using DFS
        visited = set()
        rec_stack = set()
        
        def has_cycle(node_id: str) -> bool:
            """Check if there's a cycle starting from this node."""
            visited.add(node_id)
            rec_stack.add(node_id)
            
            for neighbor in self._graph[node_id]:
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node_id)
            return False
        
        # Check all nodes for cycles
        for node in self.pack.nodes:
            if node.id not in visited:
                if has_cycle(node.id):
                    raise ValueError(f"Cycle detected in topology involving node: {node.id}")
    
    def _topological_sort(self, start_node: str) -> List[str]:
        """Get topological ordering of nodes for execution using Kahn's algorithm."""
        # Calculate in-degrees
        in_degree = {node_id: len(self._reverse_graph[node_id]) for node_id in self._node_map.keys()}
        
        # Start with nodes that have no dependencies
        queue = deque([node_id for node_id, degree in in_degree.items() if degree == 0])
        result = []
        
        while queue:
            node_id = queue.popleft()
            result.append(node_id)
            
            # Reduce in-degree for neighbors
            for neighbor in self._graph[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # Check if all nodes were processed (no cycles)
        if len(result) != len(self.pack.nodes):
            raise ValueError("Topology contains cycles - cannot determine execution order")
        
        return result
    
    async def execute(self, session_id: str, input_data: Any, 
                     entry_node: Optional[str] = None,
                     timeout_seconds: int = 300) -> Dict[str, Any]:
        """Execute topology with DAG traversal.
        
        Args:
            session_id: Session identifier
            input_data: Input data for execution
            entry_node: Entry node (if None, uses first entry point)
            timeout_seconds: Execution timeout
            
        Returns:
            Execution result with output data and metadata
        """
        trace_id = str(uuid.uuid4())
        
        # Create execution trace
        trace = ExecutionTrace(
            trace_id=trace_id,
            session_id=session_id,
            start_time=datetime.now(timezone.utc)
        )
        
        async with self._execution_lock:
            self._active_executions[trace_id] = trace
        
        try:
            # Determine entry point
            if entry_node is None:
                if not self._entry_points:
                    raise ValueError("No entry points found in topology")
                entry_node = self._entry_points[0]
            
            if entry_node not in self._node_map:
                raise ValueError(f"Entry node {entry_node} not found in topology")
            
            # Initialize context
            await self.context_store.upsert(
                session_id=session_id,
                patch={"input": input_data, "execution_start": trace.start_time.isoformat()},
                node_id=entry_node,
                trace_id=trace_id
            )
            
            # Execute DAG
            result = await self._execute_dag(
                trace_id=trace_id,
                session_id=session_id,
                entry_node=entry_node,
                timeout_seconds=timeout_seconds
            )
            
            # Update trace
            trace.end_time = datetime.now(timezone.utc)
            trace.nodes_executed = list(self._node_executions[trace_id].keys())
            
            return {
                "success": True,
                "trace_id": trace_id,
                "result": result,
                "execution_time": (trace.end_time - trace.start_time).total_seconds(),
                "nodes_executed": trace.nodes_executed,
                "performance_metrics": trace.performance_metrics
            }
            
        except Exception as e:
            trace.end_time = datetime.now(timezone.utc)
            trace.errors.append(str(e))
            self.logger.error(f"Execution failed for trace {trace_id}: {e}")
            
            return {
                "success": False,
                "trace_id": trace_id,
                "error": str(e),
                "execution_time": (trace.end_time - trace.start_time).total_seconds(),
                "nodes_executed": trace.nodes_executed
            }
        
        finally:
            # Cleanup
            async with self._execution_lock:
                if trace_id in self._active_executions:
                    del self._active_executions[trace_id]
    
    async def _execute_dag(self, trace_id: str, session_id: str, 
                          entry_node: str, timeout_seconds: int) -> Any:
        """Execute DAG starting from entry node."""
        # Topological sort for execution order
        execution_order = self._topological_sort(entry_node)
        
        # Track completed nodes
        completed_nodes: Set[str] = set()
        node_results: Dict[str, Any] = {}
        
        # Execute nodes in topological order
        for node_id in execution_order:
            if node_id in completed_nodes:
                continue
            
            # Check if all dependencies are satisfied
            dependencies = self._reverse_graph[node_id]
            if not all(dep in completed_nodes for dep in dependencies):
                # Skip for now, will be processed in next iteration
                continue
            
            # Execute node
            try:
                result = await self._execute_node(
                    trace_id=trace_id,
                    session_id=session_id,
                    node_id=node_id,
                    input_data=node_results.get(node_id, {}),
                    dependencies=node_results
                )
                
                node_results[node_id] = result
                completed_nodes.add(node_id)
                
            except Exception as e:
                self.logger.error(f"Node {node_id} execution failed: {e}")
                
                # Apply fallback strategy
                fallback_result = await self._apply_fallback(
                    trace_id=trace_id,
                    session_id=session_id,
                    node_id=node_id,
                    error=e,
                    dependencies=node_results
                )
                
                if fallback_result is not None:
                    node_results[node_id] = fallback_result
                    completed_nodes.add(node_id)
                else:
                    raise e
        
        # Return result from exit nodes
        if self._exit_points:
            exit_results = {node_id: node_results[node_id] for node_id in self._exit_points if node_id in node_results}
            return exit_results
        
        return node_results
    
    async def _execute_node(self, trace_id: str, session_id: str, 
                           node_id: str, input_data: Any, 
                           dependencies: Dict[str, Any]) -> Any:
        """Execute a single node with guardrails and validation."""
        node = self._node_map[node_id]
        
        # Create node execution record
        node_execution = NodeExecution(
            node_id=node_id,
            state=ExecutionState.RUNNING,
            start_time=datetime.now(timezone.utc),
            input_data=input_data
        )
        
        self._node_executions[trace_id][node_id] = node_execution
        
        try:
            # Apply pre-processing guardrails
            pre_result = await self.guardrails.apply_pre_processing(
                data=input_data,
                node=node,
                trace_id=trace_id
            )
            node_execution.guardrail_results.append(pre_result)
            
            if not pre_result.passed:
                raise ValueError(f"Pre-processing guardrails failed: {pre_result.message}")
            
            # Execute node with proper error handling
            output_data = await self._call_node(node, input_data, dependencies)
            
            # Apply post-processing guardrails
            post_result = await self.guardrails.apply_post_processing(
                data=output_data,
                node=node,
                trace_id=trace_id
            )
            node_execution.guardrail_results.append(post_result)
            
            if not post_result.passed:
                raise ValueError(f"Post-processing guardrails failed: {post_result.message}")
            
            # Update context
            await self.context_store.upsert(
                session_id=session_id,
                patch={f"node_{node_id}_output": output_data},
                node_id=node_id,
                trace_id=trace_id
            )
            
            # Record success
            await self.guardrails.record_success(node_id)
            
            # Update execution record
            node_execution.state = ExecutionState.COMPLETED
            node_execution.end_time = datetime.now(timezone.utc)
            node_execution.output_data = output_data
            node_execution.confidence_score = post_result.confidence
            
            return output_data
            
        except Exception as e:
            # Record failure
            await self.guardrails.record_failure(node_id)
            
            # Update execution record
            node_execution.state = ExecutionState.FAILED
            node_execution.end_time = datetime.now(timezone.utc)
            node_execution.error = str(e)
            
            raise e
    
    async def _call_node(self, node: Node, input_data: Any, dependencies: Dict[str, Any]) -> Any:
        """Call actual node implementation (placeholder)."""
        # This is where actual node implementations would be called
        # For now, return a placeholder response
        
        if node.kind == "ai":
            return {
                "response": f"AI response for {node.id}",
                "confidence": 0.9,
                "metadata": {"node_id": node.id, "kind": node.kind}
            }
        elif node.kind == "data":
            return {
                "processed_data": input_data,
                "metadata": {"node_id": node.id, "kind": node.kind}
            }
        else:
            return {
                "result": f"Processed by {node.id}",
                "metadata": {"node_id": node.id, "kind": node.kind}
            }
    
    async def _apply_fallback(self, trace_id: str, session_id: str, 
                             node_id: str, error: Exception, 
                             dependencies: Dict[str, Any]) -> Optional[Any]:
        """Apply fallback strategy for failed node."""
        node = self._node_map[node_id]
        node_execution = self._node_executions[trace_id][node_id]
        
        # Check circuit breaker configuration
        if hasattr(node, 'circuit_breaker') and node.circuit_breaker.fallback_node:
            fallback_node_id = node.circuit_breaker.fallback_node
            
            if fallback_node_id in self._node_map:
                self.logger.info(f"Applying fallback to node {fallback_node_id} for failed node {node_id}")
                
                try:
                    fallback_result = await self._execute_node(
                        trace_id=trace_id,
                        session_id=session_id,
                        node_id=fallback_node_id,
                        input_data=node_execution.input_data,
                        dependencies=dependencies
                    )
                    
                    node_execution.fallback_strategy = FallbackStrategy.FALLBACK_NODE
                    return fallback_result
                    
                except Exception as fallback_error:
                    self.logger.error(f"Fallback node {fallback_node_id} also failed: {fallback_error}")
        
        # Try retry strategy
        if node_execution.retry_count < 3:  # Max 3 retries
            node_execution.retry_count += 1
            self.logger.info(f"Retrying node {node_id}, attempt {node_execution.retry_count}")
            
            try:
                # Wait before retry
                await asyncio.sleep(2 ** node_execution.retry_count)  # Exponential backoff
                
                retry_result = await self._execute_node(
                    trace_id=trace_id,
                    session_id=session_id,
                    node_id=node_id,
                    input_data=node_execution.input_data,
                    dependencies=dependencies
                )
                
                node_execution.fallback_strategy = FallbackStrategy.RETRY
                return retry_result
                
            except Exception as retry_error:
                self.logger.error(f"Retry {node_execution.retry_count} failed for node {node_id}: {retry_error}")
        
        # Return default response if configured
        if hasattr(node, 'default_response'):
            node_execution.fallback_strategy = FallbackStrategy.DEFAULT_RESPONSE
            return node.default_response
        
        return None
    
    def get_execution_status(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Get execution status for a trace."""
        if trace_id not in self._active_executions:
            return None
        
        trace = self._active_executions[trace_id]
        node_executions = self._node_executions.get(trace_id, {})
        
        return {
            "trace_id": trace_id,
            "session_id": trace.session_id,
            "state": "running" if trace.end_time is None else "completed",
            "start_time": trace.start_time.isoformat(),
            "end_time": trace.end_time.isoformat() if trace.end_time else None,
            "nodes_executed": list(node_executions.keys()),
            "errors": trace.errors,
            "warnings": trace.warnings,
            "performance_metrics": trace.performance_metrics
        }
    
    def get_node_status(self, trace_id: str, node_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific node execution."""
        if trace_id not in self._node_executions:
            return None
        
        node_executions = self._node_executions[trace_id]
        if node_id not in node_executions:
            return None
        
        execution = node_executions[node_id]
        return {
            "node_id": node_id,
            "state": execution.state.value,
            "start_time": execution.start_time.isoformat(),
            "end_time": execution.end_time.isoformat() if execution.end_time else None,
            "retry_count": execution.retry_count,
            "confidence_score": execution.confidence_score,
            "fallback_strategy": execution.fallback_strategy.value if execution.fallback_strategy else None,
            "error": execution.error,
            "guardrail_results": [result.dict() for result in execution.guardrail_results]
        }
    
    async def cancel_execution(self, trace_id: str) -> bool:
        """Cancel a running execution."""
        if trace_id not in self._active_executions:
            return False
        
        trace = self._active_executions[trace_id]
        trace.end_time = datetime.now(timezone.utc)
        trace.errors.append("Execution cancelled by user")
        
        # Cancel all running node executions
        for node_execution in self._node_executions[trace_id].values():
            if node_execution.state == ExecutionState.RUNNING:
                node_execution.state = ExecutionState.CANCELLED
                node_execution.end_time = datetime.now(timezone.utc)
        
        return True
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the orchestrator."""
        return {
            "active_executions": len(self._active_executions),
            "total_node_executions": sum(len(executions) for executions in self._node_executions.values()),
            "circuit_breaker_stats": self.guardrails.get_stats(),
            "context_store_stats": self.context_store.get_stats(),
            "topology_stats": {
                "total_nodes": len(self.pack.nodes),
                "total_edges": len(self.pack.edges),
                "entry_points": len(self._entry_points),
                "exit_points": len(self._exit_points)
            }
        }


# Backward compatibility
TopoOrchestrator = EnhancedTopoOrchestrator
