# CHANGELOG.md

이 프로젝트의 모든 주요 변경사항을 기록한다.

형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/)를 따르며,
버전 관리는 [Semantic Versioning](https://semver.org/lang/ko/)을 준수한다.

---

## [미출시]

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
