#!/bin/bash
# SessionStart Hook - Skills Cookbook 환경 검사
# 이 hook은 각 Claude Code session 시작 시 환경 설정을 확인하기 위해 실행

set -e

echo "🔍 Skills Cookbook - Environment Check"
echo "======================================"

# virtual environment에 있는지 확인
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  WARNING: No virtual environment detected!"
    echo "   Run: source venv/bin/activate"
    echo ""
fi

# Anthropic SDK 설치 여부 확인 및 version 가져오기
if python -c "import anthropic" 2>/dev/null; then
    SDK_VERSION=$(python -c "import anthropic; print(anthropic.__version__)" 2>/dev/null || echo "unknown")
    echo "✅ Anthropic SDK: $SDK_VERSION"
    # Skills 지원 최소 version 확인
    if [[ "$SDK_VERSION" < "0.71.0" ]]; then
        echo "⚠️  SDK version $SDK_VERSION may be too old (minimum 0.71.0 for Skills support)"
        echo "   Run: pip install anthropic>=0.71.0"
        echo ""
    fi
else
    echo "❌ Anthropic SDK not installed"
    echo "   Run: pip install -r requirements.txt"
    echo ""
fi

# API key 확인
if [[ -f ".env" ]]; then
    if grep -q "^ANTHROPIC_API_KEY=sk-" .env 2>/dev/null; then
        echo "✅ API key configured in .env"
    else
        echo "⚠️  .env exists but API key may not be set"
        echo "   Check ANTHROPIC_API_KEY in .env"
        echo ""
    fi
else
    echo "⚠️  .env file not found"
    echo "   Run: cp .env.example .env"
    echo "   Then add your ANTHROPIC_API_KEY"
    echo ""
fi

# outputs directory 확인
if [[ -d "outputs" ]]; then
    FILE_COUNT=$(find outputs -type f 2>/dev/null | wc -l | tr -d ' ')
    echo "✅ outputs/ directory exists ($FILE_COUNT files)"
else
    echo "ℹ️  Creating outputs/ directory..."
    mkdir -p outputs
fi

# plan의 현재 상태 표시
if [[ -f "docs/skills_cookbook_plan.md" ]]; then
    echo ""
    echo "📊 Current Status:"
    PHASE_STATUS=$(grep -A1 "^**Phase:**" docs/skills_cookbook_plan.md 2>/dev/null | tail -1 || echo "Unknown")
    echo "   $PHASE_STATUS"
fi

echo ""
echo "======================================"
echo "Ready to work on Skills Cookbook! 🚀"
echo ""
echo "Quick commands:"
echo "  - jupyter notebook              # Launch notebooks"
echo "  - ls outputs/                   # View generated files"
echo "  - cat CLAUDE.md                 # View project guide"
