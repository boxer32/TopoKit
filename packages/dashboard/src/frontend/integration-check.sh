#!/bin/bash

echo "🔍 Frontend Integration Check"
echo "=============================="
echo ""

# Check if node_modules exists
if [ -d "node_modules" ]; then
    echo "✅ Dependencies installed"
else
    echo "⚠️  Dependencies not installed"
    echo "   Run: npm install"
    exit 1
fi

# Type check
echo ""
echo "📝 Type Checking..."
if npx tsc --noEmit 2>&1 | grep -q "error TS"; then
    echo "❌ Type errors found"
    npx tsc --noEmit 2>&1 | head -10
    exit 1
else
    echo "✅ Type check passed"
fi

# Check build
echo ""
echo "🏗️  Building..."
if npm run build 2>&1 | grep -q "error\|Error\|ERROR"; then
    echo "❌ Build failed"
    npm run build 2>&1 | tail -20
    exit 1
else
    echo "✅ Build successful"
    if [ -d "dist" ]; then
        echo "   Build output: dist/"
        ls -lh dist/ | head -5
    fi
fi

# Check backend connectivity
echo ""
echo "🌐 Backend Connectivity Check..."
if curl -s http://localhost:8080/api/v1/health > /dev/null 2>&1; then
    echo "✅ Backend server is running"
    curl -s http://localhost:8080/api/v1/health | python3 -m json.tool 2>/dev/null || echo "   Response received"
else
    echo "⚠️  Backend server not reachable"
    echo "   Start with: cd packages/dashboard && python -m uvicorn src.api.server:app --reload --port 8080"
fi

echo ""
echo "✅ Integration check complete!"
echo ""
echo "Next steps:"
echo "  1. Start backend: cd packages/dashboard && python -m uvicorn src.api.server:app --reload --port 8080"
echo "  2. Start frontend: npm run dev"
echo "  3. Open: http://localhost:3000"

