# implementation_summary.md

## 문서 메타

- 문서 버전: `v0.1 BETA`
- 상위 문서: `spec.md v0.1 BETA`
- 목적: 구현자가 이 문서를 읽고 첫 코드를 열었을 때, 어디서 시작하고 어떤 순서로 무엇을 만들지 바로 판단할 수 있어야 한다.

---

## 1. 전체 런타임 흐름

```txt
main.py
→ create_app()
→ load Settings (pydantic-settings, 환경변수 + .env)
→ ensure app data directory (OS별 분기: Windows %APPDATA%, macOS ~/Library, Linux XDG_DATA_HOME)
→ create SQLite engine (SQLAlchemy 2.0, sqlite:///chitchat.sqlite3)
→ run Alembic migrations (alembic upgrade head, 자동 실행)
→ create RepositoryRegistry (모든 테이블 Repository 단일 진입점)
→ create ProviderRegistry (Gemini/OpenRouter/LMStudio adapter 등록)
→ create ServiceRegistry (ProviderService, ProfileService, ModelService, PromptService, ChatService)
→ create MainWindow (QMainWindow, sidebar + status bar + QStackedWidget)
→ show MainWindow
→ QApplication.exec()
```

종료 흐름:

```txt
MainWindow closeEvent
→ ChatService: 진행 중 스트리밍 취소 (asyncio Task cancel)
→ DB engine dispose
→ QApplication quit
```

---

## 2. 시스템 분해표

| 시스템 | 계층 | 책임 | 의존 |
|---|---|---|---|
| Config | config/ | OS별 app data 경로, Settings 로딩 | pydantic-settings |
| Database | db/ | SQLAlchemy ORM 모델, Repository CRUD, Alembic 마이그레이션 | SQLAlchemy, Alembic |
| Domain | domain/ | 타입 계약(Pydantic 모델), ID 생성, 프롬프트 조립, 로어북 매칭 | pydantic |
| Providers | providers/ | ChatProvider Protocol 구현 3종, CapabilityMapper | httpx, google-genai |
| Secrets | secrets/ | OS keyring 래퍼, secret_ref 기반 CRUD | keyring |
| Services | services/ | 유스케이스 오케스트레이션, 트랜잭션 관리 | repositories, domain, providers, secrets |
| ViewModels | ui/viewmodels/ | UI 상태 관리, 폼 검증, Signal 발행 | services, domain |
| UI Pages | ui/pages/ | PySide6 위젯, 사용자 상호작용 | viewmodels |
| UI Widgets | ui/widgets/ | 재사용 위젯: 파라미터 폼, 프롬프트 순서 리스트, 메시지 뷰, 토큰 바 | viewmodels, domain |

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

### 3.3 ViewModel → Service 경계

- ViewModel은 Service의 공개 메서드만 호출한다.
- ViewModel은 Provider adapter를 직접 호출하지 않는다.
- ViewModel은 Qt Signal로 UI에 상태 변경을 알린다.

### 3.4 UI → ViewModel 경계

- UI 위젯은 ViewModel의 Signal을 connect한다.
- UI 위젯은 ViewModel의 공개 메서드(slot)를 호출한다.
- UI 위젯은 Service/Repository/Provider를 import하지 않는다.

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
| `profile_service.py` | UserPersona/AIPersona/Lorebook/Worldbook/ChatProfile CRUD |
| `model_service.py` | ModelProfile CRUD, capability 기반 유효성 검증 |
| `prompt_service.py` | 프롬프트 조립 오케스트레이션, PromptSnapshot 생성 |
| `chat_service.py` | ChatSession CRUD, 상태 전이, 스트리밍 실행/취소, 메시지 저장 |

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
```

각 Phase 완료 조건은 `audit_roadmap.md`에서 정의한다.

---

## 9. 유지보수 규칙

1. Provider 추가 시 `ChatProvider` Protocol을 구현하고 `ProviderRegistry`에 등록한다. Service/UI는 수정하지 않는다.
2. 새 PromptBlockKind 추가 시 `PromptBlockKind` Literal, `prompt_assembler.py`, `designs.md` PromptOrder 섹션을 동시에 갱신한다.
3. DB 스키마 변경 시 반드시 Alembic 마이그레이션을 생성한다. 수동 DDL 금지.
4. 디자인 토큰 변경 시 `ui/theme.py`만 수정한다. 개별 위젯 파일에 하드코딩된 색상은 금지.
5. `spec.md`와 구현 코드가 충돌하면 코드 생성을 멈추고 문서를 먼저 갱신한다.
