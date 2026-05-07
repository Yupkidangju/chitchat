# -*- mode: python ; coding: utf-8 -*-
# chitchat.spec
# [v1.0.0] PyInstaller 빌드 스펙 — FastAPI + Uvicorn + 프론트엔드 번들
#
# 사용법: pyinstaller chitchat.spec --noconfirm
# 결과물: output/chitchat/ (one-folder 패키지)

import os
from pathlib import Path

# 프로젝트 루트 경로
PROJECT_ROOT = Path(SPECPATH)

# frontend 정적 파일을 data로 포함
frontend_dir = PROJECT_ROOT / "frontend"

# Alembic 마이그레이션 파일을 data로 포함
alembic_dir = PROJECT_ROOT / "alembic"
alembic_ini = PROJECT_ROOT / "alembic.ini"

# i18n 로케일 파일 포함
locale_dir = PROJECT_ROOT / "src" / "chitchat" / "i18n" / "locales"

# datas: (소스 경로, 번들 내 상대 경로) 튜플 리스트
datas = [
    (str(frontend_dir), "frontend"),
]

# Alembic이 존재하면 포함
if alembic_dir.exists():
    datas.append((str(alembic_dir), "alembic"))
if alembic_ini.exists():
    datas.append((str(alembic_ini), "."))

# 로케일이 존재하면 포함
if locale_dir.exists():
    datas.append((str(locale_dir), os.path.join("chitchat", "i18n", "locales")))

# FastAPI/Uvicorn/의존성의 hidden import
hiddenimports = [
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    "fastapi",
    "starlette",
    "starlette.responses",
    "starlette.routing",
    "starlette.middleware",
    "starlette.middleware.cors",
    "starlette.staticfiles",
    "anyio",
    "anyio._backends",
    "anyio._backends._asyncio",
    "httptools",
    "dotenv",
    "email_validator",
    "multipart",
    "chitchat.main",
    "chitchat.api.app",
    "chitchat.api.routes.chat",
    "chitchat.api.routes.health",
    "chitchat.api.routes.personas",
    "chitchat.api.routes.profiles",
    "chitchat.api.routes.providers",
    "chitchat.api.routes.settings",
]

a = Analysis(
    [str(PROJECT_ROOT / "src" / "chitchat" / "main.py")],
    pathex=[str(PROJECT_ROOT / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "scipy",
        "PIL",
        "PySide6",
        "PyQt5",
        "PyQt6",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="chitchat",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="chitchat",
)
