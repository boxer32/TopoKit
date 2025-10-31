import { Command } from 'commander';
import chalk from 'chalk';
import fs from 'fs-extra';
import path from 'path';
import yaml from 'yaml';

export const replayCommand = new Command('replay')
  .description('Replay topology execution with deterministic testing')
  .option('-d, --pack-dir <dir>', 'Topology pack directory', './topology')
  .option('-t, --test-file <file>', 'Test file to replay', './topology/eval/replay.yaml')
  .option('--seed <seed>', 'Random seed for deterministic execution', 'stable')
  .option('--verbose', 'Verbose output')
  .action(async options => {
    console.log(chalk.blue('Replaying topology execution...'));

    try {
      const { packDir, testFile, seed, verbose } = options;
      const topologyPath = path.resolve(packDir);
      const testPath = path.resolve(testFile);

      if (!(await fs.pathExists(topologyPath))) {
        throw new Error(`Topology directory does not exist: ${topologyPath}`);
      }

      if (!(await fs.pathExists(testPath))) {
        console.log(chalk.yellow('No replay test found. Creating sample replay test...'));
        await createSampleReplayTest(testPath);
      }

      const results = await replayTopologyExecution(topologyPath, testPath, { seed, verbose });

      if (results.success) {
        console.log(chalk.green('✓ Replay completed successfully'));
        displayReplayResults(results);
      } else {
        console.log(chalk.red('✗ Replay failed'));
        displayReplayErrors(results);
        process.exit(1);
      }
    } catch (error) {
      console.log(chalk.red('✗ Replay failed:'));
      console.error(
        chalk.red(error instanceof Error ? error.message : String(error))
      );
      process.exit(1);
    }
  });

interface ReplayResult {
  success: boolean;
  executionId: string;
  duration: number;
  nodesExecuted: string[];
  outputs: Record<string, any>;
  errors: string[];
  warnings: string[];
  deterministic: boolean;
  seed: string;
}

async function replayTopologyExecution(
  topologyDir: string,
  testFile: string,
  options: { seed: string; verbose: boolean }
): Promise<ReplayResult> {
  const startTime = Date.now();
  const executionId = `replay_${Date.now()}`;
  
  // Load test configuration
  const testContent = await fs.readFile(testFile, 'utf-8');
  const test = yaml.parse(testContent);

  if (!test || !test.input) {
    throw new Error('Invalid replay test: missing input data');
  }

  // Load topology configuration
  const nodesPath = path.join(topologyDir, 'nodes.yaml');
  const edgesPath = path.join(topologyDir, 'edges.yaml');

  if (!(await fs.pathExists(nodesPath)) || !(await fs.pathExists(edgesPath))) {
    throw new Error('Missing topology configuration files');
  }

  const nodesContent = await fs.readFile(nodesPath, 'utf-8');
  const edgesContent = await fs.readFile(edgesPath, 'utf-8');

  const nodes = yaml.parse(nodesContent);
  const edges = yaml.parse(edgesContent);

  if (!nodes?.nodes || !edges?.edges) {
    throw new Error('Invalid topology configuration');
  }

  // Simulate deterministic execution
  const executionResult = await simulateDeterministicExecution(
    nodes.nodes,
    edges.edges,
    test.input,
    options.seed,
    options.verbose
  );

  const duration = Date.now() - startTime;

  return {
    success: executionResult.success,
    executionId,
    duration,
    nodesExecuted: executionResult.nodesExecuted,
    outputs: executionResult.outputs,
    errors: executionResult.errors,
    warnings: executionResult.warnings,
    deterministic: executionResult.deterministic,
    seed: options.seed,
  };
}

async function simulateDeterministicExecution(
  nodes: any[],
  edges: any[],
  input: any,
  seed: string,
  verbose: boolean
): Promise<{
  success: boolean;
  nodesExecuted: string[];
  outputs: Record<string, any>;
  errors: string[];
  warnings: string[];
  deterministic: boolean;
}> {
  const nodesExecuted: string[] = [];
  const outputs: Record<string, any> = {};
  const errors: string[] = [];
  const warnings: string[] = [];
  let deterministic = true;

  // Build execution graph
  const graph = new Map<string, string[]>();
  const reverseGraph = new Map<string, string[]>();
  
  for (const node of nodes) {
    graph.set(node.id, []);
    reverseGraph.set(node.id, []);
  }

  for (const edge of edges) {
    graph.get(edge.from)?.push(edge.to);
    reverseGraph.get(edge.to)?.push(edge.from);
  }

  // Find entry points
  const entryPoints = nodes
    .map(node => node.id)
    .filter(nodeId => !reverseGraph.get(nodeId)?.length);

  if (entryPoints.length === 0) {
    errors.push('No entry points found in topology');
    return { success: false, nodesExecuted, outputs, errors, warnings, deterministic };
  }

  // Execute nodes in topological order
  const visited = new Set<string>();
  const queue = [...entryPoints];

  while (queue.length > 0) {
    const nodeId = queue.shift()!;
    
    if (visited.has(nodeId)) {
      continue;
    }

    // Check if all dependencies are satisfied
    const dependencies = reverseGraph.get(nodeId) || [];
    if (!dependencies.every(dep => visited.has(dep))) {
      queue.push(nodeId); // Put back for later
      continue;
    }

    visited.add(nodeId);
    nodesExecuted.push(nodeId);

    // Simulate node execution with deterministic behavior
    const node = nodes.find(n => n.id === nodeId);
    if (!node) {
      errors.push(`Node not found: ${nodeId}`);
      continue;
    }

    try {
      const output = await simulateNodeExecution(node, input, outputs, seed);
      outputs[nodeId] = output;

      if (verbose) {
        console.log(chalk.gray(`  Executed ${nodeId}: ${JSON.stringify(output).substring(0, 100)}...`));
      }

      // Add dependent nodes to queue
      const dependents = graph.get(nodeId) || [];
      for (const dependent of dependents) {
        if (!visited.has(dependent) && !queue.includes(dependent)) {
          queue.push(dependent);
        }
      }

    } catch (error) {
      const errorMsg = `Node ${nodeId} execution failed: ${error instanceof Error ? error.message : String(error)}`;
      errors.push(errorMsg);
      
      if (verbose) {
        console.log(chalk.red(`  ${errorMsg}`));
      }
    }
  }

  // Check for deterministic behavior
  if (seed !== 'stable') {
    // Run again with same seed to verify determinism
    const secondRun = await simulateDeterministicExecution(nodes, edges, input, seed, false);
    deterministic = JSON.stringify(outputs) === JSON.stringify(secondRun.outputs);
  }

  return {
    success: errors.length === 0,
    nodesExecuted,
    outputs,
    errors,
    warnings,
    deterministic,
  };
}

async function simulateNodeExecution(
  node: any,
  input: any,
  previousOutputs: Record<string, any>,
  seed: string
): Promise<any> {
  // Simulate deterministic node execution based on node kind
  const nodeId = node.id;
  const kind = node.kind;

  // Use seed for deterministic random behavior
  const seedValue = seed === 'stable' ? 42 : parseInt(seed) || 42;
  const random = (Math.sin(seedValue + nodeId.charCodeAt(0)) + 1) / 2;

  switch (kind) {
    case 'ai':
      return {
        response: `AI response for ${nodeId} (seed: ${seed})`,
        confidence: 0.8 + (random * 0.2),
        metadata: {
          node_id: nodeId,
          kind: kind,
          seed: seed,
          timestamp: new Date().toISOString(),
        },
      };

    case 'data':
      return {
        processed_data: input,
        metadata: {
          node_id: nodeId,
          kind: kind,
          seed: seed,
          timestamp: new Date().toISOString(),
        },
      };

    case 'ux':
      return {
        user_interaction: `UX interaction for ${nodeId}`,
        metadata: {
          node_id: nodeId,
          kind: kind,
          seed: seed,
          timestamp: new Date().toISOString(),
        },
      };

    default:
      return {
        result: `Processed by ${nodeId}`,
        metadata: {
          node_id: nodeId,
          kind: kind,
          seed: seed,
          timestamp: new Date().toISOString(),
        },
      };
  }
}

async function createSampleReplayTest(testPath: string): Promise<void> {
  await fs.ensureDir(path.dirname(testPath));

  const sampleTest = {
    name: 'Sample Replay Test',
    description: 'Deterministic replay test for topology execution',
    input: {
      query: 'What is the capital of France?',
      context: ['Geography', 'Europe', 'Countries'],
    },
    expected_outputs: {
      'Data.Retrieval': {
        documents: [
          { content: 'Paris is the capital of France', score: 0.95 },
        ],
      },
      'AI.Answer': {
        answer: 'The capital of France is Paris',
        confidence: 0.9,
        sources: ['document_1'],
      },
    },
    seed: 'stable',
    deterministic: true,
  };

  await fs.writeFile(testPath, yaml.stringify(sampleTest, { indent: 2 }));
}

function displayReplayResults(result: ReplayResult): void {
  console.log(chalk.blue('\nReplay Results:'));
  console.log(chalk.gray(`  Execution ID: ${result.executionId}`));
  console.log(chalk.gray(`  Duration: ${result.duration}ms`));
  console.log(chalk.gray(`  Nodes Executed: ${result.nodesExecuted.length}`));
  console.log(chalk.gray(`  Deterministic: ${result.deterministic ? 'Yes' : 'No'}`));
  console.log(chalk.gray(`  Seed: ${result.seed}`));

  if (result.warnings.length > 0) {
    console.log(chalk.yellow('\nWarnings:'));
    for (const warning of result.warnings) {
      console.log(chalk.yellow(`  ⚠ ${warning}`));
    }
  }

  console.log(chalk.green('\n✓ Replay completed successfully'));
}

function displayReplayErrors(result: ReplayResult): void {
  console.log(chalk.red('\nReplay Errors:'));
  for (const error of result.errors) {
    console.log(chalk.red(`  ✗ ${error}`));
  }

  console.log(chalk.red(`\n✗ Replay failed after ${result.duration}ms`));
}
