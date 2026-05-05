# CHANGELOG.md

이 프로젝트의 모든 주요 변경사항을 기록한다.

형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/)를 따르며,
버전 관리는 [Semantic Versioning](https://semver.org/lang/ko/)을 준수한다.

---

## [미출시]

### 추가됨 (v1.0.0: VibeSmith 동적 페르소나 + Web 전환)

- **아키텍처 전환**: PySide6 데스크톱 앱 → Python FastAPI 백엔드 + HTML/CSS/JS 웹 프론트엔드
- **VibeSmith 동적 페르소나 시스템**: 14필드 정적 구조 → 9섹션 동적 구조
  - Fixed Canon, Core Dynamic Model, Social & Relationship Model, Adaptive Behavior Rules
  - Habits & Behavioral Texture, Emotional Dynamics, Memory Update Policy
  - Response Generation Rule, Coherence Check Report
- **동적 상태 엔진**: 매 AI 응답 후 기억/관계/감정/사회적 위치를 자동 갱신
- **원본 캐릭터 MD 문서**: 생성 시 원본 Markdown 페르소나 카드 저장 (불변)
- **SQLite+ZSTD 동적 상태 저장**: 동적 요소를 압축하여 별도 테이블에 영속화
- **프롬프트 어셈블러 v2**: 동적 상태 블록을 프롬프트 조립 시 자동 주입
- **WebSocket 스트리밍 채팅**: FastAPI WebSocket을 통한 실시간 AI 응답 수신

### 제거됨 (v1.0.0)

- PySide6 UI 레이어 전체 (pages, widgets, theme, navigation, main_window)
- PyInstaller 빌드 시스템 (chitchat.spec, scripts/build.sh)

### 추가됨 (v0.3.0: i18n + 사용자 설정 시스템)

- **i18n 국제화 시스템**: JSON 기반 경량 번역 엔진
  - `i18n/translator.py`: 싱글톤 Translator 클래스, tr() 전역 단축 함수
  - `i18n/locales/`: 5개 로케일 지원 (ko, en, ja, zh_tw, zh_cn) — **357키 × 5개 언어**
  - **전체 UI 문자열 전수 전환**: 버튼, 라벨, 타이틀, 상태 메시지, placeholder 예시, tooltip, 다이얼로그 — 10개 페이지 + navigation + main_window 완전 적용
  - 키 미존재 시 키 문자열 자체를 반환하여 UI 크래시 방지 (폴백)

- **사용자 설정 영속화**: `config/user_preferences.py`
  - `app_data_dir/settings.json`에 평문 JSON 저장 (민감 정보 없음)
  - UI 언어(ui_locale), Vibe Fill 출력 언어(vibe_output_language) 설정 지원
  - 파일 미존재/파싱 실패 시 기본값 자동 폴백

- **설정 페이지**: `ui/pages/settings_page.py`
  - UI 언어 드롭다운 (5개 로케일)
  - Vibe Fill AI 출력 언어 선택 (한국어/영어)
  - 앱 버전, 데이터 경로 표시
  - 설정 변경 시 즉시 저장, UI 언어 변경 시 재시작 안내

- **Vibe Fill 다국어 출력**: 시스템 프롬프트 3개에 `{output_language}` 동적 주입
  - `get_vibe_system_prompt()`, `get_lore_system_prompt()`, `get_world_system_prompt()` 함수 추가
  - `VibeFillService`가 `UserPreferences.vibe_output_language`를 읽어 출력 언어 자동 적용

- **테스트 확장**: 223개 (i18n 13건 — 5개 로케일 키 패리티 검증 포함, UserPreferences 8건)

### 추가됨 (v0.2.0: Vibe Fill Phase 1 — AI 기반 캐릭터 자동 생성)

- **Vibe Fill 시스템**: 바이브 텍스트 입력 → AI가 14개 필드를 자동 생성
  - `domain/vibe_fill.py`: 시스템 프롬프트 템플릿, JSON Schema, LLM 응답 파싱
  - `services/vibe_fill_service.py`: Provider LLM 스트리밍 호출, 에러 핸들링
  - Provider/Model 선택 드롭다운으로 사용자가 원하는 LLM 지정 가능

- **AI Persona 14개 필드 확장**: 기존 6개 → 14개
  - 신규 필드: 나이(age), 성별(gender), 외모(appearance), 배경(backstory), 인간관계(relationships), 특기(skills), 취미(interests), 약점(weaknesses)
  - `db/models.py`: `AIPersonaRow`에 8개 컬럼 추가 (default="" 하위호환)
  - `domain/profiles.py`: `AIPersonaData`에 8개 필드 추가
  - `services/profile_service.py`: `save_ai_persona()`에 8개 매개변수 추가

- **AI Persona UI 전면 개편**: `ui/pages/persona_page.py`
  - Vibe Fill 입력 영역 (바이브 텍스트 + Provider/Model 드롭다운 + AI로 채우기 버튼)
  - 4개 섹션으로 구조화 (기본정보/외면/내면/서사/능력/행동규칙)
  - QScrollArea 적용으로 14개 필드 스크롤 지원
  - AsyncSignalBridge를 통한 비동기 LLM 호출

- **프롬프트 조립 확장**: `services/prompt_service.py`
  - AI Persona 텍스트를 14개 필드 구조화된 캐릭터 시트로 결합
  - 빈 필드 자동 스킵으로 기존 데이터 하위호환

- **테스트**: `tests/test_vibe_fill.py` (16개)
  - 프롬프트 조립, 다양한 JSON 형식 파싱, 에러 핸들링, 타입 변환 검증

### 추가됨 (v0.2.0: Vibe Fill Phase 2 — AI 로어북 엔트리 자동 생성)

- **Lorebook Vibe Fill 시스템**: 바이브 + 캐릭터 컨텍스트 → 로어 엔트리 복수 건 자동 생성
  - `domain/vibe_fill.py`: `LORE_FILL_SYSTEM_PROMPT`, `LoreFillResult`, `build_lore_prompt()`, `parse_lore_response()` 추가
  - `services/vibe_fill_service.py`: `generate_lore_entries()` 메서드 추가 — 캐릭터 시트 조립, 기존 엔트리 중복 방지, LLM 호출
  - AI Persona 선택적 주입으로 캐릭터 세계관 연계 생성

- **로어북 UI 전면 개편**: `ui/pages/lorebook_page.py`
  - Vibe Fill 패널: AI Persona 드롭다운 + 바이브 입력 + Provider/Model 선택
  - 생성 미리보기 체크리스트: 개별 체크 on/off로 선택 저장
  - Append 방식: 기존 엔트리 유지, 새 엔트리만 추가
  - QScrollArea 적용으로 확장 UI 지원

- **트리거 + 우선순위 자동 결정**: AI가 activation_keys와 priority를 자동 판단
  - 키워드: 최소 2개, 유의어/약칭 포함
  - 우선순위: 핵심 300~500, 일반 100~200, 부가 50~100

- **테스트**: `tests/test_vibe_fill.py` (22개 추가, 총 38개)
  - 로어 프롬프트 조립, JSON 배열 파싱, 엔트리 검증, 키 정규화, priority 클램핑

### 추가됨 (v0.2.0: Vibe Fill Phase 3 — AI 세계관 자동 생성)

- **Worldbook Vibe Fill 시스템**: 바이브 + 캐릭터 + 로어북 컨텍스트 → 세계관 엔트리 청크 분할 생성
  - `domain/vibe_fill.py`: 10개 세계관 카테고리 정의, 청크 분할 설정, `WORLD_FILL_SYSTEM_PROMPT`, `WorldFillResult`, `build_world_prompt()`, `parse_world_response()`
  - `services/vibe_fill_service.py`: `generate_world_entries()` — 청크별 LLM 연쇄 호출, `_build_lore_summaries()` 로어북 요약 조립
  - AI Persona + Lorebook 복수 선택으로 세계관 연계 생성

- **10개 세계관 카테고리**: 역사, 지리, 세력/국가, 종족, 마법/기술, 경제, 종교/신화, 던전/위험지대, 일상/문화, 규칙/법칙

- **청크 분할 생성 알고리즘**:
  - 카테고리를 2~3개씩 4그룹으로 분할하여 LLM 4번 호출
  - 이전 청크의 엔트리 제목을 다음 청크에 연쇄 컨텍스트로 주입 (일관성 유지 + 토큰 절약)
  - 부분 실패 시 이전 청크 결과 유지

- **월드북 UI 전면 개편**: `ui/pages/worldbook_page.py`
  - Vibe Fill 패널: AI Persona×2 + Lorebook×2 드롭다운 + 카테고리 체크박스 + Provider/Model
  - QProgressBar 진행률 표시: "2/4 — 종족, 마법, 경제 생성 중..."
  - 생성 미리보기 체크리스트 + Append 저장

- **테스트**: `tests/test_vibe_fill.py` (23개 추가, 총 61개)
  - 카테고리 정의, 청크 분할, 프롬프트 조립, JSON 배열 파싱, 연쇄 컨텍스트

### 수정됨 (v0.1.4: 구현 감사 수정)

- `ui/pages/chat_profile_page.py`: **버그 수정 (HIGH)** — PromptOrder 보존 버그
  - 기존: ChatProfile 편집 저장 시 항상 `_DEFAULT_PROMPT_ORDER`로 덮어씀
  - 수정: 기존 프로필 편집 시 DB에 저장된 `prompt_order_json`을 유지, 새 프로필 생성 시에만 기본값 사용
  - PromptOrderPage에서 변경한 순서가 ChatProfile 수정 저장 시 초기화되는 문제 해결

- `domain/prompt_blocks.py`: **개선** — AssembledPrompt에 spec §12.6 계약 필드 추가
  - `matched_lore_entry_ids`: 매칭된 로어 엔트리 ID 목록
  - `truncated_history_message_ids`: 예산 초과로 잘린 히스토리 메시지 ID 목록

- `services/prompt_service.py`: **개선** — 조립 결과에 `matched_lore_entry_ids` 수집

- `services/chat_service.py`: **개선** — PromptSnapshot에 실제 `truncated_history_message_ids` 반영
  - 기존: 항상 빈 배열 → 수정: assembled에서 수집한 실제 ID 사용

- `tests/test_e2e_acceptance.py`: **개선** — SC-10 `test_all_imports_resolve` 빈 테스트 보강
  - 21개 핵심 모듈의 실제 import 검증 로직 추가

### 수정됨 (v0.1.4: mypy 34건 전수 해결)

- **12개 파일, 34건 mypy 오류 전수 수정** → `mypy src/chitchat` 0 errors (53 source files)
- `app.py`: `QCoreApplication.setStyleSheet` 접근 오류 → `isinstance(qapp, QApplication)` assert 보장
- `provider_page.py`: `object.message` 접근 → `getattr` 패턴으로 안전 접근, 6건 unused `type: ignore` 제거
- `prompt_service.py`: `LoreEntryRow`/`WorldEntryRow` 타입 추론 혼선 → 변수명 분리 (`entry` → `lore_entry`)
- `persona_page.py`: `QTextEdit`/`QLineEdit` 타입 불일치 → 별도 `.clear()` 호출로 분리
- `chat_profile_page.py`: `callable` → `Callable[[str], None]`, QLayoutItem None 안전 처리
- `chat_page.py`: QLayoutItem None 안전 처리 2곳
- `prompt_order_page.py`: QLayoutItem None 안전 처리
- `model_profile_page.py`: `QAbstractSpinBox.value()` 접근 → `dict[str, QDoubleSpinBox | QSpinBox]` 명시
- `chat_service.py`: `dict`/`list` 제네릭 타입 인자 추가 5건, `ChatProfileRow`/`UserPersonaRow` 반환 타입 명시
- `openrouter_provider.py`, `lmstudio_provider.py`: `dict` → `dict[str, object]` 명시
- `token_budget_bar.py`: unused `type: ignore[override]` 제거

### 수정됨 (v0.1.4: truncated_history_message_ids 실제 산출)

- `domain/prompt_assembler.py`: 히스토리 잘라내기 시 인덱스 추적 → `included_indices` 기반 잘린 메시지 ID 산출
  - `history_message_ids` 선택 매개변수 추가: 전달 시 잘린 메시지 ID를 `AssembledPrompt.truncated_history_message_ids`에 기록
  - **버그 수정 (HIGH)**: `included_indices`를 상위 스코프에서 초기화하여 `history_budget <= 0`일 때 `UnboundLocalError` 방지
- `services/prompt_service.py`: `build_prompt()`에 `history_message_ids` 매개변수 추가 및 assembler에 전달
- `services/chat_service.py`: 스트리밍 시작 시 `history_ids`를 `build_prompt()`에 전달

### 변경됨 (v0.1.4: 문서-코드 정합성 동기화)

- `spec.md`: 런타임 흐름 `run Alembic migrations` → `Base.metadata.create_all(engine)` 갱신 (실제 구현 반영)
- `spec.md`: 아키텍처 §5 ViewModel 계층에 DD-11 (의도적 간소화) 명시
- `spec.md`: 의존성 규칙 §5.1에 MVP v0.1 허용 규칙 (`ui → services` 직접 호출) 추가
- `spec.md`: 디렉토리 구조 §6을 현재 실제 파일에 맞게 전면 갱신
  - `model_service.py` 제거 (profile_service.py에 통합)
  - ViewModel 파일 제거 (DD-11에 따라 v0.2 도입 예정)
  - `async_bridge.py`, `entity_picker_dialog.py` 추가
  - 테스트 파일 12개로 현행화
- `implementation_summary.md`: §3.3~3.4 경계 계약을 DD-11에 맞게 전면 갱신 (ViewModel → Service 직접 호출)
- `audit_roadmap.md`: P5 `chat_vm.py` → `async_bridge.py`로 교체, P5-06 asyncio 통합 항목 제거
- `audit_roadmap.md`: P3 구현 항목에서 `provider_vm.py`, `profile_vm.py`, `prompt_order_list.py` 제거 → 현행 구조 반영
- `audit_roadmap.md`: 테스트 수치 129개 → 134개 갱신
- `BUILD_GUIDE.md`: 체크리스트에 `mypy src/chitchat` 통과 항목 추가, 테스트 수치 134개로 갱신
- `BUILD_GUIDE.md`: SC 수용 테스트 문구를 자동화 가능 항목(SC-01~02, SC-06~08, SC-10) + 수동 확인 항목(SC-03~05, SC-09)으로 구분
- `BUILD_GUIDE.md`: 디렉토리 생성 스크립트에서 viewmodels 폴더를 DD-11 주석으로 변경
- `README.md`: License/Contributing TBD → 실제 내용 교체

### 추가됨 (v0.1.3: 잔여 감사 수정)

- `ui/pages/prompt_order_page.py`: **신규** — 프롬프트 블록 순서 재정렬 페이지 (SC-08)
  - 7종 블록의 순서 변경, 활성화/비활성화, 미리보기, 기본값 복원
  - DD-05 결정에 따른 잠금 규칙 적용 (system_base/current_input 고정)
  - ChatProfile별 독립적 PromptOrder 저장
- `ui/pages/model_profile_page.py`: **개선** — 모델 파라미터 동적 가시성 (SC-06, DD-13)
  - supported_parameters 기반 미지원 파라미터 자동 숨김
  - capability 정보 불완전 시 경고 표시 + 전체 파라미터 노출
  - spec §11.2 Save Validation 5개 조건 적용 (Provider 비활성화, capability 미로드, max_output 초과, 범위 검증, 숨겨진 파라미터 경고)
- `ui/pages/provider_page.py`: **개선** — Provider Setup State 시각화 (spec §13.1)
  - 5단계 셋업 진행 상태를 시각적 체크리스트로 표시
  - Provider 선택/테스트/모델 패치 시 자동 갱신
- `services/chat_service.py`: **개선** — PromptSnapshot spec §12.6 규격 준수
  - chat_profile_id, user_persona_id, model_profile_id, prompt_order, blocks, matched_lore_entry_ids, truncated_history_message_ids, total_token_estimate, created_at_iso 필드 포함
- `ui/navigation.py`: 사이드바에 '📝 프롬프트 순서' 항목 추가
- `services/profile_service.py`: `update_chat_profile_prompt_order()` 메서드 추가

### 변경됨 (v0.1.3: 문서 동기화)

- `DESIGN_DECISIONS.md`: DD-11 (ViewModel 간소화), DD-12 (설정 페이지 범위), DD-13 (파라미터 가시성 전략) 추가
- `DESIGN_DECISIONS.md`: DD-05 PromptBlockKind 이름 코드 기준 통일
- `implementation_summary.md`: v0.1.2/v0.1.3 Phase 상태 갱신, §8.1 잔여 작업 목록 추가
- `designs.md`: PromptOrderPage 구현 상태 기재, §9.10 블록 이름 통일

### 추가됨 (v0.1.2: 전수조사 감사 수정)

- `ui/pages/chat_page.py`: 스트리밍 실시간 표시 — AI 응답이 매 청크마다 버블에 표시됨
  - 기존: 스트리밍 완료 후에만 버블 생성 → 개선: 실시간 `update_content()` 호출
- `ui/pages/chat_page.py`: ChatProfile / UserPersona 선택 드롭다운 추가
  - 사용자가 직접 프로필·페르소나를 선택 후 세션 생성 (기존: 자동 첫 번째 선택)
- `ui/pages/chat_page.py`: 세션 삭제 버튼 추가
- `ui/widgets/chat_message_view.py`: `update_content()` 메서드 추가 (스트리밍 실시간 갱신)
- `db/repositories.py`: `ChatSessionRepository.delete_by_id()` 추가
- `db/repositories.py`: `ChatMessageRepository.delete_by_session()` 추가
- `services/chat_service.py`: `delete_session()` 메서드 추가

### 변경됨 (v0.1.2: 문서 정합성)

- `spec.md`: PromptBlockKind 이름 통일 (`lorebook_matches` → `lorebook`, `current_user_message` → `current_input`)
  - 코드 구현과 spec 문서 간 명칭 불일치 해소 (§12.2, §14.8)
- `app.py`, `main_window.py`: 버전 문자열을 `v0.1.2`로 통일

### 추가됨 (v0.1.1: UI 개선)

- `ui/widgets/entity_picker_dialog.py`: 참조 엔티티 선택을 위한 공용 모달 다이얼로그 신규 생성
  - 검색 필터, 최대 선택 개수 제한, 빈 상태 안내 문구 지원
  - AI 페르소나 / 로어북 / 월드북 3곳에서 재사용

### 변경됨 (v0.1.1: UI 개선)

- `ui/pages/persona_page.py`: 모든 입력 필드에 구체적인 Placeholder 예제 추가
  - '경계', '목표', '제한' 등 모호했던 필드 라벨에 보조 설명 추가 (예: "경계 (원치 않는 내용)")
- `ui/pages/chat_profile_page.py`: 참조 엔티티 선택 UI를 태그 + [추가...] 다이얼로그 패턴으로 전면 개선
  - 기존 QListWidget(MultiSelection) 방식에서 EntityPickerDialog 기반으로 변경
  - 선택된 항목이 태그 형태로 표시되며 [×] 버튼으로 개별 해제 가능
  - 빈 상태일 때 안내 문구가 표시되어 사용자 행동을 유도
  - 시스템 프롬프트 필드에도 Placeholder 예제 추가
- `designs.md`: v0.1.1 구현 상태와 동기화 — Persona 필드 placeholder 및 ChatProfilePage 와이어프레임 갱신

### 수정됨 (버그 픽스)

- `scripts/build.py`: 사용하지 않는 `shutil` 모듈 import 제거 및 f-string 구문 오류 수정 (ruff lint 실패 버그 해결)

### 추가됨 (P0: 스캐폴딩)

- `pyproject.toml`: 빌드 설정 및 의존성 정의
- `src/chitchat/`: 11개 `__init__.py`로 패키지 구조 생성
- `alembic.ini` + `alembic/env.py` + `alembic/script.py.mako`: Alembic 마이그레이션 설정
- `.gitignore`: Python 프로젝트 표준 제외 패턴
- `README.md`: 5개 언어(한/영/일/중번체/중간체) 초안 작성

### 추가됨 (P1: 인프라 레이어)

- `src/chitchat/domain/ids.py`: ULID 기반 정렬 가능 ID 생성 (`new_id()`)
- `src/chitchat/domain/provider_contracts.py`: Provider 경계 계약 타입 전체
- `src/chitchat/domain/profiles.py`: Pydantic 프로필 도메인 모델 전체
- `src/chitchat/domain/chat_session.py`: 채팅 세션/메시지 도메인 타입 + 상태 전이 검증
- `src/chitchat/config/paths.py`: OS별 앱 데이터 경로 결정 + `ensure_app_dirs()`
- `src/chitchat/config/settings.py`: `AppSettings(BaseSettings)` pydantic-settings 기반 설정
- `src/chitchat/logging_config.py`: 콘솔 + 파일 동시 로깅 (UTF-8 강제)
- `src/chitchat/db/engine.py`: SQLAlchemy 엔진 팩토리 (WAL 모드, FK 강제)
- `src/chitchat/db/models.py`: ORM 모델 12개 테이블 정의
- `src/chitchat/db/repositories.py`: Repository 패턴 12종 + RepositoryRegistry
- `src/chitchat/db/migrations.py`: 프로그래밍 방식 Alembic 마이그레이션 실행
- `src/chitchat/secrets/key_store.py`: OS keyring 래퍼 (set/get/delete)
- `alembic/versions/792a*_initial_schema.py`: 첫 마이그레이션 (12 테이블)
- P1 테스트 58개: 프로필 검증, 키링 정책, Repository CRUD

### 추가됨 (P2: Provider 레이어)

- `src/chitchat/providers/base.py`: Protocol re-export, 3종 에러 타입 (Connection, Api, Stream)
- `src/chitchat/providers/capability_mapper.py`: 3종 Provider raw → ModelCapability 통합 매퍼
- `src/chitchat/providers/gemini_provider.py`: Gemini Provider adapter (google-genai SDK)
- `src/chitchat/providers/openrouter_provider.py`: OpenRouter Provider adapter (httpx, SSE)
- `src/chitchat/providers/lmstudio_provider.py`: LM Studio Provider adapter (로컬 서버, API Key 불필요)
- `src/chitchat/providers/registry.py`: ProviderRegistry (provider_kind → adapter 싱글턴)
- `src/chitchat/services/provider_service.py`: Provider CRUD, 연결 테스트, 모델 패치/캐시 갱신
- P2 테스트 18개: capability mapper, 연결 mock, 모델 목록 mock

### 추가됨 (P3: Profile CRUD + UI)

- `src/chitchat/ui/theme.py`: 네오-브루탈리즘 디자인 토큰 + 글로벌 QSS
- `src/chitchat/ui/navigation.py`: 사이드바 네비게이션 (9개 항목)
- `src/chitchat/ui/main_window.py`: QMainWindow + QStackedWidget 페이지 라우팅
- `src/chitchat/ui/pages/provider_page.py`: Provider CRUD + 연결 테스트 + 모델 패치 UI
- `src/chitchat/ui/pages/persona_page.py`: UserPersona + AIPersona 관리 페이지
- `src/chitchat/ui/pages/lorebook_page.py`: 로어북 + 엔트리 3-column 관리
- `src/chitchat/ui/pages/worldbook_page.py`: 월드북 + 엔트리 3-column 관리
- `src/chitchat/services/profile_service.py`: 7종 엔티티 CRUD 서비스
- `src/chitchat/app.py`: 앱 팩토리 (의존성 조립)
- `src/chitchat/main.py`: 앱 엔트리포인트
- P3 테스트 12개: ProfileService CRUD 통합 테스트

### 추가됨 (P4: Prompt Assembly + Lore Matching)

- `src/chitchat/domain/prompt_blocks.py`: PromptBlock, AssembledPrompt, estimate_tokens()
- `src/chitchat/domain/lorebook_matcher.py`: casefold 키워드 매칭, priority 정렬, 토큰 제한
- `src/chitchat/domain/prompt_assembler.py`: PromptOrder 기반 블록 조합, 히스토리 잘라내기
- `src/chitchat/services/prompt_service.py`: ChatProfile 기반 프롬프트 조립 오케스트레이션
- P4 테스트 20개: 로어북 매칭 10개 + 프롬프트 조립 10개

### 추가됨 (P5: Chat Streaming + Inspector)

- `src/chitchat/services/chat_service.py`: 스트리밍 실행/취소, 세션 상태 전이, 메시지 저장
- `src/chitchat/ui/pages/chat_page.py`: 세션 목록 + 타임라인 + 컴포저 + Inspector 탭
- `src/chitchat/ui/widgets/token_budget_bar.py`: 토큰 예산 시각화 바
- `src/chitchat/ui/widgets/chat_message_view.py`: 채팅 메시지 버블 위젯
- P5 테스트 12개: 세션 상태 전이 + ChatService CRUD

### 추가됨 (P6: 패키징 + 수용 테스트)

- `chitchat.spec`: PyInstaller 빌드 스펙 (one-folder, hidden imports)
- `scripts/build.sh`: 빌드 스크립트 (검증 → 빌드 → 산출물 확인)
- `tests/test_e2e_acceptance.py`: SC-01~SC-10 자동 수용 테스트 (9개)
- `BUILD_GUIDE.md`: v0.1.0b0으로 최신화, 체크리스트 갱신

### 수정됨 (정합성 감사 Remediation)

- `provider_contracts.py`: ChatProvider Protocol에 `api_key` 파라미터 추가 (Protocol ↔ 구현 시그니처 일치)
- `chat_service.py`: ChatCompletionRequest 생성 시 `provider_profile_id` 추가, `run_stream()` 래퍼 추가, `get_available_*` 도우미 메서드 추가
- `prompt_assembler.py`: 히스토리 role 매칭을 인덱스 기반으로 변경 (BUG-05 수정)
- `prompt_service.py`: worldbook 정렬 `_priority` 참조 제거 (BUG-06 수정)
- `chat_page.py`: `_on_send()`에서 `run_stream()` 호출하여 채팅 루프 완성, `_repos` 직접 접근 제거
- `LESSONS_LEARNED.md` 신규 생성 (D3D 필수 문서 G-05)

### 추가됨 (MVP Hardening)

- `ui/async_bridge.py`: Qt Signal 기반 asyncio ↔ UI 브리지 (스트리밍/비동기 작업 thread-safe)
- `ui/pages/model_profile_page.py`: 모델 프로필 CRUD UI (Provider → 모델 선택 → 파라미터 설정)
- `ui/pages/chat_profile_page.py`: 채팅 프로필 CRUD UI (ModelProfile + AI Persona + Lorebook/Worldbook + system_base)

### 변경됨 (MVP Hardening)

- `chat_page.py`: Signal 브리지로 전면 교체 (worker 스레드에서 UI 직접 접근 제거)
- `provider_page.py`: asyncio.get_event_loop() → AsyncSignalBridge worker 스레드로 교체
- `chat_service.py`: run_stream()/stop_stream() 삭제 (AsyncSignalBridge가 대체)
- `.gitignore`: chitchat.spec repo 포함으로 변경
- `BUILD_GUIDE.md`: v0.1.0b0은 create_all 사용, Alembic은 v0.2 이후로 명확화
- `app.py`: model_profiles/chat_profiles placeholder → 실제 페이지로 교체
- `async_bridge.py`: `task_finished` Signal + busy guard 추가 (공용 패턴 보강)
- `README.md`: v0.1.0b0 베타 DB 경고문 5개 언어 추가
- `tests/test_first_run_smoke.py`: 첨 완주 루트 9단계 E2E smoke 테스트 (5개)

### 변경됨

- `spec.md`: Python 런타임 핀 `3.13.13` → `3.12+` (권장 3.13, 최소 3.12) 완화
- `pyproject.toml`: build-backend를 `setuptools.build_meta`로 변경, Python 3.12+ 대응
- `BUILD_GUIDE.md`: Python 버전 요구사항 `3.12+`로 동기화

- `spec.md` v0.1 BETA: 마스터 스펙 문서 초안 작성
  - 프로젝트 정체성, 목표, 성공 기준 10개, 비목표 9개 정의
  - 동결 결정 14건 기록
  - 6계층 아키텍처 정의 (UI, ViewModel, Service, Domain, Provider, Persistence)
  - Typed Contract 전체 정의 (Provider, Profile, Prompt, Chat)
  - DB 스키마 12개 테이블 정의
  - Provider별 Capability Mapping 규칙 정의 (Gemini, OpenRouter, LM Studio)
  - 프롬프트 조립 상수, 기본 순서, 로어북 매칭 알고리즘, 컨텍스트 예산 알고리즘 정의
  - 상태 머신 정의 (Provider Setup, Chat Session)
  - 실데이터 샘플 8종 정의
  - UI CTA/검증 계약 정의
  - 보안/IP 경계 정의
  - 6단계 구현 로드맵 정의
  - 잔여 리스크 7건 식별

- `designs.md` v0.1 BETA: UI/UX 디자인 문서 작성
  - Clean Neo-Brutal Desktop Workspace 디자인 방향 결정
  - 정보 아키텍처 정의 (9개 네비게이션 항목)
  - 색상 시스템 16개 토큰 정의
  - 타이포그래피 스케일 8단계 정의
  - 레이아웃 그리드 및 반응형 브레이크포인트 4단계 정의
  - 핵심 컴포넌트 11종 규격 정의
  - 9개 페이지 와이어프레임(ASCII) 정의
  - 인터랙션/모션 규칙 정의
  - 접근성 기준 정의
  - PySide6 위젯 매핑표 정의
  - 열린 질문 5건 기록

- `implementation_summary.md` v0.1 BETA: 구현 요약 문서 작성
  - 전체 런타임 흐름 정의
  - 시스템 분해표 9개 시스템 정의
  - 경계 계약 4종 정의
  - 파일 책임표 전체 정의 (8개 디렉토리, 30+ 파일)
  - 알고리즘 메모 4종 (토큰 추정, 로어북 매칭, 컨텍스트 예산, ID 생성)
  - 동결 공식 11개 요약
  - MVP 최소 범위 정의
  - 6단계 구현 순서 정의
  - 유지보수 규칙 5건 정의

- `DESIGN_DECISIONS.md` v0.1 BETA: 핵심 결정 문서 작성
  - DD-01 ~ DD-10: 10건의 아키텍처 결정 기록
  - UI 런타임, 저장소, API Key, Provider Adapter, 프롬프트 조립, 스트리밍, 로어북, 디자인 시스템, asyncio 통합, i18n

- `BUILD_GUIDE.md` v0.1 BETA: 빌드 가이드 작성
  - 사전 준비, 안전한 스캐폴딩, 의존성 설치, 엔트리 파일 연결
  - Alembic 설정, 첫 실행 절차, 개발 명령어
  - PyInstaller 패키징, 배포 전 체크리스트, 흔한 실패 해결

- `audit_roadmap.md` v0.1 BETA: 구현 감사 로드맵 작성
  - 4종 감사 구조 정의 (정합성, 위험요소, 아키텍처, 로드맵)
  - P0~P6 총 7단계 Phase 정의
  - Phase별 구현 항목 56개 Task 정의
  - Phase별 테스트 및 검증 포인트 정의
  - 체크포인트 정책 정의
  - 핵심 리스크 7건 식별

- `CHANGELOG.md` v0.1 BETA: 변경 이력 문서 생성
