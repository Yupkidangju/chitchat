#!/usr/bin/env bash
# scripts/build.sh
# [v0.1.0b0] 빌드 스크립트: 검증 → 빌드 → 확인
#
# 사용법: bash scripts/build.sh
#
# 1단계: ruff + pytest 검증
# 2단계: PyInstaller 빌드
# 3단계: 산출물 확인
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== chitchat 빌드 스크립트 ==="
echo "프로젝트 루트: $PROJECT_ROOT"
echo ""

# 1단계: 코드 품질 검증
echo "--- [1/3] 코드 품질 검증 ---"
echo "ruff check..."
ruff check .
echo "pytest..."
pytest tests/ -q --tb=short
echo "✅ 검증 통과!"
echo ""

# 2단계: PyInstaller 빌드
echo "--- [2/3] PyInstaller 빌드 ---"
pyinstaller chitchat.spec --noconfirm --clean
echo "✅ 빌드 완료!"
echo ""

# 3단계: 산출물 확인
echo "--- [3/3] 산출물 확인 ---"
DIST_DIR="$PROJECT_ROOT/dist/chitchat"
if [ -d "$DIST_DIR" ]; then
    echo "✅ dist/chitchat/ 디렉토리 존재"
    if [ -f "$DIST_DIR/chitchat" ] || [ -f "$DIST_DIR/chitchat.exe" ]; then
        echo "✅ 실행 파일 존재"
        ls -lh "$DIST_DIR/chitchat"* 2>/dev/null || true
    else
        echo "❌ 실행 파일을 찾을 수 없습니다"
        exit 1
    fi
else
    echo "❌ dist/chitchat/ 디렉토리를 찾을 수 없습니다"
    exit 1
fi

echo ""
echo "=== 빌드 성공! ==="
echo "실행: $DIST_DIR/chitchat"
