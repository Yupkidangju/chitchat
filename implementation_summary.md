# implementation_summary.md

## 문서 메타

- 문서 버전: `v1.0.0`
- 상위 문서: `spec.md v1.0`
- 목적: 구현자가 이 문서를 읽고 첫 코드를 열었을 때, 어디서 시작하고 어떤 순서로 무엇을 만들지 바로 판단할 수 있어야 한다.

---

## 1. 전체 런타임 흐름

```txt
main.py
  → create_app()  (FastAPI)
  → run_migrations(db_path)  (Alembic 프로그래밍 방식, sqlite3 stdlib)
  → create_db_engine(db_path)  (SQLAlchemy 2.0)
  → RepositoryRegistry(session_factory)
  → ProviderRegistry()  (Gemini/OpenRouter/LMStudio adapter)
  → ServiceRegistry:
      - ProviderService, PromptService, ChatService(+DynamicStateEngine), VibeFillService
  → app.state에 모든 서비스 등록
  → StaticFiles 마운트 (frontend/)
  → uvicorn.run(app)
```

종료 흐름:

```txt
SIGINT / SIGTERM
  → FastAPI lifespan shutdown
  → DB engine dispose
  → 서버 종료
```

---

## 2. 시스템 분해표

| 시스템 | 계층 | 책임 | 의존 |
|---|---|---|---|
| Config | config/ | OS별 app data 경로, Settings/UserPreferences 로딩 | pydantic-settings |
| Database | db/ | SQLAlchemy ORM 모델, Repository CRUD, Alembic 마이그레이션 | SQLAlchemy, Alembic |
| Domain | domain/ | 타입 계약, ID 생성, 프롬프트 조립, VibeSmith 페르소나, 동적 상태 | pydantic |
| Providers | providers/ | ChatProvider Protocol 구현 3종, CapabilityMapper | httpx, google-genai |
| Secrets | secrets/ | OS keyring 래퍼, secret_ref 기반 CRUD | keyring |
| Services | services/ | 유스케이스 오케스트레이션: Chat, VibeFill, DynamicState, Prompt | repositories, domain |
| API | api/ | FastAPI 라우터, WebSocket 스트리밍, REST CRUD | FastAPI, services |
| Frontend | frontend/ | HTML/CSS/JS SPA, Neo-Brutal 디자인, WebSocket 클라이언트 | Vanilla JS |

---

## 3. 경계 계약 요약

### 3.1 Provider 경계

```python
# spec.md §8.1에서 동결
class ChatProvider(Protocol):
    provider_kind: ProviderKind
    async def validate_connection(self, profile: ProviderProfileData) -> ProviderHealth: ...
    async def list_models(self, profile: ProviderProfileData) -> list[ModelCapability]: ...
    async def get_model_capability(self, profile: ProviderProfileData, model_id: str) -> ModelCapability: ...
    async def stream_chat(self, profile: ProviderProfileData, request: ChatCompletionRequest) -> AsyncIterator[ChatStreamChunk]: ...
```

### 3.2 Service → Repository 경계

```python
# 모든 Repository는 동일 패턴을 따름
class BaseRepository(Generic[T]):
    def get_by_id(self, id: str) -> T | None: ...
    def get_all(self) -> list[T]: ...
    def upsert(self, item: T) -> T: ...
    def delete_by_id(self, id: str) -> bool: ...
```

### 3.3 API → Service 경계 (v1.0.0)

- FastAPI 라우터는 `request.app.state`를 통해 서비스에 접근한다.
- 라우터는 Provider/Repository를 직접 import하지 않는다 (Service를 통해서만 접근).
- WebSocket 엔드포인트는 ChatService.start_stream()을 호출하여 실시간 스트리밍을 수행한다.

### 3.4 Frontend → API 경계 (v1.0.0)

- 프론트엔드는 `api.js` 유틸리티를 통해 REST API와 WebSocket을 사용한다.
- 페이지별 JS 모듈(`pages/*.js`)이 SPA 라우팅을 처리한다.
- 모든 API 호출은 `fetch()` 기반이며, 스트리밍은 WebSocket을 사용한다.

---

## 4. 파일 책임표

### 4.1 config/

| 파일 | 책임 |
|---|---|
| `paths.py` | OS별 app data 디렉토리 결정, `ensure_app_dirs()` |
| `settings.py` | `AppSettings(BaseSettings)`: DB 경로, 로그 레벨, 기본 타임아웃 |

### 4.2 db/

| 파일 | 책임 |
|---|---|
| `engine.py` | `create_engine()` 팩토리, session maker |
| `models.py` | SQLAlchemy ORM 모델: `ProviderProfileRow`, `ModelCacheRow`, `ModelProfileRow`, `UserPersonaRow`, `AIPersonaRow`, `LorebookRow`, `LoreEntryRow`, `WorldbookRow`, `WorldEntryRow`, `ChatProfileRow`, `ChatSessionRow`, `ChatMessageRow` |
| `repositories.py` | `RepositoryRegistry`: 테이블별 Repository 인스턴스 관리 |
| `migrations.py` | Alembic 프로그래밍 방식 마이그레이션 실행 |

### 4.3 domain/

| 파일 | 책임 |
|---|---|
| `ids.py` | `new_id(prefix)`: ULID 기반 정렬 가능 ID 생성 |
| `profiles.py` | Pydantic 프로필 타입: `ProviderProfileData`, `ModelProfileData`, `UserPersonaData`, `AIPersonaData`, `LorebookData`, `LoreEntryData`, `WorldbookData`, `WorldEntryData`, `ChatProfileData` |
| `provider_contracts.py` | Provider 통신 타입: `ChatProvider`, `ProviderHealth`, `ModelCapability`, `ModelGenerationSettings`, `ChatCompletionRequest`, `ChatCompletionMessage`, `ChatStreamChunk` |
| `prompt_blocks.py` | `PromptBlock`, `AssembledPrompt`, `PromptOrderItem` 타입 정의 |
| `prompt_assembler.py` | `assemble_prompt()`: PromptOrder에 따라 블록 조합, 토큰 예측, 히스토리 잘라내기 |
| `lorebook_matcher.py` | `match_lore_entries()`: 최근 8개 메시지 키워드 매칭, 우선순위 정렬, 토큰 예산 제한 |
| `chat_session.py` | `ChatSessionData`, `ChatMessageData` 타입, 상태 전이 검증 함수 |
| `vibe_fill.py` | Phase 1~3 바이브 생성 도메인 (14개 필드 Persona, 다중 Lorebook, 10개 카테고리 Worldbook 프롬프트 및 응답 파싱) |

### 4.4 providers/

| 파일 | 책임 |
|---|---|
| `base.py` | `ChatProvider` Protocol re-export, 공통 에러 타입 |
| `registry.py` | `ProviderRegistry`: provider_kind → adapter 매핑 |
| `gemini_provider.py` | `GeminiProvider`: google-genai로 모델 목록/스트리밍 |
| `openrouter_provider.py` | `OpenRouterProvider`: httpx로 OpenRouter API 호출 |
| `lmstudio_provider.py` | `LMStudioProvider`: httpx로 /v1/models, /v1/chat/completions |
| `capability_mapper.py` | Provider별 raw 응답 → `ModelCapability` 정규화 |

### 4.5 secrets/

| 파일 | 책임 |
|---|---|
| `key_store.py` | `KeyStore`: keyring get/set/delete, service name = `chitchat:{provider_profile_id}` |

### 4.6 services/

| 파일 | 책임 |
|---|---|
| `provider_service.py` | Provider CRUD, 연결 테스트, 모델 목록 패치, model_cache 갱신 |
| `profile_service.py` | UserPersona/AIPersona/Lorebook/Worldbook/ModelProfile/ChatProfile CRUD, PromptOrder 갱신 |
| `prompt_service.py` | 프롬프트 조립 오케스트레이션, PromptSnapshot 생성 |
| `chat_service.py` | ChatSession CRUD, 상태 전이, 스트리밍 실행/취소, 메시지 저장 |
| `vibe_fill_service.py` | Vibe Fill (AI Persona, Lorebook, Worldbook) 연쇄 생성, 청크 분할 LLM 호출 및 진행률 콜백 관리 |

### 4.7 ui/

| 파일 | 책임 |
|---|---|
| `main_window.py` | QMainWindow, 상태바, QStackedWidget, 글로벌 토스트 |
| `navigation.py` | 사이드바 위젯, 페이지 전환 Signal |
| `theme.py` | 디자인 토큰 딕셔너리, 글로벌 Qt 스타일시트 생성 |

### 4.8 tests/

| 파일 | 검증 대상 |
|---|---|
| `test_prompt_assembler.py` | PromptOrder 순서, 블록 활성화/비활성화, 토큰 예측 |
| `test_lorebook_matcher.py` | 키워드 매칭, 대소문자 무시, 우선순위, 토큰 예산 |
| `test_provider_capability_mapper.py` | Gemini/OpenRouter/LMStudio raw → ModelCapability 변환 |
| `test_profile_validation.py` | Pydantic 모델 유효성 검증 경계값 |
| `test_secret_storage_policy.py` | keyring 호출 패턴, DB에 평문 없음 검증 |

---

## 5. 알고리즘 메모

### 5.1 토큰 추정

```python
def estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)
```

- 문자 4개당 1 토큰으로 근사한다.
- 빈 문자열은 최소 1을 반환한다.
- 이 공식은 정밀한 tokenizer를 대체하는 MVP 수준이다.

### 5.2 로어북 매칭

1. 최근 8개 메시지 + 현재 입력을 하나의 scan_text로 합친다.
2. casefold 정규화한다.
3. 모든 활성 lorebook의 활성 entry를 순회한다.
4. activation_key 중 하나라도 scan_text에 포함되면 후보에 추가한다.
5. 후보를 `(-priority, title.casefold(), id)` 기준으로 정렬한다.
6. 최대 12개, 최대 3000 토큰까지 선택한다.

### 5.3 컨텍스트 예산

1. `available = context_window_tokens - max_output_tokens` (최소 1024 보장)
2. system, persona, world, lore, current message 블록을 먼저 삽입한다.
3. 남은 예산으로 chat_history를 최신 → 과거 순으로 채운다.
4. 삽입되지 못한 메시지 ID를 `truncated_history_message_ids`로 기록한다.

### 5.4 ID 생성

```python
def new_id(prefix: str) -> str:
    return f"{prefix}{generate_ulid_lower()}"
```

- prefix는 반드시 언더스코어로 끝난다: `cp_`, `prov_`, `le_` 등.
- ULID는 시간 순 정렬이 가능하다.

### 5.5 Vibe Fill (AI Generation) 알고리즘 (v0.2.0)

**Phase 1 (Persona)**: 바이브 문자열 → `VIBE_FILL_SYSTEM_PROMPT` 주입 → JSON 14개 필드 파싱 → 기존/신규 AI Persona에 할당.
**Phase 2 (Lorebook)**: 바이브 + Persona → `LORE_FILL_SYSTEM_PROMPT` 주입 → JSON 배열 파싱 → 중복 키/제목 검증 → 임시 목록 생성 → UI에서 체크 항목만 Append DB.
**Phase 3 (Worldbook)**: 바이브 + Persona(2) + Lorebook(2) → 10개 카테고리(역사, 지리 등)를 4그룹(청크)으로 분할 → `WORLD_FILL_SYSTEM_PROMPT`에 이전 청크의 생성 제목 목록 주입 → 연쇄 호출 → 응답 병합 → UI에서 선택 Append.

---

## 6. 동결된 공식 요약

| 공식 | 값 | 출처 |
|---|---|---|
| 토큰 추정 | `max(1, (len(text) + 3) // 4)` | spec.md §12.5 |
| 로어북 스캔 메시지 수 | `8` | spec.md §12.1 |
| 로어북 최대 매칭 entry 수 | `12` | spec.md §12.1 |
| 로어북 최대 삽입 토큰 | `3000` | spec.md §12.1 |
| 월드북 최대 삽입 토큰 | `5000` | spec.md §12.1 |
| 히스토리 예약 출력 토큰 | `1024` | spec.md §12.1 |
| 프롬프트 프리뷰 최대 문자 | `24000` | spec.md §12.1 |
| 토큰 예산 경고 | `80%` | designs.md §9.8 |
| 토큰 예산 에러 | `95%` | designs.md §9.8 |
| LM Studio 기본 context | `8192` | spec.md §10.3 |
| LM Studio 기본 output | `2048` | spec.md §10.3 |

---

## 7. MVP 최소 범위 (첫 플레이어블)

MVP는 다음 경로가 한 번이라도 완주되면 달성이다:

```txt
Provider 등록 → Key 저장 → 연결 테스트 → 모델 패치
→ ModelProfile 저장 → UserPersona 저장 → AIPersona 저장
→ ChatProfile 저장 → New Chat → Send → 스트리밍 응답 수신 → Stop → Show Prompt
```

MVP에서 반드시 동작해야 하는 것:

1. 3종 Provider 등록/연결 테스트/모델 패치
2. ModelProfile에서 capability 기반 파라미터 필터링
3. UserPersona, AIPersona, Lorebook, Worldbook CRUD
4. ChatProfile 조합 및 저장
5. PromptOrder 재정렬 및 저장
6. 프롬프트 조립 및 Inspector 표시
7. 스트리밍 채팅 Send/Stop
8. 프롬프트 스냅샷 저장 및 조회
9. PyInstaller one-folder 빌드

---

## 8. 구현 순서 권장

```txt
Phase 0: 문서 + 스캐폴딩                    ✅ 완료
Phase 1: Config, DB, Keyring 기반            ✅ 완료
Phase 2: Provider Adapter + Capability Mapper ✅ 완료
Phase 3: Profile CRUD + UI 기본 화면         ✅ 완료
Phase 4: Prompt Assembly + Lore Matching     ✅ 완료
Phase 5: Chat Streaming + Inspector          ✅ 완료
Phase 6: 패키징 + 수용 테스트                ✅ 완료
정합성 감사 Remediation                       ✅ 완료 (7 버그 수정)
MVP Hardening                                  ✅ 완료 (#1~#6 전체 조치)
v0.1.1 UI 개선                                 ✅ 완료 (태그 선택, placeholder)
v0.1.2 전수조사 감사                           ✅ 완료 (스트리밍 실시간, 프로필 선택 등)
v0.1.3 잔여 감사 수정                          ✅ 완료 (아래 §8.1 참조)
v0.2.0 Vibe Fill Phase 1 (Persona)             ✅ 완료 (14필드 확장)
v0.2.0 Vibe Fill Phase 2 (Lorebook)            ✅ 완료 (복수 엔트리)
v0.2.0 Vibe Fill Phase 3 (Worldbook)           ✅ 완료 (청크 연쇄)
v0.3.0 i18n + 설정 시스템                       ✅ 완료 (357키 × 5개 언어)
```

각 Phase 완료 조건은 `audit_roadmap.md`에서 정의한다.

### 8.1 잔여 작업 목록 — v1.0.0 완료 현황

| 우선순위 | 항목 | 관련 문서 | 상태 |
|:---:|---|---|:---:|
| 🔴 높음 | PromptOrderPage 신규 구현 | spec §12.2, designs §10.9, DD-05 | ✅ 완료 |
| 🔴 높음 | ModelProfilePage 파라미터 동적 가시성 | spec §11.1, designs §10.3, DD-13 | ✅ 완료 |
| 🟡 중간 | PromptSnapshot 구조 보완 | spec §12.6, designs §9.9 | ✅ 완료 |
| 🟡 중간 | Provider Setup State 시각화 | spec §13.1, designs §10.2 | ✅ 완료 |
| 🟡 중간 | ModelProfile Save 검증 강화 | spec §11.2, designs §10.3, DD-13 | ✅ 완료 |
| 🟡 중간 | 프롬프트 Inspector 패널 | spec §12.6, DD-05 | ✅ v1.0.0 완료 |
| 🟡 중간 | 데이터 무결성 검증 (7개 엔티티 삭제 참조 검사) | DD-12 | ✅ v1.0.0 완료 |
| 🟡 중간 | 설정 페이지 고도화 (DD-12 4섹션) | DD-12 | ✅ v1.0.0 완료 |
| 🟡 중간 | 토스트 알림 시스템 (alert 제거) | designs §5 | ✅ v1.0.0 완료 |
| ⚪ 낮음 | chat.js 모듈 분리 (DD-11 재평가) | DD-11 | ✅ v1.0.0 완료 |
| ⚪ 낮음 | 다크/라이트 테마 전환 | DD-12 | ✅ v1.0.0 완료 |

---

## 9. 유지보수 규칙

1. Provider 추가 시 `ChatProvider` Protocol을 구현하고 `ProviderRegistry`에 등록한다. Service/UI는 수정하지 않는다.
2. 새 PromptBlockKind 추가 시 `PromptBlockKind` Literal, `prompt_assembler.py`, `designs.md` PromptOrder 섹션을 동시에 갱신한다.
3. DB 스키마 변경 시: (a) v0.2.0부터 `create_all()` 대신 Alembic 단독 정책을 사용한다. (b) 스키마 변경이 필요하면 `alembic revision --autogenerate`로 새 리비전을 생성한다. (c) `run_migrations()`가 앱 시작 시 자동으로 호출되어 신규/기존/partial DB를 모두 처리한다.
4. 디자인 토큰 변경 시 `ui/theme.py`만 수정한다. 개별 위젯 파일에 하드코딩된 색상은 금지.
5. `spec.md`와 구현 코드가 충돌하면 코드 생성을 멈추고 문서를 먼저 갱신한다.

---

## 10. v1.0.0 프로필 관리 인프라

### 10.1 REST API 엔드포인트 현황

| 라우트 파일 | 대상 엔티티 | 엔드포인트 수 | 상태 |
|---|---|:---:|:---:|
| `api/routes/providers.py` | ProviderProfile | 6 | ✅ |
| `api/routes/personas.py` | AIPersona (VibeFill) | 4 | ✅ |
| `api/routes/profiles.py` | ModelProfile | 4 | ✅ |
| `api/routes/profiles.py` | ChatProfile | 4 | ✅ |
| `api/routes/profiles.py` | Lorebook + LoreEntry | 5 | ✅ |
| `api/routes/profiles.py` | Worldbook + WorldEntry | 5 | ✅ |
| `api/routes/profiles.py` | UserPersona | 3 | ✅ |
| `api/routes/chat.py` | ChatSession + WebSocket + Inspector | 6 | ✅ |
| `api/routes/settings.py` | UserPreferences | 3 | ✅ |
| `api/routes/health.py` | Health | 1 | ✅ |

### 10.2 프론트엔드 페이지 현황

| 페이지 | 파일 | 주요 기능 | 상태 |
|---|---|---|:---:|
| 채팅 | `chat.js` | 3컬럼, WebSocket, 동적 상태, 프롬프트 Inspector, 세션 생성 모달 | ✅ |
| 공급자 | `providers.js` | CRUD, 연결 테스트, 모델 캐시 | ✅ |
| 모델 설정 | `models.js` | ModelProfile CRUD, Provider 연동 모델 선택 | ✅ |
| 페르소나 | `personas.js` | VibeFill AI 생성, 9섹션 편집 | ✅ |
| 로어북 | `lorebooks.js` | CRUD + LoreEntry 관리 | ✅ |
| 월드북 | `worldbooks.js` | CRUD + WorldEntry 관리 | ✅ |
| 채팅 프로필 | `chat_profiles.js` | 다중 선택 조합 | ✅ |
| 프롬프트 순서 | `prompt_order.js` | 블록 순서 편집 | ✅ |
| 설정 | `settings.js` | 4섹션 (언어, 표시, 일반, 데이터 관리), 설정 초기화 | ✅ |

