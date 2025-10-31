import { Command } from 'commander';
import chalk from 'chalk';
import fs from 'fs-extra';
import path from 'path';
import yaml from 'yaml';

export const evalCommand = new Command('eval')
  .description('Run evaluation tests on topology pack')
  .option('-d, --pack-dir <dir>', 'Topology pack directory', './topology')
  .option('-t, --test-dir <dir>', 'Test directory', './topology/eval')
  .option('--verbose', 'Verbose output')
  .action(async options => {
    console.log(chalk.blue('Running evaluation tests...'));

    try {
      const { packDir, testDir, verbose } = options;
      const topologyPath = path.resolve(packDir);
      const evalPath = path.resolve(testDir);

      if (!(await fs.pathExists(topologyPath))) {
        throw new Error(`Topology directory does not exist: ${topologyPath}`);
      }

      if (!(await fs.pathExists(evalPath))) {
        console.log(
          chalk.yellow('No evaluation tests found. Creating sample test...')
        );
        await createSampleTest(evalPath);
      }

      const results = await runEvaluationTests(topologyPath, evalPath, verbose);

      if (results.passed === results.total) {
        console.log(chalk.green(`✓ All ${results.total} tests passed`));
      } else {
        console.log(
          chalk.red(`✗ ${results.failed} of ${results.total} tests failed`)
        );
        displayTestResults(results);
        process.exit(1);
      }
    } catch (error) {
      console.log(chalk.red('✗ Evaluation failed:'));
      console.error(
        chalk.red(error instanceof Error ? error.message : String(error))
      );
      process.exit(1);
    }
  });

interface TestResult {
  name: string;
  passed: boolean;
  error: string | undefined;
  duration: number;
}

interface EvaluationResults {
  total: number;
  passed: number;
  failed: number;
  tests: TestResult[];
}

async function runEvaluationTests(
  topologyDir: string,
  evalDir: string,
  verbose: boolean
): Promise<EvaluationResults> {
  const results: TestResult[] = [];

  // Find all test files
  const testFiles = await fs.readdir(evalDir);
  const yamlTests = testFiles.filter(
    f => f.endsWith('.yaml') || f.endsWith('.yml')
  );

  if (yamlTests.length === 0) {
    throw new Error('No test files found in evaluation directory');
  }

  for (const testFile of yamlTests) {
    const testPath = path.join(evalDir, testFile);
    const testContent = await fs.readFile(testPath, 'utf-8');
    const test = yaml.parse(testContent);

    if (!test || !test.tests || !Array.isArray(test.tests)) {
      console.log(chalk.yellow(`Skipping invalid test file: ${testFile}`));
      continue;
    }

    for (const testCase of test.tests) {
      const startTime = Date.now();
      let passed = false;
      let error: string | undefined;

      try {
        await runTestCase(testCase, topologyDir);
        passed = true;
      } catch (err) {
        error = err instanceof Error ? err.message : String(err);
      }

      const duration = Date.now() - startTime;
      results.push({
        name: testCase.name || `${testFile}:${testCase.id || 'unknown'}`,
        passed,
        error,
        duration,
      });

      if (verbose) {
        const status = passed ? chalk.green('✓') : chalk.red('✗');
        console.log(
          `${status} ${testCase.name || testCase.id} (${duration}ms)`
        );
        if (error) {
          console.log(chalk.red(`  Error: ${error}`));
        }
      }
    }
  }

  return {
    total: results.length,
    passed: results.filter(r => r.passed).length,
    failed: results.filter(r => !r.passed).length,
    tests: results,
  };
}

async function runTestCase(testCase: any, topologyDir: string): Promise<void> {
  // Basic test case validation
  if (!testCase.name && !testCase.id) {
    throw new Error('Test case must have name or id');
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

  // Run test case specific validations
  if (testCase.type === 'topology_validation') {
    await validateTopologyStructure(nodes.nodes, edges.edges, testCase);
  } else if (testCase.type === 'contract_validation') {
    await validateContracts(topologyDir, testCase);
  } else if (testCase.type === 'execution_simulation') {
    await simulateExecution(nodes.nodes, edges.edges, testCase);
  } else {
    throw new Error(`Unknown test type: ${testCase.type}`);
  }
}

async function validateTopologyStructure(
  _nodes: any[],
  edges: any[],
  testCase: any
): Promise<void> {
  // Check node requirements
  if (testCase.required_nodes) {
    for (const requiredNode of testCase.required_nodes) {
      const found = _nodes.some((node: any) => node.id === requiredNode);
      if (!found) {
        throw new Error(`Required node not found: ${requiredNode}`);
      }
    }
  }

  // Check edge requirements
  if (testCase.required_edges) {
    for (const requiredEdge of testCase.required_edges) {
      const found = edges.some(
        edge => edge.from === requiredEdge.from && edge.to === requiredEdge.to
      );
      if (!found) {
        throw new Error(
          `Required edge not found: ${requiredEdge.from} -> ${requiredEdge.to}`
        );
      }
    }
  }

  // Check for cycles if specified
  if (testCase.no_cycles) {
    const hasCycles = detectCycles(_nodes, edges);
    if (hasCycles) {
      throw new Error('Topology contains cycles');
    }
  }
}

async function validateContracts(
  topologyDir: string,
  testCase: any
): Promise<void> {
  const contractsDir = path.join(topologyDir, 'contracts');

  if (!(await fs.pathExists(contractsDir))) {
    throw new Error('Contracts directory not found');
  }

  const contractFiles = await fs.readdir(contractsDir);
  const jsonContracts = contractFiles.filter(f => f.endsWith('.json'));

  if (testCase.required_contracts) {
    for (const requiredContract of testCase.required_contracts) {
      const contractFile = `${requiredContract}.json`;
      if (!jsonContracts.includes(contractFile)) {
        throw new Error(`Required contract not found: ${requiredContract}`);
      }

      // Validate contract structure
      const contractPath = path.join(contractsDir, contractFile);
      const contractContent = await fs.readFile(contractPath, 'utf-8');
      const contract = JSON.parse(contractContent);

      if (!contract.input || !contract.output) {
        throw new Error(`Invalid contract structure: ${requiredContract}`);
      }
    }
  }
}

async function simulateExecution(
  _nodes: any[],
  edges: any[],
  testCase: any
): Promise<void> {
  // Basic execution simulation
  if (testCase.input) {
    // Simulate data flow through topology
    const visited = new Set<string>();
    const queue = testCase.start_nodes || [];

    while (queue.length > 0) {
      const currentNode = queue.shift();
      if (visited.has(currentNode)) {
        continue;
      }

      visited.add(currentNode);

      // Find outgoing edges
      const outgoingEdges = edges.filter(edge => edge.from === currentNode);
      for (const edge of outgoingEdges) {
        if (!visited.has(edge.to)) {
          queue.push(edge.to);
        }
      }
    }

    // Check if all expected nodes were visited
    if (testCase.expected_nodes) {
      for (const expectedNode of testCase.expected_nodes) {
        if (!visited.has(expectedNode)) {
          throw new Error(`Expected node not reachable: ${expectedNode}`);
        }
      }
    }
  }
}

function detectCycles(nodes: any[], edges: any[]): boolean {
  const visited = new Set<string>();
  const recursionStack = new Set<string>();

  function hasCycle(nodeId: string): boolean {
    if (recursionStack.has(nodeId)) {
      return true;
    }

    if (visited.has(nodeId)) {
      return false;
    }

    visited.add(nodeId);
    recursionStack.add(nodeId);

    const outgoingEdges = edges.filter(edge => edge.from === nodeId);
    for (const edge of outgoingEdges) {
      if (hasCycle(edge.to)) {
        return true;
      }
    }

    recursionStack.delete(nodeId);
    return false;
  }

  for (const node of nodes) {
    if (!visited.has(node.id)) {
      if (hasCycle(node.id)) {
        return true;
      }
    }
  }

  return false;
}

async function createSampleTest(evalDir: string): Promise<void> {
  await fs.ensureDir(evalDir);

  const sampleTest = {
    name: 'Topology Validation Tests',
    description: 'Basic validation tests for topology structure',
    tests: [
      {
        id: 'topology_structure',
        name: 'Validate topology structure',
        type: 'topology_validation',
        required_nodes: ['UX.Intent', 'AI.Rank', 'AI.Explain'],
        required_edges: [
          { from: 'UX.Intent', to: 'AI.Rank' },
          { from: 'AI.Rank', to: 'AI.Explain' },
        ],
        no_cycles: true,
      },
      {
        id: 'contract_validation',
        name: 'Validate contracts',
        type: 'contract_validation',
        required_contracts: ['classify', 'rank', 'explain'],
      },
      {
        id: 'execution_simulation',
        name: 'Simulate execution flow',
        type: 'execution_simulation',
        input: { query: 'test query' },
        start_nodes: ['UX.Intent'],
        expected_nodes: ['AI.Rank', 'AI.Explain'],
      },
    ],
  };

  await fs.writeFile(
    path.join(evalDir, 'basic_validation.yaml'),
    yaml.stringify(sampleTest, { indent: 2 })
  );
}

function displayTestResults(results: EvaluationResults): void {
  console.log(chalk.red('\nFailed Tests:'));
  for (const test of results.tests) {
    if (!test.passed) {
      console.log(chalk.red(`  ✗ ${test.name}: ${test.error}`));
    }
  }

  console.log(chalk.blue('\nTest Summary:'));
  console.log(chalk.gray(`  Total: ${results.total}`));
  console.log(chalk.green(`  Passed: ${results.passed}`));
  console.log(chalk.red(`  Failed: ${results.failed}`));
}
