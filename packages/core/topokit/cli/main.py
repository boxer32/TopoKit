"""TopoKit CLI main entry point."""

import typer
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table

from ..core.pack_parser import PackParser, PackParseError

app = typer.Typer(
    name="topokit",
    help="TopoKit - Enterprise-grade topology-first contract system for LLM applications",
    no_args_is_help=True,
)
console = Console()


@app.command()
def init(
    template: str = typer.Option("rag-system", "--template", "-t", help="Template to use"),
    language: str = typer.Option("python", "--language", "-l", help="Programming language"),
    output_dir: str = typer.Option(".", "--output", "-o", help="Output directory"),
):
    """Initialize a new TopoKit project."""
    console.print(f"[green]Initializing TopoKit project with template: {template}[/green]")
    console.print(f"[blue]Language: {language}[/blue]")
    console.print(f"[blue]Output directory: {output_dir}[/blue]")
    
    # TODO: Implement template initialization
    console.print("[yellow]Template initialization not yet implemented[/yellow]")


@app.command()
def lint(
    pack_dir: str = typer.Option("./topology", "--pack-dir", "-d", help="Topology pack directory"),
    strict: bool = typer.Option(False, "--strict", help="Enable strict validation"),
    fix: bool = typer.Option(False, "--fix", help="Auto-fix issues where possible"),
):
    """Lint and validate topology pack."""
    console.print(f"[green]Linting topology pack: {pack_dir}[/green]")
    
    try:
        parser = PackParser(pack_dir)
        pack = parser.parse()
        
        # Validate pack
        errors = parser.validate_pack(pack)
        
        if errors:
            console.print("[red]Validation errors found:[/red]")
            for error in errors:
                console.print(f"  [red]• {error}[/red]")
            raise typer.Exit(1)
        else:
            console.print("[green]✓ Topology pack is valid[/green]")
            
            # Show pack summary
            table = Table(title="Topology Pack Summary")
            table.add_column("Component", style="cyan")
            table.add_column("Count", style="magenta")
            
            table.add_row("Nodes", str(len(pack.nodes)))
            table.add_row("Edges", str(len(pack.edges)))
            table.add_row("Contracts", str(len(pack.contracts)))
            
            console.print(table)
    
    except PackParseError as e:
        console.print(f"[red]Parse error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def graph(
    pack_dir: str = typer.Option("./topology", "--pack-dir", "-d", help="Topology pack directory"),
    output: str = typer.Option("topology.png", "--output", "-o", help="Output file"),
    format: str = typer.Option("mermaid", "--format", "-f", help="Output format"),
):
    """Generate topology visualization."""
    console.print(f"[green]Generating topology graph: {pack_dir}[/green]")
    console.print(f"[blue]Output: {output}[/blue]")
    console.print(f"[blue]Format: {format}[/blue]")
    
    try:
        parser = PackParser(pack_dir)
        pack = parser.parse()
        
        if format == "mermaid":
            mermaid_content = _generate_mermaid_graph(pack)
            console.print("[green]Mermaid graph generated:[/green]")
            console.print(f"[code]{mermaid_content}[/code]")
        else:
            console.print("[yellow]Other formats not yet implemented[/yellow]")
    
    except PackParseError as e:
        console.print(f"[red]Parse error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


def _generate_mermaid_graph(pack) -> str:
    """Generate Mermaid graph from topology pack."""
    lines = ["graph TD"]
    
    # Add nodes
    for node in pack.nodes:
        node_id = node.id.replace(".", "_")
        node_label = f"{node.id}\\n({node.kind.value})"
        lines.append(f'    {node_id}["{node_label}"]')
    
    # Add edges
    for edge in pack.edges:
        from_id = edge.from_node.replace(".", "_")
        to_id = edge.to_node.replace(".", "_")
        lines.append(f"    {from_id} --> {to_id}")
    
    return "\\n".join(lines)


if __name__ == "__main__":
    app()
