# chitchat Implementation Spec (v1.0)

## 0. 전역 문서 규칙

- 문서 버전: `v1.0`
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

### 0.1 변경 정책

| 변경 유형 | 필수 갱신 문서 |
|---|---|
| 타입/스키마 변경 | `spec.md`, `implementation_summary.md`, `audit_roadmap.md`, `CHANGELOG.md` |
| 화면/CTA 변경 | `designs.md`, `spec.md`, `audit_roadmap.md`, `CHANGELOG.md` |
| 빌드/실행 명령 변경 | `BUILD_GUIDE.md`, `spec.md`, `CHANGELOG.md` |
| Provider API 계약 변경 | `spec.md`, `implementation_summary.md`, `DESIGN_DECISIONS.md`, `CHANGELOG.md` |
| 보안/Key 저장 정책 변경 | `spec.md`, `BUILD_GUIDE.md`, `DESIGN_DECISIONS.md`, `CHANGELOG.md` |

### 0.2 플레이스홀더 금지 규칙

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

## 1. 프로젝트 정보 & 버전 관리

| 항목 | 값 |
|---|---|
| Project Name | `chitchat` |
| Version | `v1.0` |
| Target Tool | Google Antigravity |
| Target Platform | Cross-platform Web: 브라우저 기반 (localhost) |
| Language | Python (Backend) + HTML/CSS/JS (Frontend) |
| Runtime Pin | Python `3.12+` (권장 3.13, 최소 3.12) |
| Backend Framework | FastAPI + Uvicorn |
| Frontend | Vanilla HTML/CSS/JS SPA |
| Realtime | WebSocket (스트리밍 채팅) |
| Storage | SQLite local file |
| Compression | ZSTD (동적 상태 blob) |
| Secrets | OS keyring via `keyring` |
| Supported Providers | Gemini, OpenRouter, LM Studio |
| Persona System | VibeSmith 9-Section Dynamic Persona |
| License posture | RisuAI code, UI, assets, text, schema를 복제하지 않는 독립 구현 |

### 1.1 한 줄 제품 정의

`chitchat`은 VibeSmith 스타일의 동적 페르소나 시스템을 통해 살아있는 캐릭터를 생성하고, 기억·관계·감정·사회적 위치가 대화에 따라 동적으로 변화하는 AI 롤플레이 채팅 플랫폼이다. Python FastAPI 백엔드와 HTML/CSS/JS 웹 프론트엔드로 구성된다.

---

## 2. 목표, 성공 기준, 비목표

### 2.1 목표

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

### 2.2 성공 기준

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

### 2.3 v1.0.0 비목표

| 제외 항목 | 이유 |
|---|---|
| 모바일 앱 | Python 로컬 서버 + 웹 SPA 범위를 벗어남 |
| 웹 SaaS 배포 | 인증, 서버 보안, 과금 범위가 추가됨 |
| 클라우드 동기화 | 개인정보·API Key·프로필 동기화 위험 증가 |
| 이미지 생성/멀티모달 첨부 | v1.0은 텍스트 채팅과 프롬프트 조립 검증이 우선 |
| RisuAI 데이터 완전 호환 import/export | 라이선스와 스키마 의존 리스크 |
| 플러그인 시스템 | 샌드박싱과 권한 모델이 필요함 |
| 자동 벡터 메모리 | v1.0에서는 키워드 기반 로어북으로 고정 |
| TTS/STT | 핵심 채팅 UX 이후 단계 |
| 서버 저장형 계정 시스템 | 로컬 앱 범위 초과 |

---

## 3. 환경 & 기술 스택

### 3.1 환경 스냅샷

- 기준 날짜: 2026-04-29
- Python 다운로드 페이지 기준 최신 안정 버전은 3.14.4이나, 개발 런타임은 `3.12+`로 설정하고 권장 버전은 `3.13`이다. 개발 환경에서 3.13 설치가 불가능한 경우 3.12로 대체한다.
- v1.0.0에서 PySide6 의존성은 제거됨 (DD-15: FastAPI+SPA 전환). UI는 웹 브라우저에서 실행된다.
- FastAPI + Uvicorn이 백엔드 서버를 제공하며, 프론트엔드는 Vanilla HTML/CSS/JS SPA로 구성된다.
- Gemini API Models endpoint는 모델 목록과 모델 메타데이터, token limit, supported generation method를 제공한다.
- OpenRouter Models API는 `context_length`, `supported_parameters`, pricing, model id/name을 제공한다.
- LM Studio는 OpenAI-compatible `/v1/models` 및 `/v1/chat/completions` 엔드포인트를 제공한다.
- SQLAlchemy 2.0 라인을 사용하고 Alembic으로 마이그레이션을 관리한다.
- Pydantic v2 라인을 사용해 경계 타입을 검증한다.
- HTTPX는 sync/async API를 제공하므로 streaming Provider Adapter에 사용한다.
- `keyring`은 시스템 키링 접근 라이브러리로 API Key 평문 저장을 피한다.

### 3.2 동결된 의존성 정책

`pyproject.toml`은 아래 범위로 시작한다.

```toml
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
  "mypy>=1.14,<2",
  "pyinstaller>=6.20,<7",
]
```

### 3.3 런타임 저장 경로

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

## 4. 동결된 핵심 결정

| ID | Decision | Frozen Value |
|---|---|---|
| D-01 | App form | 로컬 데스크톱 앱 |
| D-02 | UI toolkit | FastAPI 백엔드 + Vanilla HTML/CSS/JS SPA (DD-15에서 PySide6 대체) |
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

## 5. 아키텍처

```txt
chitchat v1.0
├─ API Layer: FastAPI REST + WebSocket endpoints
├─ Service Layer: use cases, transactions, orchestration
├─ Domain Layer:
│  ├─ VibeSmith Persona (9-section dynamic persona cards)
│  ├─ DynamicStateEngine (기억/관계/감정/이벤트 실시간 갱신)
│  ├─ PromptAssembler v2 (동적 상태 블록 주입)
│  └─ LorebookMatcher (키워드 매칭)
├─ Provider Layer: Gemini/OpenRouter/LM Studio adapters
├─ Persistence Layer: SQLite + SQLAlchemy + ZSTD (동적 상태)
├─ Secret Layer: keyring wrapper
└─ Frontend: HTML/CSS/JS SPA (별도 static serve)
```

### 5.1 의존성 규칙

```txt
frontend(JS) -> API(FastAPI) -> services -> repositories/domain/providers/secrets

domain -> no dependency on api/db/provider implementation
providers -> domain contracts + httpx/google-genai only
db -> SQLAlchemy only
secrets -> keyring only
```

#### 5.1.1 FastAPI 의존성 주입 규칙 (v1.1.1)

FastAPI 라우터(`src/chitchat/api/routes/*.py`)의 **모든 엔드포인트(REST 및 WebSocket 포함)**는 `request.app.state` 또는 `websocket.app.state`에 직접 접근하는 것을 **엄격히 금지**한다. 반드시 `src/chitchat/api/dependencies.py`에 정의된 Provider 함수를 `Depends()`로 주입받아 사용해야 한다.

```python
# 올바른 예시 (REST)
@router.get("/sessions")
async def list_sessions(svc: ChatService = Depends(get_chat_service)):
    ...

# 올바른 예시 (WebSocket)
@router.websocket("/ws/chat/{session_id}")
async def chat_websocket(
    websocket: WebSocket,
    session_id: str,
    chat_service: ChatService = Depends(get_chat_service),
):
    ...

# 금지 — 아래 패턴은 절대 사용하지 않는다
svc = request.app.state.chat_service  # ❌
svc = websocket.app.state.chat_service  # ❌
```

#### 5.1.2 프론트엔드 아키텍처 규칙 (v1.1.1 구현 완료)

프론트엔드는 번들러 없이 Native 브라우저 ES6 모듈 기능을 사용한다. `index.html`에서는 최상위 모듈 단 하나만 `<script type="module" src="/js/app.js"></script>`로 로드하고, 나머지 모든 파일은 `import`/`export`를 사용해 의존성을 명시적으로 주입한다.

1. **ES6 모듈 구조**: `index.html` → `app.js` (단일 진입점) → 각 페이지 모듈 `import`. 모든 JS 파일에 `export` 필수.
2. **상태 캡슐화**: `js/store.js` StateStore 싱글톤 — `getState(key)`/`setState(key, value)`/`subscribe(key, callback)` API로만 상태 관리. 전역 변수(`window` 또는 모듈 루트의 공유 `let/var`)에 애플리케이션 상태를 저장하는 것을 **엄격히 금지**.
3. **에러 핸들링 일원화**: API 통신 에러는 `showToast()`로 일원화. `innerHTML`에 에러 메시지를 직접 주입하는 패턴을 **금지**.
4. **이벤트 바인딩 (강제)**: 모든 동적 DOM 생성 시 `onclick`, `onchange` 등의 HTML 인라인 이벤트 핸들러 사용을 **엄격히 금지**. 반드시 요소에 `data-action`, `data-id` 등의 Data 속성을 부여한 뒤, `container.addEventListener('click', ...)` 이벤트 위임 방식으로 처리해야 한다. 모듈 내부 함수를 `window` 객체에 할당하는 것을 **금지**.
5. **순환 import 방지**: `chat_utils.js`에 공용 함수(`renderMessageBubble` 등)를 분리하여 `chat_session.js` ↔ `chat_composer.js` 순환 의존성을 방지한다. 동적 `import()`는 순환이 불가피할 때만 허용.

### 5.2 런타임 흐름

```txt
main.py
→ create FastAPI app
→ load Settings / UserPreferences
→ ensure app data directory
→ create SQLite engine
→ run_migrations(engine)
→ create RepositoryRegistry
→ create ProviderRegistry
→ create ServiceRegistry
→ mount static files (frontend/)
→ uvicorn.run(app, host="127.0.0.1", port=8000)
```

### 5.3 VibeSmith 페르소나 아키텍처 (v1.0)

VibeSmith는 짧은 바이브 입력에서 9섹션 동적 페르소나 카드를 생성하고,
대화 진행에 따라 동적 상태를 실시간으로 갱신하는 시스템이다.

```txt
[Persona Generation Pipeline]
1. User Input (vibe text)
2. Input Parsing (fixed facts + vibe traits + implied constraints)
3. Fixed Canon Autofill (이름, 나이, 외모, 생활, 기술)
4. Dynamic Persona Autofill (동기, 공포, 자기개념, 방어전략)
5. Relationship State Model (9개 상태 변수)
6. Behavioral Texture (말투, 바디랭귀지, 일상 질감)
7. Coherence Check (10영역 일관성 검증)
8. Markdown Persona Card 출력 (원본 MD 문서)
9. DB 저장 (메타 + 검색 인덱스)

[Dynamic State Engine — 매 턴 실행]
1. 대화 분석: 기억 저장 트리거 감지 (약속, 칭찬, 경계 침범, 갈등 회복 등)
2. AI 판단: 관계 변수 변경 여부 평가 (trust, familiarity, emotional_reliance 등)
3. 기억 형성: MemoryEntry 생성 + 감정 영향 기록
4. 상태 영속화: ZSTD 압축 → SQLite dynamic_states 테이블
5. 프롬프트 반영: 다음 턴 프롬프트 조립 시 현재 동적 상태 주입
```

*   **원본 불변 원칙**: 생성 시 만들어진 MD 페르소나 문서(Fixed Canon 등)는 불변이다. 모든 변화는 dynamic_states 테이블에만 기록된다.
*   **ZSTD 압축**: 동적 상태 JSON blob은 zstandard로 압축하여 저장한다. 평균 3~5x 압축률.

### 5.4 Vibe Fill 연쇄 생성 파이프라인 (v1.1)

VibeFill은 3단계 연쇄 생성 파이프라인으로 구성된다.
각 단계의 출력이 다음 단계의 컨텍스트로 자동 주입되는 계층 구조이다.

```txt
[3단계 연쇄 생성 구조]

Phase 1: 캐릭터 생성
  입력: 바이브 텍스트
  출력: 9섹션 동적 페르소나 카드 (PersonaCard)
  API:  POST /personas/vibe-fill

Phase 2: 로어북 생성
  입력: 캐릭터(복수 선택) + 바이브 텍스트
  출력: LoreEntry 배열 (title + activation_keys + content)
  API:  POST /lorebooks/{id}/vibe-fill
  특징:
  - 선택된 캐릭터의 시트를 컨텍스트로 주입
  - 기존 엔트리 제목/키워드를 주입하여 중복 방지
  - max_output_tokens=4096, 최대 10개 엔트리

Phase 3: 세계관(월드북) 생성
  입력: 캐릭터(복수) + 로어북(복수) + 카테고리(10개 중 선택) + 바이브
  출력: WorldEntry 배열 (title + content)
  API:  POST /worldbooks/{id}/vibe-fill
  특징:
  - 선택된 캐릭터 시트 + 로어북 요약을 컨텍스트로 주입
  - 카테고리를 2~3개씩 청크로 나눠 다중 LLM 호출
  - 이전 청크의 생성 제목을 다음 청크에 주입 (연쇄 컨텍스트)

[의존 관계]
  바이브 → 캐릭터 → 로어북 → 세계관
  (각 단계는 독립 실행 가능하나, 이전 단계 출력을 참조하면 일관성 향상)
```

### 5.5 엔티티 수동 편집 (v1.1)

AI가 생성한 캐릭터, 로어 엔트리, 월드 엔트리는 모두 수동 편집이 가능하다.

| 엔티티 | API | 편집 UI |
|---|---|---|
| PersonaCard | `PUT /personas/{id}` | 9섹션 접이식 편집 + JSON 원문 편집 토글 |
| LoreEntry | `PUT /lore-entries/{id}` | 제목, 키워드, 내용, 우선순위, 활성 상태 |
| WorldEntry | `PUT /world-entries/{id}` | 제목, 내용, 우선순위, 활성 상태 |

---

## 6. 디렉토리 구조

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
│       ├── logging_config.py
│       ├── config/
│       │   ├── paths.py
│       │   └── settings.py
│       ├── db/
│       │   ├── engine.py
│       │   ├── models.py
│       │   ├── repositories.py
│       │   └── migrations.py           # Alembic 인프라 (MVP v0.1에서 미호출)
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
│       │   ├── profile_service.py      # UserPersona/AIPersona/Lorebook/Worldbook/ModelProfile/ChatProfile CRUD
│       │   ├── prompt_service.py
│       │   └── chat_service.py
│       └── ui/
│           ├── main_window.py
│           ├── navigation.py
│           ├── theme.py
│           ├── async_bridge.py          # asyncio ↔ Qt Signal 브리지 (DD-09)
│           ├── pages/
│           │   ├── chat_page.py
│           │   ├── provider_page.py
│           │   ├── model_profile_page.py
│           │   ├── persona_page.py      # UserPersona + AIPersona 통합
│           │   ├── lorebook_page.py
│           │   ├── worldbook_page.py
│           │   ├── chat_profile_page.py
│           │   └── prompt_order_page.py
│           ├── widgets/
│           │   ├── chat_message_view.py
│           │   ├── token_budget_bar.py
│           │   └── entity_picker_dialog.py
│           └── (삭제됨)                   # DD-11: v1.0.0에서 전면 ViewModel 기각, chat.js 선택적 분리
└── tests/
    ├── test_prompt_assembler.py
    ├── test_lorebook_matcher.py
    ├── test_provider_capability_mapper.py
    ├── test_provider_connection.py
    ├── test_model_list.py
    ├── test_profile_validation.py
    ├── test_profile_crud_service.py
    ├── test_secret_storage_policy.py
    ├── test_repository_crud.py
    ├── test_session_state_machine.py
    ├── test_first_run_smoke.py
    └── test_e2e_acceptance.py
```

---

## 7. ID, 열거형, 명명 계약

### 7.1 ID 접두사

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

### 7.2 열거형

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

## 8. 타입 계약

### 8.1 Provider 계약

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

### 8.2 프로필 계약

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

### 8.3 프롬프트 계약

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

### 8.4 채팅 계약

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

## 9. 데이터베이스 스키마

SQLite file: `chitchat.sqlite3`

### 9.1 테이블

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

[v0.2.0] Vibe Fill Phase 1에서 14개 필드로 확장됨 (기존 6개 + 신규 8개).

| Column | Type | Constraint | 설명 |
|---|---|---|---|
| id | TEXT | PK | |
| name | TEXT | NOT NULL, unique | 캐릭터 이름 |
| role_name | TEXT | NOT NULL | 직업/역할 |
| personality | TEXT | NOT NULL | 성격 기술 |
| speaking_style | TEXT | NOT NULL | 말투 기술 |
| goals | TEXT | NOT NULL | 추구할 목표 |
| restrictions | TEXT | NOT NULL | 행동 제한 |
| enabled | INTEGER | NOT NULL | 활성 여부 |
| age | TEXT | NOT NULL, default="" | 나이 또는 나이대 |
| gender | TEXT | NOT NULL, default="" | 성별 |
| appearance | TEXT | NOT NULL, default="" | 외모 묘사 |
| backstory | TEXT | NOT NULL, default="" | 배경 스토리 |
| relationships | TEXT | NOT NULL, default="" | 인간관계 |
| skills | TEXT | NOT NULL, default="" | 특기/능력 |
| interests | TEXT | NOT NULL, default="" | 취미/관심사 |
| weaknesses | TEXT | NOT NULL, default="" | 약점/두려움 |

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

## 10. Provider별 Capability 매핑

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

## 11. 모델 설정 UI 규칙

### 11.1 파라미터 가시성

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

### 11.2 저장 검증

`ModelProfile` cannot be saved when:

1. Provider profile is disabled.
2. Model capability is not loaded.
3. `max_output_tokens` exceeds capability max.
4. Any visible parameter is out of range.
5. Hidden unsupported parameter has non-null value.

---

## 12. 프롬프트 조립

### 12.1 상수

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

### 12.2 기본 프롬프트 순서

```json
[
  {"kind": "system_base", "enabled": true, "order_index": 0},
  {"kind": "ai_persona", "enabled": true, "order_index": 10},
  {"kind": "worldbook", "enabled": true, "order_index": 20},
  {"kind": "lorebook", "enabled": true, "order_index": 30},
  {"kind": "user_persona", "enabled": true, "order_index": 40},
  {"kind": "chat_history", "enabled": true, "order_index": 50},
  {"kind": "current_input", "enabled": true, "order_index": 60}
]
```

### 12.3 필수 블록

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

### 12.4 로어북 매칭 알고리즘

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

### 12.5 컨텍스트 예산 알고리즘

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

### 12.6 프롬프트 스냅샷

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

## 13. 상태 머신

### 13.1 Provider 셋업 상태

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

### 13.2 채팅 세션 상태

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

## 14. 실제 시드 데이터

### 14.1 Provider 프로필

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

### 14.2 모델 Capability 샘플

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

### 14.3 모델 프로필 샘플

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

### 14.4 사용자 페르소나 샘플

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

### 14.5 AI 페르소나 샘플

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

### 14.6 로어북 샘플

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

### 14.7 월드북 샘플

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

### 14.8 채팅 프로필 샘플

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
    {"kind": "lorebook", "enabled": true, "order_index": 30},
    {"kind": "user_persona", "enabled": true, "order_index": 40},
    {"kind": "chat_history", "enabled": true, "order_index": 50},
    {"kind": "current_input", "enabled": true, "order_index": 60}
  ]
}
```

---

## 15. UI CTA 및 검증 계약

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

## 16. 보안 및 IP 경계

### 16.1 시크릿 저장

- API Key never appears in SQLite.
- `ProviderProfile.secret_ref` is the only DB reference.
- Keyring service name format: `chitchat:{provider_profile_id}`.
- Keyring username format: provider kind, e.g. `gemini`, `openrouter`.
- Export never includes secrets.

### 16.2 RisuAI 참조 경계

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

### 16.3 안전하지 않은 명령

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

## 17. 구현 로드맵

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

## 18. 명령 및 검증

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

## 19. 잔여 리스크

| Risk | Impact | Mitigation |
|---|---|---|
| Provider model metadata shape changes | model settings UI mismatch | raw metadata stored, mapper unit tests |
| LM Studio token limits unavailable | bad token budget estimate | fixed defaults and warning banner |
| 브라우저 호환성 차이 | CSS 변수/WebSocket 미지원 브라우저 | 모던 브라우저 권장 (Chrome, Firefox, Edge) |
| Keyring backend unavailable on Linux | cannot save keys | show error and document SecretService requirement |
| OpenRouter provider parameter names change | hidden/invalid controls | supported_parameters used as source of truth |
| Gemini model alias deprecation | model id failure | model cache refresh and error banner |
| Large chat history slows UI | bad UX | history trimming and prompt preview char limit |

---

## 20. 프로젝트 페르소나 정의

Note to AI Agent: 이 문서를 읽는 즉시, 당신은 아래의 페르소나로 행동해야 한다.

### 역할 정체성

**Senior Python Full-Stack AI Client Architect**

### 전문성

- Python FastAPI 웹 백엔드 + Vanilla JS SPA 설계
- WebSocket 기반 실시간 스트리밍 채팅
- LLM Provider Adapter 아키텍처
- Gemini, OpenRouter, LM Studio 연동
- SQLite / SQLAlchemy 로컬 저장소 설계
- API Key 보안 저장소 설계
- 프롬프트 조립 파이프라인, 페르소나, 로어북, 세계관 데이터 모델링

### 코딩 스타일

- Documentation-first
- Type-contract-first
- Service-layer separation
- Provider 분기 로직을 UI에서 제거
- 프롬프트 조합 결과를 Inspector에서 항상 검증 가능하게 노출
- MVP 범위를 넘는 플러그인, 클라우드 동기화, 벡터 메모리 자동화는 차단

### 페르소나 강화

너는 코더가 아니라 **사양 준수 엔진(Spec-Compliance Engine)**이다. 구현 속도보다 사양 일치가 우선이다. `spec.md`, `designs.md`, `implementation_summary.md`, `BUILD_GUIDE.md`, `audit_roadmap.md`를 먼저 확인하고, 각 구현 단계가 끝날 때 테스트와 문서 정합성을 보고한다. 문서와 구현이 충돌하면 코드를 생성하지 말고 문서를 갱신하거나 사용자에게 아키텍처 결정을 요청한다.
