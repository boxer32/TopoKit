#!/usr/bin/env node

import { Command } from 'commander';
import chalk from 'chalk';
import { initCommand } from './commands/init';
import { lintCommand } from './commands/lint';
import { graphCommand } from './commands/graph';
import { evalCommand } from './commands/eval';
import { monitorCommand } from './commands/monitor';
import { replayCommand } from './commands/replay';
import { policyCommand } from './commands/policy';
import { migrateCommand } from './commands/migrate';
import { costCommand } from './commands/cost';
import { driftCommand } from './commands/drift';
import { devCommand } from './commands/dev';
import { testCommand } from './commands/test';
import { generateCommand } from './commands/generate';
import { docsCommand } from './commands/docs';
import { deployCommand } from './commands/deploy';

const program = new Command();

program
  .name('topokit-cli')
  .description('TopoKit CLI - Enterprise-grade topology-first contract system for LLM applications')
  .version('0.1.0');

// Add commands
program.addCommand(initCommand);
program.addCommand(lintCommand);
program.addCommand(graphCommand);
program.addCommand(evalCommand);
program.addCommand(monitorCommand);
program.addCommand(replayCommand);
program.addCommand(policyCommand);
program.addCommand(migrateCommand);
program.addCommand(costCommand);
program.addCommand(driftCommand);
program.addCommand(devCommand);
program.addCommand(testCommand);
program.addCommand(generateCommand);
program.addCommand(docsCommand);
program.addCommand(deployCommand);

// Global error handling
program.configureHelp({
  sortSubcommands: true,
  subcommandTerm: (cmd) => cmd.name()
});

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error(chalk.red('Uncaught Exception:'), error.message);
  process.exit(1);
});

process.on('unhandledRejection', (reason) => {
  console.error(chalk.red('Unhandled Rejection:'), reason);
  process.exit(1);
});

// Parse command line arguments
program.parse();
