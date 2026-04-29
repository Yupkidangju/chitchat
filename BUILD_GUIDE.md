# BUILD_GUIDE.md

## 문서 메타

- 문서 버전: `v0.1.0b0`
- 상위 문서: `spec.md v0.1 BETA`
- 목적: 처음 이 프로젝트를 클론한 사람이 이 문서만 보고 첫 실행을 성공시켜야 한다.

---

## 1. 사전 준비

### 1.1 필수 소프트웨어

| 소프트웨어 | 버전 | 설치 확인 명령 |
|---|---|---|
| Python | `3.12+` (권장 3.13) | `python --version` |
| pip | 최신 | `python -m pip --version` |
| Git | 최신 | `git --version` |

### 1.2 OS별 추가 요구사항

| OS | 추가 요구 |
|---|---|
| Windows 11+ | 없음 (Python 설치에 pip 포함) |
| macOS 14+ | Xcode Command Line Tools (`xcode-select --install`) |
| Ubuntu 24.04+ | `sudo apt install python3.13 python3.13-venv libxcb-cursor0 libgl1` |

### 1.3 Keyring 백엔드

| OS | 기본 백엔드 |
|---|---|
| Windows | Windows Credential Manager (기본 제공) |
| macOS | Keychain (기본 제공) |
| Linux | SecretService (GNOME Keyring 또는 KDE Wallet 필요) |

Linux에서 SecretService 백엔드가 없으면 API Key 저장이 실패한다. 다음을 설치한다:

```bash
# GNOME 환경
sudo apt install gnome-keyring

# KDE 환경
sudo apt install kwalletmanager
```

---

## 2. 안전한 스캐폴딩 절차

### 2.1 프로젝트 루트에 기존 문서가 있을 때

프로젝트 루트에 `.md` 파일이 존재하면 프레임워크 초기화 도구를 루트에서 직접 실행하지 않는다.

Python 프로젝트는 별도 스캐폴딩 도구가 필요 없다. `pyproject.toml`과 `src/` 디렉토리를 수동 생성한다.

### 2.2 디렉토리 생성

```bash
# 프로젝트 루트에서 실행
mkdir -p src/chitchat/config
mkdir -p src/chitchat/db
mkdir -p src/chitchat/domain
mkdir -p src/chitchat/providers
mkdir -p src/chitchat/secrets
mkdir -p src/chitchat/services
mkdir -p src/chitchat/ui/pages
mkdir -p src/chitchat/ui/widgets
mkdir -p src/chitchat/ui/viewmodels
mkdir -p tests
mkdir -p alembic/versions
```

### 2.3 필수 `__init__.py` 생성

```bash
find src/chitchat -type d -exec touch {}/__init__.py \;
```

---

## 3. 필수 설치 항목

### 3.1 가상환경 생성

```bash
python -m venv .venv
```

### 3.2 가상환경 활성화

```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate
```

### 3.3 의존성 설치

```bash
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

이 명령은 `pyproject.toml`의 `dependencies`와 `dev` optional-dependencies를 모두 설치한다.

---

## 4. pyproject.toml 필수 구조

```toml
[build-system]
requires = ["setuptools>=75", "wheel"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "chitchat"
version = "0.1.0b0"
requires-python = ">=3.12"
dependencies = [
  "PySide6>=6.11,<6.12",
  "SQLAlchemy>=2.0.49,<2.1",
  "alembic>=1.18.4,<1.19",
  "pydantic>=2.12,<3",
  "pydantic-settings>=2.7,<3",
  "httpx>=0.28,<0.29",
  "keyring>=25.7,<26",
  "google-genai>=1.73,<2",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.3,<9",
  "pytest-asyncio>=0.25,<1",
  "ruff>=0.8,<1",
  "mypy>=1.14,<2",
  "pyinstaller>=6.20,<7",
]

[tool.setuptools.packages.find]
where = ["src"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
ignore = ["E701", "E702"]

[tool.ruff.lint.per-file-ignores]
"src/chitchat/ui/**" = ["E501"]

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

---

## 5. 런타임 출력 경로

| OS | App Data 경로 | DB 파일 |
|---|---|---|
| Windows | `%APPDATA%\chitchat\` | `chitchat.sqlite3` |
| macOS | `~/Library/Application Support/chitchat/` | `chitchat.sqlite3` |
| Linux | `${XDG_DATA_HOME:-~/.local/share}/chitchat/` | `chitchat.sqlite3` |

앱 최초 실행 시 `paths.py`의 `ensure_app_dirs()`가 디렉토리와 하위 폴더(`logs/`, `exports/`, `backups/`)를 자동 생성한다.

---

## 6. 엔트리 파일 연결

### 6.1 main.py

```python
# src/chitchat/main.py
# 앱 엔트리 포인트. QApplication 생성 후 create_app()을 호출한다.
import sys
from PySide6.QtWidgets import QApplication
from chitchat.app import create_app

def main() -> None:
    qt_app = QApplication(sys.argv)
    window = create_app()
    window.show()
    sys.exit(qt_app.exec())

if __name__ == "__main__":
    main()
```

### 6.2 app.py

```python
# src/chitchat/app.py
# create_app() 팩토리: Settings → DB → Services → MainWindow
from chitchat.config.paths import ensure_app_dirs
from chitchat.config.settings import AppSettings
from chitchat.db.engine import create_db_engine, create_session_factory
from chitchat.db.models import Base
from chitchat.db.repositories import RepositoryRegistry
from chitchat.providers.registry import ProviderRegistry
from chitchat.ui.main_window import MainWindow
from chitchat.ui.theme import build_global_stylesheet

def create_app() -> tuple[QApplication, MainWindow]:
    settings = AppSettings()
    ensure_app_dirs(settings.app_data_dir)
    engine = create_db_engine(settings.db_path)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    repos = RepositoryRegistry(session_factory)
    # ... 서비스 생성, 페이지 등록
    return app, window
```

---

## 7. Alembic 설정

### 7.1 alembic.ini 핵심 항목

```ini
[alembic]
script_location = alembic
sqlalchemy.url = sqlite:///%(here)s/chitchat.sqlite3

[loggers]
keys = root,sqlalchemy,alembic
```

실제 런타임에서는 `alembic.ini`의 URL이 아닌 `migrations.py`에서 프로그래밍 방식으로 engine URL을 주입한다.

### 7.2 첫 마이그레이션 생성

```bash
alembic revision --autogenerate -m "initial_schema"
alembic upgrade head
```

---

## 8. 첫 실행

```bash
# 가상환경 활성화 상태에서
python -m chitchat.main
```

정상 실행 시:

1. App data 디렉토리 생성됨
2. `chitchat.sqlite3` 파일 생성됨
3. `Base.metadata.create_all(engine)` 으로 테이블 생성됨
4. MainWindow 표시됨
5. Chat 페이지에 Setup Checklist Empty State 표시됨

> **참고 (v0.1.0b0)**: 현재 버전에서는 `Base.metadata.create_all(engine)`만 사용하여 DB를 초기화한다.
> Alembic 마이그레이션은 스키마가 포함되어 있으나, 앱 시작 시 자동 실행되지는 않는다.
> 기존 DB 스키마를 변경해야 하는 v0.2 이후부터 `run_migrations(engine)`를 앱 시작에 통합할 예정이다.
> 수동으로 마이그레이션이 필요하면 `alembic upgrade head`를 실행한다.

---

## 9. 개발 명령어

### 9.1 코드 품질

```bash
# 린팅
ruff check .

# 타입 검사
mypy src

# 테스트
pytest -q

# 전체 검증 (CI와 동일)
ruff check . && mypy src && pytest -q
```

### 9.2 마이그레이션

```bash
# 새 마이그레이션 생성
alembic revision --autogenerate -m "description"

# 마이그레이션 적용
alembic upgrade head

# 마이그레이션 롤백 (1단계)
alembic downgrade -1
```

---

## 10. 패키징

### 10.1 PyInstaller 빌드

```bash
pyinstaller --noconfirm --windowed --name chitchat src/chitchat/main.py
```

### 10.2 빌드 산출물 확인

빌드 성공 시 아래 파일이 생성되어야 한다:

```txt
dist/chitchat/          ← one-folder 패키지
  chitchat              ← 실행 파일 (Windows: chitchat.exe)
  _internal/            ← 의존성 번들
build/                  ← 빌드 중간 파일
chitchat.spec           ← PyInstaller spec (pyproject.toml과 별개)
```

### 10.3 빌드 후 검증

```bash
# 패키지 실행
./dist/chitchat/chitchat

# 확인할 것:
# 1. MainWindow가 정상 표시됨
# 2. App data 디렉토리가 생성됨
# 3. SQLite DB 파일이 생성됨
# 4. Provider 페이지에서 폼이 렌더링됨
```

---

## 11. 배포 전 체크리스트

- [x] `ruff check .` 경고 없음
- [x] `pytest -q` 전체 통과 (129개)
- [x] SC-01 ~ SC-10 수용 테스트 자동화 통과
- [x] PyInstaller spec 작성 완료
- [ ] PyInstaller one-folder 빌드 성공 (OS별 수동 확인)
- [ ] 빌드된 앱에서 Provider 등록 → 채팅 전체 플로우 동작
- [x] API Key가 SQLite에 평문으로 저장되지 않음 확인
- [x] CHANGELOG.md에 v0.1.0b0 항목 기록
- [x] README.md 다국어 작성 완료

---

## 12. 흔한 실패와 해결

| 실패 증상 | 원인 | 해결 |
|---|---|---|
| `ModuleNotFoundError: chitchat` | `pip install -e .` 미실행 | `pip install -e ".[dev]"` 실행 |
| `ImportError: PySide6` | Python 버전 불일치 | Python 3.13.13 확인 |
| `KeyringError` | Linux에서 SecretService 미설치 | `gnome-keyring` 또는 `kwalletmanager` 설치 |
| Alembic `Can't locate revision` | 마이그레이션 파일 누락 | `alembic revision --autogenerate` 실행 |
| PyInstaller `hidden import` | PySide6 플러그인 누락 | `--hidden-import PySide6.QtWidgets` 추가 |
| `xcb` 관련 에러 (Linux) | X11 라이브러리 누락 | `libxcb-cursor0` 설치 |
