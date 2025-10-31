import { Command } from 'commander';
import chalk from 'chalk';
import fs from 'fs-extra';
import path from 'path';
import yaml from 'yaml';

export const graphCommand = new Command('graph')
  .description('Generate topology visualization')
  .option('-d, --pack-dir <dir>', 'Topology pack directory', './topology')
  .option('-o, --output <file>', 'Output file (default: stdout)')
  .option('-f, --format <format>', 'Output format (mermaid, dot, json, svg, png)', 'mermaid')
  .option('--theme <theme>', 'Graph theme (light, dark, colorblind)', 'light')
  .option('--layout <layout>', 'Layout algorithm (top-down, left-right, circular)', 'top-down')
  .option('--show-contracts', 'Show contract information on edges')
  .option('--show-slos', 'Show SLO information on nodes')
  .option('--show-execution-profile', 'Show execution profile details')
  .action(async options => {
    console.log(chalk.blue('Generating topology graph...'));

    try {
      const { packDir, output, format, theme, layout, showContracts, showSlos, showExecutionProfile } = options;
      const topologyPath = path.resolve(packDir);

      if (!(await fs.pathExists(topologyPath))) {
        throw new Error(`Topology directory does not exist: ${topologyPath}`);
      }

      const graph = await generateTopologyGraph(topologyPath, {
        format,
        theme,
        layout,
        showContracts,
        showSlos,
        showExecutionProfile,
      });

      if (output) {
        await fs.writeFile(output, graph);
        console.log(chalk.green(`✓ Graph saved to ${output}`));
      } else {
        console.log(chalk.green('✓ Topology graph generated:'));
        console.log(graph);
      }
    } catch (error) {
      console.log(chalk.red('✗ Graph generation failed:'));
      console.error(
        chalk.red(error instanceof Error ? error.message : String(error))
      );
      process.exit(1);
    }
  });

interface GraphOptions {
  format: string;
  theme: string;
  layout: string;
  showContracts: boolean;
  showSlos: boolean;
  showExecutionProfile: boolean;
}

async function generateTopologyGraph(
  topologyDir: string,
  options: GraphOptions
): Promise<string> {
  // Load topology configuration
  const nodesPath = path.join(topologyDir, 'nodes.yaml');
  const edgesPath = path.join(topologyDir, 'edges.yaml');

  if (!(await fs.pathExists(nodesPath)) || !(await fs.pathExists(edgesPath))) {
    throw new Error('Missing required topology files (nodes.yaml, edges.yaml)');
  }

  const nodesContent = await fs.readFile(nodesPath, 'utf-8');
  const edgesContent = await fs.readFile(edgesPath, 'utf-8');

  const nodes = yaml.parse(nodesContent);
  const edges = yaml.parse(edgesContent);

  if (!nodes?.nodes || !edges?.edges) {
    throw new Error('Invalid topology configuration');
  }

  switch (options.format.toLowerCase()) {
    case 'mermaid':
      return generateMermaidGraph(nodes.nodes, edges.edges, options);
    case 'dot':
      return generateDotGraph(nodes.nodes, edges.edges, options);
    case 'json':
      return generateJsonGraph(nodes.nodes, edges.edges, options);
    case 'svg':
      return generateSvgGraph(nodes.nodes, edges.edges, options);
    case 'png':
      return generatePngGraph(nodes.nodes, edges.edges, options);
    default:
      throw new Error(`Unsupported format: ${options.format}`);
  }
}

function generateMermaidGraph(nodes: any[], edges: any[], options: GraphOptions): string {
  const layout = options.layout === 'left-right' ? 'LR' : 'TD';
  let mermaid = `graph ${layout}\n`;

  // Add nodes
  for (const node of nodes) {
    const nodeId = node.id.replace(/[^a-zA-Z0-9]/g, '_');
    const nodeType = getNodeTypeIcon(node.kind);
    let nodeLabel = `${nodeType} ${node.id}`;
    
    // Add additional information based on options
    if (options.showSlos && node.slos) {
      const sloInfo = Object.entries(node.slos)
        .map(([key, value]) => `${key}: ${value}`)
        .join('\\n');
      nodeLabel += `\\nSLOs: ${sloInfo}`;
    }
    
    if (options.showExecutionProfile && node.execution_profile) {
      const profile = node.execution_profile;
      const profileInfo = `temp: ${profile.temperature}, top_p: ${profile.top_p}`;
      nodeLabel += `\\nProfile: ${profileInfo}`;
    }

    mermaid += `    ${nodeId}["${nodeLabel}"]\n`;
  }

  // Add edges
  for (const edge of edges) {
    const fromId = edge.from.replace(/[^a-zA-Z0-9]/g, '_');
    const toId = edge.to.replace(/[^a-zA-Z0-9]/g, '_');
    let edgeLabel = '';
    
    if (options.showContracts && edge.contracts) {
      edgeLabel = edge.contracts.join(', ');
    }

    if (edgeLabel) {
      mermaid += `    ${fromId} -->|"${edgeLabel}"| ${toId}\n`;
    } else {
      mermaid += `    ${fromId} --> ${toId}\n`;
    }
  }

  return mermaid;
}

function generateDotGraph(nodes: any[], edges: any[], options: GraphOptions): string {
  const rankdir = options.layout === 'left-right' ? 'LR' : 'TB';
  let dot = 'digraph Topology {\n';
  dot += `  rankdir=${rankdir};\n`;
  dot += '  node [shape=box, style=filled];\n\n';

  // Add nodes
  for (const node of nodes) {
    const nodeId = node.id.replace(/[^a-zA-Z0-9]/g, '_');
    const nodeColor = getNodeTypeColor(node.kind, options.theme);
    let nodeLabel = `${node.id}\\n(${node.kind})`;
    
    if (options.showSlos && node.slos) {
      const sloInfo = Object.entries(node.slos)
        .map(([key, value]) => `${key}: ${value}`)
        .join('\\n');
      nodeLabel += `\\nSLOs: ${sloInfo}`;
    }

    dot += `  ${nodeId} [label="${nodeLabel}", fillcolor="${nodeColor}"];\n`;
  }

  dot += '\n';

  // Add edges
  for (const edge of edges) {
    const fromId = edge.from.replace(/[^a-zA-Z0-9]/g, '_');
    const toId = edge.to.replace(/[^a-zA-Z0-9]/g, '_');
    let edgeLabel = '';
    
    if (options.showContracts && edge.contracts) {
      edgeLabel = edge.contracts.join(', ');
    }

    if (edgeLabel) {
      dot += `  ${fromId} -> ${toId} [label="${edgeLabel}"];\n`;
    } else {
      dot += `  ${fromId} -> ${toId};\n`;
    }
  }

  dot += '}\n';
  return dot;
}

function generateJsonGraph(nodes: any[], edges: any[], options: GraphOptions): string {
  const graph = {
    metadata: {
      format: 'topokit-graph',
      version: '1.0.0',
      generated_at: new Date().toISOString(),
      options: {
        theme: options.theme,
        layout: options.layout,
        showContracts: options.showContracts,
        showSlos: options.showSlos,
        showExecutionProfile: options.showExecutionProfile,
      },
    },
    nodes: nodes.map(node => ({
      id: node.id,
      kind: node.kind,
      version: node.version,
      scope: node.scope,
      execution_profile: options.showExecutionProfile ? node.execution_profile : undefined,
      slos: options.showSlos ? node.slos : undefined,
    })),
    edges: edges.map(edge => ({
      id: edge.id,
      from: edge.from,
      to: edge.to,
      contracts: options.showContracts ? edge.contracts : undefined,
      allow: edge.allow,
      timeout_ms: edge.timeout_ms,
      max_retries: edge.max_retries,
    })),
  };

  return JSON.stringify(graph, null, 2);
}

function generateSvgGraph(nodes: any[], edges: any[], options: GraphOptions): string {
  // For now, generate a simple SVG representation
  // In a real implementation, you might use a library like d3 or vis.js
  const width = 800;
  const height = 600;
  const nodeWidth = 120;
  const nodeHeight = 60;
  const padding = 20;
  
  let svg = `<svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">\n`;
  svg += `  <defs>\n`;
  svg += `    <style>\n`;
  svg += `      .node { fill: #e1f5fe; stroke: #01579b; stroke-width: 2; }\n`;
  svg += `      .edge { stroke: #666; stroke-width: 2; fill: none; }\n`;
  svg += `      .label { font-family: Arial, sans-serif; font-size: 12px; text-anchor: middle; }\n`;
  svg += `    </style>\n`;
  svg += `  </defs>\n`;

  // Calculate node positions (simple grid layout)
  const cols = Math.ceil(Math.sqrt(nodes.length));
  
  for (let i = 0; i < nodes.length; i++) {
    const node = nodes[i];
    const col = i % cols;
    const row = Math.floor(i / cols);
    const x = padding + col * (nodeWidth + padding);
    const y = padding + row * (nodeHeight + padding);
    
    const color = getNodeTypeColor(node.kind, options.theme);
    svg += `  <rect x="${x}" y="${y}" width="${nodeWidth}" height="${nodeHeight}" class="node" fill="${color}"/>\n`;
    svg += `  <text x="${x + nodeWidth/2}" y="${y + nodeHeight/2}" class="label">${node.id}</text>\n`;
  }

  // Add edges (simplified - just straight lines)
  for (const edge of edges) {
    const fromIndex = nodes.findIndex(n => n.id === edge.from);
    const toIndex = nodes.findIndex(n => n.id === edge.to);
    
    if (fromIndex !== -1 && toIndex !== -1) {
      const fromCol = fromIndex % cols;
      const fromRow = Math.floor(fromIndex / cols);
      const toCol = toIndex % cols;
      const toRow = Math.floor(toIndex / cols);
      
      const fromX = padding + fromCol * (nodeWidth + padding) + nodeWidth/2;
      const fromY = padding + fromRow * (nodeHeight + padding) + nodeHeight/2;
      const toX = padding + toCol * (nodeWidth + padding) + nodeWidth/2;
      const toY = padding + toRow * (nodeHeight + padding) + nodeHeight/2;
      
      svg += `  <line x1="${fromX}" y1="${fromY}" x2="${toX}" y2="${toY}" class="edge"/>\n`;
    }
  }

  svg += `</svg>`;
  return svg;
}

function generatePngGraph(nodes: any[], edges: any[], options: GraphOptions): string {
  // For PNG generation, we would typically:
  // 1. Generate SVG first
  // 2. Convert to PNG using a library like puppeteer or sharp
  // For now, return a placeholder message
  return `PNG generation not implemented yet. Use SVG format instead.\n\nSVG content:\n${generateSvgGraph(nodes, edges, options)}`;
}

function getNodeTypeIcon(kind: string): string {
  switch (kind.toLowerCase()) {
    case 'ai':
      return '🤖';
    case 'data':
      return '📊';
    case 'ux':
      return '👤';
    case 'tool':
      return '🔧';
    case 'gateway':
      return '🚪';
    default:
      return '⚙️';
  }
}

function getNodeTypeColor(kind: string, theme: string = 'light'): string {
  const colors = {
    light: {
      ai: '#e3f2fd',
      data: '#e8f5e8',
      ux: '#fff3e0',
      ops: '#f3e5f5',
      tool: '#fff8e1',
      gateway: '#f5f5f5',
      default: '#ffffff'
    },
    dark: {
      ai: '#1565c0',
      data: '#2e7d32',
      ux: '#ef6c00',
      ops: '#7b1fa2',
      tool: '#f57f17',
      gateway: '#616161',
      default: '#424242'
    },
    colorblind: {
      ai: '#1f77b4',
      data: '#ff7f0e',
      ux: '#2ca02c',
      ops: '#d62728',
      tool: '#9467bd',
      gateway: '#8c564b',
      default: '#17becf'
    }
  };

  const themeColors = colors[theme as keyof typeof colors] || colors.light;
  
  switch (kind.toLowerCase()) {
    case 'ai':
      return themeColors.ai;
    case 'data':
      return themeColors.data;
    case 'ux':
      return themeColors.ux;
    case 'ops':
      return themeColors.ops;
    case 'tool':
      return themeColors.tool;
    case 'gateway':
      return themeColors.gateway;
    default:
      return themeColors.default;
  }
}
