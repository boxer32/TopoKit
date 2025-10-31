import { Command } from 'commander';
import chalk from 'chalk';
import fs from 'fs-extra';
import path from 'path';

export const monitorCommand = new Command('monitor')
  .description('Monitor topology execution and performance')
  .option('-d, --pack-dir <dir>', 'Topology pack directory', './topology')
  .option('--watch', 'Watch for changes and auto-refresh')
  .option('--interval <ms>', 'Refresh interval in milliseconds', '5000')
  .action(async options => {
    const { packDir, watch, interval } = options;
    const topologyPath = path.resolve(packDir);

    if (!(await fs.pathExists(topologyPath))) {
      console.error(
        chalk.red(`Topology directory does not exist: ${topologyPath}`)
      );
      process.exit(1);
    }

    console.log(chalk.blue('TopoKit Monitor'));
    console.log(chalk.gray('Press Ctrl+C to exit\n'));

    if (watch) {
      await startWatching(topologyPath, parseInt(interval));
    } else {
      await displayStatus(topologyPath);
    }
  });

async function startWatching(
  topologyPath: string,
  interval: number
): Promise<void> {
  const displayStatus = async () => {
    console.clear();
    console.log(chalk.blue('TopoKit Monitor - Watching for changes...'));
    console.log(
      chalk.gray(`Last updated: ${new Date().toLocaleTimeString()}\n`)
    );

    try {
      await displayTopologyStatus(topologyPath);
    } catch (error) {
      console.error(chalk.red('Error monitoring topology:'), error);
    }
  };

  // Initial display
  await displayStatus();

  // Set up interval
  const intervalId = setInterval(displayStatus, interval);

  // Handle Ctrl+C
  process.on('SIGINT', () => {
    clearInterval(intervalId);
    console.log(chalk.yellow('\nMonitoring stopped.'));
    process.exit(0);
  });

  // Keep the process alive
  await new Promise(() => {});
}

async function displayStatus(topologyPath: string): Promise<void> {
  console.log(chalk.blue('TopoKit Monitor'));
  console.log(chalk.gray(`Topology: ${topologyPath}\n`));

  try {
    await displayTopologyStatus(topologyPath);
  } catch (error) {
    console.error(chalk.red('Error displaying status:'), error);
    process.exit(1);
  }
}

async function displayTopologyStatus(topologyPath: string): Promise<void> {
  // Check if topology files exist
  const nodesPath = path.join(topologyPath, 'nodes.yaml');
  const edgesPath = path.join(topologyPath, 'edges.yaml');
  const guardrailsPath = path.join(topologyPath, 'guardrails.yaml');
  const contractsDir = path.join(topologyPath, 'contracts');

  console.log(chalk.bold('Configuration Status:'));

  // Check nodes
  if (await fs.pathExists(nodesPath)) {
    const stats = await fs.stat(nodesPath);
    console.log(chalk.green(`  ✓ nodes.yaml (${formatFileSize(stats.size)})`));
  } else {
    console.log(chalk.red('  ✗ nodes.yaml (missing)'));
  }

  // Check edges
  if (await fs.pathExists(edgesPath)) {
    const stats = await fs.stat(edgesPath);
    console.log(chalk.green(`  ✓ edges.yaml (${formatFileSize(stats.size)})`));
  } else {
    console.log(chalk.red('  ✗ edges.yaml (missing)'));
  }

  // Check guardrails
  if (await fs.pathExists(guardrailsPath)) {
    const stats = await fs.stat(guardrailsPath);
    console.log(
      chalk.green(`  ✓ guardrails.yaml (${formatFileSize(stats.size)})`)
    );
  } else {
    console.log(chalk.yellow('  ⚠ guardrails.yaml (missing)'));
  }

  // Check contracts
  if (await fs.pathExists(contractsDir)) {
    const contractFiles = await fs.readdir(contractsDir);
    const jsonContracts = contractFiles.filter(f => f.endsWith('.json'));
    console.log(
      chalk.green(`  ✓ contracts/ (${jsonContracts.length} contracts)`)
    );
  } else {
    console.log(chalk.yellow('  ⚠ contracts/ (missing)'));
  }

  console.log();

  // Display topology summary
  try {
    const summary = await getTopologySummary(topologyPath);
    console.log(chalk.bold('Topology Summary:'));
    console.log(chalk.gray(`  Nodes: ${summary.nodes}`));
    console.log(chalk.gray(`  Edges: ${summary.edges}`));
    console.log(chalk.gray(`  Contracts: ${summary.contracts}`));
    console.log();

    // Display node details
    if (summary.nodeDetails.length > 0) {
      console.log(chalk.bold('Nodes:'));
      for (const node of summary.nodeDetails) {
        const icon = getNodeIcon(node.kind);
        console.log(chalk.gray(`  ${icon} ${node.id} (${node.kind})`));
      }
      console.log();
    }

    // Display edge details
    if (summary.edgeDetails.length > 0) {
      console.log(chalk.bold('Edges:'));
      for (const edge of summary.edgeDetails) {
        const contracts = edge.contracts ? edge.contracts.join(', ') : 'none';
        console.log(chalk.gray(`  ${edge.from} → ${edge.to} (${contracts})`));
      }
      console.log();
    }
  } catch (error) {
    console.log(chalk.red('Error parsing topology:'), error);
  }

  // Display performance metrics (simulated)
  console.log(chalk.bold('Performance Metrics:'));
  console.log(chalk.gray('  Status: Not running (simulation mode)'));
  console.log(chalk.gray('  Uptime: N/A'));
  console.log(chalk.gray('  Requests: N/A'));
  console.log(chalk.gray('  Average Response Time: N/A'));
  console.log(chalk.gray('  Error Rate: N/A'));
}

async function getTopologySummary(topologyPath: string): Promise<{
  nodes: number;
  edges: number;
  contracts: number;
  nodeDetails: Array<{ id: string; kind: string }>;
  edgeDetails: Array<{ from: string; to: string; contracts?: string[] }>;
}> {
  const yaml = await import('yaml');

  let nodes = 0;
  let edges = 0;
  let contracts = 0;
  const nodeDetails: Array<{ id: string; kind: string }> = [];
  const edgeDetails: Array<{ from: string; to: string; contracts?: string[] }> =
    [];

  // Load nodes
  const nodesPath = path.join(topologyPath, 'nodes.yaml');
  if (await fs.pathExists(nodesPath)) {
    const content = await fs.readFile(nodesPath, 'utf-8');
    const nodesData = yaml.parse(content);
    if (nodesData?.nodes) {
      nodes = nodesData.nodes.length;
      nodeDetails.push(
        ...nodesData.nodes.map((n: any) => ({
          id: n.id,
          kind: n.kind,
        }))
      );
    }
  }

  // Load edges
  const edgesPath = path.join(topologyPath, 'edges.yaml');
  if (await fs.pathExists(edgesPath)) {
    const content = await fs.readFile(edgesPath, 'utf-8');
    const edgesData = yaml.parse(content);
    if (edgesData?.edges) {
      edges = edgesData.edges.length;
      edgeDetails.push(
        ...edgesData.edges.map((e: any) => ({
          from: e.from,
          to: e.to,
          contracts: e.contracts,
        }))
      );
    }
  }

  // Load contracts
  const contractsDir = path.join(topologyPath, 'contracts');
  if (await fs.pathExists(contractsDir)) {
    const contractFiles = await fs.readdir(contractsDir);
    contracts = contractFiles.filter(f => f.endsWith('.json')).length;
  }

  return {
    nodes,
    edges,
    contracts,
    nodeDetails,
    edgeDetails,
  };
}

function getNodeIcon(kind: string): string {
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

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}
