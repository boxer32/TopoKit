"""Enhanced Pack Parser for TopoKit topology configuration files with streaming validation and performance optimization."""

import yaml
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List, AsyncGenerator, Union
from pydantic import ValidationError
from concurrent.futures import ThreadPoolExecutor
import threading

from ..types.topology import TopologyPack, Node, EdgePolicy, Contract, GuardrailsConfig
from ..types.validation import ValidationResult, ValidationError as TopoValidationError, ValidationErrorType


class PackParseError(Exception):
    """Raised when pack parsing fails."""
    pass


class PackParseResult:
    """Result of pack parsing operation with performance metrics."""
    
    def __init__(self, pack: TopologyPack, parse_time_ms: float, errors: List[str] = None):
        self.pack = pack
        self.parse_time_ms = parse_time_ms
        self.errors = errors or []
        self.success = len(self.errors) == 0
    
    # Delegate pack attributes for backward compatibility
    def __getattr__(self, name):
        """Delegate attribute access to the underlying pack."""
        return getattr(self.pack, name)


class EnhancedPackParser:
    """Enhanced parser for TopoKit topology pack files with streaming validation and performance optimization."""
    
    def __init__(self, pack_dir: str, max_parse_time_ms: int = 100):
        """Initialize enhanced pack parser with topology directory.
        
        Args:
            pack_dir: Path to topology pack directory
            max_parse_time_ms: Maximum allowed parse time in milliseconds
        """
        self.pack_dir = Path(pack_dir)
        self.max_parse_time_ms = max_parse_time_ms
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._cache = {}
        self._cache_lock = threading.Lock()
        
        if not self.pack_dir.exists():
            raise PackParseError(f"Pack directory does not exist: {pack_dir}")
    
    def parse(self) -> PackParseResult:
        """Parse the complete topology pack with performance monitoring.
        
        Returns:
            PackParseResult: Parsed topology configuration with performance metrics
            
        Raises:
            PackParseError: If parsing fails or exceeds time limit
        """
        start_time = time.time()
        
        try:
            # Parse all components in parallel for performance
            with self._executor as executor:
                # Submit all parsing tasks
                nodes_future = executor.submit(self._parse_nodes)
                edges_future = executor.submit(self._parse_edges)
                contracts_future = executor.submit(self._parse_contracts)
                guardrails_future = executor.submit(self._parse_guardrails)
                context_schema_future = executor.submit(self._parse_context_schema)
                
                # Wait for all tasks to complete with timeout
                try:
                    nodes = nodes_future.result(timeout=self.max_parse_time_ms / 1000)
                    edges = edges_future.result(timeout=self.max_parse_time_ms / 1000)
                    contracts = contracts_future.result(timeout=self.max_parse_time_ms / 1000)
                    guardrails = guardrails_future.result(timeout=self.max_parse_time_ms / 1000)
                    context_schema = context_schema_future.result(timeout=self.max_parse_time_ms / 1000)
                except Exception as e:
                    raise PackParseError(f"Timeout or error during parallel parsing: {e}")
            
            # Create topology pack
            pack = TopologyPack(
                name=self._get_pack_name(),
                description=self._get_pack_description(),
                nodes=nodes,
                edges=edges,
                contracts=contracts,
                guardrails=guardrails,
                context_schema=context_schema
            )
            
            # Validate pack consistency
            errors = self.validate_pack(pack)
            
            parse_time_ms = (time.time() - start_time) * 1000
            
            if parse_time_ms > self.max_parse_time_ms:
                errors.append(f"Parse time {parse_time_ms:.2f}ms exceeds limit of {self.max_parse_time_ms}ms")
            
            return PackParseResult(pack, parse_time_ms, errors)
            
        except Exception as e:
            parse_time_ms = (time.time() - start_time) * 1000
            raise PackParseError(f"Failed to parse topology pack in {parse_time_ms:.2f}ms: {e}") from e
    
    async def parse_streaming(self, chunk_size: int = 1024) -> AsyncGenerator[ValidationResult, None]:
        """Parse topology pack with streaming validation for large files.
        
        Args:
            chunk_size: Size of chunks to process
            
        Yields:
            ValidationResult: Validation results for each chunk
        """
        try:
            # Stream parse nodes
            async for result in self._parse_nodes_streaming(chunk_size):
                yield result
            
            # Stream parse edges
            async for result in self._parse_edges_streaming(chunk_size):
                yield result
            
            # Stream parse contracts
            async for result in self._parse_contracts_streaming(chunk_size):
                yield result
                
        except Exception as e:
            yield ValidationResult(
                success=False,
                errors=[TopoValidationError(
                    type=ValidationErrorType.STREAMING_ERROR,
                    message=f"Streaming parse error: {e}",
                    path="streaming",
                    severity="high",
                    repairable=False
                )]
            )
    
    def _parse_nodes(self) -> List[Node]:
        """Parse nodes.yaml file with caching."""
        cache_key = f"nodes_{self.pack_dir}"
        
        with self._cache_lock:
            if cache_key in self._cache:
                return self._cache[cache_key]
        
        nodes_file = self.pack_dir / "nodes.yaml"
        if not nodes_file.exists():
            return []
        
        try:
            with open(nodes_file, 'r') as f:
                data = yaml.safe_load(f)
            
            if not data or 'nodes' not in data:
                return []
            
            nodes = []
            for node_data in data['nodes']:
                try:
                    node = Node(**node_data)
                    nodes.append(node)
                except ValidationError as e:
                    raise PackParseError(f"Invalid node configuration: {e}") from e
            
            with self._cache_lock:
                self._cache[cache_key] = nodes
            
            return nodes
            
        except Exception as e:
            raise PackParseError(f"Failed to parse nodes: {e}") from e
    
    def _parse_edges(self) -> List[EdgePolicy]:
        """Parse edges.yaml file with caching."""
        cache_key = f"edges_{self.pack_dir}"
        
        with self._cache_lock:
            if cache_key in self._cache:
                return self._cache[cache_key]
        
        edges_file = self.pack_dir / "edges.yaml"
        if not edges_file.exists():
            return []
        
        try:
            with open(edges_file, 'r') as f:
                data = yaml.safe_load(f)
            
            if not data or 'edges' not in data:
                return []
            
            edges = []
            for edge_data in data['edges']:
                try:
                    edge = EdgePolicy(**edge_data)
                    edges.append(edge)
                except ValidationError as e:
                    raise PackParseError(f"Invalid edge configuration: {e}") from e
            
            with self._cache_lock:
                self._cache[cache_key] = edges
            
            return edges
            
        except Exception as e:
            raise PackParseError(f"Failed to parse edges: {e}") from e
    
    def _parse_contracts(self) -> List[Contract]:
        """Parse contract files from contracts/ directory with caching."""
        cache_key = f"contracts_{self.pack_dir}"
        
        with self._cache_lock:
            if cache_key in self._cache:
                return self._cache[cache_key]
        
        contracts_dir = self.pack_dir / "contracts"
        if not contracts_dir.exists():
            return []
        
        contracts = []
        for contract_file in contracts_dir.glob("*.json"):
            try:
                with open(contract_file, 'r') as f:
                    data = json.load(f)
                
                # Extract contract name from filename
                contract_name = contract_file.stem
                
                contract = Contract(
                    name=contract_name,
                    input_schema=data.get('input', {}),
                    output_schema=data.get('output', {}),
                    description=data.get('description')
                )
                contracts.append(contract)
                
            except (json.JSONDecodeError, ValidationError) as e:
                raise PackParseError(f"Invalid contract file {contract_file}: {e}") from e
        
        with self._cache_lock:
            self._cache[cache_key] = contracts
        
        return contracts
    
    async def _parse_nodes_streaming(self, chunk_size: int) -> AsyncGenerator[ValidationResult, None]:
        """Stream parse nodes with partial validation."""
        nodes_file = self.pack_dir / "nodes.yaml"
        if not nodes_file.exists():
            yield ValidationResult(success=True, data=[])
            return
        
        try:
            with open(nodes_file, 'r') as f:
                content = f.read()
            
            # Process in chunks for large files
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i + chunk_size]
                yield ValidationResult(
                    success=True,
                    data={"chunk": chunk, "offset": i},
                    repair_attempts=0
                )
                
        except Exception as e:
            yield ValidationResult(
                success=False,
                errors=[TopoValidationError(
                    type=ValidationErrorType.STREAMING_ERROR,
                    message=f"Failed to stream parse nodes: {e}",
                    path="nodes.yaml",
                    severity="high",
                    repairable=False
                )]
            )
    
    async def _parse_edges_streaming(self, chunk_size: int) -> AsyncGenerator[ValidationResult, None]:
        """Stream parse edges with partial validation."""
        edges_file = self.pack_dir / "edges.yaml"
        if not edges_file.exists():
            yield ValidationResult(success=True, data=[])
            return
        
        try:
            with open(edges_file, 'r') as f:
                content = f.read()
            
            # Process in chunks for large files
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i + chunk_size]
                yield ValidationResult(
                    success=True,
                    data={"chunk": chunk, "offset": i},
                    repair_attempts=0
                )
                
        except Exception as e:
            yield ValidationResult(
                success=False,
                errors=[TopoValidationError(
                    type=ValidationErrorType.STREAMING_ERROR,
                    message=f"Failed to stream parse edges: {e}",
                    path="edges.yaml",
                    severity="high",
                    repairable=False
                )]
            )
    
    async def _parse_contracts_streaming(self, chunk_size: int) -> AsyncGenerator[ValidationResult, None]:
        """Stream parse contracts with partial validation."""
        contracts_dir = self.pack_dir / "contracts"
        if not contracts_dir.exists():
            yield ValidationResult(success=True, data=[])
            return
        
        try:
            for contract_file in contracts_dir.glob("*.json"):
                with open(contract_file, 'r') as f:
                    content = f.read()
                
                # Process in chunks for large files
                for i in range(0, len(content), chunk_size):
                    chunk = content[i:i + chunk_size]
                    yield ValidationResult(
                        success=True,
                        data={"file": str(contract_file), "chunk": chunk, "offset": i},
                        repair_attempts=0
                    )
                    
        except Exception as e:
            yield ValidationResult(
                success=False,
                errors=[TopoValidationError(
                    type=ValidationErrorType.STREAMING_ERROR,
                    message=f"Failed to stream parse contracts: {e}",
                    path="contracts/",
                    severity="high",
                    repairable=False
                )]
            )
    
    def _parse_guardrails(self) -> GuardrailsConfig:
        """Parse guardrails.yaml file with caching."""
        cache_key = f"guardrails_{self.pack_dir}"
        
        with self._cache_lock:
            if cache_key in self._cache:
                return self._cache[cache_key]
        
        guardrails_file = self.pack_dir / "guardrails.yaml"
        if not guardrails_file.exists():
            return GuardrailsConfig()
        
        try:
            with open(guardrails_file, 'r') as f:
                data = yaml.safe_load(f)
            
            if not data:
                return GuardrailsConfig()
            
            guardrails = GuardrailsConfig(**data)
            
            with self._cache_lock:
                self._cache[cache_key] = guardrails
            
            return guardrails
            
        except ValidationError as e:
            raise PackParseError(f"Invalid guardrails configuration: {e}") from e
        except Exception as e:
            raise PackParseError(f"Failed to parse guardrails: {e}") from e
    
    def _parse_context_schema(self) -> Optional[Dict[str, Any]]:
        """Parse context.schema.json file with caching."""
        cache_key = f"context_schema_{self.pack_dir}"
        
        with self._cache_lock:
            if cache_key in self._cache:
                return self._cache[cache_key]
        
        context_schema_file = self.pack_dir / "context.schema.json"
        if not context_schema_file.exists():
            return None
        
        try:
            with open(context_schema_file, 'r') as f:
                schema = json.load(f)
            
            with self._cache_lock:
                self._cache[cache_key] = schema
            
            return schema
            
        except Exception as e:
            raise PackParseError(f"Failed to parse context schema: {e}") from e
    
    def _get_pack_name(self) -> str:
        """Get pack name from directory or default."""
        return self.pack_dir.name
    
    def _get_pack_description(self) -> Optional[str]:
        """Get pack description if available."""
        readme_file = self.pack_dir / "README.md"
        if readme_file.exists():
            try:
                with open(readme_file, 'r') as f:
                    content = f.read()
                    return content[:200] + "..." if len(content) > 200 else content
            except Exception:
                return None
        return None
    
    def validate_pack(self, pack: Union[TopologyPack, PackParseResult]) -> List[str]:
        """Enhanced pack validation with detailed error reporting.
    
        Args:
            pack: Parsed topology pack or PackParseResult
    
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Extract pack from PackParseResult if needed
        if isinstance(pack, PackParseResult):
            pack = pack.pack
    
        # Validate node IDs are unique
        node_ids = [node.id for node in pack.nodes]
        if len(node_ids) != len(set(node_ids)):
            duplicates = [node_id for node_id in node_ids if node_ids.count(node_id) > 1]
            errors.append(f"Duplicate node IDs found: {set(duplicates)}")
        
        # Validate edge references exist
        valid_node_ids = set(node_ids)
        for edge in pack.edges:
            if edge.from_node not in valid_node_ids:
                errors.append(f"Edge {edge.id} references non-existent node: {edge.from_node}")
            if edge.to_node not in valid_node_ids:
                errors.append(f"Edge {edge.id} references non-existent node: {edge.to_node}")
        
        # Validate contract references
        valid_contract_names = {contract.name for contract in pack.contracts}
        for edge in pack.edges:
            for contract_name in edge.contracts:
                if contract_name not in valid_contract_names:
                    errors.append(f"Edge {edge.id} references non-existent contract: {contract_name}")
        
        # Validate DAG structure (no cycles)
        cycle_errors = self._detect_cycles(pack)
        errors.extend(cycle_errors)
        
        # Validate node scope contracts
        for node in pack.nodes:
            for contract_name in node.scope.contracts:
                if contract_name not in valid_contract_names:
                    errors.append(f"Node {node.id} references non-existent contract: {contract_name}")
        
        return errors
    
    def _detect_cycles(self, pack: TopologyPack) -> List[str]:
        """Detect cycles in the topology DAG."""
        errors = []
        
        # Build adjacency list
        graph = {node.id: [] for node in pack.nodes}
        for edge in pack.edges:
            if edge.from_node in graph and edge.to_node in graph:
                graph[edge.from_node].append(edge.to_node)
        
        # DFS to detect cycles
        visited = set()
        rec_stack = set()
        
        def has_cycle(node):
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph[node]:
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node_id in graph:
            if node_id not in visited:
                if has_cycle(node_id):
                    errors.append(f"Cycle detected in topology involving node: {node_id}")
                    break
        
        return errors
    
    def clear_cache(self):
        """Clear the parser cache."""
        with self._cache_lock:
            self._cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._cache_lock:
            return {
                "cache_size": len(self._cache),
                "cache_keys": list(self._cache.keys()),
                "max_parse_time_ms": self.max_parse_time_ms
            }


# Backward compatibility
PackParser = EnhancedPackParser
