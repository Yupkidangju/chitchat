# DESIGN_DECISIONS.md

## 문서 메타

- 문서 버전: `v0.1 BETA`
- 상위 문서: `spec.md v0.1 BETA`
- 목적: 프로젝트의 핵심 결정과 그 이유, 기각한 대안을 기록하여 동일한 논쟁이 반복되는 것을 방지한다.

---

## DD-01: UI 런타임 선택

### 배경

Python 크로스플랫폼 데스크톱 앱의 UI 프레임워크를 결정해야 한다. 후보는 PySide6, PyQt6, Tkinter, Dear PyGui, Flet이다.

### 결정

**PySide6 / Qt Widgets**를 사용한다.

### 대안과 기각 사유

| 대안 | 기각 사유 |
|---|---|
| PyQt6 | GPL/상업 이중 라이선스. PySide6는 LGPL로 더 자유로움 |
| Tkinter | 네오-브루탈리즘 수준의 커스텀 스타일링이 어려움. 위젯 수가 적음 |
| Dear PyGui | 성숙도 낮음. 폼 기반 CRUD 화면에 부적합 |
| Flet | Flutter 래퍼로 추가 빌드 의존성 증가. Python 생태계 네이티브가 아님 |

### 결과

- Qt Widgets 기반 CRUD 화면 구조 채택
- QSplitter, QStackedWidget, QListView/QTableView 활용
- 글로벌 Qt 스타일시트 기반 테마 적용
- PyInstaller로 단일 폴더 패키징

---

## DD-02: 저장소 선택

### 배경

프로필, 세션, 메시지 등 구조화된 데이터를 로컬에 저장해야 한다.

### 결정

**SQLite + SQLAlchemy 2.0 ORM**을 사용한다. 마이그레이션은 **Alembic**으로 관리한다.

### 대안과 기각 사유

| 대안 | 기각 사유 |
|---|---|
| JSON 파일 | 관계형 조회(join, filter) 불가, 동시 쓰기 안전성 없음 |
| TinyDB | 인덱싱 미약, 대량 메시지 저장 성능 부족 |
| PostgreSQL | 로컬 앱에 외부 DB 서버 의존은 과잉 |
| Peewee | ORM 기능 제한적, 마이그레이션 도구 분리 필요 |

### 결과

- `chitchat.sqlite3` 단일 파일 저장
- SQLAlchemy ORM 모델과 Pydantic 도메인 모델 분리
- Alembic으로 스키마 버전 관리
- JSON 필드(`settings_json`, `prompt_order_json` 등)는 TEXT 컬럼에 저장

---

## DD-03: API Key 저장 방식

### 배경

Gemini, OpenRouter API Key를 안전하게 저장해야 한다. SQLite 평문 저장은 SC-02 성공 기준 위반이다.

### 결정

**OS keyring**을 사용하고, DB에는 `secret_ref` 문자열만 저장한다.

### 대안과 기각 사유

| 대안 | 기각 사유 |
|---|---|
| SQLite 암호화 (SQLCipher) | 추가 바이너리 의존성, 마스터 키 관리 문제 추가 |
| .env 파일 | 평문 파일, 실수로 Git에 올라갈 위험 |
| 별도 암호화 JSON | 키 파생 함수, 암호 관리 UX 추가 |
| 환경변수만 | 사용자가 매번 설정해야 함, UX 악화 |

### 결과

- `keyring` 라이브러리로 OS 비밀 저장소 접근
- Service name: `chitchat:{provider_profile_id}`
- Username: provider kind (`gemini`, `openrouter`)
- LM Studio는 secret 불필요 (`secret_ref = null`)
- Keyring 백엔드 미사용 시 Secret 패널에 에러 표시

---

## DD-04: Provider Adapter 아키텍처

### 배경

3종 Provider(Gemini, OpenRouter, LM Studio)를 통일된 인터페이스로 사용해야 한다.

### 결정

**`ChatProvider` Protocol**을 정의하고 각 Provider별 어댑터를 구현한다.

### 대안과 기각 사유

| 대안 | 기각 사유 |
|---|---|
| 단일 OpenAI-compatible 클라이언트 | Gemini는 OpenAI-compatible가 아님 (google-genai 전용) |
| LangChain 추상화 | 과도한 의존성, MVP에 불필요한 체인 개념 |
| LiteLLM | 추가 프록시 레이어, 디버깅 어려움 |
| 직접 httpx만 사용 | 코드 중복 증가, Provider 추가 시 수정 범위 확대 |

### 결과

- `ChatProvider` Protocol: `validate_connection`, `list_models`, `get_model_capability`, `stream_chat`
- `ProviderRegistry`: provider_kind → adapter 인스턴스 매핑
- Gemini: `google-genai` SDK 사용
- OpenRouter/LM Studio: `httpx` 사용
- `ModelCapability`로 Provider별 raw 응답 정규화

---

## DD-05: 프롬프트 조립 방식

### 배경

system base, AI 페르소나, 세계관, 로어북, 사용자 페르소나, 채팅 히스토리, 현재 메시지를 조합해 최종 프롬프트를 생성해야 한다.

### 결정

**`PromptOrderItem` 목록**에 따라 블록 순서를 사용자가 정의하고, `prompt_assembler.py`가 순서대로 조합한다.

### 대안과 기각 사유

| 대안 | 기각 사유 |
|---|---|
| 고정 순서 | 사용자 커스터마이징 불가, 프롬프트 실험 어려움 |
| 템플릿 문자열 (Jinja2) | 런타임 템플릿 파싱 오버헤드, 블록 단위 토큰 추정 어려움 |
| 그래프 기반 파이프라인 | MVP에 과도한 복잡도 |

### 결과

- 7종 `PromptBlockKind`: `system_base`, `ai_persona`, `worldbook`, `lorebook_matches`, `user_persona`, `chat_history`, `current_user_message`
- `system_base`, `current_user_message`는 비활성화/삭제 불가
- `chat_history`는 비활성화 가능, 삭제 불가
- 블록별 `token_estimate` 계산
- Inspector에서 조합 결과 실시간 검증

---

## DD-06: 스트리밍 실행 모델

### 배경

스트리밍 응답을 비동기로 수신하면서 UI를 업데이트해야 한다.

### 결정

**asyncio + Qt Signal 브리지**를 사용한다. Provider adapter가 `AsyncIterator[ChatStreamChunk]`를 반환하고, ChatService가 asyncio Task로 소비하며, Qt Signal로 UI에 chunk를 전달한다.

### 대안과 기각 사유

| 대안 | 기각 사유 |
|---|---|
| QThread + httpx sync | 스트리밍 취소(Stop)가 즉각적이지 않음, 리소스 낭비 |
| callback 기반 | 에러 핸들링 복잡, 타입 안전성 저하 |
| websocket only | OpenRouter/Gemini는 websocket 미지원, SSE 기반 |

### 결과

- `qasync` 또는 수동 이벤트 루프 통합으로 asyncio ↔ Qt 브리지
- `ChatService.start_stream()` → asyncio Task 생성
- `ChatService.stop_stream()` → Task cancel + 세션 상태 `stopped`
- chunk마다 Qt Signal emit → ChatPage에서 메시지 뷰 업데이트
- 에러 시 세션 상태 `failed`, 사용자 메시지 보존

---

## DD-07: 로어북 매칭 전략

### 배경

대화 컨텍스트에서 관련 로어 엔트리를 자동으로 찾아 삽입해야 한다.

### 결정

**키워드 기반 문자열 매칭**을 사용한다. 벡터 임베딩이나 의미 검색은 MVP 범위가 아니다.

### 대안과 기각 사유

| 대안 | 기각 사유 |
|---|---|
| 벡터 임베딩 (FAISS/ChromaDB) | 임베딩 모델 의존, 로컬 리소스 소비 |
| LLM 기반 동적 선택 | 추가 API 호출 비용, 응답 지연 |
| 정규식 매칭 | activation_key에 정규식을 쓰면 사용자 학습 비용 증가 |

### 결과

- casefold 정규화로 대소문자 무시
- 최근 8개 메시지 범위 스캔
- 우선순위 정렬, 최대 12개, 최대 3000 토큰
- MVP 이후 벡터 검색 확장 가능

---

## DD-08: 디자인 시스템

### 배경

UI의 시각적 일관성과 구현 효율을 위해 디자인 시스템을 결정해야 한다.

### 결정

**Clean Neo-Brutal Desktop Workspace** 스타일을 채택하고, `ui/theme.py`에 디자인 토큰을 정의하여 글로벌 Qt 스타일시트로 적용한다.

### 대안과 기각 사유

| 대안 | 기각 사유 |
|---|---|
| Material Design | Qt에서 완전한 Material 구현이 어려움, 커스텀 위젯 필요 |
| Flat minimalism | 네오-브루탈리즘의 명확한 경계선이 CRUD 화면에 더 적합 |
| Dark mode 우선 | v0.1 BETA에서 QA 범위 증가, 단일 라이트 테마로 고정 |

### 결과

- `2px`~`3px` 검은 외곽선, 하드 오프셋 그림자
- 디자인 토큰: `ui/theme.py` 단일 파일
- 위젯별 object name: `PrimaryButton`, `DangerButton`, `InspectorPanel` 등
- designs.md의 색상/타이포/간격 토큰을 코드에 1:1 매핑

---

## DD-09: asyncio ↔ Qt 이벤트 루프 통합

### 배경

PySide6 이벤트 루프와 Python asyncio 이벤트 루프를 동시에 실행해야 한다.

### 결정

**`qasync` 라이브러리**를 우선 검토하되, 안정성 문제 발생 시 **별도 스레드에서 asyncio 루프를 실행하고 `asyncio.run_coroutine_threadsafe()`로 요청을 전달**하는 대안으로 전환한다.

### 대안과 기각 사유

| 대안 | 기각 사유 |
|---|---|
| QThread에서 동기 httpx | 스트리밍 취소가 즉각적이지 않음 |
| 별도 프로세스 (multiprocessing) | IPC 복잡도 과잉, 프로세스 간 상태 공유 어려움 |

### 결과

- **최종 선택: `threading.Thread` + `asyncio.new_event_loop()` + Qt Signal 브리지** (v0.1.0b0)
- `qasync`는 PySide6 호환성 문제로 채택하지 않음
- `ui/async_bridge.py`의 `AsyncSignalBridge(QObject)`가 브리지 역할 수행:
  - worker 스레드에서 asyncio 루프 생성 → 코루틴 실행
  - 결과를 `Signal.emit()`으로 메인 Qt 스레드에 전달
  - `cancel_stream()`은 `loop.call_soon_threadsafe(task.cancel)`로 thread-safe 취소
- Service 계층(`ChatService`)은 순수 `async def`만 노출, threading 로직은 UI 브리지에 격리

---

## DD-10: i18n 전략

### 배경

D3D Protocol에 따라 다국어(한/영/일/중(번체)/중(간체)) 지원이 필요하다.

### 결정

**Qt 내장 `QTranslator` + `.ts` 파일 기반 i18n**을 사용한다.

### 대안과 기각 사유

| 대안 | 기각 사유 |
|---|---|
| gettext | Qt 위젯과의 통합이 자연스럽지 않음 |
| 자체 JSON 딕셔너리 | 번역 도구 지원 없음, 관리 복잡도 |
| babel | 웹 프레임워크 중심, PySide6와 무관 |

### 결과

- `tr()` 매크로 사용
- `.ts` 파일을 `lupdate`로 추출, `lrelease`로 컴파일
- MVP에서는 한국어/영어 기본 제공, 나머지 언어는 `.ts` 파일 제공 후 커뮤니티 번역 수용
