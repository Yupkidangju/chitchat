# LESSONS_LEARNED.md

## 문서 메타

- 프로젝트: chitchat v0.1.0b0
- 작성일: 2026-04-29
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
