# Contributing to TopoKit

Thank you for your interest in contributing to TopoKit! This document provides guidelines and information for contributors.

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+
- pnpm 8+
- Git

### Development Setup

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/your-username/topokit.git
   cd topokit
   ```

2. **Set up Python environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -e packages/core/
   pip install pytest pytest-cov black isort flake8 mypy
   ```

3. **Set up Node.js environment:**
   ```bash
   cd packages/cli
   pnpm install
   pnpm run build
   ```

4. **Run the setup script:**
   ```bash
   ./scripts/setup-dev.sh
   ```

## 🧪 Testing

### Python Tests

```bash
# Run all Python tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=topokit --cov-report=html

# Run specific test file
pytest tests/unit/test_pack_parser.py -v
```

### TypeScript Tests

```bash
cd packages/cli
pnpm test
pnpm test --coverage
```

### Integration Tests

```bash
# Test CLI with Python core
cd packages/cli
node dist/index.js init --template rag-system --output /tmp/test-integration
cd /tmp/test-integration
node /path/to/topokit/packages/cli/dist/index.js lint
```

## 📝 Code Style

### Python

We use the following tools for Python code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking

```bash
# Format code
black topokit/ tests/
isort topokit/ tests/

# Lint code
flake8 topokit/ tests/
mypy topokit/
```

### TypeScript

We use the following tools for TypeScript code quality:

- **ESLint**: Linting
- **Prettier**: Code formatting
- **TypeScript**: Type checking

```bash
cd packages/cli
pnpm run lint
pnpm run lint:fix
pnpm run type-check
```

## 🔧 Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Your Changes

- Write code following our style guidelines
- Add tests for new functionality
- Update documentation as needed

### 3. Test Your Changes

```bash
# Run all tests
pytest tests/
cd packages/cli && pnpm test

# Run linting
flake8 topokit/ tests/
cd packages/cli && pnpm run lint
```

### 4. Commit Your Changes

```bash
git add .
git commit -m "feat: add amazing new feature"
```

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `style:` Code style changes
- `refactor:` Code refactoring
- `test:` Test additions/changes
- `chore:` Build process or auxiliary tool changes

### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

## 📋 Pull Request Guidelines

### Before Submitting

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] New functionality is tested
- [ ] Documentation is updated
- [ ] Commit messages follow conventional format

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

## 🐛 Reporting Issues

### Bug Reports

When reporting bugs, please include:

1. **Environment information:**
   - Python version
   - Node.js version
   - Operating system
   - TopoKit version

2. **Steps to reproduce:**
   - Clear, numbered steps
   - Expected vs actual behavior
   - Error messages or logs

3. **Additional context:**
   - Screenshots if applicable
   - Related issues or PRs

### Feature Requests

When requesting features, please include:

1. **Use case description:**
   - What problem does this solve?
   - How would you use this feature?

2. **Proposed solution:**
   - High-level approach
   - Any design considerations

3. **Alternatives considered:**
   - Other approaches you've thought about

## 🏗️ Architecture Guidelines

### Python Core (`packages/core/`)

- Use Pydantic for data validation
- Follow functional programming principles where possible
- Write comprehensive docstrings
- Use type hints throughout

### TypeScript CLI (`packages/cli/`)

- Use Commander.js for CLI interface
- Follow functional programming principles
- Write comprehensive JSDoc comments
- Use strict TypeScript settings

### Testing Strategy

- **Unit tests**: Test individual functions/methods
- **Integration tests**: Test component interactions
- **End-to-end tests**: Test complete workflows
- **Property-based tests**: Test with generated data

## 📚 Documentation

### Code Documentation

- Write clear docstrings for all public functions
- Include type information in docstrings
- Provide usage examples where helpful

### User Documentation

- Update README.md for user-facing changes
- Add/update CLI help text
- Create diagrams for complex workflows

## 🔒 Security

### Security Considerations

- Never commit secrets or API keys
- Use environment variables for configuration
- Validate all user inputs
- Follow secure coding practices

### Reporting Security Issues

For security vulnerabilities, please email security@topokit.dev instead of creating a public issue.

## 🎯 Areas for Contribution

### High Priority

- **Orchestrator Runtime**: DAG execution engine
- **Context Store**: State management system
- **Guardrails**: Safety constraint enforcement
- **VS Code Extension**: Developer tooling

### Medium Priority

- **Performance Optimization**: Caching and batching
- **Cloud Integration**: AWS/Azure/GCP support
- **Monitoring Dashboard**: Observability tools
- **Documentation**: User guides and tutorials

### Low Priority

- **Additional Templates**: More project templates
- **Language Support**: Additional programming languages
- **UI Components**: Web-based topology editor

## 🤝 Community

### Getting Help

- **GitHub Discussions**: For questions and discussions
- **GitHub Issues**: For bug reports and feature requests
- **Discord**: For real-time chat (coming soon)

### Code of Conduct

We follow the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). Please be respectful and inclusive in all interactions.

## 📄 License

By contributing to TopoKit, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to TopoKit! 🎉
