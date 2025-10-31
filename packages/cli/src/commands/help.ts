import { Command } from 'commander';
import chalk from 'chalk';
import fs from 'fs-extra';
import path from 'path';

export const helpCommand = new Command('help')
  .description('Show help information, examples, and troubleshooting')
  .option('-c, --command <command>', 'Show help for specific command')
  .option('--examples', 'Show usage examples')
  .option('--troubleshooting', 'Show troubleshooting guide')
  .option('--quickstart', 'Show quickstart guide')
  .action(async options => {
    const { command, examples, troubleshooting, quickstart } = options;

    if (quickstart) {
      displayQuickstartGuide();
    } else if (examples) {
      displayExamples();
    } else if (troubleshooting) {
      displayTroubleshootingGuide();
    } else if (command) {
      displayCommandHelp(command);
    } else {
      displayGeneralHelp();
    }
  });

function displayGeneralHelp(): void {
  console.log(chalk.blue.bold('\nTopoKit - Enterprise-grade topology-first contract system for LLM applications\n'));
  
  console.log(chalk.gray('TopoKit enables AI/ML Engineers to build reliable, scalable, and maintainable LLM applications'));
  console.log(chalk.gray('using a topology-first approach with comprehensive contract validation and safety controls.\n'));

  console.log(chalk.bold('USAGE:'));
  console.log(chalk.gray('  topokit <command> [options]\n'));

  console.log(chalk.bold('COMMANDS:'));
  
  // Core commands
  console.log(chalk.blue('  Core Commands:'));
  console.log(chalk.gray('    init        Initialize a new TopoKit project with templates'));
  console.log(chalk.gray('    lint        Validate topology pack configuration'));
  console.log(chalk.gray('    graph       Generate topology visualization'));
  console.log(chalk.gray('    eval        Run evaluation tests on topology pack\n'));

  // Development commands
  console.log(chalk.blue('  Development:'));
  console.log(chalk.gray('    dev         Start development environment with hot reload'));
  console.log(chalk.gray('    test        Run comprehensive test suite'));
  console.log(chalk.gray('    generate    Generate code and scaffolding'));
  console.log(chalk.gray('    replay      Replay topology execution with deterministic testing\n'));

  // Production commands
  console.log(chalk.blue('  Production:'));
  console.log(chalk.gray('    monitor     Monitor topology execution and performance'));
  console.log(chalk.gray('    policy      Policy validation and management'));
  console.log(chalk.gray('    migrate     Migrate topology pack to newer version'));
  console.log(chalk.gray('    cost        Cost analysis and optimization\n'));

  // Operations commands
  console.log(chalk.blue('  Operations:'));
  console.log(chalk.gray('    drift       Drift detection and alerting'));
  console.log(chalk.gray('    docs        Generate documentation'));
  console.log(chalk.gray('    help        Show help information and examples\n'));

  console.log(chalk.bold('OPTIONS:'));
  console.log(chalk.gray('  -h, --help     Show help information'));
  console.log(chalk.gray('  -v, --version  Show version information\n'));

  console.log(chalk.bold('EXAMPLES:'));
  console.log(chalk.gray('  # Quick start'));
  console.log(chalk.gray('  topokit init --template=rag-system'));
  console.log(chalk.gray('  topokit lint'));
  console.log(chalk.gray('  topokit graph --format=mermaid\n'));

  console.log(chalk.gray('  # Development workflow'));
  console.log(chalk.gray('  topokit dev --watch'));
  console.log(chalk.gray('  topokit test --coverage'));
  console.log(chalk.gray('  topokit eval --verbose\n'));

  console.log(chalk.gray('  # Production deployment'));
  console.log(chalk.gray('  topokit monitor --watch'));
  console.log(chalk.gray('  topokit cost --optimize'));
  console.log(chalk.gray('  topokit drift --detect\n'));

  console.log(chalk.bold('GETTING HELP:'));
  console.log(chalk.gray('  topokit help --quickstart     Show quickstart guide'));
  console.log(chalk.gray('  topokit help --examples       Show usage examples'));
  console.log(chalk.gray('  topokit help --troubleshooting Show troubleshooting guide'));
  console.log(chalk.gray('  topokit help --command <cmd>  Show help for specific command\n'));

  console.log(chalk.bold('DOCUMENTATION:'));
  console.log(chalk.gray('  https://docs.topokit.dev      Official documentation'));
  console.log(chalk.gray('  https://github.com/topokit    Source code and issues'));
  console.log(chalk.gray('  https://discord.gg/topokit    Community support\n'));
}

function displayQuickstartGuide(): void {
  console.log(chalk.blue.bold('\nTopoKit Quickstart Guide\n'));
  
  console.log(chalk.bold('1. Install TopoKit CLI'));
  console.log(chalk.gray('   npm install -g @topokit/cli'));
  console.log(chalk.gray('   # or'));
  console.log(chalk.gray('   npx @topokit/cli\n'));

  console.log(chalk.bold('2. Initialize a new project'));
  console.log(chalk.gray('   topokit init --template=rag-system'));
  console.log(chalk.gray('   cd topology\n'));

  console.log(chalk.bold('3. Validate your topology'));
  console.log(chalk.gray('   topokit lint'));
  console.log(chalk.gray('   topokit graph --format=mermaid\n'));

  console.log(chalk.bold('4. Run evaluation tests'));
  console.log(chalk.gray('   topokit eval'));
  console.log(chalk.gray('   topokit test --coverage\n'));

  console.log(chalk.bold('5. Start development'));
  console.log(chalk.gray('   topokit dev --watch'));
  console.log(chalk.gray('   # Open http://localhost:3000 in your browser\n'));

  console.log(chalk.bold('6. Deploy to production'));
  console.log(chalk.gray('   topokit monitor --watch'));
  console.log(chalk.gray('   topokit cost --optimize\n'));

  console.log(chalk.bold('Next Steps:'));
  console.log(chalk.gray('  • Customize your topology configuration'));
  console.log(chalk.gray('  • Add your business logic to contracts'));
  console.log(chalk.gray('  • Create evaluation tests in eval/ directory'));
  console.log(chalk.gray('  • Deploy and monitor your topology\n'));

  console.log(chalk.bold('Templates Available:'));
  console.log(chalk.gray('  • rag-system     - Basic RAG with data retrieval and AI answers'));
  console.log(chalk.gray('  • qa-system      - Question-answering with document processing'));
  console.log(chalk.gray('  • multi-agent    - Multi-agent system with specialized agents\n'));

  console.log(chalk.bold('Need Help?'));
  console.log(chalk.gray('  topokit help --examples       Show detailed examples'));
  console.log(chalk.gray('  topokit help --troubleshooting Show troubleshooting guide'));
  console.log(chalk.gray('  https://docs.topokit.dev      Full documentation\n'));
}

function displayExamples(): void {
  console.log(chalk.blue.bold('\nTopoKit Usage Examples\n'));

  console.log(chalk.bold('Project Initialization:'));
  console.log(chalk.gray('  # Create a new RAG system'));
  console.log(chalk.gray('  topokit init --template=rag-system --output=my-rag-app\n'));

  console.log(chalk.gray('  # Create a multi-agent system'));
  console.log(chalk.gray('  topokit init --template=multi-agent --output=my-agents\n'));

  console.log(chalk.gray('  # List available templates'));
  console.log(chalk.gray('  topokit init --list-templates\n'));

  console.log(chalk.bold('Validation and Linting:'));
  console.log(chalk.gray('  # Basic validation'));
  console.log(chalk.gray('  topokit lint\n'));

  console.log(chalk.gray('  # Strict validation with auto-fix'));
  console.log(chalk.gray('  topokit lint --strict --fix\n'));

  console.log(chalk.gray('  # Validate specific directory'));
  console.log(chalk.gray('  topokit lint --pack-dir=./my-topology\n'));

  console.log(chalk.bold('Visualization:'));
  console.log(chalk.gray('  # Generate Mermaid diagram'));
  console.log(chalk.gray('  topokit graph --format=mermaid\n'));

  console.log(chalk.gray('  # Generate SVG with detailed information'));
  console.log(chalk.gray('  topokit graph --format=svg --show-contracts --show-slos\n'));

  console.log(chalk.gray('  # Generate DOT file for Graphviz'));
  console.log(chalk.gray('  topokit graph --format=dot --theme=dark --layout=left-right\n'));

  console.log(chalk.bold('Testing and Evaluation:'));
  console.log(chalk.gray('  # Run all tests'));
  console.log(chalk.gray('  topokit test\n'));

  console.log(chalk.gray('  # Run specific test types'));
  console.log(chalk.gray('  topokit test --unit --integration --coverage\n'));

  console.log(chalk.gray('  # Run evaluation tests'));
  console.log(chalk.gray('  topokit eval --verbose\n'));

  console.log(chalk.gray('  # Replay execution with deterministic testing'));
  console.log(chalk.gray('  topokit replay --seed=stable --verbose\n'));

  console.log(chalk.bold('Development:'));
  console.log(chalk.gray('  # Start development server'));
  console.log(chalk.gray('  topokit dev --watch --port=3000\n'));

  console.log(chalk.gray('  # Generate new node'));
  console.log(chalk.gray('  topokit generate --type=node --name=MyNode --template=ai\n'));

  console.log(chalk.gray('  # Generate contract'));
  console.log(chalk.gray('  topokit generate --type=contract --name=myContract\n'));

  console.log(chalk.bold('Production and Monitoring:'));
  console.log(chalk.gray('  # Monitor topology execution'));
  console.log(chalk.gray('  topokit monitor --watch --interval=5000\n'));

  console.log(chalk.gray('  # Analyze costs'));
  console.log(chalk.gray('  topokit cost --model=gpt-4 --tokens=1000 --optimize\n'));

  console.log(chalk.gray('  # Detect drift'));
  console.log(chalk.gray('  topokit drift --detect --threshold=10\n'));

  console.log(chalk.gray('  # Validate policies'));
  console.log(chalk.gray('  topokit policy --validate --test\n'));

  console.log(chalk.bold('Migration and Maintenance:'));
  console.log(chalk.gray('  # Migrate to newer version'));
  console.log(chalk.gray('  topokit migrate --from-version=1.0.0 --to-version=2.0.0\n'));

  console.log(chalk.gray('  # Dry run migration'));
  console.log(chalk.gray('  topokit migrate --dry-run --backup\n'));

  console.log(chalk.gray('  # Generate documentation'));
  console.log(chalk.gray('  topokit docs --all --format=markdown\n'));

  console.log(chalk.bold('Advanced Usage:'));
  console.log(chalk.gray('  # Custom configuration'));
  console.log(chalk.gray('  topokit init --template=rag-system --language=python\n'));

  console.log(chalk.gray('  # Batch operations'));
  console.log(chalk.gray('  for dir in */; do topokit lint --pack-dir="$dir"; done\n'));

  console.log(chalk.gray('  # CI/CD integration'));
  console.log(chalk.gray('  topokit lint && topokit test --coverage && topokit eval\n'));

  console.log(chalk.bold('Configuration Files:'));
  console.log(chalk.gray('  .topokitrc.json     - Global configuration'));
  console.log(chalk.gray('  topokit.config.js   - Project-specific configuration'));
  console.log(chalk.gray('  .env                - Environment variables\n'));

  console.log(chalk.bold('Environment Variables:'));
  console.log(chalk.gray('  TOPOKIT_LOG_LEVEL   - Logging level (debug, info, warn, error)'));
  console.log(chalk.gray('  TOPOKIT_CONFIG_DIR  - Configuration directory'));
  console.log(chalk.gray('  TOPOKIT_CACHE_DIR   - Cache directory\n'));
}

function displayTroubleshootingGuide(): void {
  console.log(chalk.blue.bold('\nTopoKit Troubleshooting Guide\n'));

  console.log(chalk.bold('Common Issues and Solutions:\n'));

  console.log(chalk.bold('1. Installation Issues'));
  console.log(chalk.gray('   Problem: Command not found'));
  console.log(chalk.gray('   Solution:'));
  console.log(chalk.gray('     npm install -g @topokit/cli'));
  console.log(chalk.gray('     # or use npx'));
  console.log(chalk.gray('     npx @topokit/cli --version\n'));

  console.log(chalk.bold('2. Project Initialization'));
  console.log(chalk.gray('   Problem: Template not found'));
  console.log(chalk.gray('   Solution:'));
  console.log(chalk.gray('     topokit init --list-templates'));
  console.log(chalk.gray('     topokit init --template=rag-system\n'));

  console.log(chalk.gray('   Problem: Permission denied'));
  console.log(chalk.gray('   Solution:'));
  console.log(chalk.gray('     chmod +x $(which topokit)'));
  console.log(chalk.gray('     # or use sudo for global install'));
  console.log(chalk.gray('     sudo npm install -g @topokit/cli\n'));

  console.log(chalk.bold('3. Validation Issues'));
  console.log(chalk.gray('   Problem: YAML parsing errors'));
  console.log(chalk.gray('   Solution:'));
  console.log(chalk.gray('     # Validate YAML syntax'));
  console.log(chalk.gray('     topokit lint --strict'));
  console.log(chalk.gray('     # Check for common issues'));
  console.log(chalk.gray('     topokit lint --fix\n'));

  console.log(chalk.gray('   Problem: Missing required files'));
  console.log(chalk.gray('   Solution:'));
  console.log(chalk.gray('     # Ensure all required files exist'));
  console.log(chalk.gray('     ls -la topology/'));
  console.log(chalk.gray('     # Recreate missing files'));
  console.log(chalk.gray('     topokit init --template=rag-system\n'));

  console.log(chalk.bold('4. Graph Generation'));
  console.log(chalk.gray('   Problem: Graph generation fails'));
  console.log(chalk.gray('   Solution:'));
  console.log(chalk.gray('     # Check topology structure'));
  console.log(chalk.gray('     topokit lint'));
  console.log(chalk.gray('     # Try different format'));
  console.log(chalk.gray('     topokit graph --format=json\n'));

  console.log(chalk.gray('   Problem: Empty or invalid graph'));
  console.log(chalk.gray('   Solution:'));
  console.log(chalk.gray('     # Verify nodes and edges'));
  console.log(chalk.gray('     topokit lint --verbose'));
  console.log(chalk.gray('     # Check for cycles'));
  console.log(chalk.gray('     topokit lint --strict\n'));

  console.log(chalk.bold('5. Testing Issues'));
  console.log(chalk.gray('   Problem: Tests fail'));
  console.log(chalk.gray('   Solution:'));
  console.log(chalk.gray('     # Run with verbose output'));
  console.log(chalk.gray('     topokit test --verbose'));
  console.log(chalk.gray('     # Check test configuration'));
  console.log(chalk.gray('     topokit eval --verbose\n'));

  console.log(chalk.gray('   Problem: No tests found'));
  console.log(chalk.gray('   Solution:'));
  console.log(chalk.gray('     # Create sample tests'));
  console.log(chalk.gray('     topokit test --unit'));
  console.log(chalk.gray('     # Generate test templates'));
  console.log(chalk.gray('     topokit generate --type=test\n'));

  console.log(chalk.bold('6. Development Server'));
  console.log(chalk.gray('   Problem: Server won\'t start'));
  console.log(chalk.gray('   Solution:'));
  console.log(chalk.gray('     # Check port availability'));
  console.log(chalk.gray('     topokit dev --port=3001'));
  console.log(chalk.gray('     # Check topology validity'));
  console.log(chalk.gray('     topokit lint\n'));

  console.log(chalk.gray('   Problem: Hot reload not working'));
  console.log(chalk.gray('   Solution:'));
  console.log(chalk.gray('     # Enable hot reload'));
  console.log(chalk.gray('     topokit dev --hot-reload'));
  console.log(chalk.gray('     # Check file permissions'));
  console.log(chalk.gray('     chmod -R 755 topology/\n'));

  console.log(chalk.bold('7. Performance Issues'));
  console.log(chalk.gray('   Problem: Slow execution'));
  console.log(chalk.gray('   Solution:'));
  console.log(chalk.gray('     # Analyze costs'));
  console.log(chalk.gray('     topokit cost --optimize'));
  console.log(chalk.gray('     # Check for drift'));
  console.log(chalk.gray('     topokit drift --detect\n'));

  console.log(chalk.gray('   Problem: High memory usage'));
  console.log(chalk.gray('   Solution:'));
  console.log(chalk.gray('     # Monitor resource usage'));
  console.log(chalk.gray('     topokit monitor --watch'));
  console.log(chalk.gray('     # Optimize configuration'));
  console.log(chalk.gray('     topokit cost --optimize\n'));

  console.log(chalk.bold('8. Migration Issues'));
  console.log(chalk.gray('   Problem: Migration fails'));
  console.log(chalk.gray('   Solution:'));
  console.log(chalk.gray('     # Dry run first'));
  console.log(chalk.gray('     topokit migrate --dry-run'));
  console.log(chalk.gray('     # Create backup'));
  console.log(chalk.gray('     topokit migrate --backup\n'));

  console.log(chalk.gray('   Problem: Version conflicts'));
  console.log(chalk.gray('   Solution:'));
  console.log(chalk.gray('     # Check current version'));
  console.log(chalk.gray('     topokit --version'));
  console.log(chalk.gray('     # Update CLI'));
  console.log(chalk.gray('     npm update -g @topokit/cli\n'));

  console.log(chalk.bold('Debugging Tips:'));
  console.log(chalk.gray('  • Use --verbose flag for detailed output'));
  console.log(chalk.gray('  • Check log files in .topokit/logs/'));
  console.log(chalk.gray('  • Enable debug mode: TOPOKIT_LOG_LEVEL=debug'));
  console.log(chalk.gray('  • Validate configuration: topokit lint --strict'));
  console.log(chalk.gray('  • Test with sample data: topokit eval\n'));

  console.log(chalk.bold('Getting Help:'));
  console.log(chalk.gray('  • Check documentation: https://docs.topokit.dev'));
  console.log(chalk.gray('  • Report issues: https://github.com/topokit/topokit/issues'));
  console.log(chalk.gray('  • Community support: https://discord.gg/topokit'));
  console.log(chalk.gray('  • Command help: topokit help --command <command>\n'));

  console.log(chalk.bold('Log Files:'));
  console.log(chalk.gray('  • Application logs: .topokit/logs/app.log'));
  console.log(chalk.gray('  • Error logs: .topokit/logs/error.log'));
  console.log(chalk.gray('  • Debug logs: .topokit/logs/debug.log\n'));
}

function displayCommandHelp(command: string): void {
  const commandHelp: Record<string, string> = {
    init: `
Initialize a new TopoKit project with templates

USAGE:
  topokit init [options]

OPTIONS:
  -t, --template <template>    Template to use (default: rag-system)
  -l, --language <language>    Programming language (default: typescript)
  -o, --output <output>        Output directory (default: .)
  --list-templates            List available templates

EXAMPLES:
  topokit init --template=rag-system
  topokit init --template=multi-agent --output=my-agents
  topokit init --list-templates
`,

    lint: `
Lint and validate topology pack configuration

USAGE:
  topokit lint [options]

OPTIONS:
  -d, --pack-dir <dir>        Topology pack directory (default: ./topology)
  --strict                    Enable strict validation
  --fix                       Auto-fix issues where possible

EXAMPLES:
  topokit lint
  topokit lint --strict --fix
  topokit lint --pack-dir=./my-topology
`,

    graph: `
Generate topology visualization

USAGE:
  topokit graph [options]

OPTIONS:
  -d, --pack-dir <dir>        Topology pack directory (default: ./topology)
  -o, --output <file>         Output file (default: stdout)
  -f, --format <format>       Output format (default: mermaid)
  --theme <theme>             Graph theme (light, dark, colorblind)
  --layout <layout>           Layout algorithm (top-down, left-right, circular)
  --show-contracts            Show contract information on edges
  --show-slos                 Show SLO information on nodes
  --show-execution-profile    Show execution profile details

EXAMPLES:
  topokit graph --format=mermaid
  topokit graph --format=svg --show-contracts --show-slos
  topokit graph --format=dot --theme=dark --layout=left-right
`,

    eval: `
Run evaluation tests on topology pack

USAGE:
  topokit eval [options]

OPTIONS:
  -d, --pack-dir <dir>        Topology pack directory (default: ./topology)
  -t, --test-dir <dir>        Test directory (default: ./topology/eval)
  --verbose                   Verbose output

EXAMPLES:
  topokit eval
  topokit eval --verbose
  topokit eval --test-dir=./custom-tests
`,

    dev: `
Start development environment with hot reload

USAGE:
  topokit dev [options]

OPTIONS:
  -d, --pack-dir <dir>        Topology pack directory (default: ./topology)
  --watch                     Watch for changes and auto-reload (default: true)
  --port <port>               Development server port (default: 3000)
  --hot-reload                Enable hot reloading (default: true)
  --debug                     Enable debug mode

EXAMPLES:
  topokit dev
  topokit dev --watch --port=3001
  topokit dev --debug
`,

    test: `
Run comprehensive test suite

USAGE:
  topokit test [options]

OPTIONS:
  -d, --pack-dir <dir>        Topology pack directory (default: ./topology)
  -t, --test-dir <dir>        Test directory (default: ./topology/tests)
  --unit                      Run unit tests only
  --integration               Run integration tests only
  --contract                  Run contract tests only
  --performance               Run performance tests only
  --coverage                  Generate test coverage report
  --verbose                   Verbose output

EXAMPLES:
  topokit test
  topokit test --unit --coverage
  topokit test --integration --verbose
`,

    monitor: `
Monitor topology execution and performance

USAGE:
  topokit monitor [options]

OPTIONS:
  -d, --pack-dir <dir>        Topology pack directory (default: ./topology)
  --watch                     Watch for changes and auto-refresh
  --interval <ms>             Refresh interval in milliseconds (default: 5000)

EXAMPLES:
  topokit monitor
  topokit monitor --watch --interval=2000
`,

    cost: `
Cost analysis and optimization

USAGE:
  topokit cost [options]

OPTIONS:
  -d, --pack-dir <dir>        Topology pack directory (default: ./topology)
  -m, --model <model>         LLM model to analyze (default: gpt-4)
  --tokens <tokens>           Estimated tokens per request (default: 1000)
  --requests <requests>       Number of requests to analyze (default: 1000)
  --optimize                  Show optimization recommendations
  --budget <budget>           Budget limit in USD (default: 100)

EXAMPLES:
  topokit cost --optimize
  topokit cost --model=gpt-3.5-turbo --tokens=500
  topokit cost --budget=50 --optimize
`,

    policy: `
Policy validation and management

USAGE:
  topokit policy [options]

OPTIONS:
  -d, --pack-dir <dir>        Topology pack directory (default: ./topology)
  -p, --policy-file <file>    Policy file to validate (default: ./topology/policies.rego)
  --validate                  Validate policy syntax and logic
  --test                      Run policy tests
  --generate                  Generate policy templates

EXAMPLES:
  topokit policy --validate
  topokit policy --test
  topokit policy --generate
`,

    migrate: `
Migrate topology pack to newer version

USAGE:
  topokit migrate [options]

OPTIONS:
  -d, --pack-dir <dir>        Topology pack directory (default: ./topology)
  -f, --from-version <version> Source version (default: 1.0.0)
  -t, --to-version <version>  Target version (default: 2.0.0)
  --dry-run                   Show what would be migrated without making changes
  --backup                    Create backup before migration (default: true)

EXAMPLES:
  topokit migrate --dry-run
  topokit migrate --from-version=1.0.0 --to-version=2.0.0
  topokit migrate --backup
`,

    drift: `
Drift detection and alerting

USAGE:
  topokit drift [options]

OPTIONS:
  -d, --pack-dir <dir>        Topology pack directory (default: ./topology)
  -b, --baseline <file>       Baseline metrics file (default: ./topology/baseline.json)
  -t, --threshold <threshold> Drift threshold percentage (default: 10)
  --detect                    Detect drift in current execution
  --baseline-create           Create baseline from current metrics
  --alert                     Send alerts for detected drift

EXAMPLES:
  topokit drift --detect
  topokit drift --baseline-create
  topokit drift --detect --threshold=5 --alert
`,

    replay: `
Replay topology execution with deterministic testing

USAGE:
  topokit replay [options]

OPTIONS:
  -d, --pack-dir <dir>        Topology pack directory (default: ./topology)
  -t, --test-file <file>      Test file to replay (default: ./topology/eval/replay.yaml)
  --seed <seed>               Random seed for deterministic execution (default: stable)
  --verbose                   Verbose output

EXAMPLES:
  topokit replay
  topokit replay --seed=12345 --verbose
  topokit replay --test-file=./custom-replay.yaml
`,

    generate: `
Code generation and scaffolding

USAGE:
  topokit generate [options]

OPTIONS:
  -d, --pack-dir <dir>        Topology pack directory (default: ./topology)
  -t, --type <type>           Generation type (default: node)
  -n, --name <name>           Name for generated component
  --template <template>       Template to use for generation
  --output <output>           Output directory (default: ./generated)
  --force                     Overwrite existing files

EXAMPLES:
  topokit generate --type=node --name=MyNode
  topokit generate --type=contract --name=myContract
  topokit generate --type=test --name=myTest
`,

    docs: `
Documentation generation

USAGE:
  topokit docs [options]

OPTIONS:
  -d, --pack-dir <dir>        Topology pack directory (default: ./topology)
  -o, --output <dir>          Output directory for documentation (default: ./docs)
  -f, --format <format>       Documentation format (default: markdown)
  --api                       Generate API documentation
  --architecture              Generate architecture documentation
  --user-guide                Generate user guide
  --all                       Generate all documentation types

EXAMPLES:
  topokit docs --all
  topokit docs --api --format=html
  topokit docs --architecture --user-guide
`
  };

  const help = commandHelp[command];
  if (help) {
    console.log(chalk.blue.bold(`\nTopoKit ${command} Command\n`));
    console.log(help);
  } else {
    console.log(chalk.red(`Unknown command: ${command}`));
    console.log(chalk.gray('Use "topokit help" to see available commands'));
  }
}
