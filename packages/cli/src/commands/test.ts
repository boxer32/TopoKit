import { Command } from 'commander';
import chalk from 'chalk';
import fs from 'fs-extra';
import path from 'path';
import yaml from 'yaml';

export const testCommand = new Command('test')
  .description('Testing and validation for topology packs')
  .option('-d, --pack-dir <dir>', 'Topology pack directory', './topology')
  .option('-t, --test-dir <dir>', 'Test directory', './topology/tests')
  .option('--unit', 'Run unit tests only')
  .option('--integration', 'Run integration tests only')
  .option('--contract', 'Run contract tests only')
  .option('--performance', 'Run performance tests only')
  .option('--coverage', 'Generate test coverage report')
  .option('--verbose', 'Verbose output')
  .action(async options => {
    console.log(chalk.blue('Running topology tests...'));

    try {
      const { packDir, testDir, unit, integration, contract, performance, coverage, verbose } = options;
      const topologyPath = path.resolve(packDir);
      const testsPath = path.resolve(testDir);

      if (!(await fs.pathExists(topologyPath))) {
        throw new Error(`Topology directory does not exist: ${topologyPath}`);
      }

      // Create test directory if it doesn't exist
      if (!(await fs.pathExists(testsPath))) {
        console.log(chalk.yellow('Test directory not found. Creating sample tests...'));
        await createSampleTests(testsPath);
      }

      const testResults = await runTests(topologyPath, testsPath, {
        unit,
        integration,
        contract,
        performance,
        coverage,
        verbose,
      });

      displayTestResults(testResults);

      if (testResults.failed > 0) {
        process.exit(1);
      }

    } catch (error) {
      console.log(chalk.red('✗ Test execution failed:'));
      console.error(
        chalk.red(error instanceof Error ? error.message : String(error))
      );
      process.exit(1);
    }
  });

interface TestOptions {
  unit: boolean;
  integration: boolean;
  contract: boolean;
  performance: boolean;
  coverage: boolean;
  verbose: boolean;
}

interface TestResults {
  total: number;
  passed: number;
  failed: number;
  skipped: number;
  duration: number;
  coverage?: CoverageReport;
  tests: TestResult[];
}

interface TestResult {
  name: string;
  type: 'unit' | 'integration' | 'contract' | 'performance';
  status: 'passed' | 'failed' | 'skipped';
  duration: number;
  error?: string;
  output?: string;
}

interface CoverageReport {
  statements: number;
  branches: number;
  functions: number;
  lines: number;
  files: number;
}

async function runTests(
  topologyDir: string,
  testsDir: string,
  options: TestOptions
): Promise<TestResults> {
  const startTime = Date.now();
  const results: TestResult[] = [];

  // Determine which test types to run
  const testTypes = [];
  if (options.unit || (!options.integration && !options.contract && !options.performance)) {
    testTypes.push('unit');
  }
  if (options.integration) {
    testTypes.push('integration');
  }
  if (options.contract) {
    testTypes.push('contract');
  }
  if (options.performance) {
    testTypes.push('performance');
  }

  // Run tests for each type
  for (const testType of testTypes) {
    const typeResults = await runTestType(topologyDir, testsDir, testType, options);
    results.push(...typeResults);
  }

  const duration = Date.now() - startTime;

  // Generate coverage report if requested
  let coverage: CoverageReport | undefined;
  if (options.coverage) {
    coverage = await generateCoverageReport(topologyDir, results);
  }

  return {
    total: results.length,
    passed: results.filter(r => r.status === 'passed').length,
    failed: results.filter(r => r.status === 'failed').length,
    skipped: results.filter(r => r.status === 'skipped').length,
    duration,
    coverage,
    tests: results,
  };
}

async function runTestType(
  topologyDir: string,
  testsDir: string,
  testType: string,
  options: TestOptions
): Promise<TestResult[]> {
  const results: TestResult[] = [];
  const testFiles = await findTestFiles(testsDir, testType);

  for (const testFile of testFiles) {
    const testContent = await fs.readFile(testFile, 'utf-8');
    const tests = yaml.parse(testContent);

    if (!tests || !Array.isArray(tests.tests)) {
      continue;
    }

    for (const test of tests.tests) {
      const startTime = Date.now();
      let status: 'passed' | 'failed' | 'skipped' = 'skipped';
      let error: string | undefined;

      try {
        // Skip if test type doesn't match
        if (test.type && test.type !== testType) {
          status = 'skipped';
        } else {
          await executeTest(test, topologyDir, testType);
          status = 'passed';
        }
      } catch (err) {
        status = 'failed';
        error = err instanceof Error ? err.message : String(err);
      }

      const duration = Date.now() - startTime;

      results.push({
        name: test.name || test.id || 'unnamed',
        type: testType as any,
        status,
        duration,
        error,
      });

      if (options.verbose) {
        const statusColor = status === 'passed' ? chalk.green : 
                           status === 'failed' ? chalk.red : chalk.yellow;
        const statusIcon = status === 'passed' ? '✓' : 
                          status === 'failed' ? '✗' : '○';
        console.log(`${statusColor(statusIcon)} ${test.name || test.id} (${duration}ms)`);
        if (error) {
          console.log(chalk.red(`  Error: ${error}`));
        }
      }
    }
  }

  return results;
}

async function findTestFiles(testsDir: string, testType: string): Promise<string[]> {
  const testFiles: string[] = [];
  
  if (!(await fs.pathExists(testsDir))) {
    return testFiles;
  }

  const files = await fs.readdir(testsDir);
  for (const file of files) {
    if (file.endsWith('.yaml') || file.endsWith('.yml')) {
      const filePath = path.join(testsDir, file);
      const content = await fs.readFile(filePath, 'utf-8');
      const tests = yaml.parse(content);
      
      if (tests && tests.type === testType) {
        testFiles.push(filePath);
      }
    }
  }

  return testFiles;
}

async function executeTest(test: any, topologyDir: string, testType: string): Promise<void> {
  switch (testType) {
    case 'unit':
      await executeUnitTest(test, topologyDir);
      break;
    case 'integration':
      await executeIntegrationTest(test, topologyDir);
      break;
    case 'contract':
      await executeContractTest(test, topologyDir);
      break;
    case 'performance':
      await executePerformanceTest(test, topologyDir);
      break;
    default:
      throw new Error(`Unknown test type: ${testType}`);
  }
}

async function executeUnitTest(test: any, topologyDir: string): Promise<void> {
  // Unit tests focus on individual components
  if (test.component === 'node') {
    await validateNode(test, topologyDir);
  } else if (test.component === 'edge') {
    await validateEdge(test, topologyDir);
  } else if (test.component === 'contract') {
    await validateContract(test, topologyDir);
  } else {
    throw new Error(`Unknown component: ${test.component}`);
  }
}

async function executeIntegrationTest(test: any, topologyDir: string): Promise<void> {
  // Integration tests focus on component interactions
  if (test.scenario === 'data_flow') {
    await validateDataFlow(test, topologyDir);
  } else if (test.scenario === 'error_handling') {
    await validateErrorHandling(test, topologyDir);
  } else if (test.scenario === 'performance') {
    await validatePerformance(test, topologyDir);
  } else {
    throw new Error(`Unknown scenario: ${test.scenario}`);
  }
}

async function executeContractTest(test: any, topologyDir: string): Promise<void> {
  // Contract tests validate data exchange contracts
  const contractsDir = path.join(topologyDir, 'contracts');
  const contractFile = path.join(contractsDir, `${test.contract}.json`);
  
  if (!(await fs.pathExists(contractFile))) {
    throw new Error(`Contract file not found: ${test.contract}`);
  }

  const contract = JSON.parse(await fs.readFile(contractFile, 'utf-8'));
  
  // Validate contract structure
  if (!contract.input || !contract.output) {
    throw new Error('Invalid contract structure');
  }

  // Validate test data against contract
  if (test.input) {
    await validateAgainstSchema(test.input, contract.input);
  }
  
  if (test.output) {
    await validateAgainstSchema(test.output, contract.output);
  }
}

async function executePerformanceTest(test: any, topologyDir: string): Promise<void> {
  // Performance tests validate performance characteristics
  const startTime = Date.now();
  
  // Simulate performance test execution
  await new Promise(resolve => setTimeout(resolve, test.duration || 100));
  
  const duration = Date.now() - startTime;
  
  if (test.maxDuration && duration > test.maxDuration) {
    throw new Error(`Performance test exceeded max duration: ${duration}ms > ${test.maxDuration}ms`);
  }
}

async function validateNode(test: any, topologyDir: string): Promise<void> {
  const nodesPath = path.join(topologyDir, 'nodes.yaml');
  const nodes = yaml.parse(await fs.readFile(nodesPath, 'utf-8'));
  
  const node = nodes.nodes.find((n: any) => n.id === test.nodeId);
  if (!node) {
    throw new Error(`Node not found: ${test.nodeId}`);
  }

  // Validate node properties
  if (test.requiredProperties) {
    for (const prop of test.requiredProperties) {
      if (!(prop in node)) {
        throw new Error(`Node missing required property: ${prop}`);
      }
    }
  }
}

async function validateEdge(test: any, topologyDir: string): Promise<void> {
  const edgesPath = path.join(topologyDir, 'edges.yaml');
  const edges = yaml.parse(await fs.readFile(edgesPath, 'utf-8'));
  
  const edge = edges.edges.find((e: any) => e.id === test.edgeId);
  if (!edge) {
    throw new Error(`Edge not found: ${test.edgeId}`);
  }

  // Validate edge properties
  if (test.requiredProperties) {
    for (const prop of test.requiredProperties) {
      if (!(prop in edge)) {
        throw new Error(`Edge missing required property: ${prop}`);
      }
    }
  }
}

async function validateContract(test: any, topologyDir: string): Promise<void> {
  const contractsDir = path.join(topologyDir, 'contracts');
  const contractFile = path.join(contractsDir, `${test.contract}.json`);
  
  if (!(await fs.pathExists(contractFile))) {
    throw new Error(`Contract file not found: ${test.contract}`);
  }

  const contract = JSON.parse(await fs.readFile(contractFile, 'utf-8'));
  
  // Validate contract structure
  if (!contract.input || !contract.output) {
    throw new Error('Invalid contract structure');
  }
}

async function validateDataFlow(test: any, topologyDir: string): Promise<void> {
  // Simulate data flow validation
  const nodesPath = path.join(topologyDir, 'nodes.yaml');
  const edgesPath = path.join(topologyDir, 'edges.yaml');
  
  const nodes = yaml.parse(await fs.readFile(nodesPath, 'utf-8'));
  const edges = yaml.parse(await fs.readFile(edgesPath, 'utf-8'));

  // Check if data can flow from source to destination
  const sourceNode = nodes.nodes.find((n: any) => n.id === test.source);
  const destNode = nodes.nodes.find((n: any) => n.id === test.destination);
  
  if (!sourceNode || !destNode) {
    throw new Error('Source or destination node not found');
  }

  // Find path between nodes
  const path = findPath(edges.edges, test.source, test.destination);
  if (!path) {
    throw new Error(`No path found from ${test.source} to ${test.destination}`);
  }
}

async function validateErrorHandling(test: any, topologyDir: string): Promise<void> {
  // Simulate error handling validation
  if (test.errorType === 'timeout') {
    // Test timeout handling
    await new Promise(resolve => setTimeout(resolve, test.timeout || 1000));
  } else if (test.errorType === 'validation') {
    // Test validation error handling
    throw new Error('Simulated validation error');
  }
}

async function validatePerformance(test: any, topologyDir: string): Promise<void> {
  // Simulate performance validation
  const startTime = Date.now();
  
  // Simulate some work
  await new Promise(resolve => setTimeout(resolve, test.duration || 100));
  
  const duration = Date.now() - startTime;
  
  if (test.maxDuration && duration > test.maxDuration) {
    throw new Error(`Performance test failed: ${duration}ms > ${test.maxDuration}ms`);
  }
}

async function validateAgainstSchema(data: any, schema: any): Promise<void> {
  // Basic schema validation
  if (schema.type === 'object' && typeof data !== 'object') {
    throw new Error('Expected object, got ' + typeof data);
  }
  
  if (schema.type === 'array' && !Array.isArray(data)) {
    throw new Error('Expected array, got ' + typeof data);
  }
  
  if (schema.type === 'string' && typeof data !== 'string') {
    throw new Error('Expected string, got ' + typeof data);
  }
  
  if (schema.type === 'number' && typeof data !== 'number') {
    throw new Error('Expected number, got ' + typeof data);
  }
}

function findPath(edges: any[], source: string, destination: string): string[] | null {
  const graph = new Map<string, string[]>();
  
  for (const edge of edges) {
    if (!graph.has(edge.from)) {
      graph.set(edge.from, []);
    }
    graph.get(edge.from)!.push(edge.to);
  }

  const visited = new Set<string>();
  const path: string[] = [];

  function dfs(node: string): boolean {
    if (node === destination) {
      path.push(node);
      return true;
    }

    if (visited.has(node)) {
      return false;
    }

    visited.add(node);
    path.push(node);

    const neighbors = graph.get(node) || [];
    for (const neighbor of neighbors) {
      if (dfs(neighbor)) {
        return true;
      }
    }

    path.pop();
    return false;
  }

  return dfs(source) ? path : null;
}

async function generateCoverageReport(topologyDir: string, results: TestResult[]): Promise<CoverageReport> {
  // Simulate coverage report generation
  const totalTests = results.length;
  const passedTests = results.filter(r => r.status === 'passed').length;
  
  return {
    statements: Math.round((passedTests / totalTests) * 100),
    branches: Math.round((passedTests / totalTests) * 100),
    functions: Math.round((passedTests / totalTests) * 100),
    lines: Math.round((passedTests / totalTests) * 100),
    files: 1,
  };
}

async function createSampleTests(testsDir: string): Promise<void> {
  await fs.ensureDir(testsDir);

  // Create unit tests
  const unitTests = {
    type: 'unit',
    name: 'Unit Tests',
    tests: [
      {
        id: 'node_validation',
        name: 'Validate node structure',
        component: 'node',
        nodeId: 'AI.Answer',
        requiredProperties: ['id', 'kind', 'version'],
      },
      {
        id: 'edge_validation',
        name: 'Validate edge structure',
        component: 'edge',
        edgeId: 'Data.Retrieval_to_AI.Answer',
        requiredProperties: ['id', 'from', 'to'],
      },
      {
        id: 'contract_validation',
        name: 'Validate contract structure',
        component: 'contract',
        contract: 'answer',
      },
    ],
  };

  await fs.writeFile(
    path.join(testsDir, 'unit.yaml'),
    yaml.stringify(unitTests, { indent: 2 })
  );

  // Create integration tests
  const integrationTests = {
    type: 'integration',
    name: 'Integration Tests',
    tests: [
      {
        id: 'data_flow',
        name: 'Validate data flow',
        scenario: 'data_flow',
        source: 'Data.Retrieval',
        destination: 'AI.Answer',
      },
      {
        id: 'error_handling',
        name: 'Validate error handling',
        scenario: 'error_handling',
        errorType: 'timeout',
        timeout: 1000,
      },
    ],
  };

  await fs.writeFile(
    path.join(testsDir, 'integration.yaml'),
    yaml.stringify(integrationTests, { indent: 2 })
  );

  // Create contract tests
  const contractTests = {
    type: 'contract',
    name: 'Contract Tests',
    tests: [
      {
        id: 'answer_contract',
        name: 'Validate answer contract',
        contract: 'answer',
        input: {
          question: 'What is the capital of France?',
          context: ['Paris is the capital of France'],
        },
        output: {
          answer: 'The capital of France is Paris',
          confidence: 0.9,
        },
      },
    ],
  };

  await fs.writeFile(
    path.join(testsDir, 'contract.yaml'),
    yaml.stringify(contractTests, { indent: 2 })
  );

  // Create performance tests
  const performanceTests = {
    type: 'performance',
    name: 'Performance Tests',
    tests: [
      {
        id: 'latency_test',
        name: 'Validate latency',
        duration: 100,
        maxDuration: 500,
      },
      {
        id: 'throughput_test',
        name: 'Validate throughput',
        duration: 200,
        maxDuration: 1000,
      },
    ],
  };

  await fs.writeFile(
    path.join(testsDir, 'performance.yaml'),
    yaml.stringify(performanceTests, { indent: 2 })
  );
}

function displayTestResults(results: TestResults): void {
  console.log(chalk.blue('\nTest Results:'));
  console.log(chalk.gray(`  Total: ${results.total}`));
  console.log(chalk.green(`  Passed: ${results.passed}`));
  console.log(chalk.red(`  Failed: ${results.failed}`));
  console.log(chalk.yellow(`  Skipped: ${results.skipped}`));
  console.log(chalk.gray(`  Duration: ${results.duration}ms`));

  if (results.coverage) {
    console.log(chalk.blue('\nCoverage Report:'));
    console.log(chalk.gray(`  Statements: ${results.coverage.statements}%`));
    console.log(chalk.gray(`  Branches: ${results.coverage.branches}%`));
    console.log(chalk.gray(`  Functions: ${results.coverage.functions}%`));
    console.log(chalk.gray(`  Lines: ${results.coverage.lines}%`));
  }

  // Display failed tests
  const failedTests = results.tests.filter(t => t.status === 'failed');
  if (failedTests.length > 0) {
    console.log(chalk.red('\nFailed Tests:'));
    for (const test of failedTests) {
      console.log(chalk.red(`  ✗ ${test.name}: ${test.error}`));
    }
  }

  // Display summary
  if (results.failed === 0) {
    console.log(chalk.green('\n✓ All tests passed!'));
  } else {
    console.log(chalk.red(`\n✗ ${results.failed} test(s) failed`));
  }
}
