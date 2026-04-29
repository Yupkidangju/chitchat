# chitchat Implementation Spec (v0.1 BETA)

## 0. Global Documentation Rules

- 문서 버전: `v0.1 BETA`
- 프로젝트명: `chitchat`
- 문서 상태: Initial Specification & Implementation Entry
- 문서 우선순위: 코드보다 문서가 우선이다.
- 이 문서의 목적: 구현자가 추가 기획 회의 없이 MVP 구현을 시작할 수 있을 만큼 범위, 타입, 데이터, 화면, 검증 경로를 닫는다.
- 기준 문서:
  - `spec.md`: 마스터 계약.
  - `designs.md`: UI/UX와 화면 동작 계약.
  - `implementation_summary.md`: 구현 시작점과 파일 책임.
  - `DESIGN_DECISIONS.md`: 동결된 결정과 기각한 대안.
  - `BUILD_GUIDE.md`: 첫 실행, 빌드, 패키징 절차.
  - `audit_roadmap.md`: 구현 감사 기준.
  - `CHANGELOG.md`: 문서 변경 이력.
  - `.antigravityrules`: Google Antigravity 에이전트 운영 규칙.

### 0.1 Change Policy

| 변경 유형 | 필수 갱신 문서 |
|---|---|
| 타입/스키마 변경 | `spec.md`, `implementation_summary.md`, `audit_roadmap.md`, `CHANGELOG.md` |
| 화면/CTA 변경 | `designs.md`, `spec.md`, `audit_roadmap.md`, `CHANGELOG.md` |
| 빌드/실행 명령 변경 | `BUILD_GUIDE.md`, `spec.md`, `CHANGELOG.md` |
| Provider API 계약 변경 | `spec.md`, `implementation_summary.md`, `DESIGN_DECISIONS.md`, `CHANGELOG.md` |
| 보안/Key 저장 정책 변경 | `spec.md`, `BUILD_GUIDE.md`, `DESIGN_DECISIONS.md`, `CHANGELOG.md` |

### 0.2 Anti-Placeholder Rule

최종 구현 명세에서 아래 표현은 금지한다.

- 적당히
- 필요시
- 나중에
- 유연하게
- 자연스럽게
- 대충
- 상황에 따라

예외적으로 MVP 이후 범위를 말할 때만 `Out of Scope` 또는 `Post-MVP` 섹션에 격리한다.

---

## 1. Project Identity & Versioning

| 항목 | 값 |
|---|---|
| Project Name | `chitchat` |
| Version | `v0.1 BETA` |
| Target Tool | Google Antigravity |
| Target Platform | Cross-platform Desktop: Windows 11+, macOS 14+, Ubuntu 24.04+ |
| Language | Python |
| Runtime Pin | Python `3.12+` (권장 3.13, 최소 3.12) |
| UI Runtime | PySide6 / Qt Widgets |
| Storage | SQLite local file |
| Secrets | OS keyring via `keyring` |
| Supported Providers | Gemini, OpenRouter, LM Studio |
| License posture | RisuAI code, UI, assets, text, schema를 복제하지 않는 독립 구현 |

### 1.1 One-Sentence Product Definition

`chitchat`은 Provider, 모델, 모델 파라미터, 사용자 페르소나, AI 페르소나, 로어북, 세계관, 프롬프트 조합 순서를 저장하고 조합해 대화 세션을 실행하는 Python 크로스플랫폼 데스크톱 AI 채팅 앱이다.

---

## 2. Goals, Success Criteria, Non-Goals

### 2.1 Goals

1. Gemini, OpenRouter, LM Studio Provider를 하나의 Provider Adapter 인터페이스로 지원한다.
2. Provider와 Key 또는 endpoint를 등록하면 모델 목록을 불러온다.
3. 모델을 선택하면 모델 capability에 기반해 가능한 파라미터만 표시한다.
4. 모델 설정은 `ModelProfile`로 저장한다.
5. 사용자 페르소나를 `UserPersona`로 저장한다.
6. AI 페르소나, 로어북, 세계관을 각각 복수 생성·선택할 수 있다.
7. AI 채팅 설정 조합은 `ChatProfile`로 별도 저장한다.
8. 채팅 시작 시 `UserPersona`와 `ChatProfile`을 선택한다.
9. 프롬프트 블록 조합 순서는 설정 메뉴에서 재정렬 가능해야 한다.
10. 실제 응답 요청 직전 조합된 프롬프트와 로어북 매칭 결과를 Inspector에서 확인할 수 있다.

### 2.2 Success Criteria

MVP는 아래 10개 검증을 통과해야 완료로 본다.

| ID | 성공 기준 | 검증 방식 |
|---|---|---|
| SC-01 | ProviderProfile 3종 생성 가능 | 수동 UI + DB row 확인 |
| SC-02 | API Key는 SQLite에 평문 저장되지 않음 | DB dump 검색 |
| SC-03 | Gemini 모델 목록 로딩 가능 | 실제 API 또는 mock provider 테스트 |
| SC-04 | OpenRouter 모델 목록 로딩 가능 | 실제 API 또는 mock provider 테스트 |
| SC-05 | LM Studio `/v1/models` 로딩 가능 | 로컬 서버 또는 mock provider 테스트 |
| SC-06 | 모델 capability에 없는 파라미터는 UI에서 숨김 | unit test + 수동 UI |
| SC-07 | 로어북 키워드가 최근 8개 메시지에서 매칭됨 | unit test |
| SC-08 | PromptOrder 변경 시 최종 프롬프트 순서가 변경됨 | unit test |
| SC-09 | 스트리밍 중 Stop 버튼으로 취소 가능 | 수동 UI + service test |
| SC-10 | PyInstaller one-folder build 생성 | OS별 빌드 명령 실행 |

### 2.3 Non-Goals for v0.1 BETA

| 제외 항목 | 이유 |
|---|---|
| 모바일 앱 | Python 데스크톱 MVP 범위를 벗어남 |
| 웹 SaaS 배포 | 인증, 서버 보안, 과금 범위가 추가됨 |
| 클라우드 동기화 | 개인정보·API Key·프로필 동기화 위험 증가 |
| 이미지 생성/멀티모달 첨부 | 첫 MVP는 텍스트 채팅과 프롬프트 조립 검증이 우선 |
| RisuAI 데이터 완전 호환 import/export | 라이선스와 스키마 의존 리스크 |
| 플러그인 시스템 | 샌드박싱과 권한 모델이 필요함 |
| 자동 벡터 메모리 | MVP에서는 키워드 기반 로어북으로 고정 |
| TTS/STT | 핵심 채팅 UX 이후 단계 |
| 서버 저장형 계정 시스템 | 로컬 앱 MVP 범위 초과 |

---

## 3. Grounded Environment & Tech Stack

### 3.1 Grounding Snapshot

- 기준 날짜: 2026-04-29
- Python 다운로드 페이지 기준 최신 안정 버전은 3.14.4이나, MVP 개발 런타임은 `3.12+`로 설정하고 권장 버전은 `3.13`이다. 개발 환경에서 3.13 설치가 불가능한 경우 3.12로 대체한다.
- PySide6는 Qt for Python의 공식 Python 바인딩이며, PyPI 최신 라인은 `6.11.x`이다.
- PyInstaller는 Python 애플리케이션과 의존성을 패키징하며 Python 3.8+를 지원한다.
- Gemini API Models endpoint는 모델 목록과 모델 메타데이터, token limit, supported generation method를 제공한다.
- OpenRouter Models API는 `context_length`, `supported_parameters`, pricing, model id/name을 제공한다.
- LM Studio는 OpenAI-compatible `/v1/models` 및 `/v1/chat/completions` 엔드포인트를 제공한다.
- SQLAlchemy 2.0 라인을 사용하고 Alembic으로 마이그레이션을 관리한다.
- Pydantic v2 라인을 사용해 경계 타입을 검증한다.
- HTTPX는 sync/async API를 제공하므로 streaming Provider Adapter에 사용한다.
- `keyring`은 시스템 키링 접근 라이브러리로 API Key 평문 저장을 피한다.

### 3.2 Frozen Dependency Policy

`pyproject.toml`은 아래 범위로 시작한다.

```toml
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
```

### 3.3 Runtime Storage Paths

| OS | App Data Directory |
|---|---|
| Windows | `%APPDATA%/chitchat/` |
| macOS | `~/Library/Application Support/chitchat/` |
| Linux | `${XDG_DATA_HOME:-~/.local/share}/chitchat/` |

Files:

```txt
chitchat.sqlite3
logs/chitchat.log
exports/
backups/
```

---

## 4. Frozen Key Decisions

| ID | Decision | Frozen Value |
|---|---|---|
| D-01 | App form | 로컬 데스크톱 앱 |
| D-02 | UI toolkit | PySide6 Qt Widgets |
| D-03 | Storage | SQLite + SQLAlchemy ORM |
| D-04 | Migration | Alembic |
| D-05 | Secrets | OS keyring; DB에는 `secret_ref`만 저장 |
| D-06 | Provider boundary | `ChatProvider` Protocol |
| D-07 | Model capability | Provider 응답을 `ModelCapability`로 정규화 |
| D-08 | Prompt assembly | `PromptOrderItem` 목록에 따라 블록 조합 |
| D-09 | Lore matching | 최근 8개 메시지 키워드 매칭 |
| D-10 | Context budget | output 예약 1024 tokens, lore 최대 3000 tokens |
| D-11 | Streaming | Provider Adapter가 `AsyncIterator[ChatStreamChunk]` 반환 |
| D-12 | UI architecture | UI는 Service와 ViewModel만 호출, Provider 직접 호출 금지 |
| D-13 | RisuAI relation | 기능적 참고만 허용, 코드/문구/에셋/스키마 복제 금지 |
| D-14 | Antigravity mode | Planning Mode 필수, Fast/Turbo식 무검증 실행 금지 |

---

## 5. Architecture

```txt
chitchat
├─ UI Layer: PySide6 pages/widgets
├─ ViewModel Layer: UI state and form validation
├─ Service Layer: use cases, transactions, orchestration
├─ Domain Layer: typed profile contracts, prompt assembly, lore matching
├─ Provider Layer: Gemini/OpenRouter/LM Studio adapters
├─ Persistence Layer: SQLite + SQLAlchemy repositories
└─ Secret Layer: keyring wrapper
```

### 5.1 Dependency Rule

```txt
ui -> viewmodels -> services -> repositories/domain/providers/secrets
domain -> no dependency on ui/db/provider implementation
providers -> domain contracts + httpx/google-genai only
db -> SQLAlchemy only
secrets -> keyring only
```

### 5.2 Runtime Flow

```txt
main.py
→ create_app()
→ load Settings
→ ensure app data directory
→ create SQLite engine
→ run Alembic migrations
→ create RepositoryRegistry
→ create ProviderRegistry
→ create ServiceRegistry
→ create MainWindow
→ show MainWindow
```

---

## 6. Directory Structure

```txt
chitchat/
├── .antigravityrules
├── spec.md
├── designs.md
├── implementation_summary.md
├── DESIGN_DECISIONS.md
├── BUILD_GUIDE.md
├── audit_roadmap.md
├── CHANGELOG.md
├── README.md
├── pyproject.toml
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
├── src/
│   └── chitchat/
│       ├── __init__.py
│       ├── main.py
│       ├── app.py
│       ├── config/
│       │   ├── paths.py
│       │   └── settings.py
│       ├── db/
│       │   ├── engine.py
│       │   ├── models.py
│       │   ├── repositories.py
│       │   └── migrations.py
│       ├── domain/
│       │   ├── ids.py
│       │   ├── profiles.py
│       │   ├── provider_contracts.py
│       │   ├── prompt_blocks.py
│       │   ├── prompt_assembler.py
│       │   ├── lorebook_matcher.py
│       │   └── chat_session.py
│       ├── providers/
│       │   ├── base.py
│       │   ├── registry.py
│       │   ├── gemini_provider.py
│       │   ├── openrouter_provider.py
│       │   ├── lmstudio_provider.py
│       │   └── capability_mapper.py
│       ├── secrets/
│       │   └── key_store.py
│       ├── services/
│       │   ├── provider_service.py
│       │   ├── profile_service.py
│       │   ├── model_service.py
│       │   ├── prompt_service.py
│       │   └── chat_service.py
│       ├── ui/
│       │   ├── main_window.py
│       │   ├── navigation.py
│       │   ├── pages/
│       │   │   ├── chat_page.py
│       │   │   ├── provider_page.py
│       │   │   ├── model_profile_page.py
│       │   │   ├── persona_page.py
│       │   │   ├── ai_persona_page.py
│       │   │   ├── lorebook_page.py
│       │   │   ├── worldbook_page.py
│       │   │   ├── chat_profile_page.py
│       │   │   └── prompt_order_page.py
│       │   ├── widgets/
│       │   │   ├── model_parameter_form.py
│       │   │   ├── prompt_order_list.py
│       │   │   ├── chat_message_view.py
│       │   │   └── token_budget_bar.py
│       │   └── viewmodels/
│       │       ├── chat_vm.py
│       │       ├── provider_vm.py
│       │       └── profile_vm.py
│       └── logging_config.py
└── tests/
    ├── test_prompt_assembler.py
    ├── test_lorebook_matcher.py
    ├── test_provider_capability_mapper.py
    ├── test_profile_validation.py
    └── test_secret_storage_policy.py
```

---

## 7. IDs, Enums, and Naming Contracts

### 7.1 ID Prefixes

| Entity | Prefix | Example |
|---|---|---|
| ProviderProfile | `prov_` | `prov_gemini_main` |
| ModelCache | `mc_` | `mc_openrouter_claude_sonnet` |
| ModelProfile | `mp_` | `mp_or_roleplay_balanced` |
| UserPersona | `up_` | `up_default_writer` |
| AIPersona | `ap_` | `ap_librarian_mira` |
| Lorebook | `lb_` | `lb_city_lore` |
| LoreEntry | `le_` | `le_city_gate` |
| Worldbook | `wb_` | `wb_nocturne_city` |
| WorldEntry | `we_` | `we_magic_law` |
| ChatProfile | `cp_` | `cp_nocturne_main` |
| ChatSession | `cs_` | `cs_20260429_001` |
| ChatMessage | `cm_` | `cm_001` |

ID generation rule:

```python
def new_id(prefix: str) -> str:
    # prefix must include trailing underscore, e.g. "cp_"
    # body uses lowercase ULID-like sortable identifier.
    return f"{prefix}{generate_ulid_lower()}"
```

### 7.2 Enums

```python
from typing import Literal

ProviderKind = Literal["gemini", "openrouter", "lm_studio"]
Role = Literal["system", "user", "assistant"]
ChatSessionStatus = Literal["draft", "active", "streaming", "stopped", "failed", "archived"]
PromptBlockKind = Literal[
    "system_base",
    "ai_persona",
    "worldbook",
    "lorebook_matches",
    "user_persona",
    "chat_history",
    "current_user_message",
]
ParameterName = Literal[
    "temperature",
    "top_p",
    "top_k",
    "max_output_tokens",
    "presence_penalty",
    "frequency_penalty",
    "seed",
    "stop",
]
```

---

## 8. Typed Contracts

### 8.1 Provider Contracts

```python
from collections.abc import AsyncIterator
from typing import Protocol, Literal
from pydantic import BaseModel, Field, AnyHttpUrl

class ProviderProfileData(BaseModel):
    id: str
    name: str = Field(min_length=1, max_length=80)
    provider_kind: ProviderKind
    base_url: str | None = None
    secret_ref: str | None = None
    enabled: bool = True
    timeout_seconds: int = Field(default=60, ge=5, le=300)

class ProviderHealth(BaseModel):
    ok: bool
    provider_kind: ProviderKind
    checked_at_iso: str
    message: str
    latency_ms: int | None = None

class ModelCapability(BaseModel):
    provider_kind: ProviderKind
    model_id: str
    display_name: str
    context_window_tokens: int | None = Field(default=None, ge=1)
    max_output_tokens: int | None = Field(default=None, ge=1)
    supported_parameters: set[ParameterName]
    supports_streaming: bool
    supports_system_prompt: bool
    supports_json_mode: bool
    raw: dict

class ModelGenerationSettings(BaseModel):
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    top_k: int | None = Field(default=None, ge=1, le=500)
    max_output_tokens: int = Field(default=1024, ge=1)
    presence_penalty: float | None = Field(default=None, ge=-2.0, le=2.0)
    frequency_penalty: float | None = Field(default=None, ge=-2.0, le=2.0)
    seed: int | None = None
    stop: list[str] = Field(default_factory=list, max_length=8)

class ChatCompletionMessage(BaseModel):
    role: Role
    content: str = Field(min_length=1)

class ChatCompletionRequest(BaseModel):
    provider_profile_id: str
    model_id: str
    settings: ModelGenerationSettings
    messages: list[ChatCompletionMessage]
    stream: bool = True

class ChatStreamChunk(BaseModel):
    delta: str
    finish_reason: str | None = None
    usage: dict | None = None
    raw: dict | None = None

class ChatProvider(Protocol):
    provider_kind: ProviderKind

    async def validate_connection(self, profile: ProviderProfileData) -> ProviderHealth:
        ...

    async def list_models(self, profile: ProviderProfileData) -> list[ModelCapability]:
        ...

    async def get_model_capability(
        self,
        profile: ProviderProfileData,
        model_id: str,
    ) -> ModelCapability:
        ...

    async def stream_chat(
        self,
        profile: ProviderProfileData,
        request: ChatCompletionRequest,
    ) -> AsyncIterator[ChatStreamChunk]:
        ...
```

### 8.2 Profile Contracts

```python
class ModelProfileData(BaseModel):
    id: str
    name: str = Field(min_length=1, max_length=80)
    provider_profile_id: str
    model_id: str
    settings: ModelGenerationSettings
    created_at_iso: str
    updated_at_iso: str

class UserPersonaData(BaseModel):
    id: str
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=4000)
    speaking_style: str = Field(default="", max_length=2000)
    boundaries: str = Field(default="", max_length=2000)
    enabled: bool = True

class AIPersonaData(BaseModel):
    id: str
    name: str = Field(min_length=1, max_length=80)
    role_name: str = Field(min_length=1, max_length=120)
    personality: str = Field(min_length=1, max_length=4000)
    speaking_style: str = Field(min_length=1, max_length=3000)
    goals: str = Field(default="", max_length=3000)
    restrictions: str = Field(default="", max_length=3000)
    enabled: bool = True

class LoreEntryData(BaseModel):
    id: str
    lorebook_id: str
    title: str = Field(min_length=1, max_length=120)
    activation_keys: list[str] = Field(min_length=1, max_length=32)
    content: str = Field(min_length=1, max_length=6000)
    priority: int = Field(default=100, ge=0, le=1000)
    enabled: bool = True

class LorebookData(BaseModel):
    id: str
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=1000)
    entries: list[LoreEntryData] = Field(default_factory=list)

class WorldEntryData(BaseModel):
    id: str
    worldbook_id: str
    title: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=6000)
    priority: int = Field(default=100, ge=0, le=1000)
    enabled: bool = True

class WorldbookData(BaseModel):
    id: str
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=1000)
    entries: list[WorldEntryData] = Field(default_factory=list)
```

### 8.3 Prompt Contracts

```python
class PromptOrderItem(BaseModel):
    kind: PromptBlockKind
    enabled: bool
    order_index: int = Field(ge=0, le=100)

class ChatProfileData(BaseModel):
    id: str
    name: str = Field(min_length=1, max_length=80)
    model_profile_id: str
    ai_persona_ids: list[str] = Field(min_length=1, max_length=5)
    lorebook_ids: list[str] = Field(default_factory=list, max_length=10)
    worldbook_ids: list[str] = Field(default_factory=list, max_length=10)
    prompt_order: list[PromptOrderItem]
    system_base: str = Field(default=DEFAULT_SYSTEM_BASE, max_length=4000)
    created_at_iso: str
    updated_at_iso: str

class PromptBlock(BaseModel):
    kind: PromptBlockKind
    title: str
    content: str
    token_estimate: int
    source_ids: list[str] = Field(default_factory=list)

class AssembledPrompt(BaseModel):
    blocks: list[PromptBlock]
    messages: list[ChatCompletionMessage]
    total_token_estimate: int
    truncated_history_message_ids: list[str]
    matched_lore_entry_ids: list[str]
```

### 8.4 Chat Contracts

```python
class ChatSessionData(BaseModel):
    id: str
    title: str = Field(min_length=1, max_length=120)
    chat_profile_id: str
    user_persona_id: str
    status: ChatSessionStatus
    created_at_iso: str
    updated_at_iso: str

class ChatMessageData(BaseModel):
    id: str
    session_id: str
    role: Role
    content: str = Field(min_length=1)
    prompt_snapshot_json: str | None = None
    created_at_iso: str
    token_estimate: int
```

---

## 9. Database Schema

SQLite file: `chitchat.sqlite3`

### 9.1 Tables

#### `provider_profiles`

| Column | Type | Constraint |
|---|---|---|
| id | TEXT | PK |
| name | TEXT | NOT NULL, unique |
| provider_kind | TEXT | NOT NULL |
| base_url | TEXT | nullable |
| secret_ref | TEXT | nullable |
| enabled | INTEGER | NOT NULL, default 1 |
| timeout_seconds | INTEGER | NOT NULL, default 60 |
| created_at | TEXT | NOT NULL |
| updated_at | TEXT | NOT NULL |

#### `model_cache`

| Column | Type | Constraint |
|---|---|---|
| id | TEXT | PK |
| provider_profile_id | TEXT | FK provider_profiles.id |
| model_id | TEXT | NOT NULL |
| display_name | TEXT | NOT NULL |
| context_window_tokens | INTEGER | nullable |
| max_output_tokens | INTEGER | nullable |
| supported_parameters_json | TEXT | NOT NULL |
| supports_streaming | INTEGER | NOT NULL |
| supports_system_prompt | INTEGER | NOT NULL |
| supports_json_mode | INTEGER | NOT NULL |
| raw_json | TEXT | NOT NULL |
| fetched_at | TEXT | NOT NULL |

Unique index: `(provider_profile_id, model_id)`.

#### `model_profiles`

| Column | Type | Constraint |
|---|---|---|
| id | TEXT | PK |
| name | TEXT | NOT NULL, unique |
| provider_profile_id | TEXT | FK |
| model_id | TEXT | NOT NULL |
| settings_json | TEXT | NOT NULL |
| created_at | TEXT | NOT NULL |
| updated_at | TEXT | NOT NULL |

#### `user_personas`

| Column | Type | Constraint |
|---|---|---|
| id | TEXT | PK |
| name | TEXT | NOT NULL, unique |
| description | TEXT | NOT NULL |
| speaking_style | TEXT | NOT NULL |
| boundaries | TEXT | NOT NULL |
| enabled | INTEGER | NOT NULL |

#### `ai_personas`

| Column | Type | Constraint |
|---|---|---|
| id | TEXT | PK |
| name | TEXT | NOT NULL, unique |
| role_name | TEXT | NOT NULL |
| personality | TEXT | NOT NULL |
| speaking_style | TEXT | NOT NULL |
| goals | TEXT | NOT NULL |
| restrictions | TEXT | NOT NULL |
| enabled | INTEGER | NOT NULL |

#### `lorebooks`, `lore_entries`, `worldbooks`, `world_entries`

- Parent table stores `id`, `name`, `description`, `created_at`, `updated_at`.
- Entry table stores parent FK, `title`, `activation_keys_json` or `priority`, `content`, `enabled`.
- LoreEntry requires at least one activation key.
- WorldEntry does not use activation key in v0.1; all enabled selected world entries are inserted.

#### `chat_profiles`

| Column | Type | Constraint |
|---|---|---|
| id | TEXT | PK |
| name | TEXT | NOT NULL, unique |
| model_profile_id | TEXT | FK |
| ai_persona_ids_json | TEXT | NOT NULL |
| lorebook_ids_json | TEXT | NOT NULL |
| worldbook_ids_json | TEXT | NOT NULL |
| prompt_order_json | TEXT | NOT NULL |
| system_base | TEXT | NOT NULL |
| created_at | TEXT | NOT NULL |
| updated_at | TEXT | NOT NULL |

#### `chat_sessions`

| Column | Type | Constraint |
|---|---|---|
| id | TEXT | PK |
| title | TEXT | NOT NULL |
| chat_profile_id | TEXT | FK |
| user_persona_id | TEXT | FK |
| status | TEXT | NOT NULL |
| created_at | TEXT | NOT NULL |
| updated_at | TEXT | NOT NULL |

#### `chat_messages`

| Column | Type | Constraint |
|---|---|---|
| id | TEXT | PK |
| session_id | TEXT | FK |
| role | TEXT | NOT NULL |
| content | TEXT | NOT NULL |
| prompt_snapshot_json | TEXT | nullable |
| token_estimate | INTEGER | NOT NULL |
| created_at | TEXT | NOT NULL |

---

## 10. Provider-Specific Capability Mapping

### 10.1 Gemini

Required profile fields:

```json
{
  "provider_kind": "gemini",
  "base_url": null,
  "secret_ref": "chitchat:prov_gemini_main"
}
```

Mapping:

| Source | Target |
|---|---|
| model name | `model_id` |
| display name | `display_name` |
| input token limit | `context_window_tokens` |
| output token limit | `max_output_tokens` |
| supported generation methods | `supports_streaming`, `supports_system_prompt` inferred |
| raw metadata | `raw` |

Gemini must use `google-genai` for model metadata and content generation in v0.1. For streaming, Provider returns `ChatStreamChunk(delta=...)` for each text delta.

### 10.2 OpenRouter

Required profile fields:

```json
{
  "provider_kind": "openrouter",
  "base_url": "https://openrouter.ai/api/v1",
  "secret_ref": "chitchat:prov_openrouter_main"
}
```

Mapping:

| Source | Target |
|---|---|
| `id` | `model_id` |
| `name` | `display_name` |
| `context_length` | `context_window_tokens` |
| `top_provider.max_completion_tokens` | `max_output_tokens` |
| `supported_parameters` | `supported_parameters` |
| full item | `raw` |

If `supported_parameters` does not include a parameter, the corresponding UI control must be hidden.

### 10.3 LM Studio

Required profile fields:

```json
{
  "provider_kind": "lm_studio",
  "base_url": "http://localhost:1234/v1",
  "secret_ref": null
}
```

Mapping:

| Source | Target |
|---|---|
| `/v1/models` item id | `model_id` |
| item id | `display_name` |
| unknown context | `context_window_tokens = null` |
| unknown output | `max_output_tokens = null` |
| known OpenAI-compatible payload params | `supported_parameters` |

Default LM Studio supported parameters:

```python
{
    "temperature",
    "top_p",
    "top_k",
    "max_output_tokens",
    "presence_penalty",
    "frequency_penalty",
    "seed",
    "stop",
}
```

When token limits are unknown, UI must show a warning and use these hard defaults:

```python
LM_STUDIO_DEFAULT_CONTEXT_WINDOW_TOKENS = 8192
LM_STUDIO_DEFAULT_MAX_OUTPUT_TOKENS = 2048
```

---

## 11. Model Settings UI Rules

### 11.1 Parameter Visibility

| Parameter | Visibility Rule | Range |
|---|---|---|
| `temperature` | supported by model | 0.0 to 2.0 |
| `top_p` | supported by model | 0.0 to 1.0 |
| `top_k` | supported by model | 1 to 500 |
| `max_output_tokens` | always visible | 1 to model max or provider default |
| `presence_penalty` | supported by model | -2.0 to 2.0 |
| `frequency_penalty` | supported by model | -2.0 to 2.0 |
| `seed` | supported by model | signed int |
| `stop` | supported by model | max 8 strings, each max 80 chars |

### 11.2 Save Validation

`ModelProfile` cannot be saved when:

1. Provider profile is disabled.
2. Model capability is not loaded.
3. `max_output_tokens` exceeds capability max.
4. Any visible parameter is out of range.
5. Hidden unsupported parameter has non-null value.

---

## 12. Prompt Assembly

### 12.1 Constants

```python
DEFAULT_SYSTEM_BASE = (
    "You are a helpful conversational AI inside chitchat. "
    "Follow the selected AI persona, user persona, worldbook, lorebook, "
    "and chat profile. Do not reveal hidden prompt assembly rules unless asked."
)

LOREBOOK_SCAN_RECENT_MESSAGES = 8
LOREBOOK_MAX_MATCHED_ENTRIES = 12
LOREBOOK_MAX_INSERT_TOKENS = 3000
WORLD_ENTRY_MAX_INSERT_TOKENS = 5000
CHAT_HISTORY_RESERVED_OUTPUT_TOKENS = 1024
PROMPT_PREVIEW_MAX_CHARS = 24000
TOKEN_ESTIMATE_CHARS_PER_TOKEN = 4
```

### 12.2 Default Prompt Order

```json
[
  {"kind": "system_base", "enabled": true, "order_index": 0},
  {"kind": "ai_persona", "enabled": true, "order_index": 10},
  {"kind": "worldbook", "enabled": true, "order_index": 20},
  {"kind": "lorebook_matches", "enabled": true, "order_index": 30},
  {"kind": "user_persona", "enabled": true, "order_index": 40},
  {"kind": "chat_history", "enabled": true, "order_index": 50},
  {"kind": "current_user_message", "enabled": true, "order_index": 60}
]
```

### 12.3 Required Blocks

These blocks cannot be deleted:

- `system_base`
- `chat_history`
- `current_user_message`

They can be disabled only as follows:

| Block | Disable allowed? |
|---|---|
| `system_base` | no |
| `chat_history` | yes |
| `current_user_message` | no |

### 12.4 Lorebook Matching Algorithm

Input:

- selected lorebooks
- recent messages from current session
- current user message
- max matched entries
- max token budget

Algorithm:

```python
def match_lore_entries(lorebooks, recent_messages, current_message):
    scan_text = "\n".join(m.content for m in recent_messages[-8:]) + "\n" + current_message
    scan_text_normalized = scan_text.casefold()

    candidates = []
    for entry in all_enabled_lore_entries(lorebooks):
        for key in entry.activation_keys:
            if key.casefold().strip() and key.casefold().strip() in scan_text_normalized:
                candidates.append(entry)
                break

    candidates.sort(key=lambda e: (-e.priority, e.title.casefold(), e.id))
    selected = []
    token_sum = 0
    for entry in candidates:
        estimate = estimate_tokens(entry.content)
        if len(selected) >= 12:
            break
        if token_sum + estimate > 3000:
            continue
        selected.append(entry)
        token_sum += estimate
    return selected
```

### 12.5 Context Budget Algorithm

```python
def estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)

def available_prompt_tokens(capability, settings):
    context = capability.context_window_tokens or 8192
    output = settings.max_output_tokens or 1024
    return max(1024, context - output)

def trim_chat_history(messages, available_tokens):
    # system/persona/world/lore/current are inserted first.
    # history is added newest-first then reversed.
    selected = []
    token_sum = 0
    for msg in reversed(messages):
        t = estimate_tokens(msg.content)
        if token_sum + t > available_tokens:
            break
        selected.append(msg)
        token_sum += t
    return list(reversed(selected))
```

### 12.6 Prompt Snapshot

Every assistant message must store `prompt_snapshot_json` containing:

```json
{
  "chat_profile_id": "cp_nocturne_main",
  "user_persona_id": "up_default_writer",
  "model_profile_id": "mp_or_balanced",
  "prompt_order": [],
  "blocks": [],
  "matched_lore_entry_ids": [],
  "truncated_history_message_ids": [],
  "total_token_estimate": 5120,
  "created_at_iso": "2026-04-29T12:00:00+09:00"
}
```

---

## 13. State Machines

### 13.1 Provider Setup State

```txt
empty
→ editing
→ saved_without_secret
→ secret_saved
→ connection_tested
→ models_fetched
→ model_profile_ready
```

Invalid transitions:

- `empty -> models_fetched`
- `saved_without_secret -> connection_tested` for Gemini/OpenRouter
- `secret_saved -> models_fetched` without successful connection test

### 13.2 Chat Session State

```txt
draft
→ active
→ streaming
→ active
→ archived

streaming
→ stopped
→ active

streaming
→ failed
→ active
```

Rules:

- `Send` button is enabled only in `active`.
- `Stop` button is enabled only in `streaming`.
- `Archive` is disabled in `streaming`.
- Failed stream creates an error banner and does not delete the user message.

---

## 14. Real Seed Data

### 14.1 Provider Profiles

```json
[
  {
    "id": "prov_gemini_main",
    "name": "Gemini Main",
    "provider_kind": "gemini",
    "base_url": null,
    "secret_ref": "chitchat:prov_gemini_main",
    "enabled": true,
    "timeout_seconds": 60
  },
  {
    "id": "prov_openrouter_main",
    "name": "OpenRouter Main",
    "provider_kind": "openrouter",
    "base_url": "https://openrouter.ai/api/v1",
    "secret_ref": "chitchat:prov_openrouter_main",
    "enabled": true,
    "timeout_seconds": 90
  },
  {
    "id": "prov_lmstudio_local",
    "name": "LM Studio Local",
    "provider_kind": "lm_studio",
    "base_url": "http://localhost:1234/v1",
    "secret_ref": null,
    "enabled": true,
    "timeout_seconds": 120
  }
]
```

### 14.2 Model Capability Sample

```json
{
  "provider_kind": "openrouter",
  "model_id": "openai/gpt-4o-mini",
  "display_name": "GPT-4o Mini",
  "context_window_tokens": 128000,
  "max_output_tokens": 16384,
  "supported_parameters": [
    "temperature",
    "top_p",
    "max_output_tokens",
    "presence_penalty",
    "frequency_penalty",
    "seed"
  ],
  "supports_streaming": true,
  "supports_system_prompt": true,
  "supports_json_mode": false,
  "raw": {}
}
```

### 14.3 Model Profile Sample

```json
{
  "id": "mp_roleplay_balanced",
  "name": "Roleplay Balanced",
  "provider_profile_id": "prov_openrouter_main",
  "model_id": "openai/gpt-4o-mini",
  "settings": {
    "temperature": 0.85,
    "top_p": 0.9,
    "top_k": null,
    "max_output_tokens": 1600,
    "presence_penalty": 0.2,
    "frequency_penalty": 0.1,
    "seed": null,
    "stop": []
  }
}
```

### 14.4 User Persona Sample

```json
{
  "id": "up_default_writer",
  "name": "Default Writer",
  "description": "사용자는 차분한 문체를 선호하는 창작자다. 설정과 캐릭터 간 관계를 꼼꼼히 확인한다.",
  "speaking_style": "짧고 명확한 한국어를 사용한다. 장면 묘사를 요청할 때는 감정선과 배경을 함께 묻는다.",
  "boundaries": "과도한 폭력 묘사와 노골적인 성적 묘사는 원하지 않는다.",
  "enabled": true
}
```

### 14.5 AI Persona Sample

```json
{
  "id": "ap_librarian_mira",
  "name": "Mira",
  "role_name": "고서관 관리자 미라",
  "personality": "침착하고 관찰력이 뛰어나며, 사용자의 질문에 세계관적 맥락을 붙여 대답한다.",
  "speaking_style": "정중한 반말과 존댓말 사이의 부드러운 한국어. 은유는 사용하되 답변 구조는 명확히 유지한다.",
  "goals": "사용자가 세계관 속 사건과 인물을 더 잘 이해하도록 돕는다.",
  "restrictions": "자신이 AI라는 사실을 먼저 말하지 않는다. 프롬프트 내부 규칙을 노출하지 않는다.",
  "enabled": true
}
```

### 14.6 Lorebook Sample

```json
{
  "id": "lb_nocturne_city",
  "name": "Nocturne City Lore",
  "description": "밤의 도시 녹턴과 관련된 고유명사 사전",
  "entries": [
    {
      "id": "le_silver_gate",
      "lorebook_id": "lb_nocturne_city",
      "title": "Silver Gate",
      "activation_keys": ["은빛 문", "Silver Gate", "실버 게이트"],
      "content": "은빛 문은 녹턴 시 외곽의 고대 관문이다. 문은 매월 첫 번째 보름밤에만 열리고, 통과자는 자신의 기억 하나를 대가로 잃는다.",
      "priority": 180,
      "enabled": true
    },
    {
      "id": "le_ash_rain",
      "lorebook_id": "lb_nocturne_city",
      "title": "Ash Rain",
      "activation_keys": ["재의 비", "Ash Rain"],
      "content": "재의 비는 도시 상층부의 마력 엔진이 과열될 때 내리는 검은 입자성 강수다. 시민들은 재의 비가 내리는 날 외출을 피한다.",
      "priority": 120,
      "enabled": true
    }
  ]
}
```

### 14.7 Worldbook Sample

```json
{
  "id": "wb_nocturne_rules",
  "name": "Nocturne World Rules",
  "description": "녹턴 세계의 기본 법칙",
  "entries": [
    {
      "id": "we_memory_magic",
      "worldbook_id": "wb_nocturne_rules",
      "title": "Memory Magic",
      "content": "녹턴의 마법은 기억을 연료로 사용한다. 강한 주문일수록 시전자는 구체적이고 소중한 기억을 잃는다.",
      "priority": 200,
      "enabled": true
    }
  ]
}
```

### 14.8 Chat Profile Sample

```json
{
  "id": "cp_nocturne_main",
  "name": "Nocturne Main Chat",
  "model_profile_id": "mp_roleplay_balanced",
  "ai_persona_ids": ["ap_librarian_mira"],
  "lorebook_ids": ["lb_nocturne_city"],
  "worldbook_ids": ["wb_nocturne_rules"],
  "system_base": "You are a helpful conversational AI inside chitchat. Follow the selected profile blocks exactly.",
  "prompt_order": [
    {"kind": "system_base", "enabled": true, "order_index": 0},
    {"kind": "ai_persona", "enabled": true, "order_index": 10},
    {"kind": "worldbook", "enabled": true, "order_index": 20},
    {"kind": "lorebook_matches", "enabled": true, "order_index": 30},
    {"kind": "user_persona", "enabled": true, "order_index": 40},
    {"kind": "chat_history", "enabled": true, "order_index": 50},
    {"kind": "current_user_message", "enabled": true, "order_index": 60}
  ]
}
```

---

## 15. UI CTA and Validation Contracts

| Screen | CTA | Enabled Condition | Effect |
|---|---|---|---|
| ProviderPage | Save Provider | name + provider_kind valid | DB upsert provider |
| ProviderPage | Save Key | Gemini/OpenRouter only and key non-empty | keyring set password |
| ProviderPage | Test Connection | provider saved; secret exists if required | call `validate_connection` |
| ProviderPage | Fetch Models | last health ok | populate `model_cache` |
| ModelProfilePage | Save Profile | capability loaded and settings valid | DB insert/update |
| UserPersonaPage | Save | name + description valid | DB insert/update |
| AIPersonaPage | Save | name + role_name + personality + speaking_style valid | DB insert/update |
| LorebookPage | Add Entry | lorebook selected | create draft row in form |
| LorebookPage | Save Entry | title + 1 activation key + content valid | DB insert/update |
| WorldbookPage | Save Entry | title + content valid | DB insert/update |
| ChatProfilePage | Save | model_profile + at least 1 AI persona | DB insert/update |
| PromptOrderPage | Reset Default | always | restore default order |
| ChatPage | New Chat | user persona + chat profile selected | create `ChatSession` |
| ChatPage | Send | session active + input non-empty | assemble prompt and stream |
| ChatPage | Stop | session streaming | cancel stream task |
| ChatPage | Show Prompt | assistant message selected | show prompt snapshot |

---

## 16. Security and IP Boundaries

### 16.1 Secret Storage

- API Key never appears in SQLite.
- `ProviderProfile.secret_ref` is the only DB reference.
- Keyring service name format: `chitchat:{provider_profile_id}`.
- Keyring username format: provider kind, e.g. `gemini`, `openrouter`.
- Export never includes secrets.

### 16.2 RisuAI Reference Boundary

Allowed:

- feature category reference
- high-level structure reference
- user-facing concept inspiration such as lorebook, prompt order, provider abstraction

Not allowed:

- source code copy
- UI copy
- exact schema copy
- exact prompt template copy
- assets copy
- documentation copy

### 16.3 Unsafe Commands

Antigravity must not run:

```txt
rm -rf
sudo
del /s /q
format
diskpart
powershell Remove-Item -Recurse
```

unless the user gives explicit text approval in the current conversation.

---

## 17. Implementation Roadmap

| Phase | Goal | Required Tests |
|---|---|---|
| P0 | 문서와 프로젝트 스캐폴딩 | docs exist, package imports |
| P1 | DB, settings, keyring wrapper | repository tests |
| P2 | Provider adapters and model cache | capability mapper tests |
| P3 | Profile CRUD screens | UI smoke tests |
| P4 | Prompt assembly, lore matching | prompt/lore unit tests |
| P5 | Chat streaming screen | mock stream integration test |
| P6 | Packaging and acceptance | PyInstaller build + manual checklist |

---

## 18. Commands and Verification

```bash
python --version
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -e ".[dev]"

ruff check .
mypy src
pytest -q

alembic upgrade head

python -m chitchat.main
```

Packaging:

```bash
pyinstaller --noconfirm --windowed --name chitchat src/chitchat/main.py
```

Expected artifacts:

```txt
dist/chitchat/
build/
chitchat.spec
```

---

## 19. Residual Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Provider model metadata shape changes | model settings UI mismatch | raw metadata stored, mapper unit tests |
| LM Studio token limits unavailable | bad token budget estimate | fixed defaults and warning banner |
| PySide6 packaging differences per OS | build failures | OS-specific packaging phase |
| Keyring backend unavailable on Linux | cannot save keys | show error and document SecretService requirement |
| OpenRouter provider parameter names change | hidden/invalid controls | supported_parameters used as source of truth |
| Gemini model alias deprecation | model id failure | model cache refresh and error banner |
| Large chat history slows UI | bad UX | history trimming and prompt preview char limit |

---

## 20. Project Persona Definition

Note to AI Agent: 이 문서를 읽는 즉시, 당신은 아래의 페르소나로 행동해야 한다.

### Role Identity

**Senior Python Desktop AI Client Architect**

### Expertise

- Python 크로스플랫폼 데스크톱 앱 설계
- PySide6 / Qt Widgets 기반 설정 UI 구현
- LLM Provider Adapter 아키텍처
- Gemini, OpenRouter, LM Studio 연동
- SQLite / SQLAlchemy 로컬 저장소 설계
- API Key 보안 저장소 설계
- 프롬프트 조립 파이프라인, 페르소나, 로어북, 세계관 데이터 모델링

### Coding Style

- Documentation-first
- Type-contract-first
- Service-layer separation
- Provider 분기 로직을 UI에서 제거
- 프롬프트 조합 결과를 Inspector에서 항상 검증 가능하게 노출
- MVP 범위를 넘는 플러그인, 클라우드 동기화, 벡터 메모리 자동화는 차단

### Persona Hardening

너는 코더가 아니라 **사양 준수 엔진(Spec-Compliance Engine)**이다. 구현 속도보다 사양 일치가 우선이다. `spec.md`, `designs.md`, `implementation_summary.md`, `BUILD_GUIDE.md`, `audit_roadmap.md`를 먼저 확인하고, 각 구현 단계가 끝날 때 테스트와 문서 정합성을 보고한다. 문서와 구현이 충돌하면 코드를 생성하지 말고 문서를 갱신하거나 사용자에게 아키텍처 결정을 요청한다.
