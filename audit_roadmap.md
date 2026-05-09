# audit_roadmap.md

## 문서 메타

- 문서 버전: `v1.1.1`
- 상위 문서: `spec.md v1.1.1`
- 목적: 이 문서는 구현 감사 프레임이다. "다음에 뭐 하지?"가 아니라 "지금 이 Phase를 넘겨도 되는가?"를 판단하게 해준다.

---

## 1. 감사 구조

모든 Phase 전환 시 아래 4가지 감사를 수행한다.

| 감사 유형 | 질문 | 실패 시 행동 |
|---|---|---|
| 정합성 감사 | 코드와 문서가 일치하는가? | 코드 생성 중단, 문서 동기화 |
| 위험요소 감사 | 알려진 리스크가 구현을 막는가? | 리스크 완화 또는 격리 |
| 아키텍처 감사 | 의존성 규칙을 위반하는가? | 계층 분리 수정 |
| 로드맵 감사 | 이 Phase의 모든 항목이 검증됐는가? | 미완료 항목 식별 후 속행/차단 결정 |

---

## 2. Phase 0: 문서와 스캐폴딩

### 목표

프로젝트의 모든 필수 문서가 작성되고, 빈 소스 디렉토리 구조와 `pyproject.toml`이 존재하며, 가상환경에서 `pip install -e ".[dev]"`가 성공한다.

### 구현 항목

| ID | 항목 | 크기 | 파일 |
|---|---|---|---|
| P0-01 | `pyproject.toml` 작성 | XS | `pyproject.toml` |
| P0-02 | `src/chitchat/` 디렉토리 구조 생성 | XS | `src/chitchat/**/__init__.py` |
| P0-03 | `alembic.ini` + `alembic/env.py` 작성 | S | `alembic.ini`, `alembic/env.py` |
| P0-04 | 필수 문서 7종 작성 | M | `spec.md`, `designs.md`, `implementation_summary.md`, `DESIGN_DECISIONS.md`, `BUILD_GUIDE.md`, `audit_roadmap.md`, `CHANGELOG.md` |
| P0-05 | `README.md` 다국어 초안 | S | `README.md` |
| P0-06 | `.gitignore` 작성 | XS | `.gitignore` |

### 검증 포인트

- [x] `python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"` 성공
- [x] `python -c "import chitchat"` 에러 없음
- [x] 필수 문서 7종 + README.md 존재
- [x] `ruff check .` 경고 없음

### 체크포인트 판정

✅ P0 완료: 가상환경 설치 성공 + 빈 패키지 import 성공 + 문서 8종 존재.

---

## 3. Phase 1: 인프라 레이어 (Config, DB, Keyring)

### 목표

OS별 앱 데이터 경로 결정, SQLite 엔진 생성, Alembic 마이그레이션 적용, Keyring 래퍼가 동작한다.

### 구현 항목

| ID | 항목 | 크기 | 파일 |
|---|---|---|---|
| P1-01 | `paths.py`: OS별 app data 경로, `ensure_app_dirs()` | S | `src/chitchat/config/paths.py` |
| P1-02 | `settings.py`: `AppSettings(BaseSettings)` | S | `src/chitchat/config/settings.py` |
| P1-03 | `engine.py`: SQLAlchemy engine 팩토리 | S | `src/chitchat/db/engine.py` |
| P1-04 | `models.py`: ORM 모델 전체 (12 테이블) | M | `src/chitchat/db/models.py` |
| P1-05 | `repositories.py`: `RepositoryRegistry` + 테이블별 Repository | M | `src/chitchat/db/repositories.py` |
| P1-06 | `migrations.py`: 프로그래밍 방식 Alembic 실행 | S | `src/chitchat/db/migrations.py` |
| P1-07 | `alembic/env.py` 실제 구현 | S | `alembic/env.py` |
| P1-08 | 첫 Alembic revision 생성 | XS | `alembic/versions/` |
| P1-09 | `key_store.py`: Keyring 래퍼 | S | `src/chitchat/secrets/key_store.py` |
| P1-10 | `ids.py`: ULID 기반 ID 생성 | XS | `src/chitchat/domain/ids.py` |
| P1-11 | `profiles.py`: Pydantic 도메인 모델 전체 | M | `src/chitchat/domain/profiles.py` |
| P1-12 | `provider_contracts.py`: Provider 통신 타입 | S | `src/chitchat/domain/provider_contracts.py` |
| P1-13 | `logging_config.py`: 로깅 설정 | XS | `src/chitchat/logging_config.py` |

### 테스트

| 테스트 | 검증 대상 |
|---|---|
| `test_profile_validation.py` | Pydantic 모델 경계값 검증 (min_length, max_length, ge, le) |
| `test_secret_storage_policy.py` | keyring set/get/delete 호출 패턴, DB에 평문 없음 |
| `test_repository_crud.py` | 각 테이블 insert/get/update/delete |

### 알고리즘 메모

- `new_id(prefix)`: `python-ulid` 라이브러리 또는 `ulid-py` 사용. `prefix + ulid.lower()` 형태.
- `estimate_tokens(text)`: `max(1, (len(text) + 3) // 4)`.

### 검증 포인트

- [x] `alembic upgrade head` 성공
- [x] `pytest tests/test_profile_validation.py -q` 통과 (32개)
- [x] `pytest tests/test_secret_storage_policy.py -q` 통과 (8개)
- [x] `pytest tests/test_repository_crud.py -q` 통과 (18개)
- [x] SQLite 파일에 12개 테이블 + alembic_version 존재 확인
- [x] `ruff check .` 0 에러

### 체크포인트 판정

✅ P1 완료: DB 생성 + 마이그레이션 + Repository CRUD + Keyring CRUD + Pydantic 검증 테스트 58개 전체 통과.

---

## 4. Phase 2: Provider 어댑터 + Capability 매퍼

### 목표

3종 Provider adapter가 `ChatProvider` Protocol을 구현하고, 각 Provider의 raw 응답을 `ModelCapability`로 정규화한다.

### 구현 항목

| ID | 항목 | 크기 | 파일 |
|---|---|---|---|
| P2-01 | `base.py`: Protocol re-export, 공통 에러 타입 | XS | `src/chitchat/providers/base.py` |
| P2-02 | `capability_mapper.py`: Provider별 raw → `ModelCapability` | M | `src/chitchat/providers/capability_mapper.py` |
| P2-03 | `gemini_provider.py`: `GeminiProvider` 구현 | M | `src/chitchat/providers/gemini_provider.py` |
| P2-04 | `openrouter_provider.py`: `OpenRouterProvider` 구현 | M | `src/chitchat/providers/openrouter_provider.py` |
| P2-05 | `lmstudio_provider.py`: `LMStudioProvider` 구현 | M | `src/chitchat/providers/lmstudio_provider.py` |
| P2-06 | `registry.py`: `ProviderRegistry` | S | `src/chitchat/providers/registry.py` |
| P2-07 | `provider_service.py`: Provider CRUD, 연결 테스트, 모델 패치 | M | `src/chitchat/services/provider_service.py` |

### 테스트

| 테스트 | 검증 대상 |
|---|---|
| `test_provider_capability_mapper.py` | Gemini/OpenRouter/LMStudio raw 샘플 → `ModelCapability` 정규화 |
| `test_provider_connection.py` | mock provider로 `validate_connection` 성공/실패 |
| `test_model_list.py` | mock provider로 `list_models` 반환값 검증 |

### 알고리즘 메모

- **Gemini**: `google-genai` SDK의 `models.list()`로 모델 메타데이터 획득. `input_token_limit` → `context_window_tokens`, `output_token_limit` → `max_output_tokens`.
- **OpenRouter**: `GET https://openrouter.ai/api/v1/models` 호출. `context_length`, `top_provider.max_completion_tokens`, `supported_parameters` 직접 매핑.
- **LM Studio**: `GET http://localhost:1234/v1/models`. token limit 미제공 시 `context_window_tokens = None`, 기본값 `8192`/`2048` 적용.

### 검증 포인트

- [x] `pytest tests/test_provider_capability_mapper.py -q` 통과 (15개)
- [x] `pytest tests/test_provider_connection.py -q` 통과 (4개)
- [x] `pytest tests/test_model_list.py -q` 통과 (3개)
- [x] mock provider로 3종 모두 `list_models` → `ModelCapability[]` 반환 확인
- [x] LM Studio의 unknown token limit 시 기본값 적용 확인
- [x] `ruff check .` 0 에러

### 체크포인트 판정

✅ P2 완료: 3종 Provider adapter + Capability Mapper + ProviderRegistry + ProviderService 구현 완료. 테스트 76개 전체 통과.

---

## 5. Phase 3: Profile CRUD + UI 기본 화면

> ⚠️ **아키텍처 주의**: P3는 PySide6 시대에 작성된 Phase이다. v1.0.0에서 FastAPI+SPA로 전환되었으며, P9에서 재구현되었다.

### 목표

7개 설정 화면(Provider, ModelProfile, UserPersona, AIPersona, Lorebook, Worldbook, ChatProfile)의 CRUD가 동작하고, 네오-브루탈리즘 기본 테마가 적용된 UI가 렌더링된다.

### 구현 항목

| ID | 항목 | 크기 | 파일 |
|---|---|---|---|
| P3-01 | `theme.py`: 디자인 토큰 딕셔너리, 글로벌 스타일시트 | M | `src/chitchat/ui/theme.py` |
| P3-02 | `main_window.py`: QMainWindow + QStackedWidget | M | `src/chitchat/ui/main_window.py` |
| P3-03 | `navigation.py`: 사이드바 | S | `src/chitchat/ui/navigation.py` |
| P3-04 | `app.py`: create_app() 팩토리 완성 | S | `src/chitchat/app.py` |
| P3-05 | `main.py`: 엔트리 포인트 완성 | XS | `src/chitchat/main.py` |
| P3-06 | `provider_page.py`: Provider CRUD + 연결 테스트 + 모델 패치 UI | M | `src/chitchat/ui/pages/provider_page.py` |
| P3-07 | `model_profile_page.py`: 모델 프로필 CRUD UI | M | `src/chitchat/ui/pages/model_profile_page.py` |
| P3-08 | `profile_service.py` (UserPersona, AIPersona, ModelProfile 포함) | S | `src/chitchat/services/profile_service.py` |
| P3-09 | `persona_page.py` (UserPersona + AIPersona 통합) | M | `src/chitchat/ui/pages/persona_page.py` |
| P3-10 | `lorebook_page.py` | M | `src/chitchat/ui/pages/lorebook_page.py` |
| P3-11 | `worldbook_page.py` | M | `src/chitchat/ui/pages/worldbook_page.py` |
| P3-12 | `chat_profile_page.py` + `entity_picker_dialog.py` | M | `src/chitchat/ui/pages/chat_profile_page.py` |
| P3-13 | `prompt_order_page.py` | M | `src/chitchat/ui/pages/prompt_order_page.py` |
| P3-14 | DD-11: ViewModel 계층 — v1.0.0에서 전면 도입 기각, chat.js 선택적 분리 | — | — |

### 테스트

| 테스트 | 검증 대상 |
|---|---|
| `test_model_save_validation.py` | capability 기반 파라미터 유효성 |
| UI 수동 테스트 | 각 페이지 렌더링, 폼 입력, Save CTA 동작 |

### 검증 포인트

- [x] `python -m chitchat.main` 실행 시 MainWindow 표시 (import 검증 완료)
- [x] 사이드바 9개 항목 클릭 시 페이지 전환
- [x] Provider 페이지에서 Save Provider → DB 저장 확인
- [x] 각 Persona 페이지에서 CRUD 동작 확인
- [x] Lorebook 키워드 쉼표 구분 입력/저장 동작 확인
- [x] 네오-브루탈리즘 테마 적용 (디자인 토큰, 글로벌 QSS)
- [x] `pytest tests/test_profile_crud_service.py -q` 통과 (12개)
- [x] `ruff check .` 0 에러
- [x] 전체 테스트 88개 통과

### 체크포인트 판정

✅ P3 완료: 7종 설정 페이지 (5개 실구현 + 2개 플레이스홀더) + ProfileService CRUD + 네오-브루탈 테마 + 88개 테스트 통과.

---

## 6. Phase 4: 프롬프트 조립 + 로어 매칭

### 목표

`PromptOrder`에 따른 블록 조합, 로어북 키워드 매칭, 컨텍스트 예산 관리, 히스토리 잘라내기가 동작하고 단위 테스트를 통과한다.

### 구현 항목

| ID | 항목 | 크기 | 파일 |
|---|---|---|---|
| P4-01 | `prompt_blocks.py`: `PromptBlock`, `AssembledPrompt`, `PromptOrderItem` | S | `src/chitchat/domain/prompt_blocks.py` |
| P4-02 | `lorebook_matcher.py`: `match_lore_entries()` | S | `src/chitchat/domain/lorebook_matcher.py` |
| P4-03 | `prompt_assembler.py`: `assemble_prompt()` | M | `src/chitchat/domain/prompt_assembler.py` |
| P4-04 | `prompt_service.py`: 프롬프트 조립 오케스트레이션 | M | `src/chitchat/services/prompt_service.py` |
| P4-05 | `chat_session.py`: 도메인 타입 + 상태 전이 | S | `src/chitchat/domain/chat_session.py` |

### 테스트

| 테스트 | 검증 대상 |
|---|---|
| `test_prompt_assembler.py` | 블록 순서, 블록 활성화/비활성화, 토큰 예측 합산, 히스토리 잘라내기 |
| `test_lorebook_matcher.py` | 키워드 매칭, casefold, 우선순위 정렬, 최대 12개, 최대 3000 토큰 |

### 알고리즘 메모

- **블록 조합**: `PromptOrderItem`을 `order_index` 순으로 정렬하고, `enabled=True`인 블록만 삽입한다.
- **로어북 매칭**: spec.md §12.4 알고리즘 그대로 구현. casefold + `in` 연산자.
- **히스토리 잘라내기**: system/persona/world/lore/current 블록 토큰 합산 후, 남은 예산으로 최신 메시지부터 삽입.

### 검증 포인트

- [x] `pytest tests/test_prompt_assembler.py -q` 통과 (10개)
- [x] `pytest tests/test_lorebook_matcher.py -q` 통과 (10개)
- [x] SC-07 (로어북 최근 8개 매칭) casefold + scan_messages=8 테스트 통과
- [x] SC-08 (PromptOrder 변경 시 순서 변경) enabled=False 블록 제외 테스트 통과
- [x] `ruff check .` 0 에러
- [x] 전체 테스트 108개 통과

### 체크포인트 판정

✅ P4 완료: 프롬프트 조립 엔진 + 로어북 매칭 + 히스토리 잘라내기 + 토큰 예산 관리. 108개 테스트 통과.

---

## 7. Phase 5: 채팅 스트리밍 + Inspector

> ⚠️ **아키텍처 주의**: P5는 PySide6 시대에 작성된 Phase이다. v1.0.0에서 FastAPI+WebSocket+SPA로 재구현되었으며, P9에서 완성되었다.

### 목표

사용자가 메시지를 보내면 스트리밍 응답을 수신하고, Stop으로 취소할 수 있으며, Prompt Inspector에서 조합 결과를 확인할 수 있다.

### 구현 항목

| ID | 항목 | 크기 | 파일 |
|---|---|---|---|
| P5-01 | `chat_service.py`: 스트리밍 실행/취소, 세션 상태 전이 | M | `src/chitchat/services/chat_service.py` |
| P5-02 | `async_bridge.py`: Qt Signal 기반 asyncio ↔ UI 브리지 (DD-11: ViewModel 대신 사용) | M | `src/chitchat/ui/async_bridge.py` |
| P5-03 | `chat_page.py`: 세션 리스트, 타임라인, 컴포저, Inspector | L | `src/chitchat/ui/pages/chat_page.py` |
| P5-04 | `chat_message_view.py`: 메시지 버블 위젯 | M | `src/chitchat/ui/widgets/chat_message_view.py` |
| P5-05 | `token_budget_bar.py`: 토큰 예산 시각화 | S | `src/chitchat/ui/widgets/token_budget_bar.py` |

### 테스트

| 테스트 | 검증 대상 |
|---|---|
| `test_chat_streaming.py` | mock provider 스트리밍, 취소, 에러 처리 |
| `test_session_state_machine.py` | 상태 전이: draft→active→streaming→active, streaming→stopped, streaming→failed |
| UI 수동 테스트 | Send/Stop 동작, Inspector 표시 |

### 알고리즘 메모

- **스트리밍**: `ChatService.start_stream()`이 asyncio Task를 생성한다. Task는 Provider의 `stream_chat()`으로부터 `ChatStreamChunk`를 수신하고, 매 chunk마다 Qt Signal을 emit한다.
- **취소**: `ChatService.stop_stream()`이 Task를 cancel한다. `asyncio.CancelledError`를 잡아 세션 상태를 `stopped`로 전환한다.
- **프롬프트 스냅샷**: Send 시 조합 결과를 JSON으로 직렬화하여 `ChatMessageData.prompt_snapshot_json`에 저장한다.

### 검증 포인트

- [x] `pytest tests/test_session_state_machine.py -q` 통과 (12개)
- [x] draft → active → streaming → stopped/failed 전이 검증
- [x] archived에서 복원 불가 검증
- [x] 세션 생성/메시지 저장/조회 CRUD 검증
- [x] ChatPage UI 위젯 통합 (세션 목록 + 타임라인 + 컴포저 + Inspector)
- [x] TokenBudgetBar 예산 시각화 위젯 구현
- [x] `ruff check .` 0 에러
- [x] 전체 테스트 120개 통과

### 체크포인트 판정

✅ P5 완료: ChatService + 상태 전이 + 스트리밍 인프라 + ChatPage UI + Inspector. 120개 테스트 통과.

---

## 8. Phase 6: 패키징 + 수용 테스트

### 목표

PyInstaller one-folder 빌드가 성공하고, 빌드된 앱에서 전체 플로우가 동작하며, SC-01 ~ SC-10 성공 기준을 모두 통과한다.

### 구현 항목

| ID | 항목 | 크기 | 파일 |
|---|---|---|---|
| P6-01 | PyInstaller spec 최적화 | S | `chitchat.spec` (PyInstaller용) |
| P6-02 | OS별 패키징 테스트 | M | 수동 |
| P6-03 | SC-01 ~ SC-10 수용 테스트 실행 | M | 수동 + 자동 |
| P6-04 | README.md 다국어 완성 | S | `README.md` |
| P6-05 | CHANGELOG.md v0.1.0b0 기록 | XS | `CHANGELOG.md` |

### 검증 포인트

- [x] `chitchat.spec` PyInstaller 스펙 작성 완료
- [x] `scripts/build.sh` 빌드 스크립트 작성 완료
- [x] SC-01: Provider 3종 생성 (자동 테스트 통과)
- [x] SC-02: API Key SQLite 평문 미저장 (자동 테스트 통과)
- [x] SC-06: 미지원 파라미터 UI 숨김 (자동 테스트 통과)
- [x] SC-07: 로어북 최근 8개 매칭 (자동 테스트 통과)
- [x] SC-08: PromptOrder 변경 시 순서 변경 (자동 테스트 통과)
- [x] SC-10: 전체 모듈 import + 버전 + 문서 존재 (자동 테스트 통과)
- [ ] SC-03~05: Provider 실제 API 호출 (수동 확인 필요)
- [ ] SC-09: 스트리밍 Stop 취소 (수동 확인 필요)
- [x] `ruff check .` 0 에러
- [x] 전체 테스트 213개 통과 (v1.1.1 기준)

### 체크포인트 판정

✅ P6 완료 (자동화 가능 항목): PyInstaller spec + 빌드 스크립트 + SC 자동 수용 테스트 6개(SC-01~02, SC-06~08, SC-10) 통과 + 223개 전체 테스트 통과.
SC-03~05, SC-09(4개)는 실제 API Key 및 Provider 서버가 필요하여 수동 검증 대상.

---

## 8. Phase 8: Vibe Fill 시스템 (v0.2.0)

### 목표

사용자의 짧은 바이브 문자열을 바탕으로 AI가 구체적인 롤플레이 데이터(캐릭터, 로어북, 세계관)를 자동 생성하는 기능을 구현하고 검증한다.

### 구현 항목

| ID | 항목 | 크기 | 파일 |
|---|---|---|---|
| P8-01 | Phase 1: Persona (14개 필드 확장 및 프롬프트 조립) | M | `domain/vibe_fill.py`, `persona_page.py` |
| P8-02 | Phase 2: Lorebook (배열 파싱 및 Append UI) | M | `domain/vibe_fill.py`, `lorebook_page.py` |
| P8-03 | Phase 3: Worldbook (10개 카테고리 템플릿 및 청크 연쇄) | L | `domain/vibe_fill.py`, `services/vibe_fill_service.py`, `worldbook_page.py` |
| P8-04 | Vibe Fill 통합 테스트 케이스 보강 및 223개 테스트 통과 | M | `tests/test_vibe_fill_service.py`, `tests/test_migrations.py` |

### 테스트

| 테스트 | 검증 대상 |
|---|---|
| Phase 1 Tests | 단일 캐릭터 JSON 파싱, 기본값 폴백, 프롬프트 조립 |
| Phase 2 Tests | 로어북 JSON 배열 파싱, 키 정규화, priority 클램핑 |
| Phase 3 Tests | 10개 카테고리 분할, 청크 설정, 연쇄 컨텍스트 주입 |

### 알고리즘 메모

- **Worldbook 청크 연쇄**: `[역사, 지리, 세력/국가]`, `[종족, 마법/기술, 경제]`, `[종교/신화, 던전/위험지대]`, `[일상/문화, 규칙/법칙]` 4개 청크로 분할하여 LLM을 호출한다.
- 이전 청크 결과 중 `title`만 추출하여 다음 청크 시스템 프롬프트에 주입 (토큰 오버플로 방지 및 논리적 일관성 유지).

### 검증 포인트

- [x] Phase 1, 2, 3 로직 및 61개 단위 테스트 + 서비스 결합 테스트 작성 완료
- [x] `ruff check .` 0 에러
- [x] `mypy src/chitchat` 0 에러
- [x] `pytest -q` 전체 223개 통과 (test_vibe_fill.py 61개 + test_vibe_fill_service.py 결합 테스트 + test_migrations.py 4개 포함)

### 체크포인트 판정

✅ P8 완료: Vibe Fill 전체 파이프라인(Phase 1~3), DB 마이그레이션 회귀 방지 포함 223개 테스트 통과.

---

## 9. 체크포인트 정책

| 조건 | 행동 |
|---|---|
| Phase 내 검증 포인트 100% 통과 | 다음 Phase 진행 |
| Phase 내 검증 포인트 80% 이상 통과, 실패 항목이 다음 Phase에서 해결 가능 | 다음 Phase 진행 + 잔여 항목 명시 |
| Phase 내 검증 포인트 80% 미만 통과 | Phase 재수행 |
| 문서-코드 불일치 발견 | 코드 생성 즉시 중단, 문서 동기화 후 재개 |
| 아키텍처 규칙 위반 발견 | 위반 수정 후 해당 Phase 검증 포인트 재실행 |

---

## 10. 핵심 리스크

| 리스크 | 영향 | Phase | 완화 |
|---|---|---|---|
| `google-genai` SDK 변경 | Gemini provider 깨짐 | P2 | raw 메타데이터 저장, mapper 단위 테스트 |
| OpenRouter `supported_parameters` 필드명 변경 | 파라미터 숨김 실패 | P2 | `supported_parameters`를 source of truth로 사용 |
| LM Studio token limit 미제공 | 토큰 예산 부정확 | P2 | 기본값 `8192`/`2048` + 경고 배너 |
| Keyring 백엔드 미사용 (Linux) | Key 저장 실패 | P1 | 에러 배너 + SecretService 설치 가이드 |
| asyncio ↔ Qt 통합 불안정 | 스트리밍 UI 멈춤 | P5 | `qasync` 실패 시 Thread 대안 전환 |
| 브라우저 호환성 차이 | UI 깨짐 | P9 | 모던 브라우저 권장 (Chrome/Firefox/Edge) |
| 대량 채팅 히스토리 UI 성능 | UX 저하 | P5 | 가상화 리스트 또는 보이는 위젯만 렌더링 |

---

## 10. Phase 9: v1.0.0 풀스택 전환 + 프로덕션 강화

### 목표

PySide6 → FastAPI+SPA 풀스택 전환을 완료하고, 데이터 무결성 검증, 설정 고도화, 프롬프트 Inspector, 토스트 시스템 등 프로덕션 수준의 기능을 구현한다.

### 구현 항목

| ID | 항목 | 크기 | 파일 |
|---|---|---|---|
| P9-01 | DB 스키마 + PySide6 제거 + FastAPI+SPA 전환 | L | 전체 아키텍처 |
| P9-02 | REST API 43개 엔드포인트 구현 | L | `api/routes/*.py` |
| P9-03 | 프론트엔드 9개 페이지 구현 | L | `frontend/js/pages/*.js` |
| P9-04 | DynamicStateEngine AI 판단 기반 상태 분석 | M | `services/dynamic_state_engine.py` |
| P9-05 | VibeSmith 9섹션 동적 캐릭터 시스템 | M | `domain/vibesmith_persona.py` |
| P9-06 | 프롬프트 Inspector 패널 | M | `chat.js`, `chat.py` |
| P9-07 | 7개 엔티티 삭제 참조 무결성 검증 | M | `profile_service.py`, `provider_service.py` |
| P9-08 | 설정 페이지 4섹션 고도화 (DD-12) | M | `settings.js`, `settings.py`, `user_preferences.py` |
| P9-09 | 토스트 알림 시스템 (alert 완전 제거) | S | `api.js`, 9개 페이지 JS |
| P9-10 | 회귀 테스트 강화 (211건) | M | `tests/*.py` |

### 테스트

| 테스트 | 검증 대상 |
|---|---|
| `test_profile_crud_service.py` | 7개 엔티티 CRUD + 참조 무결성 (21건) |
| `test_user_preferences.py` | 설정 확장 필드 저장/로드/리셋 (15건) |
| `test_session_state_machine.py` | 세션 상태 전이 (12건) |
| `test_prompt_assembler.py` | 프롬프트 조립 + Inspector 스냅샷 (10건) |

### 검증 포인트

- [x] `ruff check .` 0 에러
- [x] `pytest -q` 전체 213건 통과
- [x] 프론트엔드 `alert()` 사용 0건
- [x] 참조 무결성: 7개 엔티티 삭제 차단 + Provider 참조 검사
- [x] 설정: 4섹션 UI + 초기화 + 확장 필드 영속화
- [x] Inspector: 우측 패널 탭 전환, 스냅샷 저장/조회

### 체크포인트 판정

✅ P9 완료: v1.0.0 풀스택 전환 + 프로덕션 강화 전체 완료. 213건 테스트 통과.

---

## 11. Phase별 예상 작업량

| Phase | Task 수 | 예상 규모 | 누적 파일 수 |
|---|---|---|---|
| P0 | 6 | S | ~15 |
| P1 | 13 | M | ~30 |
| P2 | 7 | M | ~40 |
| P3 | 14 | L | ~55 |
| P4 | 5 | M | ~60 |
| P5 | 6 | L | ~66 |
| P6 | 5 | M | ~68 |
| P8 | 4 | L | ~72 |
| P9 | 10 | XL | ~85 |

전체 Task: 70개. MVP 도달까지 6 Phase, Vibe Fill 1 Phase, v1.0.0 풀스택 전환 1 Phase, v1.1.1 프론트엔드 강화 1 Phase.

---

## 12. Phase 10: v1.1.1 프론트엔드 아키텍처 강화

### 목표

5차 감사 권고 사항을 반영하여 프론트엔드의 모듈 구조와 이벤트 바인딩을 프로덕션 수준으로 강화한다.

### 구현 항목

| ID | 항목 | 크기 | 파일 |
|---|---|---|---|
| P10-01 | 인라인 onclick 전면 제거 + 이벤트 위임 전환 (7개 모듈) | M | `frontend/js/pages/*.js` |
| P10-02 | window 브릿지 완전 삭제 | S | `frontend/js/pages/*.js` |
| P10-03 | 순환 import 해소 (`chat_utils.js` 분리 + 동적 import) | S | `chat_session.js`, `chat_composer.js`, `chat_utils.js` |
| P10-04 | optional chaining 좌측 할당 에러 수정 | XS | `models.js`, `personas.js`, `lorebooks.js`, `worldbooks.js`, `chat_profiles.js` |
| P10-05 | NoCacheMiddleware 추가 (개발 환경 캐시 방지) | S | `src/chitchat/api/app.py` |
| P10-06 | spec.md §5.1.2 이벤트 바인딩 규칙 추가 | XS | `spec.md` |
| P10-07 | DD-24 갱신 (이벤트 위임 + 순환 import 해소) | XS | `DESIGN_DECISIONS.md` |

### 검증 포인트

- [x] `grep -rnE 'onclick="|onchange="|onsubmit="|oninput="' frontend/js/**/*.js` → 0건 (HTML 인라인 속성 방지)
- [x] `grep -rnE '\.onclick\s*=|\.onchange\s*=' frontend/js/**/*.js` → 0건 (JS 프로퍼티 할당 방지 — chat_composer.js 등 동적 DOM 포함)
- [x] `grep -rn 'window\.' frontend/js/pages/*.js` → 0건 (window 브릿지 완전 제거)
- [x] `node --check` 전체 JS 파일 문법 통과
- [x] 브라우저에서 14개 모듈 전부 로드 성공 (✅)
- [x] 네비게이션, 모달 열기/닫기, 이벤트 위임 전체 정상 동작
- [x] `ruff check .` 0 에러
- [x] `mypy src/chitchat` 0 에러
- [x] `pytest -q` 213건 통과

### 체크포인트 판정

✅ P10 완료: 이벤트 위임 전면 전환 + window 브릿지 완전 삭제 + 순환 import 해소 + NoCacheMiddleware. 213건 테스트 통과.
