#!/usr/bin/env python3
# scripts/build.py
# [v1.0.0] 크로스플랫폼 빌드 스크립트
#
# FastAPI + Uvicorn 웹 서버를 PyInstaller로 패키징한다.
# 실행 파일 실행 시 로컬 서버가 시작되고 브라우저가 자동으로 열린다.
#
# 지원:
# 1. 멀티 플랫폼 (Windows, macOS, Linux)
# 2. 명령형(CLI) / 인터랙티브(--interactive) 지원
# 3. /output 폴더에 산출물 저장
# 4. 빌드 후 ZIP 패키징 옵션
# 5. 빌드 시간 측정 및 상세 리포트
#
# 사용법 (명령형):
#   python scripts/build.py                    # 기본 빌드
#   python scripts/build.py --skip-tests       # 테스트 건너뛰기
#   python scripts/build.py --clean --zip      # 캐시 정리 + ZIP 생성
#   python scripts/build.py --interactive      # 인터랙티브 모드
#
# 사용법 (인터랙티브):
#   python scripts/build.py --interactive

from __future__ import annotations

import argparse
import os
import platform
import shutil
import stat
import subprocess
import sys
import time
import zipfile
from pathlib import Path

# ──────────────────────────────────────────────────────────────
# 상수
# ──────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"
SPEC_FILE = PROJECT_ROOT / "chitchat.spec"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
BUILD_DIR = PROJECT_ROOT / "build"

# 플랫폼별 실행 파일 이름
EXE_NAME = "chitchat.exe" if platform.system() == "Windows" else "chitchat"

# ANSI 색상 — Windows에서도 지원하기 위해 os.system 호출로 VT100 활성화
if platform.system() == "Windows":
    os.system("")  # Windows 터미널에서 ANSI 시퀀스 활성화

# 색상 코드 (터미널 지원 여부에 따라 비활성화)
_SUPPORTS_COLOR = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    """ANSI 색상 코드를 적용한다. 터미널이 아니면 평문 반환."""
    if not _SUPPORTS_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


def _green(text: str) -> str:
    return _c("32", text)


def _red(text: str) -> str:
    return _c("31", text)


def _yellow(text: str) -> str:
    return _c("33", text)


def _cyan(text: str) -> str:
    return _c("36", text)


def _bold(text: str) -> str:
    return _c("1", text)


# ──────────────────────────────────────────────────────────────
# 플랫폼 감지
# ──────────────────────────────────────────────────────────────

def get_platform_info() -> dict[str, str]:
    """현재 플랫폼의 상세 정보를 수집한다."""
    info: dict[str, str] = {
        "os": platform.system(),
        "os_version": platform.version(),
        "release": platform.release(),
        "arch": platform.machine(),
        "python": platform.python_version(),
        "python_path": sys.executable,
    }

    # OS별 추가 정보
    if info["os"] == "Darwin":
        info["display_name"] = f"macOS {platform.mac_ver()[0]} ({info['arch']})"
    elif info["os"] == "Windows":
        info["display_name"] = f"Windows {platform.win32_ver()[1]} ({info['arch']})"
    elif info["os"] == "Linux":
        # Linux 배포판 정보 수집 시도
        try:
            import distro  # type: ignore[import-untyped]
            info["display_name"] = f"{distro.name()} {distro.version()} ({info['arch']})"
        except ImportError:
            info["display_name"] = f"Linux {info['release']} ({info['arch']})"
    else:
        info["display_name"] = f"{info['os']} {info['release']} ({info['arch']})"

    return info


# ──────────────────────────────────────────────────────────────
# 유틸리티
# ──────────────────────────────────────────────────────────────

def ensure_venv() -> None:
    """가상환경이 활성화되어 있지 않다면 프로젝트 내의 .venv 또는 venv를 찾아 재실행한다."""
    if os.environ.get("VIRTUAL_ENV"):
        return

    for venv_name in [".venv", "venv"]:
        venv_path = PROJECT_ROOT / venv_name
        if venv_path.is_dir():
            if platform.system() == "Windows":
                bin_dir = venv_path / "Scripts"
                python_exe = bin_dir / "python.exe"
            else:
                bin_dir = venv_path / "bin"
                python_exe = bin_dir / "python"

            if python_exe.exists() and str(Path(sys.executable).resolve()) != str(python_exe.resolve()):
                print(f"🔄 가상환경({venv_name}) 파이썬으로 재실행합니다: {python_exe}")
                os.environ["VIRTUAL_ENV"] = str(venv_path)
                os.environ["PATH"] = f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"
                os.execv(str(python_exe), [str(python_exe)] + sys.argv)


def run_cmd(
    cmd: list[str],
    cwd: Path | None = None,
    check: bool = True,
    capture: bool = False,
) -> tuple[bool, str]:
    """명령어를 실행하고 (성공 여부, 출력) 튜플을 반환한다."""
    print(f"  {_cyan('▶')} {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd or PROJECT_ROOT,
            check=check,
            capture_output=capture,
            text=True,
        )
        output = (result.stdout or "") if capture else ""
        return True, output
    except subprocess.CalledProcessError as e:
        output = (e.stdout or "") + (e.stderr or "") if capture else ""
        print(f"  {_red('✗')} 명령어 실패 (종료 코드 {e.returncode})")
        return False, output
    except FileNotFoundError:
        print(f"  {_red('✗')} 명령어를 찾을 수 없습니다: {cmd[0]}")
        return False, ""


def prompt_yes_no(question: str, default: bool = True) -> bool:
    """인터랙티브 환경에서 Yes/No를 묻는다."""
    default_str = "[Y/n]" if default else "[y/N]"
    while True:
        resp = input(f"  {_yellow('?')} {question} {default_str}: ").strip().lower()
        if not resp:
            return default
        if resp in ("y", "yes"):
            return True
        if resp in ("n", "no"):
            return False
        print("    y 또는 n을 입력해주세요.")


def prompt_choice(question: str, choices: list[str], default: int = 0) -> int:
    """인터랙티브 환경에서 선택지를 묻는다. 0-indexed 결과를 반환한다."""
    print(f"\n  {_yellow('?')} {question}")
    for i, choice in enumerate(choices):
        marker = _green("●") if i == default else "○"
        print(f"    {marker} [{i + 1}] {choice}")
    while True:
        resp = input(f"    선택 (기본값: {default + 1}): ").strip()
        if not resp:
            return default
        try:
            idx = int(resp) - 1
            if 0 <= idx < len(choices):
                return idx
        except ValueError:
            pass
        print(f"    1~{len(choices)} 사이의 숫자를 입력해주세요.")


def format_time(seconds: float) -> str:
    """초 단위 시간을 사람이 읽기 쉬운 형태로 변환한다."""
    if seconds < 60:
        return f"{seconds:.1f}초"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}분 {secs:.1f}초"


def format_size(bytes_size: int) -> str:
    """바이트 크기를 사람이 읽기 쉬운 형태로 변환한다."""
    if bytes_size < 1024:
        return f"{bytes_size} B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.1f} KB"
    elif bytes_size < 1024 * 1024 * 1024:
        return f"{bytes_size / (1024 * 1024):.1f} MB"
    return f"{bytes_size / (1024 * 1024 * 1024):.2f} GB"


def get_dir_size(path: Path) -> int:
    """디렉토리의 전체 크기(바이트)를 재귀적으로 계산한다."""
    total = 0
    for f in path.rglob("*"):
        if f.is_file():
            total += f.stat().st_size
    return total


# ──────────────────────────────────────────────────────────────
# 빌드 단계
# ──────────────────────────────────────────────────────────────

def check_prerequisites() -> tuple[bool, list[str]]:
    """빌드에 필요한 모든 전제 조건을 확인한다.

    반환: (모두 통과 여부, 경고 메시지 리스트)
    """
    warnings: list[str] = []
    all_ok = True

    # 1. Python 버전
    py_ver = sys.version_info
    if py_ver < (3, 12):
        print(f"  {_red('✗')} Python 3.12+ 필요 (현재: {py_ver.major}.{py_ver.minor})")
        all_ok = False
    else:
        print(f"  {_green('✓')} Python {py_ver.major}.{py_ver.minor}.{py_ver.micro}")

    # 2. PyInstaller
    try:
        import PyInstaller
        print(f"  {_green('✓')} PyInstaller {PyInstaller.__version__}")
    except ImportError:
        print(f"  {_red('✗')} PyInstaller가 설치되어 있지 않습니다")
        all_ok = False

    # 3. chitchat.spec
    if SPEC_FILE.exists():
        print(f"  {_green('✓')} chitchat.spec")
    else:
        print(f"  {_red('✗')} chitchat.spec 파일 없음")
        all_ok = False

    # 4. frontend 디렉토리
    if FRONTEND_DIR.exists():
        file_count = sum(1 for _ in FRONTEND_DIR.rglob("*") if _.is_file())
        print(f"  {_green('✓')} frontend/ ({file_count}개 파일)")
    else:
        print(f"  {_red('✗')} frontend/ 디렉토리 없음")
        all_ok = False

    # 5. 가상환경
    if os.environ.get("VIRTUAL_ENV"):
        print(f"  {_green('✓')} 가상환경 활성화됨")
    else:
        warnings.append("가상환경 미활성화 — 시스템 Python으로 빌드됩니다")
        print(f"  {_yellow('△')} 가상환경 미활성화")

    # 6. OS별 추가 확인
    if platform.system() == "Linux":
        # UPX 존재 확인 (선택)
        if shutil.which("upx"):
            print(f"  {_green('✓')} UPX 압축기 사용 가능")
        else:
            warnings.append("UPX 미설치 — 실행 파일 크기가 더 클 수 있습니다")
            print(f"  {_yellow('△')} UPX 미설치 (선택)")

    return all_ok, warnings


def install_pyinstaller() -> bool:
    """PyInstaller를 설치한다."""
    print(f"\n  {_cyan('▶')} PyInstaller 설치 중...")
    ok, _ = run_cmd([sys.executable, "-m", "pip", "install", "pyinstaller>=6.20,<7"])
    return ok


def run_code_verification(interactive: bool) -> bool:
    """린트와 테스트를 실행한다."""
    print(f"\n{'─' * 60}")
    print(f"  {_bold('[1/3] 코드 검증')}")
    print(f"{'─' * 60}")

    # Ruff 린팅
    print("\n  📋 Ruff 린트 검사...")
    ok, _ = run_cmd([sys.executable, "-m", "ruff", "check", "src/", "tests/"])
    if not ok:
        if interactive and prompt_yes_no("Ruff 검증 실패. 계속 진행하시겠습니까?", default=False):
            pass
        else:
            return False

    # Pytest
    print("\n  🧪 테스트 실행...")
    ok, _ = run_cmd([sys.executable, "-m", "pytest", "tests/", "-q", "--tb=short"])
    if not ok:
        if interactive and prompt_yes_no("테스트 실패. 계속 진행하시겠습니까?", default=False):
            pass
        else:
            return False

    print(f"\n  {_green('✓')} 코드 검증 통과!")
    return True


def run_pyinstaller_build(out_dir: Path, clean: bool) -> bool:
    """PyInstaller 빌드를 실행한다."""
    print(f"\n{'─' * 60}")
    print(f"  {_bold('[2/3] PyInstaller 빌드')}")
    print(f"{'─' * 60}")

    out_dir.mkdir(parents=True, exist_ok=True)

    build_cmd = [
        sys.executable, "-m", "PyInstaller",
        str(SPEC_FILE),
        "--noconfirm",
        "--distpath", str(out_dir),
        "--workpath", str(BUILD_DIR),
    ]
    if clean:
        build_cmd.append("--clean")

    print()
    ok, _ = run_cmd(build_cmd)
    if not ok:
        print(f"\n  {_red('✗')} PyInstaller 빌드 실패!")
        return False

    # Linux/macOS: 실행 파일에 실행 권한 설정
    exe_path = out_dir / "chitchat" / EXE_NAME
    if exe_path.exists() and platform.system() != "Windows":
        exe_path.chmod(exe_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    print(f"\n  {_green('✓')} PyInstaller 빌드 성공!")
    return True


def verify_artifacts(out_dir: Path) -> dict[str, str | int | bool]:
    """빌드 산출물을 검증하고 상세 정보를 반환한다."""
    print(f"\n{'─' * 60}")
    print(f"  {_bold('[3/3] 산출물 검증')}")
    print(f"{'─' * 60}")

    result: dict[str, str | int | bool] = {"success": True}
    target_dir = out_dir / "chitchat"

    if not target_dir.exists():
        print(f"\n  {_red('✗')} 출력 디렉토리 없음: {target_dir}")
        result["success"] = False
        return result

    # 실행 파일 검증
    exe_path = target_dir / EXE_NAME
    if exe_path.exists():
        exe_size = exe_path.stat().st_size
        print(f"  {_green('✓')} 실행 파일: {EXE_NAME} ({format_size(exe_size)})")
        result["exe_size"] = exe_size
    else:
        print(f"  {_red('✗')} 실행 파일 미생성: {EXE_NAME}")
        result["success"] = False

    # 프론트엔드 번들 검증
    frontend_bundle = target_dir / "_internal" / "frontend"
    if frontend_bundle.exists():
        fe_size = get_dir_size(frontend_bundle)
        fe_files = sum(1 for _ in frontend_bundle.rglob("*") if _.is_file())
        print(f"  {_green('✓')} 프론트엔드 번들: {fe_files}개 파일 ({format_size(fe_size)})")
        result["frontend_size"] = fe_size
    else:
        print(f"  {_yellow('△')} 프론트엔드 번들 미포함")

    # 전체 크기
    total_size = get_dir_size(target_dir)
    print(f"  {_green('✓')} 전체 패키지 크기: {format_size(total_size)}")
    result["total_size"] = total_size
    result["target_dir"] = str(target_dir)

    return result


def create_zip_package(out_dir: Path) -> Path | None:
    """빌드 산출물을 ZIP으로 패키징한다.

    파일명 형식: chitchat-v1.0.0-{os}-{arch}.zip
    """
    target_dir = out_dir / "chitchat"
    if not target_dir.exists():
        return None

    os_name = platform.system().lower()
    arch = platform.machine().lower()
    zip_name = f"chitchat-v1.0.0-{os_name}-{arch}.zip"
    zip_path = out_dir / zip_name

    print(f"\n  📦 ZIP 패키징 중: {zip_name}")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for file in target_dir.rglob("*"):
            if file.is_file():
                arcname = file.relative_to(out_dir)
                zf.write(file, arcname)

    zip_size = zip_path.stat().st_size
    print(f"  {_green('✓')} ZIP 생성 완료: {zip_name} ({format_size(zip_size)})")
    return zip_path


# ──────────────────────────────────────────────────────────────
# 메인 로직
# ──────────────────────────────────────────────────────────────

def main() -> None:
    ensure_venv()

    parser = argparse.ArgumentParser(
        description="Chitchat v1.0.0 빌드 스크립트 — FastAPI + Uvicorn + PyInstaller",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  python scripts/build.py                   기본 빌드 (검증 → 빌드 → 확인)
  python scripts/build.py --skip-tests      코드 검증 생략
  python scripts/build.py --clean --zip     캐시 정리 + ZIP 생성
  python scripts/build.py --interactive     인터랙티브 모드
        """,
    )
    parser.add_argument(
        "--interactive", "-i", action="store_true",
        help="인터랙티브 모드 — 각 단계별 옵션을 묻습니다",
    )
    parser.add_argument(
        "--skip-tests", action="store_true",
        help="코드 검증(ruff, pytest) 건너뛰기",
    )
    parser.add_argument(
        "--output", "-o", type=str, default=str(DEFAULT_OUTPUT_DIR),
        help=f"빌드 산출물 저장 경로 (기본값: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--clean", action="store_true",
        help="빌드 전 이전 캐시 지우기",
    )
    parser.add_argument(
        "--zip", action="store_true",
        help="빌드 후 ZIP 패키지 생성",
    )

    args = parser.parse_args()
    start_time = time.time()

    # ── 헤더 출력 ──
    pinfo = get_platform_info()
    print()
    print(f"  {_bold('╔══════════════════════════════════════════════════╗')}")
    print(f"  {_bold('║')}  💬 Chitchat v1.0.0 빌드 스크립트              {_bold('║')}")
    print(f"  {_bold('║')}  FastAPI + Uvicorn + Vanilla JS SPA            {_bold('║')}")
    print(f"  {_bold('╚══════════════════════════════════════════════════╝')}")
    print()
    print(f"  플랫폼:   {pinfo['display_name']}")
    print(f"  Python:   {pinfo['python']} ({pinfo['python_path']})")

    # ── 인터랙티브 모드 설정 ──
    if args.interactive:
        print(f"\n  {_bold('── 인터랙티브 설정 ──')}")

        args.skip_tests = not prompt_yes_no("코드 검증(ruff, pytest)을 실행하시겠습니까?", default=True)
        args.clean = prompt_yes_no("기존 빌드 캐시를 지우시겠습니까?", default=True)
        args.zip = prompt_yes_no("빌드 후 ZIP 패키지를 생성하시겠습니까?", default=False)

        custom_output = input(f"  {_yellow('?')} 출력 폴더 (기본값: {args.output}): ").strip()
        if custom_output:
            args.output = custom_output

    out_dir = Path(args.output).resolve()
    print(f"  출력:     {out_dir}")

    # ── 전제 조건 확인 ──
    print(f"\n  {_bold('── 전제 조건 확인 ──')}")
    prereq_ok, prereq_warnings = check_prerequisites()

    if not prereq_ok:
        # PyInstaller가 없으면 설치 제안
        try:
            import PyInstaller  # noqa: F401
        except ImportError:
            if args.interactive:
                if prompt_yes_no("PyInstaller를 지금 설치하시겠습니까?"):
                    if install_pyinstaller():
                        prereq_ok = True
            else:
                print(f"\n  {_red('✗')} PyInstaller를 설치해주세요: pip install pyinstaller>=6.20")

        if not prereq_ok:
            print(f"\n  {_red('✗')} 전제 조건 미충족 — 빌드를 중단합니다.")
            sys.exit(1)

    if prereq_warnings:
        for w in prereq_warnings:
            print(f"  {_yellow('△')} {w}")

    os.chdir(PROJECT_ROOT)

    # ── 단계 1: 코드 검증 ──
    if not args.skip_tests:
        if not run_code_verification(args.interactive):
            print(f"\n  {_red('✗')} 코드 검증 실패 — 빌드를 중단합니다.")
            sys.exit(1)
    else:
        print(f"\n{'─' * 60}")
        print(f"  {_bold('[1/3] 코드 검증')} — {_yellow('생략')}")
        print(f"{'─' * 60}")

    # ── 단계 2: PyInstaller 빌드 ──
    if not run_pyinstaller_build(out_dir, args.clean):
        sys.exit(1)

    # ── 단계 3: 산출물 검증 ──
    artifacts = verify_artifacts(out_dir)
    if not artifacts.get("success"):
        print(f"\n  {_red('✗')} 산출물 검증 실패!")
        sys.exit(1)

    # ── 단계 4: ZIP 패키징 (선택) ──
    zip_path = None
    if args.zip:
        zip_path = create_zip_package(out_dir)

    # ── 최종 리포트 ──
    elapsed = time.time() - start_time
    target_dir = artifacts.get("target_dir", str(out_dir / "chitchat"))
    exe_path = Path(target_dir) / EXE_NAME

    print()
    print(f"  {_bold('╔══════════════════════════════════════════════════╗')}")
    print(f"  {_bold('║')}  {_green('✓ 빌드 성공!')}                                   {_bold('║')}")
    print(f"  {_bold('╚══════════════════════════════════════════════════╝')}")
    print()
    print(f"  소요 시간:  {format_time(elapsed)}")
    print(f"  플랫폼:     {pinfo['display_name']}")
    print(f"  실행 파일:  {exe_path}")
    print(f"  패키지:     {format_size(artifacts.get('total_size', 0))}")  # type: ignore[arg-type]
    if zip_path:
        print(f"  ZIP:        {zip_path.name} ({format_size(zip_path.stat().st_size)})")
    print()

    # OS별 실행 안내
    if platform.system() == "Windows":
        print(f"  실행 방법:  {exe_path}")
    elif platform.system() == "Darwin":
        print(f"  실행 방법:  ./{exe_path.relative_to(PROJECT_ROOT)}")
        print("  참고:       macOS Gatekeeper 경고 시 '시스템 설정 → 보안'에서 허용하세요.")
    else:
        print(f"  실행 방법:  ./{exe_path.relative_to(PROJECT_ROOT)}")

    print()
    print("  → 실행 시 http://localhost:8000 에서 서버가 시작되고")
    print("    브라우저가 자동으로 열립니다.")
    print()


if __name__ == "__main__":
    main()
