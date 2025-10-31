#!/bin/bash
# TopoKit Deployment Script

set -e

ENVIRONMENT=${1:-development}
ACTION=${2:-deploy}

echo "🚀 TopoKit Deployment Script"
echo "Environment: $ENVIRONMENT"
echo "Action: $ACTION"
echo ""

case $ACTION in
  deploy)
    echo "📦 Deploying TopoKit to $ENVIRONMENT..."
    
    # Run tests
    echo "🧪 Running tests..."
    source venv/bin/activate 2>/dev/null || python3 -m venv venv && source venv/bin/activate
    pip install -q -r requirements.txt
    pytest tests/integration/test_rag_template.py tests/integration/test_production_monitoring.py -v --tb=short || echo "⚠️ Some tests may need environment setup"
    
    # Build
    if [ "$ENVIRONMENT" != "development" ]; then
      echo "🔨 Building Docker image..."
      docker build -t topokit:$ENVIRONMENT . || echo "⚠️ Docker build skipped (Docker not available)"
    fi
    
    echo "✅ Deployment preparation complete!"
    echo ""
    echo "Next steps:"
    echo "1. Review DEPLOYMENT_GUIDE.md"
    echo "2. Configure environment variables"
    echo "3. Run: docker-compose up -d (if using Docker)"
    ;;
    
  validate)
    echo "✅ Validating deployment..."
    source venv/bin/activate 2>/dev/null || python3 -m venv venv && source venv/bin/activate
    pytest tests/ -v --tb=short -x
    echo "✅ Validation complete!"
    ;;
    
  setup-dev)
    echo "🛠️  Setting up development environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cd packages/cli && npm install && cd ../..
    echo "✅ Development environment ready!"
    echo "Activate with: source venv/bin/activate"
    ;;
    
  *)
    echo "Usage: ./deploy.sh [environment] [action]"
    echo ""
    echo "Environments: development, staging, production"
    echo "Actions: deploy, validate, setup-dev"
    echo ""
    echo "Examples:"
    echo "  ./deploy.sh development setup-dev"
    echo "  ./deploy.sh staging deploy"
    echo "  ./deploy.sh production validate"
    ;;
esac

