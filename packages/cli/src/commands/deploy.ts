import { Command } from 'commander';
import chalk from 'chalk';
import fs from 'fs-extra';
import path from 'path';
import yaml from 'yaml';

export const deployCommand = new Command('deploy')
  .description('Deploy TopoKit applications to production with enterprise-grade monitoring, security, and reliability features')
  .option('-d, --pack-dir <dir>', 'Topology pack directory', './topology')
  .option('-e, --environment <env>', 'Deployment environment (development|staging|production)', 'production')
  .option('-n, --name <name>', 'Deployment name')
  .option('--id <id>', 'Deployment ID (for updates)')
  .option('--cpu-cores <cores>', 'CPU cores required', '4')
  .option('--memory-mb <mb>', 'Memory in MB required', '4096')
  .option('--storage-gb <gb>', 'Storage in GB required', '20')
  .option('--min-instances <instances>', 'Minimum number of instances', '2')
  .option('--max-instances <instances>', 'Maximum number of instances', '5')
  .option('--auto-scaling', 'Enable auto-scaling', true)
  .option('--no-auto-scaling', 'Disable auto-scaling')
  .option('--health-check-endpoint <endpoint>', 'Health check endpoint', '/health')
  .option('--metrics-port <port>', 'Metrics port', '8080')
  .option('--enable-ssl', 'Enable SSL/TLS', true)
  .option('--no-ssl', 'Disable SSL/TLS')
  .option('--alert-channels <channels>', 'Alert channels (comma-separated: slack,email,webhook)', 'slack,email')
  .option('--dry-run', 'Perform a dry run without actual deployment')
  .option('--validate-only', 'Only validate deployment configuration')
  .option('--force', 'Force deployment even if validation fails')
  .action(async options => {
    console.log(chalk.blue('Deploying TopoKit application...'));

    try {
      const {
        packDir,
        environment,
        name,
        id,
        cpuCores,
        memoryMb,
        storageGb,
        minInstances,
        maxInstances,
        autoScaling,
        healthCheckEndpoint,
        metricsPort,
        enableSsl,
        alertChannels,
        dryRun,
        validateOnly,
        force,
      } = options;

      const topologyPath = path.resolve(packDir);

      if (!(await fs.pathExists(topologyPath))) {
        throw new Error(`Topology directory does not exist: ${topologyPath}`);
      }

      // Validate environment
      const validEnvironments = ['development', 'staging', 'production'];
      if (!validEnvironments.includes(environment)) {
        throw new Error(`Invalid environment: ${environment}. Must be one of: ${validEnvironments.join(', ')}`);
      }

      // Load and validate topology
      console.log(chalk.gray('Loading topology...'));
      const topologyData = await loadTopology(topologyPath);
      
      if (!topologyData) {
        throw new Error('Failed to load topology');
      }

      // Generate deployment name if not provided
      const deploymentName = name || `${topologyData.name || 'topology'}-${environment}`;
      const deploymentId = id || `deployment-${Date.now()}`;

      // Create deployment configuration
      console.log(chalk.gray('Creating deployment configuration...'));
      const deploymentConfig = createDeploymentConfig({
        environment,
        cpuCores: parseInt(cpuCores),
        memoryMb: parseInt(memoryMb),
        storageGb: parseInt(storageGb),
        minInstances: parseInt(minInstances),
        maxInstances: parseInt(maxInstances),
        autoScaling,
        healthCheckEndpoint,
        metricsPort: parseInt(metricsPort),
        enableSsl,
        alertChannels: alertChannels.split(',').map((c: string) => c.trim()),
      });

      // Validate deployment configuration
      console.log(chalk.gray('Validating deployment configuration...'));
      const validationResult = validateDeploymentConfiguration(deploymentConfig, environment);

      if (!validationResult.valid && !force) {
        console.log(chalk.red('✗ Deployment validation failed:'));
        validationResult.errors.forEach((error: string) => {
          console.log(chalk.red(`  - ${error}`));
        });
        throw new Error('Deployment validation failed');
      }

      if (validationResult.warnings.length > 0) {
        console.log(chalk.yellow('⚠ Deployment warnings:'));
        validationResult.warnings.forEach((warning: string) => {
          console.log(chalk.yellow(`  - ${warning}`));
        });
      }

      if (validateOnly) {
        console.log(chalk.green('✓ Deployment configuration is valid!'));
        console.log(chalk.blue('\nDeployment Summary:'));
        displayDeploymentSummary({
          id: deploymentId,
          name: deploymentName,
          environment,
          config: deploymentConfig,
          topology: topologyData,
        });
        return;
      }

      if (dryRun) {
        console.log(chalk.blue('\n[DRY RUN] Deployment would be created with:'));
        displayDeploymentSummary({
          id: deploymentId,
          name: deploymentName,
          environment,
          config: deploymentConfig,
          topology: topologyData,
        });
        return;
      }

      // Create deployment
      console.log(chalk.gray('Creating deployment...'));
      const deployment = await createDeployment({
        id: deploymentId,
        name: deploymentName,
        topologyId: topologyData.name || 'topology',
        topologyVersion: topologyData.version || '1.0.0',
        config: deploymentConfig,
        createdBy: process.env.USER || 'deployment-user',
      });

      console.log(chalk.green('✓ Deployment created successfully!'));

      // Display deployment summary
      console.log(chalk.blue('\nDeployment Summary:'));
      displayDeploymentSummary({
        id: deployment.id,
        name: deployment.name,
        environment: deployment.config.environment,
        config: deployment.config,
        topology: topologyData,
      });

      // Display next steps
      console.log(chalk.blue('\nNext steps:'));
      console.log(chalk.gray(`1. Monitor deployment: topokit-cli monitor --deployment-id=${deployment.id}`));
      console.log(chalk.gray(`2. View dashboard: Access TopoView dashboard at http://localhost:${metricsPort}`));
      console.log(chalk.gray('3. Check health: Monitor health status and metrics'));

    } catch (error) {
      console.log(chalk.red('✗ Deployment failed:'));
      console.error(
        chalk.red(error instanceof Error ? error.message : String(error))
      );
      process.exit(1);
    }
  });

interface TopologyData {
  name?: string;
  version?: string;
  nodes?: any[];
  edges?: any[];
  contracts?: any[];
}

async function loadTopology(topologyPath: string): Promise<TopologyData | null> {
  try {
    const nodesPath = path.join(topologyPath, 'nodes.yaml');
    const edgesPath = path.join(topologyPath, 'edges.yaml');
    
    if (!(await fs.pathExists(nodesPath))) {
      throw new Error(`Nodes file not found: ${nodesPath}`);
    }

    const nodesContent = await fs.readFile(nodesPath, 'utf-8');
    const nodesData = yaml.parse(nodesContent);

    let edgesData = { edges: [] };
    if (await fs.pathExists(edgesPath)) {
      const edgesContent = await fs.readFile(edgesPath, 'utf-8');
      edgesData = yaml.parse(edgesContent);
    }

    // Try to extract name from directory or nodes
    const name = path.basename(topologyPath);

    return {
      name,
      version: '1.0.0',
      nodes: nodesData.nodes || [],
      edges: edgesData.edges || [],
      contracts: [],
    };
  } catch (error) {
    console.error(chalk.red(`Failed to load topology: ${error}`));
    return null;
  }
}

interface DeploymentConfigOptions {
  environment: string;
  cpuCores: number;
  memoryMb: number;
  storageGb: number;
  minInstances: number;
  maxInstances: number;
  autoScaling: boolean;
  healthCheckEndpoint: string;
  metricsPort: number;
  enableSsl: boolean;
  alertChannels: string[];
}

function createDeploymentConfig(options: DeploymentConfigOptions): any {
  return {
    environment: options.environment,
    resources: {
      cpu_cores: options.cpuCores,
      memory_mb: options.memoryMb,
      storage_gb: options.storageGb,
      max_instances: options.maxInstances,
      min_instances: options.minInstances,
      auto_scaling: options.autoScaling,
    },
    health_check: {
      enabled: true,
      endpoint: options.healthCheckEndpoint,
      interval_seconds: 30,
      timeout_seconds: 10,
      failure_threshold: 3,
      success_threshold: 1,
    },
    security: {
      enable_ssl: options.enableSsl,
      enable_authentication: true,
      enable_authorization: true,
      enable_audit_logging: true,
      enable_pii_redaction: options.environment === 'production',
      enable_encryption: options.environment === 'production',
    },
    monitoring: {
      enable_metrics: true,
      enable_tracing: true,
      enable_logging: true,
      metrics_port: options.metricsPort,
      log_level: options.environment === 'production' ? 'INFO' : 'DEBUG',
      alert_enabled: true,
      alert_channels: options.alertChannels,
    },
  };
}

interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

function validateDeploymentConfiguration(
  config: any,
  environment: string
): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  // Production-specific validations
  if (environment === 'production') {
    if (!config.security.enable_ssl) {
      errors.push('SSL must be enabled for production deployments');
    }
    if (!config.security.enable_authentication) {
      errors.push('Authentication must be enabled for production deployments');
    }
    if (!config.security.enable_authorization) {
      errors.push('Authorization must be enabled for production deployments');
    }
    if (!config.security.enable_audit_logging) {
      errors.push('Audit logging must be enabled for production deployments');
    }
    if (!config.monitoring.alert_enabled) {
      warnings.push('Alerting is recommended for production deployments');
    }
    if (config.resources.min_instances < 2) {
      warnings.push('Production deployments should have at least 2 instances for high availability');
    }
  }

  // Resource validations
  if (config.resources.min_instances > config.resources.max_instances) {
    errors.push('Minimum instances cannot exceed maximum instances');
  }
  if (config.resources.memory_mb < 512) {
    warnings.push('Memory should be at least 512MB for production workloads');
  }
  if (config.resources.cpu_cores < 1) {
    errors.push('CPU cores must be at least 1');
  }

  // Health check validations
  if (!config.health_check.enabled) {
    warnings.push('Health checks are recommended for production deployments');
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
  };
}

interface DeploymentOptions {
  id: string;
  name: string;
  topologyId: string;
  topologyVersion: string;
  config: any;
  createdBy: string;
}

async function createDeployment(options: DeploymentOptions): Promise<any> {
  // In a real implementation, this would create a deployment via API or database
  // For now, we'll return a deployment object that matches our Deployment model
  return {
    id: options.id,
    name: options.name,
    topology_id: options.topologyId,
    topology_version: options.topologyVersion,
    status: 'pending',
    config: options.config,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    created_by: options.createdBy,
  };
}

interface DeploymentSummary {
  id: string;
  name: string;
  environment: string;
  config: any;
  topology: TopologyData;
}

function displayDeploymentSummary(summary: DeploymentSummary): void {
  console.log(chalk.gray(`  Deployment ID: ${summary.id}`));
  console.log(chalk.gray(`  Name: ${summary.name}`));
  console.log(chalk.gray(`  Environment: ${summary.environment}`));
  console.log(chalk.gray(`  Topology: ${summary.topology.name || 'N/A'}`));
  console.log(chalk.gray(`  Version: ${summary.topology.version || 'N/A'}`));
  console.log(chalk.gray(`  Nodes: ${summary.topology.nodes?.length || 0}`));
  console.log(chalk.gray(`  Edges: ${summary.topology.edges?.length || 0}`));
  console.log(chalk.gray(`  CPU Cores: ${summary.config.resources.cpu_cores}`));
  console.log(chalk.gray(`  Memory: ${summary.config.resources.memory_mb}MB`));
  console.log(chalk.gray(`  Storage: ${summary.config.resources.storage_gb}GB`));
  console.log(chalk.gray(`  Instances: ${summary.config.resources.min_instances}-${summary.config.resources.max_instances}`));
  console.log(chalk.gray(`  Auto-scaling: ${summary.config.resources.auto_scaling ? 'Enabled' : 'Disabled'}`));
  console.log(chalk.gray(`  SSL: ${summary.config.security.enable_ssl ? 'Enabled' : 'Disabled'}`));
  console.log(chalk.gray(`  Metrics Port: ${summary.config.monitoring.metrics_port}`));
  console.log(chalk.gray(`  Alert Channels: ${summary.config.monitoring.alert_channels.join(', ')}`));
}

