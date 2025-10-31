"""TopoKit API for CLI integration and execution."""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import yaml

from .orchestrator import EnhancedTopoOrchestrator
from .pack_parser import EnhancedPackParser
from .schema_validator import SchemaValidator
from .context_store import EnhancedContextStore, MergeStrategy, ConflictResolutionStrategy
from .guardrails import MultiStageGuardrails, PolicyEnvironment
from ..types.topology import TopologyPack
from ..types.validation import ValidationResult

logger = logging.getLogger(__name__)


class TopoKitAPI:
    """TopoKit API for CLI integration and execution."""
    
    def __init__(self):
        """Initialize TopoKit API."""
        self.pack_parser = EnhancedPackParser()
        self.schema_validator = SchemaValidator()
        self.context_store = EnhancedContextStore(
            merge_strategy=MergeStrategy.FIELD_LEVEL_CRDT,
            conflict_resolution=ConflictResolutionStrategy.AUTOMATIC
        )
        self.guardrails = None  # Will be initialized with pack
        self.orchestrator = None  # Will be initialized with pack
    
    def load_topology_pack(self, pack_dir: str) -> TopologyPack:
        """Load topology pack from directory.
        
        Args:
            pack_dir: Path to topology pack directory
            
        Returns:
            Loaded topology pack
            
        Raises:
            ValueError: If pack directory is invalid or missing required files
        """
        pack_path = Path(pack_dir)
        
        if not pack_path.exists():
            raise ValueError(f"Topology pack directory does not exist: {pack_dir}")
        
        if not pack_path.is_dir():
            raise ValueError(f"Path is not a directory: {pack_dir}")
        
        # Load required files
        nodes_file = pack_path / "nodes.yaml"
        edges_file = pack_path / "edges.yaml"
        guardrails_file = pack_path / "guardrails.yaml"
        
        if not nodes_file.exists():
            raise ValueError(f"Missing required file: {nodes_file}")
        if not edges_file.exists():
            raise ValueError(f"Missing required file: {edges_file}")
        if not guardrails_file.exists():
            raise ValueError(f"Missing required file: {guardrails_file}")
        
        # Parse files
        try:
            with open(nodes_file, 'r', encoding='utf-8') as f:
                nodes_data = yaml.safe_load(f)
            
            with open(edges_file, 'r', encoding='utf-8') as f:
                edges_data = yaml.safe_load(f)
            
            with open(guardrails_file, 'r', encoding='utf-8') as f:
                guardrails_data = yaml.safe_load(f)
            
            # Load contracts
            contracts = []
            contracts_dir = pack_path / "contracts"
            if contracts_dir.exists():
                for contract_file in contracts_dir.glob("*.yaml"):
                    with open(contract_file, 'r', encoding='utf-8') as f:
                        contract_data = yaml.safe_load(f)
                        contracts.append(contract_data)
            
            # Create topology pack
            pack = TopologyPack(
                name=pack_path.name,
                description=f"Topology pack loaded from {pack_dir}",
                nodes=nodes_data.get('nodes', []),
                edges=edges_data.get('edges', []),
                contracts=contracts,
                guardrails=guardrails_data
            )
            
            # Initialize guardrails and orchestrator
            self.guardrails = MultiStageGuardrails(
                pack.guardrails,
                PolicyEnvironment.DEVELOPMENT
            )
            self.orchestrator = EnhancedTopoOrchestrator(
                pack=pack,
                context_store=self.context_store,
                guardrails=self.guardrails,
                schema_validator=self.schema_validator
            )
            
            return pack
            
        except Exception as e:
            raise ValueError(f"Failed to load topology pack: {e}")
    
    def validate_topology(self, pack_dir: str) -> ValidationResult:
        """Validate topology pack.
        
        Args:
            pack_dir: Path to topology pack directory
            
        Returns:
            Validation result
        """
        try:
            # Load and validate pack
            pack = self.load_topology_pack(pack_dir)
            
            # Basic validation
            errors = []
            
            # Check for cycles
            if self.orchestrator:
                try:
                    self.orchestrator._validate_dag_structure()
                except ValueError as e:
                    errors.append({
                        "type": "semantic_error",
                        "message": str(e),
                        "path": "topology",
                        "severity": "high",
                        "repairable": False
                    })
            
            # Validate contracts
            for contract in pack.contracts:
                try:
                    # Validate input schema
                    if contract.input_schema:
                        self.schema_validator.validate_schema(contract.input_schema)
                    
                    # Validate output schema
                    if contract.output_schema:
                        self.schema_validator.validate_schema(contract.output_schema)
                        
                except Exception as e:
                    errors.append({
                        "type": "schema_error",
                        "message": f"Invalid contract {contract.name}: {e}",
                        "path": f"contracts/{contract.name}",
                        "severity": "high",
                        "repairable": False
                    })
            
            return ValidationResult(
                success=len(errors) == 0,
                data=pack,
                errors=errors
            )
            
        except Exception as e:
            return ValidationResult(
                success=False,
                errors=[{
                    "type": "unknown_error",
                    "message": str(e),
                    "path": "topology",
                    "severity": "critical",
                    "repairable": False
                }]
            )
    
    async def execute_topology(self, pack_dir: str, input_data: Any, 
                             session_id: str = "default") -> Dict[str, Any]:
        """Execute topology with input data.
        
        Args:
            pack_dir: Path to topology pack directory
            input_data: Input data for execution
            session_id: Session identifier
            
        Returns:
            Execution result
        """
        try:
            # Load topology pack
            pack = self.load_topology_pack(pack_dir)
            
            if not self.orchestrator:
                raise ValueError("Orchestrator not initialized")
            
            # Execute topology
            result = await self.orchestrator.execute(
                session_id=session_id,
                input_data=input_data
            )
            
            return result
                
            except Exception as e:
            logger.error(f"Topology execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "trace_id": None
            }
    
    def generate_graph(self, pack_dir: str, format: str = "mermaid") -> str:
        """Generate topology graph.
        
        Args:
            pack_dir: Path to topology pack directory
            format: Output format (mermaid, dot, json)
            
        Returns:
            Graph representation
        """
        try:
            pack = self.load_topology_pack(pack_dir)
            
            if format.lower() == "mermaid":
                return self._generate_mermaid_graph(pack)
            elif format.lower() == "dot":
                return self._generate_dot_graph(pack)
            elif format.lower() == "json":
                return self._generate_json_graph(pack)
            else:
                raise ValueError(f"Unsupported format: {format}")
                
            except Exception as e:
            logger.error(f"Graph generation failed: {e}")
            return f"Error generating graph: {e}"
    
    def _generate_mermaid_graph(self, pack: TopologyPack) -> str:
        """Generate Mermaid graph."""
        lines = ["graph TD"]
        
        # Add nodes
        for node in pack.nodes:
            node_id = node.id.replace(".", "_").replace("-", "_")
            node_type = self._get_node_type_icon(node.kind)
            lines.append(f'    {node_id}["{node_type} {node.id}"]')
        
        # Add edges
        for edge in pack.edges:
            from_id = edge.from_node.replace(".", "_").replace("-", "_")
            to_id = edge.to_node.replace(".", "_").replace("-", "_")
            
            if edge.contracts:
                contract_label = ", ".join(edge.contracts)
                lines.append(f'    {from_id} -->|"{contract_label}"| {to_id}')
            else:
                lines.append(f'    {from_id} --> {to_id}')
        
        return "\n".join(lines)
    
    def _generate_dot_graph(self, pack: TopologyPack) -> str:
        """Generate DOT graph."""
        lines = ["digraph Topology {"]
        lines.append("  rankdir=TB;")
        lines.append("  node [shape=box, style=filled];")
        lines.append("")
        
        # Add nodes
        for node in pack.nodes:
            node_id = node.id.replace(".", "_").replace("-", "_")
            color = self._get_node_type_color(node.kind)
            lines.append(f'  {node_id} [label="{node.id}\\n({node.kind})", fillcolor="{color}"];')
        
        lines.append("")
        
        # Add edges
        for edge in pack.edges:
            from_id = edge.from_node.replace(".", "_").replace("-", "_")
            to_id = edge.to_node.replace(".", "_").replace("-", "_")
            
            if edge.contracts:
                contract_label = ", ".join(edge.contracts)
                lines.append(f'  {from_id} -> {to_id} [label="{contract_label}"];')
            else:
                lines.append(f'  {from_id} -> {to_id};')
        
        lines.append("}")
        return "\n".join(lines)
    
    def _generate_json_graph(self, pack: TopologyPack) -> str:
        """Generate JSON graph."""
        graph = {
            "metadata": {
                "format": "topokit-graph",
                "version": "1.0.0",
                "generated_at": "2024-01-01T00:00:00Z"
            },
            "nodes": [
                {
                    "id": node.id,
                    "kind": node.kind,
                    "version": node.version,
                    "scope": node.scope.dict() if hasattr(node.scope, 'dict') else node.scope
                }
                for node in pack.nodes
            ],
            "edges": [
                {
                    "id": edge.id,
                    "from": edge.from_node,
                    "to": edge.to_node,
                    "contracts": edge.contracts,
                    "allow": edge.allow,
                    "timeout_ms": edge.timeout_ms,
                    "max_retries": edge.max_retries
                }
                for edge in pack.edges
            ]
        }
        
        return json.dumps(graph, indent=2)
    
    def _get_node_type_icon(self, kind: str) -> str:
        """Get icon for node type."""
        icons = {
            "ai": "🤖",
            "data": "📊",
            "ux": "👤",
            "ops": "⚙️"
        }
        return icons.get(kind.lower(), "⚙️")
    
    def _get_node_type_color(self, kind: str) -> str:
        """Get color for node type."""
        colors = {
            "ai": "#e3f2fd",
            "data": "#e8f5e8",
            "ux": "#fff3e0",
            "ops": "#f3e5f5"
        }
        return colors.get(kind.lower(), "#ffffff")


# CLI integration functions
def run_validation(pack_dir: str) -> Dict[str, Any]:
    """Run validation and return results for CLI."""
    api = TopoKitAPI()
    result = api.validate_topology(pack_dir)
    
    return {
        "success": result.success,
        "errors": result.errors,
        "data": result.data.dict() if result.data else None
    }


def run_execution(pack_dir: str, input_data: Any, session_id: str = "default") -> Dict[str, Any]:
    """Run execution and return results for CLI."""
    api = TopoKitAPI()
    
    # Run in event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(api.execute_topology(pack_dir, input_data, session_id))
        return result
    finally:
        loop.close()


def run_graph_generation(pack_dir: str, format: str = "mermaid") -> str:
    """Generate graph and return for CLI."""
    api = TopoKitAPI()
    return api.generate_graph(pack_dir, format)


if __name__ == "__main__":
    # CLI entry point
    import argparse
    
    parser = argparse.ArgumentParser(description="TopoKit API CLI")
    parser.add_argument("command", choices=["validate", "execute", "graph"])
    parser.add_argument("--pack-dir", required=True, help="Topology pack directory")
    parser.add_argument("--input", help="Input data for execution (JSON)")
    parser.add_argument("--session-id", default="default", help="Session ID")
    parser.add_argument("--format", default="mermaid", help="Graph format")
    
    args = parser.parse_args()
    
    if args.command == "validate":
        result = run_validation(args.pack_dir)
        print(json.dumps(result, indent=2))
        
    elif args.command == "execute":
        input_data = json.loads(args.input) if args.input else {}
        result = run_execution(args.pack_dir, input_data, args.session_id)
        print(json.dumps(result, indent=2))
        
    elif args.command == "graph":
        graph = run_graph_generation(args.pack_dir, args.format)
        print(graph)