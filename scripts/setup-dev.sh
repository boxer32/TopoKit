#!/bin/bash

# TopoKit Development Setup Script
# This script sets up the development environment for TopoKit

set -e

echo "🚀 Setting up TopoKit development environment..."

# Check Python version
echo "📋 Checking Python version..."
python3 --version

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🐍 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install package in development mode
echo "📦 Installing TopoKit in development mode..."
pip install -e .

# Install development dependencies
echo "🛠️ Installing development dependencies..."
pip install pytest pytest-cov black isort flake8 mypy

# Verify installation
echo "✅ Verifying installation..."
topokit --help

# Run tests
echo "🧪 Running tests..."
pytest tests/ -v

echo "🎉 Development environment setup complete!"
echo ""
echo "To activate the environment in the future, run:"
echo "  source venv/bin/activate"
echo ""
echo "To run tests:"
echo "  pytest tests/ -v"
echo ""
echo "To lint code:"
echo "  black packages/core/"
echo "  isort packages/core/"
echo "  flake8 packages/core/"
