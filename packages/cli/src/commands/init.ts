import { Command } from 'commander';
import chalk from 'chalk';
import fs from 'fs-extra';
import path from 'path';
import { TemplateManager } from '../templates/template-manager';

export const initCommand = new Command('init')
  .description('Initialize a new TopoKit project')
  .option('-t, --template <template>', 'Template to use', 'rag-system')
  .option('-l, --language <language>', 'Programming language', 'typescript')
  .option('-o, --output <output>', 'Output directory', '.')
  .option('--list-templates', 'List available templates')
  .action(async options => {
    try {
      const { template, language, output, listTemplates } = options;
      
      // Initialize template manager
      const templateManager = new TemplateManager();
      
      // List templates if requested
      if (listTemplates) {
        const templates = await templateManager.listTemplates();
        console.log(chalk.blue('Available templates:'));
        templates.forEach(t => console.log(chalk.gray(`  - ${t}`)));
        return;
      }

      console.log(chalk.blue('Initializing TopoKit project...'));
      console.log(chalk.gray(`Template: ${template}`));
      console.log(chalk.gray(`Language: ${language}`));
      console.log(chalk.gray(`Output: ${output}`));

      // Create project structure
      const projectDir = path.resolve(output);
      await fs.ensureDir(projectDir);

      // Create topology directory
      const topologyDir = path.join(projectDir, 'topology');
      await fs.ensureDir(topologyDir);

      // Generate template files using template manager
      await templateManager.generateFromTemplate(template, topologyDir, {
        projectName: path.basename(projectDir),
        language,
      });

      console.log(chalk.green('✓ TopoKit project initialized successfully!'));

      console.log(chalk.blue('\nNext steps:'));
      console.log(chalk.gray('1. cd ' + projectDir));
      console.log(chalk.gray('2. topokit-cli lint'));
      console.log(chalk.gray('3. topokit-cli graph'));
      console.log(chalk.gray('4. topokit-cli eval'));
    } catch (error) {
      console.log(chalk.red('✗ Failed to initialize project:'));
      console.error(
        chalk.red(error instanceof Error ? error.message : String(error))
      );
      process.exit(1);
    }
  });

