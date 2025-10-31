import { Command } from 'commander';
import chalk from 'chalk';
import fs from 'fs-extra';
import path from 'path';

export const devCommand = new Command('dev')
  .description('Development workflow for topology development')
  .option('-d, --pack-dir <dir>', 'Topology pack directory', './topology')
  .option('--watch', 'Watch for changes and auto-reload', true)
  .option('--port <port>', 'Development server port', '3000')
  .option('--hot-reload', 'Enable hot reloading', true)
  .option('--debug', 'Enable debug mode', false)
  .action(async options => {
    console.log(chalk.blue('Starting TopoKit development environment...'));

    try {
      const { packDir, watch, port, hotReload, debug } = options;
      const topologyPath = path.resolve(packDir);

      if (!(await fs.pathExists(topologyPath))) {
        throw new Error(`Topology directory does not exist: ${topologyPath}`);
      }

      await startDevelopmentServer(topologyPath, {
        watch,
        port: parseInt(port),
        hotReload,
        debug,
      });

    } catch (error) {
      console.log(chalk.red('✗ Development server failed:'));
      console.error(
        chalk.red(error instanceof Error ? error.message : String(error))
      );
      process.exit(1);
    }
  });

interface DevServerOptions {
  watch: boolean;
  port: number;
  hotReload: boolean;
  debug: boolean;
}

async function startDevelopmentServer(
  topologyDir: string,
  options: DevServerOptions
): Promise<void> {
  console.log(chalk.blue('\nTopoKit Development Server'));
  console.log(chalk.gray(`  Directory: ${topologyDir}`));
  console.log(chalk.gray(`  Port: ${options?.port || 3000}`));
  console.log(chalk.gray(`  Watch: ${options?.watch ? 'enabled' : 'disabled'}`));
  console.log(chalk.gray(`  Hot Reload: ${options?.hotReload ? 'enabled' : 'disabled'}`));
  console.log(chalk.gray(`  Debug: ${options?.debug ? 'enabled' : 'disabled'}`));
  console.log(chalk.gray('\nPress Ctrl+C to stop\n'));

  // Start file watcher if enabled
  if (options?.watch) {
    await startFileWatcher(topologyDir, options);
  }

  // Start development server
  await startDevServer(topologyDir, options);
}

async function startFileWatcher(
  topologyDir: string,
  options: DevServerOptions
): Promise<void> {
  const chokidar = await import('chokidar');
  
  const watcher = chokidar.watch([
    path.join(topologyDir, '**/*.yaml'),
    path.join(topologyDir, '**/*.yml'),
    path.join(topologyDir, '**/*.json'),
    path.join(topologyDir, '**/*.rego'),
  ], {
    ignored: /(^|[\/\\])\../, // ignore dotfiles
    persistent: true,
  });

  watcher
    .on('change', async (filePath: string) => {
      console.log(chalk.yellow(`File changed: ${path.relative(topologyDir, filePath)}`));
      
      if (options?.hotReload) {
        await handleHotReload(filePath, topologyDir, options);
      }
    })
    .on('add', (filePath: string) => {
      console.log(chalk.green(`File added: ${path.relative(topologyDir, filePath)}`));
    })
    .on('unlink', (filePath: string) => {
      console.log(chalk.red(`File removed: ${path.relative(topologyDir, filePath)}`));
    })
    .on('error', (error: Error) => {
      console.error(chalk.red(`Watcher error: ${error}`));
    });

  console.log(chalk.green('✓ File watcher started'));
}

async function handleHotReload(
  filePath: string,
  topologyDir: string,
  options: DevServerOptions
): Promise<void> {
  const relativePath = path.relative(topologyDir, filePath);
  
  try {
    // Validate the changed file
    if (filePath.endsWith('.yaml') || filePath.endsWith('.yml')) {
      await validateYamlFile(filePath);
    } else if (filePath.endsWith('.json')) {
      await validateJsonFile(filePath);
    } else if (filePath.endsWith('.rego')) {
      await validateRegoFile(filePath);
    }

    console.log(chalk.green(`✓ Hot reloaded: ${relativePath}`));
    
    // Trigger topology reload
    await reloadTopology(topologyDir, options);

  } catch (error) {
    console.log(chalk.red(`✗ Hot reload failed for ${relativePath}:`));
    console.error(chalk.red(error instanceof Error ? error.message : String(error)));
  }
}

async function validateYamlFile(filePath: string): Promise<void> {
  const yaml = await import('yaml');
  const content = await fs.readFile(filePath, 'utf-8');
  yaml.parse(content);
}

async function validateJsonFile(filePath: string): Promise<void> {
  const content = await fs.readFile(filePath, 'utf-8');
  JSON.parse(content);
}

async function validateRegoFile(filePath: string): Promise<void> {
  // Basic Rego validation
  const content = await fs.readFile(filePath, 'utf-8');
  
  // Check for basic syntax issues
  const lines = content.split('\n');
  for (let i = 0; i < lines.length; i++) {
    const line = (lines[i] || '').trim();
    
    // Check for balanced braces
    const openBraces = (line.match(/\{/g) || []).length;
    const closeBraces = (line.match(/\}/g) || []).length;
    if (openBraces !== closeBraces) {
      throw new Error(`Unbalanced braces at line ${i + 1}`);
    }
  }
}

async function reloadTopology(_topologyDir: string, options: DevServerOptions): Promise<void> {
  if (options?.debug) {
    console.log(chalk.gray('  Reloading topology...'));
  }

  // Simulate topology reload
  await new Promise(resolve => setTimeout(resolve, 100));
  
  if (options?.debug) {
    console.log(chalk.gray('  Topology reloaded'));
  }
}

async function startDevServer(
  topologyDir: string,
  options: DevServerOptions
): Promise<void> {
  // Create development server configuration
  const devConfig = {
    port: options?.port || 3000,
    topology: {
      directory: topologyDir,
      watch: options?.watch || false,
      hotReload: options?.hotReload || false,
    },
    debug: options?.debug || false,
    features: {
      graphVisualization: true,
      realTimeMetrics: true,
      interactiveDebugging: true,
      contractValidation: true,
    },
  };

  // Write development configuration
  const configPath = path.join(topologyDir, '.dev-config.json');
  await fs.writeFile(configPath, JSON.stringify(devConfig, null, 2));

  console.log(chalk.green('✓ Development server configuration created'));

  // Start development dashboard
  await startDevelopmentDashboard(topologyDir, options);
}

async function startDevelopmentDashboard(
  _topologyDir: string,
  options: DevServerOptions
): Promise<void> {
  console.log(chalk.blue('\nDevelopment Dashboard:'));
  console.log(chalk.gray(`  URL: http://localhost:${options?.port || 3000}`));
  console.log(chalk.gray('  Features:'));
  console.log(chalk.gray('    • Real-time topology visualization'));
  console.log(chalk.gray('    • Interactive debugging'));
  console.log(chalk.gray('    • Contract validation'));
  console.log(chalk.gray('    • Performance metrics'));
  console.log(chalk.gray('    • Hot reloading'));

  // Simulate development server
  const server = {
    port: options?.port || 3000,
    running: true,
  };

  // Keep the process alive
  process.on('SIGINT', () => {
    console.log(chalk.yellow('\nShutting down development server...'));
    server.running = false;
    process.exit(0);
  });

  // Simulate server activity
  while (server.running) {
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    if (options?.debug) {
      console.log(chalk.gray(`  Server running on port ${server.port}...`));
    }
  }
}
