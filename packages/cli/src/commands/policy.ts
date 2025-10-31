import { Command } from 'commander';
import chalk from 'chalk';
import fs from 'fs-extra';
import path from 'path';
import yaml from 'yaml';

export const policyCommand = new Command('policy')
  .description('Policy validation and management')
  .option('-d, --pack-dir <dir>', 'Topology pack directory', './topology')
  .option('-p, --policy-file <file>', 'Policy file to validate', './topology/policies.rego')
  .option('--validate', 'Validate policy syntax and logic')
  .option('--test', 'Run policy tests')
  .option('--generate', 'Generate policy templates')
  .action(async options => {
    console.log(chalk.blue('Policy management...'));

    try {
      const { packDir, policyFile, validate, test, generate } = options;
      const topologyPath = path.resolve(packDir);
      const policyPath = path.resolve(policyFile);

      if (generate) {
        await generatePolicyTemplates(topologyPath);
        console.log(chalk.green('✓ Policy templates generated'));
        return;
      }

      if (!(await fs.pathExists(topologyPath))) {
        throw new Error(`Topology directory does not exist: ${topologyPath}`);
      }

      if (validate) {
        const results = await validatePolicies(topologyPath, policyPath);
        if (results.valid) {
          console.log(chalk.green('✓ All policies are valid'));
          displayPolicySummary(results);
        } else {
          console.log(chalk.red('✗ Policy validation failed'));
          displayPolicyErrors(results);
          process.exit(1);
        }
      }

      if (test) {
        const results = await runPolicyTests(topologyPath, policyPath);
        if (results.passed === results.total) {
          console.log(chalk.green(`✓ All ${results.total} policy tests passed`));
        } else {
          console.log(chalk.red(`✗ ${results.failed} of ${results.total} policy tests failed`));
          displayPolicyTestResults(results);
          process.exit(1);
        }
      }

    } catch (error) {
      console.log(chalk.red('✗ Policy operation failed:'));
      console.error(
        chalk.red(error instanceof Error ? error.message : String(error))
      );
      process.exit(1);
    }
  });

interface PolicyValidationResult {
  valid: boolean;
  policies: PolicyInfo[];
  errors: PolicyError[];
  warnings: PolicyWarning[];
}

interface PolicyInfo {
  name: string;
  type: string;
  description: string;
  rules: number;
  complexity: 'low' | 'medium' | 'high';
}

interface PolicyError {
  policy: string;
  line: number;
  message: string;
  severity: 'error' | 'warning';
}

interface PolicyWarning {
  policy: string;
  message: string;
  suggestion: string;
}

interface PolicyTestResult {
  total: number;
  passed: number;
  failed: number;
  tests: Array<{
    name: string;
    passed: boolean;
    error?: string;
  }>;
}

async function validatePolicies(
  topologyDir: string,
  policyFile: string
): Promise<PolicyValidationResult> {
  const policies: PolicyInfo[] = [];
  const errors: PolicyError[] = [];
  const warnings: PolicyWarning[] = [];

  // Check if policy file exists
  if (!(await fs.pathExists(policyFile))) {
    errors.push({
      policy: 'main',
      line: 0,
      message: 'Policy file not found',
      severity: 'error',
    });
    return { valid: false, policies, errors, warnings };
  }

  try {
    const policyContent = await fs.readFile(policyFile, 'utf-8');
    
    // Basic Rego syntax validation
    const regoValidation = validateRegoSyntax(policyContent);
    if (!regoValidation.valid) {
      errors.push(...regoValidation.errors);
      return { valid: false, policies, errors, warnings };
    }

    // Extract policy information
    const policyInfo = extractPolicyInfo(policyContent);
    policies.push(...policyInfo);

    // Validate policy against topology
    const topologyValidation = await validatePoliciesAgainstTopology(
      topologyDir,
      policyContent
    );
    errors.push(...topologyValidation.errors);
    warnings.push(...topologyValidation.warnings);

  } catch (error) {
    errors.push({
      policy: 'main',
      line: 0,
      message: `Failed to read policy file: ${error instanceof Error ? error.message : String(error)}`,
      severity: 'error',
    });
  }

  return {
    valid: errors.length === 0,
    policies,
    errors,
    warnings,
  };
}

function validateRegoSyntax(content: string): { valid: boolean; errors: PolicyError[] } {
  const errors: PolicyError[] = [];
  const lines = content.split('\n');

  // Basic Rego syntax checks
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    const lineNum = i + 1;

    // Check for common Rego syntax issues
    if (line.includes('package') && !line.startsWith('package ')) {
      errors.push({
        policy: 'main',
        line: lineNum,
        message: 'Package declaration must be at start of line',
        severity: 'error',
      });
    }

    if (line.includes('import') && !line.startsWith('import ')) {
      errors.push({
        policy: 'main',
        line: lineNum,
        message: 'Import statement must be at start of line',
        severity: 'error',
      });
    }

    // Check for balanced braces
    const openBraces = (line.match(/\{/g) || []).length;
    const closeBraces = (line.match(/\}/g) || []).length;
    if (openBraces !== closeBraces) {
      errors.push({
        policy: 'main',
        line: lineNum,
        message: 'Unbalanced braces in policy rule',
        severity: 'error',
      });
    }
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

function extractPolicyInfo(content: string): PolicyInfo[] {
  const policies: PolicyInfo[] = [];
  const lines = content.split('\n');

  let currentPolicy: Partial<PolicyInfo> = {};
  let ruleCount = 0;

  for (const line of lines) {
    const trimmed = line.trim();

    // Detect policy rules
    if (trimmed.includes('=') && !trimmed.startsWith('#')) {
      ruleCount++;
    }

    // Detect policy definitions
    if (trimmed.startsWith('policy_')) {
      if (currentPolicy.name) {
        policies.push({
          name: currentPolicy.name,
          type: currentPolicy.type || 'unknown',
          description: currentPolicy.description || '',
          rules: ruleCount,
          complexity: ruleCount < 5 ? 'low' : ruleCount < 15 ? 'medium' : 'high',
        });
      }

      currentPolicy = {
        name: trimmed.split('(')[0],
        type: 'policy',
        description: '',
      };
      ruleCount = 0;
    }
  }

  // Add the last policy
  if (currentPolicy.name) {
    policies.push({
      name: currentPolicy.name,
      type: currentPolicy.type || 'unknown',
      description: currentPolicy.description || '',
      rules: ruleCount,
      complexity: ruleCount < 5 ? 'low' : ruleCount < 15 ? 'medium' : 'high',
    });
  }

  return policies;
}

async function validatePoliciesAgainstTopology(
  topologyDir: string,
  policyContent: string
): Promise<{ errors: PolicyError[]; warnings: PolicyWarning[] }> {
  const errors: PolicyError[] = [];
  const warnings: PolicyWarning[] = [];

  // Load topology configuration
  const nodesPath = path.join(topologyDir, 'nodes.yaml');
  const edgesPath = path.join(topologyDir, 'edges.yaml');

  if (!(await fs.pathExists(nodesPath)) || !(await fs.pathExists(edgesPath))) {
    errors.push({
      policy: 'main',
      line: 0,
      message: 'Cannot validate policies: topology configuration missing',
      severity: 'error',
    });
    return { errors, warnings };
  }

  const nodesContent = await fs.readFile(nodesPath, 'utf-8');
  const edgesContent = await fs.readFile(edgesPath, 'utf-8');

  const nodes = yaml.parse(nodesContent);
  const edges = yaml.parse(edgesContent);

  if (!nodes?.nodes || !edges?.edges) {
    errors.push({
      policy: 'main',
      line: 0,
      message: 'Invalid topology configuration',
      severity: 'error',
    });
    return { errors, warnings };
  }

  // Extract node and edge IDs from topology
  const nodeIds = nodes.nodes.map((n: any) => n.id);
  const edgeIds = edges.edges.map((e: any) => e.id);

  // Check if policy references exist in topology
  const policyLines = policyContent.split('\n');
  for (let i = 0; i < policyLines.length; i++) {
    const line = policyLines[i];
    const lineNum = i + 1;

    // Check for node references
    for (const nodeId of nodeIds) {
      if (line.includes(nodeId) && !nodeIds.includes(nodeId)) {
        warnings.push({
          policy: 'main',
          message: `Policy references unknown node: ${nodeId}`,
          suggestion: 'Verify node ID exists in topology',
        });
      }
    }

    // Check for edge references
    for (const edgeId of edgeIds) {
      if (line.includes(edgeId) && !edgeIds.includes(edgeId)) {
        warnings.push({
          policy: 'main',
          message: `Policy references unknown edge: ${edgeId}`,
          suggestion: 'Verify edge ID exists in topology',
        });
      }
    }
  }

  return { errors, warnings };
}

async function runPolicyTests(
  topologyDir: string,
  policyFile: string
): Promise<PolicyTestResult> {
  const tests: Array<{ name: string; passed: boolean; error?: string }> = [];

  // Basic policy tests
  tests.push({
    name: 'Policy file exists',
    passed: await fs.pathExists(policyFile),
    error: await fs.pathExists(policyFile) ? undefined : 'Policy file not found',
  });

  if (await fs.pathExists(policyFile)) {
    const policyContent = await fs.readFile(policyFile, 'utf-8');

    tests.push({
      name: 'Policy syntax valid',
      passed: validateRegoSyntax(policyContent).valid,
      error: validateRegoSyntax(policyContent).valid ? undefined : 'Invalid Rego syntax',
    });

    tests.push({
      name: 'Policy has rules',
      passed: policyContent.includes('=') && !policyContent.trim().startsWith('#'),
      error: 'Policy file appears to be empty or contains only comments',
    });

    tests.push({
      name: 'Policy references topology',
      passed: await validatePoliciesAgainstTopology(topologyDir, policyContent).then(r => r.errors.length === 0),
      error: 'Policy validation against topology failed',
    });
  }

  return {
    total: tests.length,
    passed: tests.filter(t => t.passed).length,
    failed: tests.filter(t => !t.passed).length,
    tests,
  };
}

async function generatePolicyTemplates(topologyDir: string): Promise<void> {
  const policiesDir = path.join(topologyDir, 'policies');
  await fs.ensureDir(policiesDir);

  // Generate basic policy template
  const basicPolicy = `package topokit.policies

# Basic topology policies for TopoKit
# Generated by topokit-cli policy --generate

# Allow all operations by default
default allow = true

# Policy for node execution
policy_node_execution[node_id] {
    # Add your node execution policies here
    # Example: node_id == "AI.Answer"
}

# Policy for edge traversal
policy_edge_traversal[edge_id] {
    # Add your edge traversal policies here
    # Example: edge_id == "Data.Retrieval_to_AI.Answer"
}

# Policy for contract validation
policy_contract_validation[contract_name] {
    # Add your contract validation policies here
    # Example: contract_name == "answer"
}

# Policy for resource access
policy_resource_access[resource] {
    # Add your resource access policies here
    # Example: resource == "database"
}

# Policy for data privacy
policy_data_privacy[data_type] {
    # Add your data privacy policies here
    # Example: data_type == "pii"
}
`;

  await fs.writeFile(path.join(policiesDir, 'main.rego'), basicPolicy);

  // Generate test policy
  const testPolicy = `package topokit.policies.test

# Test policies for TopoKit
# Generated by topokit-cli policy --generate

test_allow_all {
    allow == true
}

test_node_execution {
    policy_node_execution["AI.Answer"] == true
}

test_edge_traversal {
    policy_edge_traversal["Data.Retrieval_to_AI.Answer"] == true
}

test_contract_validation {
    policy_contract_validation["answer"] == true
}
`;

  await fs.writeFile(path.join(policiesDir, 'test.rego'), testPolicy);

  // Generate README
  const readme = `# TopoKit Policies

This directory contains Rego policies for TopoKit topology management.

## Files

- \`main.rego\` - Main policy definitions
- \`test.rego\` - Policy tests
- \`README.md\` - This file

## Usage

\`\`\`bash
# Validate policies
topokit-cli policy --validate

# Run policy tests
topokit-cli policy --test

# Generate new templates
topokit-cli policy --generate
\`\`\`

## Policy Structure

Policies are written in Rego and define rules for:

- Node execution permissions
- Edge traversal permissions
- Contract validation rules
- Resource access control
- Data privacy requirements

## Examples

See the generated \`main.rego\` file for example policy structures.
`;

  await fs.writeFile(path.join(policiesDir, 'README.md'), readme);
}

function displayPolicySummary(result: PolicyValidationResult): void {
  console.log(chalk.blue('\nPolicy Summary:'));
  console.log(chalk.gray(`  Policies: ${result.policies.length}`));
  console.log(chalk.gray(`  Errors: ${result.errors.length}`));
  console.log(chalk.gray(`  Warnings: ${result.warnings.length}`));

  if (result.policies.length > 0) {
    console.log(chalk.blue('\nPolicies:'));
    for (const policy of result.policies) {
      const complexityColor = policy.complexity === 'high' ? chalk.red : 
                            policy.complexity === 'medium' ? chalk.yellow : chalk.green;
      console.log(chalk.gray(`  ${policy.name} (${policy.type}) - ${complexityColor(policy.complexity)} complexity`));
    }
  }
}

function displayPolicyErrors(result: PolicyValidationResult): void {
  console.log(chalk.red('\nPolicy Errors:'));
  for (const error of result.errors) {
    const location = error.line > 0 ? `:${error.line}` : '';
    console.log(chalk.red(`  ${error.policy}${location}: ${error.message}`));
  }

  if (result.warnings.length > 0) {
    console.log(chalk.yellow('\nPolicy Warnings:'));
    for (const warning of result.warnings) {
      console.log(chalk.yellow(`  ${warning.policy}: ${warning.message}`));
      console.log(chalk.gray(`    Suggestion: ${warning.suggestion}`));
    }
  }
}

function displayPolicyTestResults(result: PolicyTestResult): void {
  console.log(chalk.red('\nFailed Policy Tests:'));
  for (const test of result.tests) {
    if (!test.passed) {
      console.log(chalk.red(`  ✗ ${test.name}: ${test.error}`));
    }
  }

  console.log(chalk.blue('\nPolicy Test Summary:'));
  console.log(chalk.gray(`  Total: ${result.total}`));
  console.log(chalk.green(`  Passed: ${result.passed}`));
  console.log(chalk.red(`  Failed: ${result.failed}`));
}
