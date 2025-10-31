import { Command } from 'commander';
import chalk from 'chalk';
import fs from 'fs-extra';
import path from 'path';
import yaml from 'yaml';

export const costCommand = new Command('cost')
  .description('Cost analysis and optimization for topology execution')
  .option('-d, --pack-dir <dir>', 'Topology pack directory', './topology')
  .option('-m, --model <model>', 'LLM model to analyze', 'gpt-4')
  .option('--tokens <tokens>', 'Estimated tokens per request', '1000')
  .option('--requests <requests>', 'Number of requests to analyze', '1000')
  .option('--optimize', 'Show optimization recommendations')
  .option('--budget <budget>', 'Budget limit in USD', '100')
  .action(async options => {
    console.log(chalk.blue('Analyzing topology costs...'));

    try {
      const { packDir, model, tokens, requests, optimize, budget } = options;
      const topologyPath = path.resolve(packDir);

      if (!(await fs.pathExists(topologyPath))) {
        throw new Error(`Topology directory does not exist: ${topologyPath}`);
      }

      const analysis = await analyzeTopologyCosts(topologyPath, {
        model,
        tokens: parseInt(tokens),
        requests: parseInt(requests),
        budget: parseFloat(budget),
      });

      displayCostAnalysis(analysis);

      if (optimize) {
        const optimizations = await generateOptimizationRecommendations(topologyPath, analysis);
        displayOptimizations(optimizations);
      }

    } catch (error) {
      console.log(chalk.red('✗ Cost analysis failed:'));
      console.error(
        chalk.red(error instanceof Error ? error.message : String(error))
      );
      process.exit(1);
    }
  });

interface CostAnalysis {
  totalCost: number;
  budget: number;
  withinBudget: boolean;
  breakdown: CostBreakdown;
  recommendations: string[];
  warnings: string[];
}

interface CostBreakdown {
  byNode: Record<string, NodeCost>;
  byModel: Record<string, ModelCost>;
  byOperation: Record<string, OperationCost>;
  total: {
    inputTokens: number;
    outputTokens: number;
    requests: number;
    cost: number;
  };
}

interface NodeCost {
  nodeId: string;
  kind: string;
  estimatedTokens: number;
  estimatedCost: number;
  percentage: number;
}

interface ModelCost {
  model: string;
  inputTokens: number;
  outputTokens: number;
  cost: number;
  percentage: number;
}

interface OperationCost {
  operation: string;
  tokens: number;
  cost: number;
  percentage: number;
}

interface OptimizationRecommendation {
  type: 'token_reduction' | 'model_switch' | 'caching' | 'batching' | 'architecture';
  priority: 'high' | 'medium' | 'low';
  description: string;
  potentialSavings: number;
  effort: 'low' | 'medium' | 'high';
  implementation: string[];
}

// Model pricing (as of 2024, in USD per 1K tokens)
const MODEL_PRICING = {
  'gpt-4': { input: 0.03, output: 0.06 },
  'gpt-4-turbo': { input: 0.01, output: 0.03 },
  'gpt-3.5-turbo': { input: 0.001, output: 0.002 },
  'claude-3-opus': { input: 0.015, output: 0.075 },
  'claude-3-sonnet': { input: 0.003, output: 0.015 },
  'claude-3-haiku': { input: 0.00025, output: 0.00125 },
  'llama-2-70b': { input: 0.0007, output: 0.0009 },
  'llama-2-13b': { input: 0.0002, output: 0.0002 },
  'llama-2-7b': { input: 0.0001, output: 0.0001 },
};

async function analyzeTopologyCosts(
  topologyDir: string,
  options: {
    model: string;
    tokens: number;
    requests: number;
    budget: number;
  }
): Promise<CostAnalysis> {
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

  // Calculate costs for each node
  const nodeCosts: Record<string, NodeCost> = {};
  const modelCosts: Record<string, ModelCost> = {};
  const operationCosts: Record<string, OperationCost> = {};

  let totalInputTokens = 0;
  let totalOutputTokens = 0;
  let totalCost = 0;

  for (const node of nodes.nodes) {
    const nodeCost = calculateNodeCost(node, options);
    nodeCosts[node.id] = nodeCost;

    // Aggregate by model
    const model = node.execution_profile?.model || options.model;
    if (!modelCosts[model]) {
      modelCosts[model] = {
        model,
        inputTokens: 0,
        outputTokens: 0,
        cost: 0,
        percentage: 0,
      };
    }
    modelCosts[model].inputTokens += nodeCost.estimatedTokens;
    modelCosts[model].cost += nodeCost.estimatedCost;

    // Aggregate by operation type
    const operation = node.kind;
    if (!operationCosts[operation]) {
      operationCosts[operation] = {
        operation,
        tokens: 0,
        cost: 0,
        percentage: 0,
      };
    }
    operationCosts[operation].tokens += nodeCost.estimatedTokens;
    operationCosts[operation].cost += nodeCost.estimatedCost;

    totalInputTokens += nodeCost.estimatedTokens;
    totalOutputTokens += nodeCost.estimatedTokens * 0.5; // Assume 50% output ratio
    totalCost += nodeCost.estimatedCost;
  }

  // Calculate percentages
  for (const nodeId in nodeCosts) {
    const nodeCost = nodeCosts[nodeId];
    if (nodeCost) {
      nodeCost.percentage = (nodeCost.estimatedCost / totalCost) * 100;
    }
  }

  for (const model in modelCosts) {
    const modelCost = modelCosts[model];
    if (modelCost) {
      modelCost.percentage = (modelCost.cost / totalCost) * 100;
    }
  }

  for (const operation in operationCosts) {
    const operationCost = operationCosts[operation];
    if (operationCost) {
      operationCost.percentage = (operationCost.cost / totalCost) * 100;
    }
  }

  const breakdown: CostBreakdown = {
    byNode: nodeCosts,
    byModel: modelCosts,
    byOperation: operationCosts,
    total: {
      inputTokens: totalInputTokens,
      outputTokens: totalOutputTokens,
      requests: options.requests,
      cost: totalCost,
    },
  };

  const recommendations: string[] = [];
  const warnings: string[] = [];

  // Generate recommendations
  if (totalCost > (options?.budget || 0)) {
    warnings.push(`Total cost ($${totalCost.toFixed(2)}) exceeds budget ($${options?.budget || 0})`);
    recommendations.push('Consider switching to a more cost-effective model');
    recommendations.push('Implement caching to reduce redundant API calls');
  }

  // Find most expensive nodes
  const sortedNodes = Object.values(nodeCosts).sort((a, b) => (b?.estimatedCost || 0) - (a?.estimatedCost || 0));
  if (sortedNodes.length > 0 && sortedNodes[0] && (sortedNodes[0].percentage || 0) > 50) {
    recommendations.push(`Node ${sortedNodes[0].nodeId} accounts for ${(sortedNodes[0].percentage || 0).toFixed(1)}% of costs`);
  }

  return {
    totalCost,
    budget: options.budget,
    withinBudget: totalCost <= options.budget,
    breakdown,
    recommendations,
    warnings,
  };
}

function calculateNodeCost(node: any, options: { model: string; tokens: number; requests: number }): NodeCost {
  const model = node.execution_profile?.model || options.model;
  const pricing = MODEL_PRICING[model as keyof typeof MODEL_PRICING] || MODEL_PRICING['gpt-4'];

  // Estimate tokens based on node type and configuration
  let estimatedTokens = options.tokens;

  // Adjust based on node kind
  switch (node.kind) {
    case 'ai':
      // AI nodes typically use more tokens
      estimatedTokens *= 1.5;
      break;
    case 'data':
      // Data nodes typically use fewer tokens
      estimatedTokens *= 0.3;
      break;
    case 'ux':
      // UX nodes use moderate tokens
      estimatedTokens *= 0.8;
      break;
    default:
      estimatedTokens *= 1.0;
  }

  // Adjust based on execution profile
  if (node.execution_profile?.max_tokens) {
    estimatedTokens = Math.min(estimatedTokens, node.execution_profile.max_tokens);
  }

  // Calculate cost
  const inputCost = (estimatedTokens * pricing.input) / 1000;
  const outputCost = (estimatedTokens * 0.5 * pricing.output) / 1000; // Assume 50% output
  const estimatedCost = (inputCost + outputCost) * (options?.requests || 1);

  return {
    nodeId: node.id,
    kind: node.kind,
    estimatedTokens: Math.round(estimatedTokens),
    estimatedCost: Math.round(estimatedCost * 100) / 100,
    percentage: 0, // Will be calculated later
  };
}

async function generateOptimizationRecommendations(
  _topologyDir: string,
  analysis: CostAnalysis
): Promise<OptimizationRecommendation[]> {
  const recommendations: OptimizationRecommendation[] = [];

  // Token reduction recommendations
  if (analysis.breakdown.total.inputTokens > 10000) {
    recommendations.push({
      type: 'token_reduction',
      priority: 'high',
      description: 'Reduce input token usage by optimizing prompts and context',
      potentialSavings: analysis.totalCost * 0.2,
      effort: 'medium',
      implementation: [
        'Review and optimize prompt templates',
        'Implement context compression',
        'Use more specific queries',
      ],
    });
  }

  // Model switching recommendations
  const mostExpensiveModel = Object.values(analysis.breakdown.byModel)
    .sort((a, b) => b.cost - a.cost)[0];

  if (mostExpensiveModel && mostExpensiveModel.cost > analysis.totalCost * 0.5) {
    recommendations.push({
      type: 'model_switch',
      priority: 'high',
      description: `Switch from ${mostExpensiveModel.model} to a more cost-effective model`,
      potentialSavings: mostExpensiveModel.cost * 0.6,
      effort: 'low',
      implementation: [
        'Update model configuration in nodes.yaml',
        'Test performance with new model',
        'Update contracts if needed',
      ],
    });
  }

  // Caching recommendations
  if (analysis.breakdown.total.requests > 100) {
    recommendations.push({
      type: 'caching',
      priority: 'medium',
      description: 'Implement caching to reduce redundant API calls',
      potentialSavings: analysis.totalCost * 0.3,
      effort: 'medium',
      implementation: [
        'Add caching configuration to nodes',
        'Implement cache invalidation strategy',
        'Monitor cache hit rates',
      ],
    });
  }

  // Batching recommendations
  if (analysis.breakdown.total.requests > 1000) {
    recommendations.push({
      type: 'batching',
      priority: 'medium',
      description: 'Implement request batching to reduce API overhead',
      potentialSavings: analysis.totalCost * 0.15,
      effort: 'high',
      implementation: [
        'Modify request handling logic',
        'Implement batch processing queue',
        'Update error handling for batches',
      ],
    });
  }

  // Architecture recommendations
  const expensiveNodes = Object.values(analysis.breakdown.byNode || {})
    .filter(node => node && node.percentage > 30)
    .sort((a, b) => (b?.percentage || 0) - (a?.percentage || 0));

  if (expensiveNodes.length > 0 && expensiveNodes[0]) {
    recommendations.push({
      type: 'architecture',
      priority: 'low',
      description: `Consider breaking down expensive node: ${expensiveNodes[0].nodeId}`,
      potentialSavings: (expensiveNodes[0].estimatedCost || 0) * 0.2,
      effort: 'high',
      implementation: [
        'Split node into smaller, focused components',
        'Implement parallel processing where possible',
        'Optimize data flow between nodes',
      ],
    });
  }

  return recommendations;
}

function displayCostAnalysis(analysis: CostAnalysis): void {
  console.log(chalk.blue('\nCost Analysis:'));
  console.log(chalk.gray(`  Total Cost: $${analysis.totalCost.toFixed(2)}`));
  console.log(chalk.gray(`  Budget: $${analysis.budget.toFixed(2)}`));
  console.log(chalk.gray(`  Within Budget: ${analysis.withinBudget ? chalk.green('Yes') : chalk.red('No')}`));

  // Display breakdown by node
  console.log(chalk.blue('\nCost Breakdown by Node:'));
  const sortedNodes = Object.values(analysis.breakdown.byNode)
    .sort((a, b) => b.estimatedCost - a.estimatedCost);

  for (const node of sortedNodes) {
    const costColor = node.estimatedCost > analysis.totalCost * 0.2 ? chalk.red : chalk.green;
    console.log(chalk.gray(`  ${node.nodeId} (${node.kind}): ${costColor(`$${node.estimatedCost.toFixed(2)}`)} (${node.percentage.toFixed(1)}%)`));
  }

  // Display breakdown by model
  console.log(chalk.blue('\nCost Breakdown by Model:'));
  const sortedModels = Object.values(analysis.breakdown.byModel)
    .sort((a, b) => b.cost - a.cost);

  for (const model of sortedModels) {
    console.log(chalk.gray(`  ${model.model}: $${model.cost.toFixed(2)} (${model.percentage.toFixed(1)}%)`));
  }

  // Display breakdown by operation
  console.log(chalk.blue('\nCost Breakdown by Operation:'));
  const sortedOperations = Object.values(analysis.breakdown.byOperation)
    .sort((a, b) => b.cost - a.cost);

  for (const operation of sortedOperations) {
    console.log(chalk.gray(`  ${operation.operation}: $${operation.cost.toFixed(2)} (${operation.percentage.toFixed(1)}%)`));
  }

  // Display warnings
  if (analysis.warnings.length > 0) {
    console.log(chalk.yellow('\nWarnings:'));
    for (const warning of analysis.warnings) {
      console.log(chalk.yellow(`  ⚠ ${warning}`));
    }
  }

  // Display recommendations
  if (analysis.recommendations.length > 0) {
    console.log(chalk.blue('\nRecommendations:'));
    for (const recommendation of analysis.recommendations) {
      console.log(chalk.gray(`  • ${recommendation}`));
    }
  }
}

function displayOptimizations(recommendations: OptimizationRecommendation[]): void {
  console.log(chalk.blue('\nOptimization Recommendations:'));

  for (const rec of recommendations) {
    const priorityColor = rec.priority === 'high' ? chalk.red : 
                         rec.priority === 'medium' ? chalk.yellow : chalk.green;
    const effortColor = rec.effort === 'high' ? chalk.red : 
                       rec.effort === 'medium' ? chalk.yellow : chalk.green;

    console.log(chalk.blue(`\n${rec.type.toUpperCase()}:`));
    console.log(chalk.gray(`  Description: ${rec.description}`));
    console.log(chalk.gray(`  Priority: ${priorityColor(rec.priority)}`));
    console.log(chalk.gray(`  Effort: ${effortColor(rec.effort)}`));
    console.log(chalk.gray(`  Potential Savings: $${rec.potentialSavings.toFixed(2)}`));
    
    console.log(chalk.gray('  Implementation:'));
    for (const step of rec.implementation) {
      console.log(chalk.gray(`    • ${step}`));
    }
  }
}
