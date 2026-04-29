#!/usr/bin/env bash
# scripts/build.sh
# Python 기반 멀티플랫폼 빌드 스크립트로 위임합니다.

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

python3 scripts/build.py "$@"
