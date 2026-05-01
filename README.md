# chitchat

## 🇰🇷 한국어

### 소개

`chitchat`은 Provider, 모델, 모델 파라미터, 사용자 페르소나, AI 페르소나, 로어북, 세계관, 프롬프트 조합 순서를 저장하고 조합해 대화 세션을 실행하는 Python 크로스플랫폼 데스크톱 AI 채팅 앱입니다.

### 주요 기능

- **다중 Provider 지원**: Gemini, OpenRouter, LM Studio를 하나의 인터페이스로 사용
- **모델 Capability 기반 설정**: 모델이 지원하는 파라미터만 표시하여 설정 오류 방지
- **프롬프트 조립 시스템**: AI 페르소나, 로어북, 세계관, 사용자 페르소나를 조합하여 프롬프트 생성
- **Vibe Fill AI 자동 생성 (v0.2)**: 짧은 바이브 텍스트를 바탕으로 AI 캐릭터, 로어북, 10개 카테고리의 세계관 엔트리를 자동 생성
- **프롬프트 Inspector**: 실제 요청 직전 조합된 프롬프트와 로어북 매칭 결과를 실시간 검증
- **스트리밍 채팅**: 실시간 스트리밍 응답과 Stop 취소 지원
- **안전한 키 저장**: OS 키링을 사용하여 API Key를 안전하게 보호

### 기술 스택

- Python 3.13 | PySide6 | SQLAlchemy + SQLite | Pydantic v2 | httpx | keyring

### 설치 및 실행

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e ".[dev]"
python -m chitchat.main
```

자세한 설치 가이드는 [BUILD_GUIDE.md](BUILD_GUIDE.md)를 참고하세요.

> 💡 **v0.2.0 업데이트 안내**: v0.2.0부터는 앱 시작 시 데이터베이스 스키마 자동 마이그레이션을 지원합니다.

---

## 🇺🇸 English

### Introduction

`chitchat` is a Python cross-platform desktop AI chat application that stores and combines Providers, models, model parameters, user personas, AI personas, lorebooks, worldbooks, and prompt assembly orders to run conversation sessions.

### Key Features

- **Multi-Provider Support**: Use Gemini, OpenRouter, and LM Studio through a single interface
- **Model Capability-Based Settings**: Display only parameters supported by the selected model
- **Prompt Assembly System**: Combine AI personas, lorebooks, worldbooks, and user personas to build prompts
- **Vibe Fill AI Auto-Generation (v0.2)**: Automatically generate AI characters, lorebooks, and worldbook entries across 10 categories based on brief vibe texts
- **Prompt Inspector**: Verify assembled prompts and lorebook matching results before each request
- **Streaming Chat**: Real-time streaming responses with Stop cancellation support
- **Secure Key Storage**: Protect API keys using the OS keyring

### Tech Stack

- Python 3.13 | PySide6 | SQLAlchemy + SQLite | Pydantic v2 | httpx | keyring

### Installation & Running

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e ".[dev]"
python -m chitchat.main
```

See [BUILD_GUIDE.md](BUILD_GUIDE.md) for the full installation guide.

> 💡 **v0.2.0 Update Notice**: Starting from v0.2.0, the app supports automatic database schema migration upon startup.

---

## 🇯🇵 日本語

### はじめに

`chitchat`は、Provider、モデル、モデルパラメータ、ユーザーペルソナ、AIペルソナ、ロアブック、ワールドブック、プロンプト組み立て順序を保存・組み合わせて会話セッションを実行するPythonクロスプラットフォームデスクトップAIチャットアプリです。

### 主な機能

- **マルチProvider対応**: Gemini、OpenRouter、LM Studioを単一インターフェースで使用
- **モデルCapabilityベースの設定**: モデルがサポートするパラメータのみ表示
- **プロンプト組み立てシステム**: AIペルソナ、ロアブック、ワールドブック、ユーザーペルソナを組み合わせてプロンプトを生成
- **プロンプトInspector**: リクエスト直前に組み立てられたプロンプトとロアブックマッチング結果をリアルタイム検証
- **ストリーミングチャット**: リアルタイムストリーミング応答とStopキャンセル対応
- **安全なキー保管**: OSキーリングを使用してAPIキーを安全に保護

### インストールと実行

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e ".[dev]"
python -m chitchat.main
```

> 💡 **v0.2.0 アップデートのお知らせ**: v0.2.0から、アプリ起動時のデータベーススキーマの自動マイグレーションをサポートします。

---

## 🇹🇼 繁體中文

### 簡介

`chitchat` 是一款 Python 跨平台桌面 AI 聊天應用程式，可儲存並組合 Provider、模型、模型參數、使用者角色、AI 角色、知識庫、世界觀和提示詞組裝順序來執行對話工作階段。

### 主要功能

- **多 Provider 支援**: 透過單一介面使用 Gemini、OpenRouter 和 LM Studio
- **基於模型能力的設定**: 僅顯示所選模型支援的參數
- **提示詞組裝系統**: 組合 AI 角色、知識庫、世界觀和使用者角色來建立提示詞
- **提示詞檢查器**: 在每次請求前驗證組裝的提示詞和知識庫匹配結果
- **串流聊天**: 即時串流回應，支援停止取消
- **安全金鑰儲存**: 使用 OS 金鑰鏈保護 API 金鑰

### 安裝與執行

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e ".[dev]"
python -m chitchat.main
```

> 💡 **v0.2.0 更新公告**: 從 v0.2.0 開始，應用程式啟動時支援資料庫架構的自動遷移。

---

## 🇨🇳 简体中文

### 简介

`chitchat` 是一款 Python 跨平台桌面 AI 聊天应用程序，可存储并组合 Provider、模型、模型参数、用户角色、AI 角色、知识库、世界观和提示词组装顺序来执行对话会话。

### 主要功能

- **多 Provider 支持**: 通过单一界面使用 Gemini、OpenRouter 和 LM Studio
- **基于模型能力的设置**: 仅显示所选模型支持的参数
- **提示词组装系统**: 组合 AI 角色、知识库、世界观和用户角色来构建提示词
- **提示词检查器**: 在每次请求前验证组装的提示词和知识库匹配结果
- **流式聊天**: 实时流式响应，支持停止取消
- **安全密钥存储**: 使用 OS 密钥链保护 API 密钥

### 安装与运行

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m chitchat.main
```

> 💡 **v0.2.0 更新公告**: 从 v0.2.0 开始，应用程序启动时支持数据库架构的自动迁移。

---

## License

MIT License — 자세한 내용은 [LICENSE](LICENSE) 파일을 참고하세요.

## Contributing

기여를 환영합니다! 이슈를 생성하거나 Pull Request를 제출해 주세요.

- **버그 리포트**: GitHub Issues에 등록
- **기능 제안**: Discussion 또는 Issue로 제안
- **코드 기여**: Fork → Branch → PR 패턴
- **커밋 메시지**: [Conventional Commits](https://www.conventionalcommits.org/) 형식 준수
