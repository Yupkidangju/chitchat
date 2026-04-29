#!/usr/bin/env python3
# scripts/build.py
# [v0.1.0b0] 크로스플랫폼 빌드 스크립트
#
# 지원:
# 1. 멀티 플랫폼 (Windows, macOS, Linux)
# 2. 명령형(CLI) / 인터랙티브 지원
# 3. /output 폴더에 산출물 저장

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"

def run_cmd(cmd: list[str], cwd: Path | None = None, check: bool = True) -> bool:
    """명령어를 실행하고 성공 여부를 반환한다."""
    print(f"🔄 실행 중: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, cwd=cwd or PROJECT_ROOT, check=check)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 명령어 실패 (종료 코드 {e.returncode}): {' '.join(cmd)}")
        return False
    except FileNotFoundError:
        print(f"❌ 명령어를 찾을 수 없습니다: {cmd[0]}")
        return False

def prompt_yes_no(question: str, default: bool = True) -> bool:
    """인터랙티브 환경에서 Yes/No를 묻는다."""
    default_str = "[Y/n]" if default else "[y/N]"
    while True:
        resp = input(f"{question} {default_str}: ").strip().lower()
        if not resp:
            return default
        if resp in ("y", "yes"):
            return True
        if resp in ("n", "no"):
            return False
        print("y 또는 n을 입력해주세요.")

def check_dependencies() -> bool:
    """빌드에 필요한 도구가 설치되어 있는지 확인한다."""
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("⚠️ PyInstaller가 설치되어 있지 않습니다.")
        if prompt_yes_no("지금 requirements.txt를 통해 설치하시겠습니까?"):
            return run_cmd([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        return False
    return True

def main() -> None:
    parser = argparse.ArgumentParser(description="Chitchat 멀티플랫폼 빌드 스크립트")
    parser.add_argument("--interactive", action="store_true", help="인터랙티브 모드로 실행")
    parser.add_argument("--skip-tests", action="store_true", help="코드 검증(ruff, pytest) 건너뛰기")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT_DIR), help="빌드 산출물 저장 경로")
    parser.add_argument("--clean", action="store_true", help="빌드 전 이전 캐시 지우기")
    
    args = parser.parse_args()

    # 인터랙티브 모드일 경우 값을 다시 묻기
    if args.interactive:
        print("=== Chitchat 인터랙티브 빌드 설정 ===")
        ans_test = prompt_yes_no("코드 검증(ruff, pytest)을 실행하시겠습니까?", default=not args.skip_tests)
        args.skip_tests = not ans_test
        
        ans_clean = prompt_yes_no("기존 빌드 캐시를 지우시겠습니까?", default=True)
        args.clean = ans_clean

        custom_output = input(f"출력 폴더를 지정하세요 (기본값: {args.output}): ").strip()
        if custom_output:
            args.output = custom_output

    out_dir = Path(args.output).resolve()
    
    os.chdir(PROJECT_ROOT)
    print(f"\n=== Chitchat 빌드 스크립트 ===")
    print(f"현재 플랫폼: {platform.system()} ({platform.release()})")
    print(f"출력 폴더: {out_dir}")
    
    if not check_dependencies():
        print("❌ 의존성 부족으로 빌드를 중단합니다.")
        sys.exit(1)

    # 1. 코드 검증
    if not args.skip_tests:
        print("\n--- [1/3] 코드 검증 ---")
        if not run_cmd([sys.executable, "-m", "ruff", "check", "."]):
            if args.interactive and not prompt_yes_no("Ruff 검증 실패. 계속 진행하시겠습니까?", default=False):
                sys.exit(1)
            elif not args.interactive:
                sys.exit(1)
                
        if not run_cmd([sys.executable, "-m", "pytest", "tests/", "-q", "--tb=short"]):
            if args.interactive and not prompt_yes_no("Pytest 실패. 계속 진행하시겠습니까?", default=False):
                sys.exit(1)
            elif not args.interactive:
                sys.exit(1)
        print("✅ 검증 통과!")
    else:
        print("\n--- [1/3] 코드 검증 생략 ---")

    # 2. PyInstaller 빌드
    print("\n--- [2/3] PyInstaller 빌드 ---")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    build_cmd = [
        "pyinstaller", 
        "chitchat.spec", 
        "--noconfirm",
        "--distpath", str(out_dir),
        "--workpath", str(PROJECT_ROOT / "build")
    ]
    if args.clean:
        build_cmd.append("--clean")
        
    if not run_cmd(build_cmd):
        print("❌ 빌드 실패!")
        sys.exit(1)
    
    print("✅ 빌드 완료!")

    # 3. 산출물 확인
    print("\n--- [3/3] 산출물 확인 ---")
    target_dir = out_dir / "chitchat"
    if target_dir.exists():
        print(f"✅ {target_dir} 폴더 생성 확인됨")
        exe_name = "chitchat.exe" if platform.system() == "Windows" else "chitchat"
        exe_path = target_dir / exe_name
        if exe_path.exists():
            print(f"✅ 실행 파일 존재: {exe_path}")
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"   크기: {size_mb:.2f} MB")
        else:
            print("⚠️ 경고: 실행 파일을 찾을 수 없습니다.")
    else:
        print("❌ 예상한 출력 디렉토리가 없습니다.")
        sys.exit(1)

    print("\n=== 모든 작업 성공! ===")
    print(f"결과물 경로: {target_dir}")

if __name__ == "__main__":
    main()
