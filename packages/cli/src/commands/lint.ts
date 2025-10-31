import { Command } from 'commander';
import chalk from 'chalk';
import fs from 'fs-extra';
import path from 'path';
import yaml from 'yaml';
import Ajv from 'ajv';
import addFormats from 'ajv-formats';

export const lintCommand = new Command('lint')
  .description('Lint and validate topology pack')
  .option('-d, --pack-dir <dir>', 'Topology pack directory', './topology')
  .option('--strict', 'Enable strict validation')
  .option('--fix', 'Auto-fix issues where possible')
  .action(async options => {
    console.log(chalk.blue('Linting topology pack...'));

    try {
      const { packDir, strict, fix } = options;
      const topologyPath = path.resolve(packDir);

      if (!(await fs.pathExists(topologyPath))) {
        throw new Error(`Topology directory does not exist: ${topologyPath}`);
      }

      const results = await lintTopologyPack(topologyPath, { strict, fix });

      if (results.errors.length === 0) {
        console.log(chalk.green('✓ Topology pack is valid'));
        displaySummary(results);
        if (results.warnings.length > 0) {
          displayWarnings(results.warnings);
        }
      } else {
        console.log(chalk.red('✗ Topology pack has validation errors'));
        displayErrors(results.errors);
        if (results.warnings.length > 0) {
          displayWarnings(results.warnings);
        }
        process.exit(1);
      }
    } catch (error) {
      console.log(chalk.red('✗ Linting failed:'));
      console.error(
        chalk.red(error instanceof Error ? error.message : String(error))
      );
      process.exit(1);
    }
  });

interface LintResult {
  nodes: number;
  edges: number;
  contracts: number;
  errors: LintError[];
  warnings: LintWarning[];
}

interface LintError {
  file: string;
  message: string;
  line?: number;
  column?: number;
  severity: 'error' | 'warning';
}

interface LintWarning {
  file: string;
  message: string;
  line?: number;
  column?: number;
}

async function lintTopologyPack(
  topologyDir: string,
  options: { strict: boolean; fix: boolean }
): Promise<LintResult> {
  const errors: LintError[] = [];
  const warnings: LintWarning[] = [];
  const ajv = new Ajv({ allErrors: true });
  addFormats(ajv);

  // Check required files
  const requiredFiles = ['nodes.yaml', 'edges.yaml', 'guardrails.yaml'];
  for (const file of requiredFiles) {
    const filePath = path.join(topologyDir, file);
    if (!(await fs.pathExists(filePath))) {
      errors.push({
        file,
        message: `Required file missing: ${file}`,
        severity: 'error',
      });
    }
  }

  // Load and validate topology data
  let topologyData: any = {};
  const nodeIds = new Set<string>();
  const edgeIds = new Set<string>();
  const contractNames = new Set<string>();

  // Validate nodes.yaml
  const nodesPath = path.join(topologyDir, 'nodes.yaml');
  if (await fs.pathExists(nodesPath)) {
    try {
      const content = await fs.readFile(nodesPath, 'utf-8');
      const nodes = yaml.parse(content);
      topologyData.nodes = nodes;

      if (!nodes || !Array.isArray(nodes.nodes)) {
        errors.push({
          file: 'nodes.yaml',
          message: 'Invalid nodes structure: expected array of nodes',
          severity: 'error',
        });
      } else {
        // Validate each node
        for (let i = 0; i < nodes.nodes.length; i++) {
          const node = nodes.nodes[i];
          const nodeLine = i + 1;
          
          // Required fields validation
          if (!node.id) {
            errors.push({
              file: 'nodes.yaml',
              message: `Node ${i}: missing required field 'id'`,
              line: nodeLine,
              severity: 'error',
            });
          } else {
            if (nodeIds.has(node.id)) {
              errors.push({
                file: 'nodes.yaml',
                message: `Duplicate node ID: ${node.id}`,
                line: nodeLine,
                severity: 'error',
              });
            }
            nodeIds.add(node.id);
          }

          if (!node.kind) {
            errors.push({
              file: 'nodes.yaml',
              message: `Node ${i}: missing required field 'kind'`,
              line: nodeLine,
              severity: 'error',
            });
          } else if (!['ux', 'ai', 'data', 'ops'].includes(node.kind)) {
            errors.push({
              file: 'nodes.yaml',
              message: `Node ${i}: invalid kind '${node.kind}'. Must be one of: ux, ai, data, ops`,
              line: nodeLine,
              severity: 'error',
            });
          }

          // Validate execution profile
          if (node.execution_profile) {
            const profile = node.execution_profile;
            if (profile.temperature !== undefined && (profile.temperature < 0 || profile.temperature > 2)) {
              errors.push({
                file: 'nodes.yaml',
                message: `Node ${i}: temperature must be between 0 and 2`,
                line: nodeLine,
                severity: 'error',
              });
            }
            if (profile.top_p !== undefined && (profile.top_p < 0 || profile.top_p > 1)) {
              errors.push({
                file: 'nodes.yaml',
                message: `Node ${i}: top_p must be between 0 and 1`,
                line: nodeLine,
                severity: 'error',
              });
            }
            if (profile.max_tokens !== undefined && profile.max_tokens <= 0) {
              errors.push({
                file: 'nodes.yaml',
                message: `Node ${i}: max_tokens must be positive`,
                line: nodeLine,
                severity: 'error',
              });
            }
          }

          // Validate SLOs
          if (node.slos) {
            const slos = node.slos;
            const sloFields = ['schema_pass_rate', 'drift_threshold', 'latency_budget', 'context_precision', 'consistency_rate', 'cost_budget'];
            for (const field of sloFields) {
              if (slos[field] && typeof slos[field] !== 'string') {
                warnings.push({
                  file: 'nodes.yaml',
                  message: `Node ${i}: SLO field '${field}' should be a string with units`,
                  line: nodeLine,
                });
              }
            }
          }

          // Check for unused contracts
          if (node.scope?.contracts) {
            for (const contractName of node.scope.contracts) {
              if (!contractNames.has(contractName)) {
                warnings.push({
                  file: 'nodes.yaml',
                  message: `Node ${i}: references undefined contract '${contractName}'`,
                  line: nodeLine,
                });
              }
            }
          }
        }
      }
    } catch (error) {
      errors.push({
        file: 'nodes.yaml',
        message: `YAML parsing error: ${error instanceof Error ? error.message : String(error)}`,
        severity: 'error',
      });
    }
  }

  // Validate edges.yaml
  const edgesPath = path.join(topologyDir, 'edges.yaml');
  if (await fs.pathExists(edgesPath)) {
    try {
      const content = await fs.readFile(edgesPath, 'utf-8');
      const edges = yaml.parse(content);
      topologyData.edges = edges;

      if (!edges || !Array.isArray(edges.edges)) {
        errors.push({
          file: 'edges.yaml',
          message: 'Invalid edges structure: expected array of edges',
          severity: 'error',
        });
      } else {
        // Validate each edge
        for (let i = 0; i < edges.edges.length; i++) {
          const edge = edges.edges[i];
          const edgeLine = i + 1;
          
          // Required fields validation
          if (!edge.id) {
            errors.push({
              file: 'edges.yaml',
              message: `Edge ${i}: missing required field 'id'`,
              line: edgeLine,
              severity: 'error',
            });
          } else {
            if (edgeIds.has(edge.id)) {
              errors.push({
                file: 'edges.yaml',
                message: `Duplicate edge ID: ${edge.id}`,
                line: edgeLine,
                severity: 'error',
              });
            }
            edgeIds.add(edge.id);
          }

          if (!edge.from) {
            errors.push({
              file: 'edges.yaml',
              message: `Edge ${i}: missing required field 'from'`,
              line: edgeLine,
              severity: 'error',
            });
          } else if (!nodeIds.has(edge.from)) {
            errors.push({
              file: 'edges.yaml',
              message: `Edge ${i}: references undefined node '${edge.from}'`,
              line: edgeLine,
              severity: 'error',
            });
          }

          if (!edge.to) {
            errors.push({
              file: 'edges.yaml',
              message: `Edge ${i}: missing required field 'to'`,
              line: edgeLine,
              severity: 'error',
            });
          } else if (!nodeIds.has(edge.to)) {
            errors.push({
              file: 'edges.yaml',
              message: `Edge ${i}: references undefined node '${edge.to}'`,
              line: edgeLine,
              severity: 'error',
            });
          }

          // Validate edge properties
          if (edge.timeout_ms !== undefined && edge.timeout_ms <= 0) {
            errors.push({
              file: 'edges.yaml',
              message: `Edge ${i}: timeout_ms must be positive`,
              line: edgeLine,
              severity: 'error',
            });
          }

          if (edge.max_retries !== undefined && edge.max_retries < 0) {
            errors.push({
              file: 'edges.yaml',
              message: `Edge ${i}: max_retries must be non-negative`,
              line: edgeLine,
              severity: 'error',
            });
          }

          // Check for self-loops
          if (edge.from === edge.to) {
            warnings.push({
              file: 'edges.yaml',
              message: `Edge ${i}: self-loop detected (${edge.from} -> ${edge.to})`,
              line: edgeLine,
            });
          }

          // Check for unused contracts in edge
          if (edge.contracts) {
            for (const contractName of edge.contracts) {
              if (!contractNames.has(contractName)) {
                warnings.push({
                  file: 'edges.yaml',
                  message: `Edge ${i}: references undefined contract '${contractName}'`,
                  line: edgeLine,
                });
              }
            }
          }
        }
      }
    } catch (error) {
      errors.push({
        file: 'edges.yaml',
        message: `YAML parsing error: ${error instanceof Error ? error.message : String(error)}`,
        severity: 'error',
      });
    }
  }

  // Validate contracts
  const contractsDir = path.join(topologyDir, 'contracts');
  let contractCount = 0;
  if (await fs.pathExists(contractsDir)) {
    const contractFiles = await fs.readdir(contractsDir);
    for (const file of contractFiles) {
      if (file.endsWith('.yaml') || file.endsWith('.yml') || file.endsWith('.json')) {
        contractCount++;
        const contractPath = path.join(contractsDir, file);
        try {
          const content = await fs.readFile(contractPath, 'utf-8');
          let contract: any;
          
          if (file.endsWith('.json')) {
            contract = JSON.parse(content);
          } else {
            contract = yaml.parse(content);
          }

          // Basic contract validation
          if (!contract.name) {
            errors.push({
              file: `contracts/${file}`,
              message: 'Contract must have a name',
              severity: 'error',
            });
          } else {
            contractNames.add(contract.name);
          }

          if (!contract.input_schema && !contract.input) {
            errors.push({
              file: `contracts/${file}`,
              message: 'Contract must have input schema',
              severity: 'error',
            });
          }

          if (!contract.output_schema && !contract.output) {
            errors.push({
              file: `contracts/${file}`,
              message: 'Contract must have output schema',
              severity: 'error',
            });
          }

          // Validate JSON Schema if present
          const inputSchema = contract.input_schema || contract.input;
          const outputSchema = contract.output_schema || contract.output;
          
          if (inputSchema && ajv) {
            try {
              ajv.compile(inputSchema);
            } catch (error) {
              errors.push({
                file: `contracts/${file}`,
                message: `Invalid input schema: ${error instanceof Error ? error.message : String(error)}`,
                severity: 'error',
              });
            }
          }

          if (outputSchema && ajv) {
            try {
              ajv.compile(outputSchema);
            } catch (error) {
              errors.push({
                file: `contracts/${file}`,
                message: `Invalid output schema: ${error instanceof Error ? error.message : String(error)}`,
                severity: 'error',
              });
            }
          }
        } catch (error) {
          errors.push({
            file: `contracts/${file}`,
            message: `Parsing error: ${error instanceof Error ? error.message : String(error)}`,
            severity: 'error',
          });
        }
      }
    }
  }

  // Check for DAG cycles
  if (topologyData.edges && topologyData.edges.edges) {
    const cycleResult = detectCycles(topologyData.edges.edges, nodeIds);
    if (cycleResult.hasCycle) {
      errors.push({
        file: 'edges.yaml',
        message: `Cycle detected in topology: ${cycleResult.cycle.join(' -> ')}`,
        severity: 'error',
      });
    }
  }

  // Check for orphaned nodes
  if (topologyData.edges && topologyData.edges.edges) {
    const connectedNodes = new Set<string>();
    for (const edge of topologyData.edges.edges) {
      if (edge.from) connectedNodes.add(edge.from);
      if (edge.to) connectedNodes.add(edge.to);
    }
    
    for (const nodeId of nodeIds) {
      if (!connectedNodes.has(nodeId)) {
        warnings.push({
          file: 'nodes.yaml',
          message: `Node '${nodeId}' is not connected to any edges`,
          severity: 'warning',
        });
      }
    }
  }

  // Count nodes and edges
  let nodeCount = 0;
  let edgeCount = 0;

  try {
    if (await fs.pathExists(nodesPath)) {
      const content = await fs.readFile(nodesPath, 'utf-8');
      const nodes = yaml.parse(content);
      nodeCount = Array.isArray(nodes.nodes) ? nodes.nodes.length : 0;
    }
  } catch {
    // Error already reported above
  }

  try {
    if (await fs.pathExists(edgesPath)) {
      const content = await fs.readFile(edgesPath, 'utf-8');
      const edges = yaml.parse(content);
      edgeCount = Array.isArray(edges.edges) ? edges.edges.length : 0;
    }
  } catch {
    // Error already reported above
  }

  return {
    nodes: nodeCount,
    edges: edgeCount,
    contracts: contractCount,
    errors,
    warnings,
  };
}

function detectCycles(edges: any[], nodeIds: Set<string>): { hasCycle: boolean; cycle: string[] } {
  const graph = new Map<string, string[]>();
  const visited = new Set<string>();
  const recStack = new Set<string>();
  
  // Build adjacency list
  for (const nodeId of nodeIds) {
    graph.set(nodeId, []);
  }
  
  for (const edge of edges) {
    if (edge.from && edge.to && graph.has(edge.from)) {
      graph.get(edge.from)!.push(edge.to);
    }
  }
  
  function hasCycleDFS(node: string, path: string[]): boolean {
    if (recStack.has(node)) {
      const cycleStart = path.indexOf(node);
      return true;
    }
    
    if (visited.has(node)) {
      return false;
    }
    
    visited.add(node);
    recStack.add(node);
    path.push(node);
    
    const neighbors = graph.get(node) || [];
    for (const neighbor of neighbors) {
      if (hasCycleDFS(neighbor, [...path])) {
        return true;
      }
    }
    
    recStack.delete(node);
    return false;
  }
  
  for (const nodeId of nodeIds) {
    if (!visited.has(nodeId)) {
      if (hasCycleDFS(nodeId, [])) {
        return { hasCycle: true, cycle: [] }; // Cycle detected but path not tracked
      }
    }
  }
  
  return { hasCycle: false, cycle: [] };
}

function displaySummary(result: LintResult): void {
  console.log(chalk.blue('\nTopology Pack Summary:'));
  console.log(chalk.gray(`  Nodes: ${result.nodes}`));
  console.log(chalk.gray(`  Edges: ${result.edges}`));
  console.log(chalk.gray(`  Contracts: ${result.contracts}`));
  
  if (result.warnings.length > 0) {
    console.log(chalk.yellow(`  Warnings: ${result.warnings.length}`));
  }
}

function displayErrors(errors: LintError[]): void {
  console.log(chalk.red('\nValidation Errors:'));
  for (const error of errors) {
    const location = error.line
      ? `:${error.line}${error.column ? `:${error.column}` : ''}`
      : '';
    const severity = error.severity === 'error' ? chalk.red : chalk.yellow;
    console.log(severity(`  ${error.file}${location}: ${error.message}`));
  }
}

function displayWarnings(warnings: LintWarning[]): void {
  if (warnings.length === 0) return;
  
  console.log(chalk.yellow('\nWarnings:'));
  for (const warning of warnings) {
    const location = warning.line
      ? `:${warning.line}${warning.column ? `:${warning.column}` : ''}`
      : '';
    console.log(chalk.yellow(`  ${warning.file}${location}: ${warning.message}`));
  }
}
