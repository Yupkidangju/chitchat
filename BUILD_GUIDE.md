# BUILD_GUIDE.md

## 문서 메타

- 문서 버전: `v1.0.0`
- 상위 문서: `spec.md v1.0.0`
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
| Ubuntu 24.04+ | `sudo apt install python3.13 python3.13-venv` |

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
mkdir -p src/chitchat/api/routes
mkdir -p src/chitchat/config
mkdir -p src/chitchat/db
mkdir -p src/chitchat/domain
mkdir -p src/chitchat/providers
mkdir -p src/chitchat/secrets
mkdir -p src/chitchat/services
mkdir -p frontend/css
mkdir -p frontend/js/pages
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
# pip를 항상 최신으로 유지
python -m pip install --upgrade pip

# requirements.txt 기반 의존성 설치
pip install -r requirements.txt

# 현재 프로젝트 모듈(chitchat) 설치
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
version = "1.0.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115,<1",
  "uvicorn[standard]>=0.34,<1",
  "SQLAlchemy>=2.0.49,<2.1",
  "alembic>=1.18.4,<1.19",
  "pydantic>=2.12,<3",
  "pydantic-settings>=2.7,<3",
  "httpx>=0.28,<0.29",
  "keyring>=25.7,<26",
  "google-genai>=1.73,<2",
  "zstandard>=0.23,<1",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.3,<9",
  "pytest-asyncio>=0.25,<1",
  "ruff>=0.8,<1",
]

[tool.setuptools.packages.find]
where = ["src"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
ignore = ["E701", "E702"]

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
# [v1.0.0] FastAPI + Uvicorn 앱 엔트리 포인트.
# DB 초기화 → FastAPI 라우트 등록 → 정적 파일 서빙 → Uvicorn 실행.

import uvicorn
from chitchat.app import create_app

app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

### 6.2 app.py

```python
# src/chitchat/app.py
# create_app() 팩토리: Settings → DB → Services → FastAPI 라우트 등록.

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from chitchat.config.paths import ensure_app_dirs
from chitchat.config.settings import AppSettings
from chitchat.db.engine import create_db_engine, create_session_factory
from chitchat.db.migrations import run_migrations

def create_app() -> FastAPI:
    settings = AppSettings()
    ensure_app_dirs(settings.app_data_dir)
    engine = create_db_engine(settings.db_path)
    run_migrations(engine)
    # ... 라우트 등록, 정적 파일 마운트
    return app
```

---

## 7. Alembic 설정

### 7.1 데이터베이스 마이그레이션

- `run_migrations(engine)` 단일 호출로 신규 DB 스키마 생성과 기존 DB 업그레이드를 모두 처리한다.
- 내부적으로 `alembic_version` 테이블과 컬럼 존재 여부를 분석하여 신규/기존/partial DB를 자동 감지한다.

### 7.2 alembic.ini 핵심 항목

```ini
[alembic]
script_location = alembic
sqlalchemy.url = sqlite:///%(here)s/chitchat.sqlite3

[loggers]
keys = root,sqlalchemy,alembic
```

실제 런타임에서는 `alembic.ini`의 URL이 아닌 `migrations.py`에서 프로그래밍 방식으로 engine URL을 주입한다.

### 7.3 첫 마이그레이션 생성

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
3. `run_migrations(engine)` → Alembic이 전체 스키마 생성
4. FastAPI 서버가 `http://127.0.0.1:8000`에서 시작됨
5. 브라우저에서 `http://localhost:8000` 접속 시 채팅 페이지 표시됨

> **참고 (v1.0.0)**: 앱 시작 시 `run_migrations(engine)`이 호출되어 기존 DB 스키마가 최신 상태로 유지된다. 수동으로 마이그레이션이 필요하면 `alembic upgrade head`를 실행한다.

---

## 9. 개발 명령어

### 9.1 코드 품질

```bash
# 린팅
ruff check .

# 테스트
pytest -q

# 전체 검증
ruff check src/ tests/ && pytest -q
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

## 10. 배포 전 체크리스트

- [x] `ruff check .` 경고 없음
- [x] `pytest -q` 전체 통과 (213건)
- [x] SC-01~02, SC-06~08 수용 테스트 통과
- [ ] SC-03~05, SC-09 수용 테스트 (실제 Provider API 필요, 수동 확인)
- [x] API Key가 SQLite에 평문으로 저장되지 않음 확인
- [x] CHANGELOG.md에 v1.0.0 항목 기록
- [x] README.md 다국어 작성 완료

---

## 11. 흔한 실패와 해결

| 실패 증상 | 원인 | 해결 |
|---|---|---|
| `ModuleNotFoundError: chitchat` | `pip install -e .` 미실행 | `pip install -e ".[dev]"` 실행 |
| `KeyringError` | Linux에서 SecretService 미설치 | `gnome-keyring` 또는 `kwalletmanager` 설치 |
| Alembic `Can't locate revision` | 마이그레이션 파일 누락 | `alembic revision --autogenerate` 실행 |
| `Address already in use` | 포트 8000 충돌 | 기존 프로세스 종료 또는 `--port 8001` 사용 |
