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

- 7종 `PromptBlockKind`: `system_base`, `ai_persona`, `worldbook`, `lorebook`, `user_persona`, `chat_history`, `current_input`
- `system_base`, `current_input`는 비활성화/삭제 불가
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

---

## DD-11: ViewModel 계층 — 전면 도입 기각, chat.js 선택적 분리

### 배경

spec.md §5 아키텍처에서 `ui → viewmodels → services` 의존 규칙을 정의했으나, v0.1.0b0에서 PySide6 ViewModel 계층을 의도적으로 생략했다. 이후 DD-15에서 FastAPI+SPA로 전환하면서, Qt ViewModel의 의미 자체가 소멸했다. v1.0.0에서 웹 SPA 맥락에 맞게 재평가했다.

### 결정

**전면 ViewModel 계층 도입을 기각한다.** 9개 페이지 중 8개가 200줄 이하로 복잡도가 ViewModel 정당화 수준 미달이다. 대신 가장 큰 `chat.js`(579줄)만 3개 모듈로 분리한다:

- `chat.js` (101줄): 레이아웃 렌더링 + 이벤트 바인딩 오케스트레이터
- `chat_session.js` (188줄): 세션 CRUD + 생성 모달 + 메시지 렌더링
- `chat_composer.js` (313줄): WebSocket 연결 + 메시지 전송 + 동적 상태 + Inspector

### 대안과 기각 사유

| 대안 | 기각 사유 |
|---|---|
| 9개 파일 전체에 ViewModel 패턴 적용 | 8개가 200줄 이하, 보일러플레이트만 증가 |
| React/Vue 도입 후 컴포넌트 + 상태 관리 | 기존 1,963 LoC 재작성 비용 대비 실익 없음. DD-15에서 Vanilla JS 동결 |
| 아무것도 안 함 | chat.js 579줄은 세션/스트리밍/Inspector 혼재로 유지보수 곤란 |

### 결과

- `frontend/js/pages/` 내 chat 관련 파일이 3개로 분리됨
- `index.html`에서 `chat_session.js` → `chat_composer.js` → `chat.js` 순서로 로딩
- 전역 상태 `currentSessionId`는 `chat.js`에서 선언, 하위 모듈에서 참조

---

## DD-12: Vibe Fill Phase 1 (Persona) 필드 확장

### 배경

AI 페르소나 자동 생성 시 단순 요약이 아닌 롤플레이에 특화된 구체적인 필드가 필요하다. 기존 6개 필드만으로는 AI가 개연성 있는 캐릭터를 만들기 부족했다.

### 결정

AI Persona 모델을 **14개 필드(나이, 성별, 외모, 배경, 인간관계, 특기 등 추가)**로 확장하고, 생성 시 JSON 구조화된 출력을 강제한다.

### 대안과 기각 사유

| 대안 | 기각 사유 |
|---|---|
| 단일 Markdown 텍스트로 생성 | 프롬프트 조립 시 특정 필드만 강조하거나 제외하기 어려움. 파싱 복잡 |
| 기존 6개 필드 유지 | 캐릭터의 외모, 배경, 관계 등 핵심 롤플레이 요소가 누락됨 |

### 결과

- `AIPersonaData`에 8개 필드 추가.
- `VIBE_FILL_SYSTEM_PROMPT`는 14개 키를 가진 JSON 객체 반환 강제.

---

## DD-13: Vibe Fill Phase 2 (Lorebook) Append 저장 방식

### 배경

로어북 자동 생성 시 기존에 사용자가 만든 엔트리를 덮어쓰면 데이터 유실 위험이 크다.

### 결정

Vibe Fill 결과는 즉시 저장되지 않고 UI에 **미리보기 체크리스트**로 표시되며, 사용자가 선택한 항목만 기존 로어북에 **Append(추가)**된다. 중복된 키/제목은 덮어쓰지 않고 무시하거나 대체한다.

### 대안과 기각 사유

| 대안 | 기각 사유 |
|---|---|
| 전체 덮어쓰기 (Overwrite) | 기존 수동 작성 엔트리 영구 손실 위험 |
| 임시 로어북(Draft) 분리 저장 | 로어북 관리 파편화 발생. 매번 로어북을 새로 만들어야 함 |

### 결과

- `LorebookPage`에 생성 결과 미리보기 목록 추가.
- 저장 버튼 클릭 시 선택 항목만 DB에 Insert.

---

## DD-14: Vibe Fill Phase 3 (Worldbook) 청크 분할 알고리즘

### 배경

세계관(Worldbook)은 방대한 정보(역사, 지리, 종족 등 10개 카테고리)를 요구한다. 한 번의 LLM 호출로 10개 카테고리를 모두 생성하면 출력 토큰 제한(Max Tokens)에 걸려 응답이 잘릴 위험이 매우 높다.

### 결정

10개 카테고리를 **2~3개씩 4개의 청크(그룹)로 분할하여 LLM을 4번 연쇄 호출**한다. 일관성 유지를 위해 이전 청크에서 생성된 엔트리 제목 목록을 다음 청크의 시스템 프롬프트(컨텍스트)에 주입한다.

### 대안과 기각 사유

| 대안 | 기각 사유 |
|---|---|
| 모델의 Context Window를 믿고 한 번에 호출 | 오픈소스 모델(LM Studio)이나 작은 모델에서 출력 토큰 오버플로 빈발 |
| 이전 청크의 내용(Content) 전체를 다음 청크에 전달 | 입력 토큰 비용 기하급수적 증가. (O(N^2)) |
| 병렬(Parallel) 호출 | 카테고리 간 논리적 연결(예: 역사와 지리의 연관성)이 끊어짐 |

### 결과

- `vibe_fill_service.py`에서 비동기 순차 연쇄 호출 구현.
- 이전 결과는 제목(Title)만 추출하여 토큰 절약.
- 부분 실패 내성 확보 (3번째 청크에서 실패해도 1,2번째 결과는 유지).
- UI에 QProgressBar로 N/4 진행률 실시간 피드백 표시.

### 대안과 기각 사유

| 대안 | 기각 사유 |
|---|---|
| 모든 페이지에 ViewModel 즉시 구현 | 대부분의 페이지가 단순 CRUD이므로 Service 직접 호출로 충분, ViewModel이 Service를 단순 포워딩하는 보일러플레이트가 됨 |
| MVVM 프레임워크 도입 (Qt QML 등) | PySide6 Widgets 기반이므로 QML 전환은 과도한 변경 |

### 결과

- `ui/viewmodels/__init__.py`만 존재, 실제 ViewModel 클래스 없음
- UI 페이지는 `__init__`에서 Service를 직접 주입받아 호출
- `AsyncSignalBridge`가 비동기 결과의 thread-safe 전달을 담당하여 ViewModel의 상태 관리 역할 일부를 대체
- 향후 `chat_vm.py`, `profile_vm.py` 등은 폼 검증 복잡도가 증가할 때 도입

---

## DD-12: 설정 페이지 범위

### 배경

사이드바에 "⚡ 설정" 항목이 존재하지만, MVP v0.1 범위에서 구체적인 설정 항목이 정의되지 않았다.

### 결정

**MVP v0.1에서 설정 페이지는 앱 데이터 경로, 로그 레벨 표시용 플레이스홀더로 유지한다.** v0.2에서 아래 항목을 구현한다:
1. 앱 데이터 경로 표시 및 폴더 열기
2. 로그 레벨 변경
3. 테마 전환 (라이트/다크)
4. 언어 설정
5. DB 백업/복원
6. 캐시 초기화

### 결과

- `settings.js`에서 4개 섹션(언어, 표시, 일반, 데이터 관리)으로 확장 완료 (v1.0.0)
- `UserPreferences`에 `theme`, `font_size`, `streaming_enabled`, `default_provider_id` 필드 추가
- `POST /settings/reset` 엔드포인트로 설정 초기화 지원
- 폰트 크기 변경 시 CSS 변수 `--font-size-base` 즉시 적용

---

## DD-13: 모델 파라미터 동적 가시성 전략

### 배경

spec.md §11.1에 따라 모델이 지원하지 않는 파라미터는 UI에서 숨겨야 한다. 현재 구현에서는 모든 파라미터가 항상 표시된다.

### 결정

**ModelProfilePage에서 선택된 모델의 `ModelCapability.supported_parameters`를 조회하여, 해당 파라미터를 지원하지 않는 스핀박스/입력 필드를 `setVisible(False)`로 동적 숨김 처리한다.**

### 구현 계획

1. 모델 콤보 변경 시 `ProviderService.get_cached_models()`에서 해당 모델의 `ModelCapability`를 조회
2. `supported_parameters` 집합에 포함되지 않은 파라미터 행을 `QFormLayout`에서 `setRowVisible(row, False)` 처리
3. `max_output_tokens`는 spec 규정에 따라 항상 표시
4. Save 시 숨겨진(미지원) 파라미터에 non-null 값이 있으면 경고 표시

### 결과

- `model_profile_page.py`에서 `_on_model_changed()` 슬롯 추가
- `model_cache` DB에 `supported_parameters_json` 필드 참조
- LM Studio 등 capability 정보가 불완전한 경우 모든 파라미터를 표시하되 경고 표시

---

## DD-15: v1.0.0 풀스택 아키텍처 전환

### 배경

PySide6 데스크톱 앱의 크로스플랫폼 빌드 관리, Qt 이벤트 루프와 asyncio 통합의 복잡도, 그리고 모바일/웹 접근성 부재가 개발 병목이 되었다.

### 결정

**PySide6 UI를 완전히 제거하고, FastAPI 백엔드 + 순수 HTML/CSS/JS SPA 프론트엔드로 전환한다.**

### 대안과 기각 사유

| 대안 | 기각 사유 |
|---|---|
| PySide6 유지 + Tauri 래핑 | Rust 빌드 체인 추가, 복잡도만 증가 |
| Flet (Flutter 래퍼) | 추가 런타임 의존, Python 네이티브가 아님 |
| Electron + Python 백엔드 | Node.js 의존 추가, 메모리 사용량 과다 |
| Gradio/Streamlit | 커스텀 UI 제어 불가, 프로덕션 품질 부족 |

### 결과

- FastAPI (`uvicorn`) 서버가 REST API + WebSocket + 정적 파일을 서빙
- 프론트엔드는 `frontend/` 디렉토리에 순수 HTML/CSS/JS SPA로 구현
- `qasync`, `AsyncSignalBridge` 등 Qt-asyncio 브리지 코드 제거
- DD-06, DD-09의 결정이 대체됨: WebSocket이 스트리밍 통신을 직접 처리

---

## DD-16: VibeSmith 9섹션 동적 캐릭터 시스템

### 배경

기존 14개 필드 AI 페르소나는 정적이며, 대화 과정에서 관계 변화, 기억 형성, 감정 변동이 반영되지 않았다.

### 결정

**VibeSmith 9섹션 PersonaCard + DynamicCharacterState 분리 아키텍처를 채택한다.** 원본 캐릭터는 MD 문서로 보존하고, 동적 상태는 ZSTD 압축 후 SQLite에 저장한다.

### 대안과 기각 사유

| 대안 | 기각 사유 |
|---|---|
| 기존 14개 필드 확장 | 동적 상태(관계, 기억)가 정적 스키마에 맞지 않음 |
| 전체를 JSON 파일로 관리 | 동시 접근, 트랜잭션, 인덱싱 불가 |
| Redis/외부 캐시 | 로컬 앱에 외부 서비스 의존 과잉 |

### 결과

- `PersonaCardRow`: 9섹션 메타데이터 + `persona_json` (전체 JSON)
- `DynamicStateRow`: ZSTD 압축 바이너리 (`state_blob`), 세션별 버전 관리
- `MemoryRow`: 기억 엔트리 (트리거 타입, 감정 임팩트)
- `DynamicStateEngine`: 매 AI 응답 후 상태 갱신 → 프롬프트에 동적 주입
- 관계 상태 변수 9개: trust, familiarity, emotional_reliance, conflict_level 등

---

## DD-17: Alembic 마이그레이션 SQLite 데드락 해결

### 배경

`run_migrations(engine)` 함수가 `inspect(engine)`으로 테이블 정보를 수집한 후 `command.upgrade`를 호출하는 과정에서, SQLAlchemy의 connection pool이 잠금을 유지하여 Alembic의 새 connection이 무한 대기하는 SQLite 데드락이 발생했다.

추가로, Alembic `env.py`의 `fileConfig(config.config_file_name)`이 Python `logging`의 root logger를 재설정하면서 uvicorn의 내부 로거를 파괴하여 서버 시작 자체가 블로킹되는 문제가 있었다.

### 결정

1. **`run_migrations`의 시그니처를 `(engine: Engine)` → `(db_path: Path)`로 변경** — SQLAlchemy pool과 완전히 독립된 `sqlite3` stdlib으로 테이블 정보를 수집한다.
2. **`env.py`의 `fileConfig` 호출을 조건부로 변경** — 환경변수 `CHITCHAT_PROGRAMMATIC_ALEMBIC`이 설정되면 `fileConfig`를 건너뛴다.
3. **마이그레이션을 engine 생성 전에 실행** — `run_migrations(db_path)` → `create_db_engine(db_path)` → `create_session_factory(engine)` 순서.

### 대안과 기각 사유

| 대안 | 기각 사유 |
|---|---|
| `engine.dispose()` 후 upgrade | dispose 후에도 WAL shm 파일이 잠금을 유지할 수 있음 |
| `with engine.connect()` 후 upgrade | context manager 종료 후에도 pool에 connection이 반환되어 WAL 잠금 유지 |
| Alembic을 별도 프로세스로 실행 | IPC 복잡도, 에러 핸들링 어려움 |

### 결과

- `migrations.py`: `sqlite3.connect()` → PRAGMA/inspect → `conn.close()` → Alembic upgrade
- `env.py`: `os.environ.get("CHITCHAT_PROGRAMMATIC_ALEMBIC")` 체크로 fileConfig 건너뛰기
- `app.py`: `run_migrations(db_path)` → `create_db_engine(db_path)` → `create_session_factory(engine)`

## DD-18: DynamicStateEngine ↔ ChatService 비차단 통합

### 배경

VibeSmith 9섹션 캐릭터 시스템은 대화가 진행되면서 관계/기억/감정이 동적으로 변화해야 한다. 이 변화를 매 턴마다 반영하되, 갱신 실패가 채팅 흐름을 차단해서는 안 된다.

### 결정

1. **DynamicStateEngine을 ChatService에 optional 주입** — `__init__`의 마지막 매개변수로 `DynamicStateEngine | None`을 받는다. None이면 갱신을 건너뛴다.
2. **스트리밍 완료 → `_update_dynamic_state()` 비차단 호출** — 어시스턴트 메시지 저장 직후, `streaming → active` 전이 이전에 호출한다. 전체를 `try/except`로 감싸서 실패 시 `logger.exception`만 남긴다.
3. **키워드 기반 1차 분석 → 향후 AI 판단으로 교체** — 현재는 `_analyze_and_update()`에서 7개 한국어 키워드를 매칭하여 기억 트리거와 관계 변수를 조정한다. 향후 별도 AI 분석 프롬프트로 교체 예정.
4. **ZSTD 압축 blob으로 SQLite 영속화** — `DynamicStateRepository.upsert()`로 `dynamic_states` 테이블에 저장한다.

### 대안과 기각 사유

| 대안 | 기각 사유 |
|---|---|
| 별도 background task로 분리 | 턴 동기화 보장 어려움, 상태 경합 위험 |
| WebSocket 메시지에 상태 변경 포함 | 프로토콜 복잡도 증가, 클라이언트가 상태를 관리해야 함 |
| 매 N턴마다만 갱신 | 중요한 순간을 놓칠 수 있음 |

### 결과

- `chat_service.py`: `start_stream()` 내부에서 `await self._update_dynamic_state()` 호출
- `api/routes/chat.py`: `GET /sessions/{id}/dynamic-state`로 ZSTD 해동 후 JSON 조회
- `frontend/js/pages/chat.js`: 스트리밍 `done` 시 `refreshDynamicState()` 자동 호출
