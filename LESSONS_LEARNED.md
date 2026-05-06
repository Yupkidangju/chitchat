# LESSONS_LEARNED.md

## 문서 메타

- 프로젝트: chitchat v1.0.0
- 작성일: 2026-04-29 (v0.1.0b0) → 갱신: 2026-05-06 (v1.0.0)
- 목적: 프로젝트 진행 중 축적된 교훈을 기록하여 향후 유사 프로젝트에서 동일 실수를 방지한다.

---

## 1. Protocol ↔ 구현 시그니처 일치 의무

### 교훈

`ChatProvider` Protocol을 정의할 때 `api_key` 파라미터를 누락하고, 실제 adapter에서만 추가했다. Python duck typing으로 런타임에는 동작했으나, mypy strict에서 에러가 발생하며 설계 의도가 모호해졌다.

### 대책

- Protocol 정의 시 구현체의 **모든 파라미터**를 포함한다 (Optional이더라도).
- Protocol 변경 시 모든 구현체와 호출부를 동시에 갱신한다.

---

## 2. Pydantic Required 필드 검증

### 교훈

`ChatCompletionRequest`의 `provider_profile_id`가 required 필드로 정의되었으나, `chat_service.py`에서 생성 시 누락했다. 테스트에서 이 경로가 호출되지 않아 발견되지 않았다.

### 대책

- Pydantic 모델의 required 필드는 생성부에서 반드시 전달하는지 테스트한다.
- 스트리밍 E2E 통합 테스트를 mock 기반으로라도 작성하여 `ChatCompletionRequest` 생성까지 검증한다.

---

## 3. asyncio ↔ Qt 이벤트 루프 통합

### 교훈

`start_stream()`을 `async def`로 구현했으나, Qt 이벤트 루프에서 호출할 브리지 코드가 없어 채팅 루프가 완성되지 않았다. `_on_send()`에서 메시지 저장만 수행하고 AI 응답 호출을 누락했다.

### 대책

- Threading 기반 브리지: `threading.Thread` + `asyncio.new_event_loop()` 패턴으로 Qt 이벤트 루프를 차단하지 않으면서 async 코드를 실행한다.
- 콜백은 UI 스레드에서 실행되는 것이 보장되지 않으므로, Qt Signal/Slot 또는 `QMetaObject.invokeMethod`로 UI 갱신을 래핑해야 한다 (향후 안정화 과제).

---

## 4. content 동일성 기반 매칭의 위험

### 교훈

`prompt_assembler.py`에서 히스토리 메시지의 role을 `content == block.content`로 매칭했다. 동일 내용 메시지가 여러 개일 때 첫 번째만 매칭되어 잘못된 role이 할당될 수 있었다.

### 대책

- 인덱스 기반 매칭으로 변경. 히스토리 블록은 원본 메시지의 순서적 부분 집합이므로, 인덱스를 진행시키며 매칭한다.

---

## 5. 서비스 캡슐화 위반 경고

### 교훈

`ChatPage`에서 `self._svc._repos`로 내부 Repository에 직접 접근했다. 서비스 계층의 존재 의의를 훼손하는 패턴이다.

### 대책

- UI 계층은 Service의 public 메서드만 호출한다.
- Service에 필요한 도우미 메서드를 추가하여 캡슐화를 유지한다.

---

## 6. 문서 ↔ 코드 동기화 시점

### 교훈

Phase 단위로 문서를 동기화했으나, Phase 내부에서 구현 세부사항이 변경되었을 때 (예: `PromptBlockKind` Literal 값 변경) 문서가 즉시 갱신되지 않았다.

### 대책

- **코드 변경 → 문서 동기화** 순서를 Phase 완료 시점이 아닌 **각 파일 변경 시점**에 수행한다.
- `audit_roadmap.md`의 체크포인트를 활용하여 Phase 내 중간 검증을 수행한다.

---

## 7. 테스트 커버리지 갭

### 교훈

P5 스트리밍 관련 코드(`start_stream`, `run_stream`, ChatPage `_on_send`)는 단위 테스트만 존재하고 통합 테스트가 없었다. 이로 인해 `ChatCompletionRequest` 생성 시 필수 필드 누락, Protocol 시그니처 불일치 등이 발견되지 않았다.

### 대책

- mock Provider를 사용한 스트리밍 통합 테스트를 작성한다.
- 최소한 `ChatCompletionRequest` 생성 → Provider 호출 경로까지 커버하는 E2E 테스트를 추가한다.

---

## 8. PySide6 → FastAPI+SPA 아키텍처 전환

### 교훈

PySide6 기반 데스크톱 앱을 FastAPI+순수 HTML/CSS/JS SPA로 전환했다. Qt 이벤트 루프와 asyncio 통합의 복잡성, 크로스 플랫폼 빌드 파이프라인 관리 비용이 웹 기반 아키텍처의 단순함 대비 과도했다.

### 대책

- 단일 사용자 로컬 앱은 **경량 웹 서버 + 브라우저 SPA**가 데스크톱 프레임워크보다 개발/배포/디버깅 비용이 낮다.
- asyncio 기반 서비스 레이어를 유지하면서, 프론트엔드를 완전히 분리하여 양쪽의 복잡성을 격리한다.
- Qt Signal/Slot 대신 WebSocket 스트리밍으로 실시간 통신을 구현하면 테스트가 훨씬 쉽다.

---

## 9. SQLite 마이그레이션 데드락 (DD-17)

### 교훈

SQLAlchemy `create_engine()` 후 Alembic `run_migrations()`를 실행하면, SQLite의 단일 쓰기 잠금으로 인해 데드락이 발생했다. 또한 uvicorn 내에서 Alembic의 `fileConfig()`가 로거를 파괴하는 부수효과도 발견했다.

### 대책

- `run_migrations()`를 `sqlite3` stdlib로 전환하여 SQLAlchemy pool과 완전 분리한다.
- `CHITCHAT_PROGRAMMATIC_ALEMBIC=1` 환경변수로 `fileConfig()` 호출을 조건부로 차단한다.
- 마이그레이션 완료 후에만 SQLAlchemy engine을 생성하는 순서를 강제한다.

---

## 10. 정적 파일 캐시 문제

### 교훈

FastAPI `StaticFiles`로 프론트엔드를 서빙할 때, 브라우저가 JS 파일을 캐시하여 코드 변경이 반영되지 않는 문제가 빈번히 발생했다. 특히 새 페이지 추가 후 기존 코드가 계속 실행되어 디버깅 시간을 낭비했다.

### 대책

- `<script src="...?v=N">` 캐시 버스팅 쿼리 파라미터를 사용한다.
- 개발 중에는 브라우저 DevTools의 "Disable cache" 옵션을 활성화한다.
- 향후 빌드 파이프라인 도입 시 파일 해시 기반 캐시 버스팅을 적용한다.

---

## 11. 모달 z-index 레이어링

### 교훈

모달을 `page-container` 안에 배치하면 부모의 `overflow: hidden`이나 `z-index` 스택 컨텍스트에 의해 가려질 수 있다. chat-layout의 CSS가 모달을 덮어버리는 현상이 발생했다.

### 대책

- 모달은 반드시 `document.body` 직속에 추가하고, inline `z-index: 9999`로 최상위 레이어를 보장한다.
- `position: fixed`로 뷰포트 전체를 덮는 오버레이를 사용한다.

---

## 12. 전역 유틸 함수 분리

### 교훈

`escapeHtml()` 같은 공통 유틸 함수가 `providers.js`에 정의되어 다른 페이지에서 암묵적으로 의존했다. 스크립트 로딩 순서가 바뀌면 `ReferenceError`가 발생할 수 있는 취약점이다.

### 대책

- 공통 유틸 함수는 `api.js`같은 전역 모듈에 분리하여 의존 관계를 명시적으로 만든다.
- 향후 ES Module 전환 시 `import/export`로 의존성을 명확히 관리한다.

---

## 13. 참조 무결성 검증의 필수성

### 교훈

엔티티 삭제 API가 boolean 반환만 하고, 참조 중인 다른 엔티티(ChatProfile → AIPersona, ChatSession → ChatProfile 등)의 존재를 확인하지 않았다. 이로 인해 "고아 참조(orphan reference)"가 남아 데이터 일관성이 깨질 수 있는 위험이 있었다.

### 대책

- 삭제 서비스 메서드에서 **모든 외래 키 역방향 참조**를 검사한 후 `ValueError`를 발생시킨다.
- API 라우트에서 `ValueError`를 `HTTP 409 Conflict`로 변환하여 클라이언트에 명시적 거부를 전달한다.
- 프론트엔드에서는 에러 메시지를 토스트로 표시하여 사용자가 원인을 즉시 파악할 수 있게 한다.

---

## 14. alert() 제거와 토스트 시스템 도입

### 교훈

`alert()`는 브라우저를 완전히 차단(blocking)하여 사용자 경험을 크게 저해한다. 특히 삭제 실패 시 409 에러 메시지가 `alert()`로 표시되면 UX가 매우 불편하다.

### 대책

- 전역 `showToast(message, type, duration)` 함수를 구현하여 비차단(non-blocking) 알림을 제공한다.
- 타입별 색상 구분(success/error/warning/info)으로 시각적 맥락을 전달한다.
- 에러 토스트는 5초 유지로 설정하여 사용자가 메시지를 충분히 읽을 수 있게 한다.

---

## 15. 설정 확장 시 기본값 폴백 전략

### 교훈

`UserPreferences`에 새 필드(theme, font_size, streaming_enabled, default_provider_id)를 추가할 때, 기존 `settings.json`에 해당 키가 없는 환경에서 `KeyError`가 발생했다.

### 대책

- 모든 설정 로드 시 `data.get("key", default_value)` 패턴으로 누락 키를 기본값으로 폴백한다.
- `reset()` 메서드가 확장된 필드까지 초기화하도록 보장한다.
- 새 필드 추가 시 반드시 저장/로드/리셋 테스트를 함께 작성한다.

---

## 16. 프롬프트 Inspector의 디버깅 가치

### 교훈

프롬프트 조립 결과를 사용자가 실시간으로 확인할 수 없어, AI 응답 품질 문제가 발생했을 때 원인(프롬프트 구성 오류 vs 모델 한계)을 구분하기 어려웠다.

### 대책

- 프롬프트 Inspector 패널을 우측 패널 탭으로 구현하여 블록 구성, 토큰 사용량, 로어 매칭 결과를 시각화한다.
- 전송 시 `PromptSnapshot`을 메시지에 저장하여, 과거 대화의 프롬프트 상태도 사후 분석할 수 있게 한다.
- `[🔍 프롬프트]` 버튼 → Inspector 탭 자동 전환으로 직관적 접근을 제공한다.
