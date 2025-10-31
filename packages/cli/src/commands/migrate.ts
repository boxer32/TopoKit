import { Command } from 'commander';
import chalk from 'chalk';
import fs from 'fs-extra';
import path from 'path';
import yaml from 'yaml';

export const migrateCommand = new Command('migrate')
  .description('Migrate topology pack to newer version')
  .option('-d, --pack-dir <dir>', 'Topology pack directory', './topology')
  .option('-f, --from-version <version>', 'Source version', '1.0.0')
  .option('-t, --to-version <version>', 'Target version', '2.0.0')
  .option('--dry-run', 'Show what would be migrated without making changes')
  .option('--backup', 'Create backup before migration', true)
  .action(async options => {
    console.log(chalk.blue('Migrating topology pack...'));

    try {
      const { packDir, fromVersion, toVersion, dryRun, backup } = options;
      const topologyPath = path.resolve(packDir);

      if (!(await fs.pathExists(topologyPath))) {
        throw new Error(`Topology directory does not exist: ${topologyPath}`);
      }

      const migrationPlan = await createMigrationPlan(topologyPath, fromVersion, toVersion);

      if (dryRun) {
        console.log(chalk.yellow('Dry run - no changes will be made'));
        displayMigrationPlan(migrationPlan);
        return;
      }

      if (backup) {
        await createBackup(topologyPath);
        console.log(chalk.green('✓ Backup created'));
      }

      const results = await executeMigration(topologyPath, migrationPlan);

      if (results.success) {
        console.log(chalk.green('✓ Migration completed successfully'));
        displayMigrationResults(results);
      } else {
        console.log(chalk.red('✗ Migration failed'));
        displayMigrationErrors(results);
        process.exit(1);
      }
    } catch (error) {
      console.log(chalk.red('✗ Migration failed:'));
      console.error(
        chalk.red(error instanceof Error ? error.message : String(error))
      );
      process.exit(1);
    }
  });

interface MigrationPlan {
  fromVersion: string;
  toVersion: string;
  steps: MigrationStep[];
  warnings: string[];
  estimatedTime: number;
}

interface MigrationStep {
  id: string;
  description: string;
  type: 'file_update' | 'file_create' | 'file_delete' | 'directory_create' | 'validation';
  file?: string;
  changes?: any;
  critical: boolean;
}

interface MigrationResult {
  success: boolean;
  stepsCompleted: number;
  totalSteps: number;
  errors: string[];
  warnings: string[];
  duration: number;
  filesChanged: string[];
}

async function createMigrationPlan(
  topologyDir: string,
  fromVersion: string,
  toVersion: string
): Promise<MigrationPlan> {
  const steps: MigrationStep[] = [];
  const warnings: string[] = [];

  // Check current version
  const currentVersion = await getCurrentVersion(topologyDir);
  if (currentVersion !== fromVersion) {
    warnings.push(`Current version (${currentVersion}) does not match expected from-version (${fromVersion})`);
  }

  // Version-specific migration steps
  if (fromVersion === '1.0.0' && toVersion === '2.0.0') {
    steps.push(
      {
        id: 'update_nodes_schema',
        description: 'Update nodes.yaml schema to v2.0.0',
        type: 'file_update',
        file: 'nodes.yaml',
        critical: true,
      },
      {
        id: 'update_edges_schema',
        description: 'Update edges.yaml schema to v2.0.0',
        type: 'file_update',
        file: 'edges.yaml',
        critical: true,
      },
      {
        id: 'update_guardrails_schema',
        description: 'Update guardrails.yaml schema to v2.0.0',
        type: 'file_update',
        file: 'guardrails.yaml',
        critical: false,
      },
      {
        id: 'create_migration_metadata',
        description: 'Create migration metadata file',
        type: 'file_create',
        file: 'migration.json',
        critical: false,
      },
      {
        id: 'validate_migration',
        description: 'Validate migrated topology',
        type: 'validation',
        critical: true,
      }
    );
  } else if (fromVersion === '2.0.0' && toVersion === '3.0.0') {
    steps.push(
      {
        id: 'add_observability_config',
        description: 'Add observability configuration',
        type: 'file_create',
        file: 'observability.yaml',
        critical: false,
      },
      {
        id: 'update_contracts_schema',
        description: 'Update contract schema to v3.0.0',
        type: 'file_update',
        file: 'contracts/',
        critical: true,
      },
      {
        id: 'add_security_policies',
        description: 'Add security policy templates',
        type: 'file_create',
        file: 'security/',
        critical: false,
      }
    );
  } else {
    warnings.push(`Migration from ${fromVersion} to ${toVersion} is not supported`);
  }

  return {
    fromVersion,
    toVersion,
    steps,
    warnings,
    estimatedTime: steps.length * 2, // 2 seconds per step
  };
}

async function getCurrentVersion(topologyDir: string): Promise<string> {
  // Try to read version from various sources
  const versionFiles = [
    'version.txt',
    'package.json',
    'topology.json',
  ];

  for (const file of versionFiles) {
    const filePath = path.join(topologyDir, file);
    if (await fs.pathExists(filePath)) {
      try {
        const content = await fs.readFile(filePath, 'utf-8');
        if (file === 'package.json') {
          const pkg = JSON.parse(content);
          return pkg.version || '1.0.0';
        } else {
          return content.trim();
        }
      } catch {
        // Continue to next file
      }
    }
  }

  // Default version
  return '1.0.0';
}

async function executeMigration(
  topologyDir: string,
  plan: MigrationPlan
): Promise<MigrationResult> {
  const startTime = Date.now();
  const errors: string[] = [];
  const warnings: string[] = [...plan.warnings];
  const filesChanged: string[] = [];
  let stepsCompleted = 0;

  for (const step of plan.steps) {
    try {
      console.log(chalk.gray(`  ${step.description}...`));

      switch (step.type) {
        case 'file_update':
          if (step.file) {
            await updateFile(topologyDir, step.file, step);
            filesChanged.push(step.file);
          }
          break;

        case 'file_create':
          if (step.file) {
            await createFile(topologyDir, step.file, step);
            filesChanged.push(step.file);
          }
          break;

        case 'file_delete':
          if (step.file) {
            await deleteFile(topologyDir, step.file);
            filesChanged.push(step.file);
          }
          break;

        case 'directory_create':
          if (step.file) {
            await createDirectory(topologyDir, step.file);
            filesChanged.push(step.file);
          }
          break;

        case 'validation':
          await validateMigration(topologyDir);
          break;
      }

      stepsCompleted++;
      console.log(chalk.green(`    ✓ ${step.description}`));

    } catch (error) {
      const errorMsg = `Step ${step.id} failed: ${error instanceof Error ? error.message : String(error)}`;
      errors.push(errorMsg);

      if (step.critical) {
        console.log(chalk.red(`    ✗ ${step.description} (CRITICAL)`));
        break;
      } else {
        console.log(chalk.yellow(`    ⚠ ${step.description} (NON-CRITICAL)`));
        warnings.push(errorMsg);
      }
    }
  }

  const duration = Date.now() - startTime;

  return {
    success: errors.length === 0,
    stepsCompleted,
    totalSteps: plan.steps.length,
    errors,
    warnings,
    duration,
    filesChanged,
  };
}

async function updateFile(
  topologyDir: string,
  fileName: string,
  step: MigrationStep
): Promise<void> {
  const filePath = path.join(topologyDir, fileName);

  if (!(await fs.pathExists(filePath))) {
    throw new Error(`File not found: ${fileName}`);
  }

  const content = await fs.readFile(filePath, 'utf-8');
  let updatedContent = content;

  // Apply version-specific updates
  if (fileName === 'nodes.yaml') {
    updatedContent = await updateNodesSchema(content, step);
  } else if (fileName === 'edges.yaml') {
    updatedContent = await updateEdgesSchema(content, step);
  } else if (fileName === 'guardrails.yaml') {
    updatedContent = await updateGuardrailsSchema(content, step);
  }

  await fs.writeFile(filePath, updatedContent);
}

async function updateNodesSchema(content: string, step: MigrationStep): Promise<string> {
  const nodes = yaml.parse(content);

  if (!nodes || !nodes.nodes) {
    throw new Error('Invalid nodes.yaml structure');
  }

  // Add version field if missing
  if (!nodes.version) {
    nodes.version = '2.0.0';
  }

  // Update node schema for v2.0.0
  for (const node of nodes.nodes) {
    // Add required fields for v2.0.0
    if (!node.metadata) {
      node.metadata = {
        created: new Date().toISOString(),
        version: '2.0.0',
      };
    }

    // Add observability config
    if (!node.observability) {
      node.observability = {
        enabled: true,
        metrics: true,
        tracing: true,
        logging: true,
      };
    }

    // Add security config
    if (!node.security) {
      node.security = {
        encryption: false,
        authentication: false,
        authorization: false,
      };
    }
  }

  return yaml.stringify(nodes, { indent: 2 });
}

async function updateEdgesSchema(content: string, step: MigrationStep): Promise<string> {
  const edges = yaml.parse(content);

  if (!edges || !edges.edges) {
    throw new Error('Invalid edges.yaml structure');
  }

  // Add version field if missing
  if (!edges.version) {
    edges.version = '2.0.0';
  }

  // Update edge schema for v2.0.0
  for (const edge of edges.edges) {
    // Add required fields for v2.0.0
    if (!edge.metadata) {
      edge.metadata = {
        created: new Date().toISOString(),
        version: '2.0.0',
      };
    }

    // Add observability config
    if (!edge.observability) {
      edge.observability = {
        enabled: true,
        metrics: true,
        tracing: true,
      };
    }

    // Add security config
    if (!edge.security) {
      edge.security = {
        encryption: false,
        authentication: false,
      };
    }
  }

  return yaml.stringify(edges, { indent: 2 });
}

async function updateGuardrailsSchema(content: string, step: MigrationStep): Promise<string> {
  const guardrails = yaml.parse(content);

  if (!guardrails) {
    throw new Error('Invalid guardrails.yaml structure');
  }

  // Add version field if missing
  if (!guardrails.version) {
    guardrails.version = '2.0.0';
  }

  // Add new guardrails for v2.0.0
  if (!guardrails.observability) {
    guardrails.observability = {
      enabled: true,
      metrics_retention_days: 30,
      log_level: 'info',
    };
  }

  if (!guardrails.security) {
    guardrails.security = {
      enabled: true,
      encryption_required: false,
      authentication_required: false,
    };
  }

  return yaml.stringify(guardrails, { indent: 2 });
}

async function createFile(topologyDir: string, fileName: string, step: MigrationStep): Promise<void> {
  const filePath = path.join(topologyDir, fileName);

  if (fileName === 'migration.json') {
    const migrationData = {
      version: '2.0.0',
      migrated_at: new Date().toISOString(),
      from_version: '1.0.0',
      to_version: '2.0.0',
      steps_completed: step.id,
    };
    await fs.writeFile(filePath, JSON.stringify(migrationData, null, 2));
  } else if (fileName === 'observability.yaml') {
    const observabilityConfig = {
      version: '2.0.0',
      metrics: {
        enabled: true,
        retention_days: 30,
        export_interval: '60s',
      },
      tracing: {
        enabled: true,
        sampling_rate: 0.1,
      },
      logging: {
        enabled: true,
        level: 'info',
        format: 'json',
      },
    };
    await fs.writeFile(filePath, yaml.stringify(observabilityConfig, { indent: 2 }));
  }
}

async function createDirectory(topologyDir: string, dirName: string): Promise<void> {
  const dirPath = path.join(topologyDir, dirName);
  await fs.ensureDir(dirPath);

  if (dirName === 'security') {
    // Create security policy templates
    const securityPolicy = `package topokit.security

# Security policies for TopoKit
# Generated during migration

default allow = false

# Allow authenticated users
allow {
    input.user.authenticated == true
}

# Allow specific operations
allow {
    input.operation == "read"
    input.resource.type == "public"
}
`;

    await fs.writeFile(
      path.join(dirPath, 'policies.rego'),
      securityPolicy
    );
  }
}

async function deleteFile(topologyDir: string, fileName: string): Promise<void> {
  const filePath = path.join(topologyDir, fileName);
  if (await fs.pathExists(filePath)) {
    await fs.remove(filePath);
  }
}

async function validateMigration(topologyDir: string): Promise<void> {
  // Validate that all required files exist and are valid
  const requiredFiles = ['nodes.yaml', 'edges.yaml', 'guardrails.yaml'];
  
  for (const file of requiredFiles) {
    const filePath = path.join(topologyDir, file);
    if (!(await fs.pathExists(filePath))) {
      throw new Error(`Required file missing after migration: ${file}`);
    }

    // Basic YAML validation
    try {
      const content = await fs.readFile(filePath, 'utf-8');
      yaml.parse(content);
    } catch (error) {
      throw new Error(`Invalid YAML in ${file}: ${error instanceof Error ? error.message : String(error)}`);
    }
  }
}

async function createBackup(topologyDir: string): Promise<void> {
  const backupDir = `${topologyDir}.backup.${Date.now()}`;
  await fs.copy(topologyDir, backupDir);
  console.log(chalk.gray(`Backup created at: ${backupDir}`));
}

function displayMigrationPlan(plan: MigrationPlan): void {
  console.log(chalk.blue('\nMigration Plan:'));
  console.log(chalk.gray(`  From: ${plan.fromVersion}`));
  console.log(chalk.gray(`  To: ${plan.toVersion}`));
  console.log(chalk.gray(`  Steps: ${plan.steps.length}`));
  console.log(chalk.gray(`  Estimated time: ${plan.estimatedTime}s`));

  if (plan.warnings.length > 0) {
    console.log(chalk.yellow('\nWarnings:'));
    for (const warning of plan.warnings) {
      console.log(chalk.yellow(`  ⚠ ${warning}`));
    }
  }

  console.log(chalk.blue('\nMigration Steps:'));
  for (const step of plan.steps) {
    const critical = step.critical ? chalk.red('(CRITICAL)') : chalk.gray('(optional)');
    console.log(chalk.gray(`  ${step.id}: ${step.description} ${critical}`));
  }
}

function displayMigrationResults(result: MigrationResult): void {
  console.log(chalk.blue('\nMigration Results:'));
  console.log(chalk.gray(`  Steps completed: ${result.stepsCompleted}/${result.totalSteps}`));
  console.log(chalk.gray(`  Duration: ${result.duration}ms`));
  console.log(chalk.gray(`  Files changed: ${result.filesChanged.length}`));

  if (result.warnings.length > 0) {
    console.log(chalk.yellow('\nWarnings:'));
    for (const warning of result.warnings) {
      console.log(chalk.yellow(`  ⚠ ${warning}`));
    }
  }

  if (result.filesChanged.length > 0) {
    console.log(chalk.blue('\nFiles Changed:'));
    for (const file of result.filesChanged) {
      console.log(chalk.gray(`  ${file}`));
    }
  }
}

function displayMigrationErrors(result: MigrationResult): void {
  console.log(chalk.red('\nMigration Errors:'));
  for (const error of result.errors) {
    console.log(chalk.red(`  ✗ ${error}`));
  }

  console.log(chalk.red(`\n✗ Migration failed after ${result.duration}ms`));
  console.log(chalk.yellow('Check the backup directory for the original files'));
}
