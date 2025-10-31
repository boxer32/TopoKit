#!/bin/bash
echo "🚀 Quick Frontend Validation"
echo ""
echo "📦 Structure Check:"
components=$(find src/components -name "*.tsx" 2>/dev/null | wc -l | tr -d ' ')
pages=$(find src/pages -name "*.tsx" 2>/dev/null | wc -l | tr -d ' ')
monitoring=$(find src/monitoring -name "*.tsx" 2>/dev/null | wc -l | tr -d ' ')
echo "   Components: $components"
echo "   Pages: $pages"
echo "   Monitoring: $monitoring"
echo ""
echo "🔧 Config Files:"
configs=$(ls package.json tsconfig.json vite.config.ts index.html 2>/dev/null | wc -l | tr -d ' ')
echo "   Found: $configs/4"
echo ""
echo "✅ Validation: Complete"
