# -*- mode: python ; coding: utf-8 -*-
# chitchat.spec
# [v0.3.0] PyInstaller 빌드 스펙
#
# `pyinstaller chitchat.spec` 으로 빌드한다.
# one-folder 모드. PySide6 플러그인 및 alembic 데이터 포함.

import sys
from pathlib import Path

block_cipher = None
root = Path(SPECPATH)

a = Analysis(
    [str(root / 'src' / 'chitchat' / 'main.py')],
    pathex=[str(root / 'src')],
    binaries=[],
    datas=[
        # Alembic 설정 및 마이그레이션 파일
        (str(root / 'alembic.ini'), '.'),
        (str(root / 'alembic'), 'alembic'),
        # [v0.3.0] i18n 번역 사전 파일
        (str(root / 'src' / 'chitchat' / 'i18n' / 'locales'), 'chitchat/i18n/locales'),
    ],
    hiddenimports=[
        # PySide6 필수 플러그인
        'PySide6.QtWidgets',
        'PySide6.QtCore',
        'PySide6.QtGui',
        # SQLAlchemy 드라이버
        'sqlalchemy.dialects.sqlite',
        # Pydantic
        'pydantic',
        'pydantic_settings',
        # Keyring 백엔드
        'keyring.backends',
        # httpx 전송
        'httpx',
        'httpcore',
        # google-genai
        'google.genai',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 테스트/개발 도구 제외
        'pytest',
        'ruff',
        'mypy',
        'pyinstaller',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='chitchat',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # --windowed 모드
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='chitchat',
)
