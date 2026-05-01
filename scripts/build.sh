#!/usr/bin/env bash
# scripts/build.sh
# Python 기반 멀티플랫폼 빌드 스크립트로 위임합니다.

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# 가상환경이 활성화되어 있지 않다면 자동 활성화
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -d ".venv" ]; then
        source .venv/bin/activate
        echo "🔄 가상환경(.venv)을 자동으로 활성화했습니다."
    elif [ -d "venv" ]; then
        source venv/bin/activate
        echo "🔄 가상환경(venv)을 자동으로 활성화했습니다."
    fi
fi

python3 scripts/build.py "$@"
