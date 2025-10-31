# TopoKit VS Code Extension

VS Code extension for TopoKit topology-first contract system development.

## Features

- **Pack Explorer**: Tree view of topology packs, nodes, edges, contracts, and guardrails
- **Lint-on-Save**: Real-time validation of topology files
- **Graph View**: Interactive visualization of topology structure
- **Contract Validation**: Inline validation and hover information
- **Test Runner**: Execute TopoKit tests from VS Code
- **Debug Console**: Step-through execution debugging (coming soon)

## Development

```bash
# Install dependencies
npm install

# Compile
npm run compile

# Watch mode
npm run watch

# Package extension
vsce package
```

## Installation

```bash
# Install from package
code --install-extension topokit-vscode-0.1.0.vsix
```

