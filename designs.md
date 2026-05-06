# designs.md

## 1. Overview

`chitchat`의 UI/UX 방향은 **Clean Neo-Brutal Desktop Workspace**로 고정한다. 핵심은 강한 검은 외곽선, 평면적인 카드, 명확한 단계 표시, 과장 없는 색상 대비를 사용해 Provider 설정부터 프롬프트 조립·채팅 실행·Inspector 검증까지 한 번에 이해되는 데스크톱 앱을 만드는 것이다.

이 디자인은 장식적인 네오-브루탈리즘이 아니라 구현자가 바로 만들 수 있는 **구조적 네오-브루탈리즘**이다. 모든 주요 영역은 두꺼운 선, 명확한 제목 바, 강한 CTA, 단일 선택 상태, 상태 배너, 고정된 폼 검증 규칙으로 닫는다.

핵심 화면은 다음 흐름을 따른다.

```txt
Provider 등록 → Key 저장/연결 테스트 → 모델 목록 불러오기 → ModelProfile 저장
→ UserPersona / AIPersona / Lorebook / Worldbook 작성
→ ChatProfile 조합 → PromptOrder 확인 → New Chat → Send → Prompt Inspector 검증
```

## 2. Product Context

### Product

- 제품명: `chitchat`
- 제품 유형: Python FastAPI 백엔드 + HTML/CSS/JS 웹 프론트엔드 AI 채팅 앱
- 백엔드: FastAPI + uvicorn
- 프론트엔드: 순수 HTML/CSS/JS SPA (Neo-Brutal 디자인 시스템)
- 저장소: SQLite 로컬 파일
- Secret 저장: OS keyring, DB에는 `secret_ref`만 저장
- 지원 Provider: Gemini, OpenRouter, LM Studio
- 캐릭터 시스템: VibeSmith 9섹션 동적 페르소나 + ZSTD 압축 상태 저장

### Target Users

- LLM Provider와 모델 파라미터를 직접 관리하는 고급 사용자
- 창작용 AI 채팅을 위해 페르소나, 로어북, 세계관, 프롬프트 순서를 조합하는 사용자
- 프롬프트가 어떻게 구성됐는지 실제 요청 직전에 검증하려는 사용자

### Business Goal

MVP의 목표는 사용자가 외부 기획 회의 없이 로컬 데스크톱에서 Provider 등록, 모델 설정, 프로필 조합, 프롬프트 검증, 스트리밍 채팅까지 수행하게 하는 것이다.

### Constraints

- UI는 Provider Adapter를 직접 호출하지 않는다. UI는 ViewModel과 Service만 호출한다.
- API Key는 SQLite에 노출하지 않는다.
- 모델 capability에 없는 파라미터 컨트롤은 화면에서 숨긴다.
- PromptOrder는 사용자가 재정렬할 수 있어야 한다.
- Inspector는 조합된 PromptBlock, 로어북 매칭 결과, token estimate, 잘린 history ID를 보여준다.
- RisuAI의 코드, UI, 에셋, 문구, 스키마를 복제하지 않는다.

### Assumptions

- v0.1 BETA는 단일 라이트 테마만 제공한다.
- 최소 지원 창 크기는 `1120 x 720`이다.
- 권장 창 크기는 `1440 x 900`이다.
- 960px 미만 폭에서는 탐색과 Inspector를 접는 compact desktop layout을 사용한다.
- 모바일 앱은 v0.1 BETA 타깃이 아니지만, 좁은 화면 동작은 향후 이식이 가능하도록 정의한다.

## 3. Design Principles

1. **Setup clarity before visual flair**  
   Provider 등록과 모델 capability 상태가 가장 먼저 이해되어야 한다. 장식보다 단계, 상태, CTA 조건을 우선한다.

2. **One workspace, many editors**  
   모든 설정 화면은 `목록 패널 + 편집 패널 + 상태/검증 패널` 패턴을 반복한다. 사용자가 새 화면마다 구조를 다시 학습하지 않게 한다.

3. **Visible contracts**  
   숨겨진 데이터 계약은 UI에 표시한다. 예: `secret_ref`, `supported_parameters`, `max_output_tokens`, `matched_lore_entry_ids`, `truncated_history_message_ids`.

4. **Strong boundaries, low decoration**  
   네오-브루탈리즘은 두꺼운 선과 명확한 면 분리로 구현한다. 과한 회전, 3D, 글리치, 강한 그림자는 쓰지 않는다.

5. **State over mood**  
   성공, 경고, 실패, streaming, stopped, archived 상태가 색상·문구·아이콘·버튼 활성 조건으로 동시에 드러나야 한다.

6. **Prompt trust is the product**  
   채팅 화면의 우측 Inspector는 부가 기능이 아니라 신뢰의 핵심이다. 사용자는 응답 전후에 프롬프트 조합 근거를 확인할 수 있어야 한다.

## 4. Information Architecture

### Primary Navigation

왼쪽 고정 사이드바를 사용한다.

```txt
Chat
Providers
Model Profiles
User Personas
AI Personas
Lorebooks
Worldbooks
Chat Profiles
Prompt Order
```

### Navigation Hierarchy

| Level | Area | Purpose |
|---|---|---|
| App Shell | Sidebar + Top Status Bar | 현재 화면, Provider health, DB path, global alerts 표시 |
| Primary Pages | Chat, Providers, Models, Profiles | 핵심 작업 수행 |
| Detail Panels | Editor, Inspector, Preview | 선택 항목 편집 및 검증 |
| Overlays | Confirm, Prompt Snapshot, Error Detail | 흐름을 끊지 않고 상세 확인 |

### Default Landing

앱 첫 실행 시 `Chat` 페이지를 열되, 채팅 시작 조건이 충족되지 않으면 중앙에 **Setup Checklist Empty State**를 표시한다.

체크리스트 순서:

1. Provider 저장
2. API Key 저장 또는 LM Studio endpoint 확인
3. 연결 테스트 성공
4. 모델 목록 불러오기
5. ModelProfile 저장
6. UserPersona 저장
7. AIPersona 저장
8. ChatProfile 저장
9. New Chat 생성

### Screen Inventory

| Screen | Route Key | Primary Data | Primary CTA |
|---|---|---|---|
| ChatPage | `chat` | ChatSession, ChatMessage, AssembledPrompt | Send / Stop |
| ProviderPage | `providers` | ProviderProfile, ProviderHealth, ModelCache | Test Connection / Fetch Models |
| ModelProfilePage | `model_profiles` | ModelProfile, ModelCapability | Save Profile |
| UserPersonaPage | `user_personas` | UserPersona | Save |
| AIPersonaPage | `ai_personas` | AIPersona | Save |
| LorebookPage | `lorebooks` | Lorebook, LoreEntry | Save Entry |
| WorldbookPage | `worldbooks` | Worldbook, WorldEntry | Save Entry |
| ChatProfilePage | `chat_profiles` | ChatProfile, PromptOrderItem | Save |
| PromptOrderPage | `prompt_order` | PromptOrderItem[] | Reset Default / Save Order |

## 5. Visual Direction

### Style Family

- Base: Neo-Brutalism
- Execution: Clean utility desktop UI
- Secondary influence: AI-native workspace, technical editor, prompt debugging console

### Visual Rules

- Outer borders use `2px` or `3px` solid ink.
- Main panels use flat surfaces, not gradients.
- Accent blocks use saturated color only for CTA, active nav, warnings, and selected cards.
- Shadows are offset hard shadows, never blurred glass shadows.
- Corners are lightly rounded: `6px` for controls, `10px` for panels.
- Icons use one SVG outline family with `2px` stroke.
- Dense editor screens use compact spacing, but text never drops below `12px`.

### Surface Model

| Surface | Use | Style |
|---|---|---|
| App background | Global field | Warm off-white |
| Primary panel | Page content | White, 3px ink border |
| Secondary panel | Lists and side panels | Cream, 2px ink border |
| Raised action card | Empty states and setup steps | Accent background, 3px ink border, 4px hard shadow |
| Inspector panel | Prompt verification | Pale cyan surface, 3px ink border |
| Error panel | Failure details | Pale red surface, 3px ink border |

### Guardrails

- No purple AI gradient background.
- No dark default theme in v0.1 BETA.
- No glassmorphism.
- No low-contrast gray-on-gray forms.
- No hidden icon-only CTAs for destructive or state-changing actions.

## 6. Color System

### Core Tokens

| Token | Hex | Use |
|---|---:|---|
| `color.bg` | `#F4F0E8` | Main app background |
| `color.surface` | `#FFFDF7` | Main content panels |
| `color.surface_alt` | `#EFE7D3` | Sidebar, list backgrounds |
| `color.ink` | `#111111` | Text, borders, icons |
| `color.text_muted` | `#525252` | Secondary labels |
| `color.border` | `#111111` | All structural borders |
| `color.primary` | `#0057FF` | Active selection, links, selected rows |
| `color.secondary` | `#FFE500` | Active nav, setup highlights |
| `color.cta` | `#FF5A1F` | Primary action buttons |
| `color.success` | `#1FA971` | Healthy connection, saved state |
| `color.warning` | `#FFB000` | LM Studio token limit warning, stale cache |
| `color.error` | `#D72638` | Failed stream, validation error |
| `color.info` | `#00A6D6` | Inspector, prompt metadata |
| `color.disabled_bg` | `#D7D2C8` | Disabled controls |
| `color.focus` | `#00D1FF` | Keyboard focus ring |

### Role Rules

- Primary CTA uses orange `#FF5A1F` with black text and `3px` border.
- Destructive actions use white surface with red border and red text, not filled red by default.
- Active navigation uses yellow fill with black text.
- Inspector uses cyan tint to separate verification from editing.
- Success state never uses color alone: include check icon and text.
- Error state never uses color alone: include error icon, failing action name, and recovery instruction.

### Contrast Rules

- Body text on all light surfaces uses `#111111`.
- Muted text is never used for required field labels.
- Disabled controls keep visible label contrast and show disabled reason in tooltip or helper text.
- Token budget warnings switch from neutral to warning at 80%, error at 95%.

## 7. Typography

### Font Stack

PySide6 font configuration:

```txt
Primary UI: Noto Sans KR, Inter, Segoe UI, Apple SD Gothic Neo, system sans-serif
Mono/Data: JetBrains Mono, D2Coding, SF Mono, Consolas, monospace
```

### Type Scale

| Role | Size | Weight | Use |
|---|---:|---:|---|
| App title | 24px | 800 | App name in sidebar |
| Page title | 22px | 800 | Top of each page |
| Section title | 17px | 800 | Panel headers |
| Body | 14px | 500 | Default labels and content |
| Dense body | 13px | 500 | Tables, lists, compact forms |
| Caption | 12px | 600 | Metadata, token estimates |
| Mono value | 12px | 600 | IDs, model names, token counts |
| Button | 14px | 800 | CTA and toolbar buttons |

### Tone

- Labels are short and concrete: `Provider`, `Model ID`, `Secret Ref`, `Token Budget`.
- Error messages state action + cause + next action.
- Empty states tell the user exactly which CTA to use next.
- IDs and enum values are displayed in mono text chips.

## 8. Layout and Grid

### App Shell

Desktop layout uses a full-height shell.

```txt
Window
├─ Sidebar: 236px fixed
├─ Main Area
│  ├─ Top Status Bar: 48px fixed
│  └─ Page Content: flexible
└─ Global Toast Stack: top-right, max 3 visible
```

### Spacing Rhythm

| Token | Value | Use |
|---|---:|---|
| `space.1` | 4px | Dense icon gaps |
| `space.2` | 8px | Label/control gaps |
| `space.3` | 12px | Form row gaps |
| `space.4` | 16px | Card padding |
| `space.5` | 20px | Panel internal spacing |
| `space.6` | 24px | Page section gap |
| `space.8` | 32px | Large page padding |

### Page Container

- Page padding: `24px` desktop, `16px` compact.
- Panel gap: `16px`.
- Main panels use `QSplitter` where resizing is valuable.
- Lists keep min width `240px` and max width `340px`.
- Inspector keeps width `360px` desktop and becomes a right drawer below `1280px`.

### Breakpoints

| Width | Behavior |
|---:|---|
| `>= 1440px` | Full 3-column workspace; Inspector visible when toggled |
| `1120px–1439px` | Sidebar full; Inspector drawer overlays page content |
| `960px–1119px` | Sidebar collapses to 72px icons; page uses 2-column split |
| `< 960px` | Compact desktop mode; navigation becomes top strip; editors stack vertically |

### Mobile Collapse Logic

Mobile is not a v0.1 target. For future narrow rendering, each page collapses into this order:

1. Page header and primary CTA
2. List or selector
3. Editor form
4. Preview / Inspector
5. Secondary metadata

No table keeps horizontal scrolling in narrow mode. Tables become labeled rows.

## 9. Key Components

### 9.1 App Sidebar

- Width: `236px`, collapsed width `72px`.
- Background: `color.surface_alt`.
- Border: right `3px color.ink`.
- Active item: yellow fill, black border, left notch.
- Each nav item: icon `20px`, label `14px/800`, height `44px`.
- Disabled nav items are not used. Pages remain accessible and show empty states.

### 9.2 Top Status Bar

Shows:

- Current page title
- Active Provider health summary
- Model cache freshness
- SQLite path short label
- Global error indicator

States:

| State | Display |
|---|---|
| Healthy | Green chip `Connected` + provider name |
| Untested | Yellow chip `Not tested` |
| Failed | Red chip `Connection failed` + details button |
| Streaming | Blue chip `Streaming` + session title |

### 9.3 Buttons

| Variant | Style | Use |
|---|---|---|
| Primary | Orange fill, black border, hard shadow | Save, Send, New Chat |
| Secondary | White fill, black border | Add Entry, Show Prompt, Fetch Models |
| Tertiary | Transparent, underline on hover | View details, copy ID |
| Danger | White fill, red text/border | Archive, Delete draft |
| Disabled | Gray fill, black border at 40% opacity | Any invalid action |

Button states:

- Hover: translate visual emphasis through shadow offset from `2px` to `4px`; layout position does not move.
- Pressed: shadow offset becomes `0px`; background darkens by 4%.
- Focus: `2px` cyan outer ring outside black border.
- Loading: left spinner plus verb text, e.g. `Testing...`.

### 9.4 Inputs and Forms

- Labels are always visible above controls.
- Required label suffix: `*` in red.
- Border: `2px color.ink`.
- Focus: `2px color.focus` outside border.
- Invalid: red border + inline error below field.
- Helper text: muted, 12px, max one sentence.
- Character counters appear for fields with max length.
- Password/API key fields show masked value and `Save Key` as separate CTA.

### 9.5 Cards

- Default card: white surface, `2px` border, `8px` radius.
- Important cards: `3px` border, `4px 4px 0 #111111` hard shadow.
- Selected card: blue top bar `6px` and black border.
- Clickable card hover: background `#FFF6B8`, no layout shift.

### 9.6 Tables and Lists

- Header row: black text, yellow background, `2px` bottom border.
- Row height: `44px` normal, `36px` dense.
- Selected row: blue outline and pale blue fill `#E8F0FF`.
- Empty table: centered card with next CTA.
- IDs use mono chips, truncated middle with copy action.

### 9.7 Status Banners

Banner anatomy:

```txt
[icon] [status title] [short cause]                         [action]
```

Examples:

- `LM Studio token limits unknown. Using context 8192 and output 2048.`
- `Stream failed. User message was kept. Retry after checking Provider health.`
- `Keyring unavailable. Install system SecretService support before saving keys.`

### 9.8 Token Budget Bar

- Height: `18px`.
- Segments: system, persona, worldbook, lorebook, history, current message, reserved output.
- Label: `5,120 / 128,000 tokens`.
- Warning at 80%, error at 95%.
- Clicking segment in Inspector scrolls to the related PromptBlock.

### 9.9 Prompt Inspector

Inspector tabs:

1. `Blocks`
2. `Messages`
3. `Lore Matches`
4. `Truncation`
5. `Raw Snapshot`

Inspector header shows:

- `total_token_estimate`
- `matched_lore_entry_ids` count
- `truncated_history_message_ids` count
- `created_at_iso`

### 9.10 Prompt Order Item

Each item includes:

- drag handle
- block title
- `kind` mono chip
- enabled toggle
- lock icon for non-deletable required blocks
- order index

Rules:

- `system_base` cannot be disabled or deleted.
- `current_input` cannot be disabled or deleted.
- `chat_history` cannot be deleted but can be disabled.
- Reordering updates `order_index` in increments of 10.

### 9.11 Chat Message Bubble

User message:

- Right aligned on desktop.
- White card with blue top strip.
- Shows token estimate and timestamp.

Assistant message:

- Left aligned.
- White card with black border and orange response marker.
- During streaming, shows live text and a small `Streaming` chip.
- After completion, shows `Show Prompt` secondary CTA.

System/error message:

- Full-width banner card.
- Error state never deletes the user message.

## 10. Page-by-Page Guidance

### 10.1 ChatPage

Goal: create and run chat sessions while keeping prompt assembly inspectable.

Structure:

1. Session sidebar + ChatProfile / UserPersona 선택 드롭다운
2. Message timeline (스크롤 영역)
3. Composer bar (입력 + Send/Stop)
4. Token Budget Bar
5. Inspector panel (세션 정보 / 프롬프트 스냅샷 탭)

Primary actions:

- `New Chat`: ChatProfile과 UserPersona가 드롭다운에서 선택된 상태에서만 enabled.
- `Send`: enabled only when session status is `active` and input is non-empty.
- `Stop`: enabled only when session status is `streaming`.
- `Delete`: 현재 선택된 세션을 삭제 (확인 다이얼로그 후).
- `Show Prompt`: assistant 메시지의 스냅샷이 Inspector 탭에 자동 표시됨.

[v0.1.2 구현 상태]:
- ✅ 스트리밍 실시간 표시: AI 응답이 매 청크마다 버블에 즉시 표시 (update_content)
- ✅ ChatProfile / UserPersona 선택 드롭다운: 사용자가 세션 생성 전 직접 선택
- ✅ 세션 삭제: 삭제 버튼 + 확인 다이얼로그
- ✅ 자동 스크롤: 스트리밍 중 타임라인이 자동으로 맨 아래로 이동

### 10.2 ProviderPage

Goal: move Provider setup from empty to models fetched without invalid transitions.

Structure:

1. Provider list
2. Provider editor form
3. Setup state stepper
4. Health result panel
5. Model cache table

Primary actions:

- `Save Provider`
- `Save Key`
- `Test Connection`
- `Fetch Models`

The stepper must block visual confusion. `Fetch Models` is disabled until the last health check is successful.

> **구현 상태 (v0.1.3)**: `provider_page.py`에서 5단계 셋업 진행 상태를 시각적 체크리스트로 표시.
> Provider 선택 / 저장 / 테스트 / 모델 패치 시 자동 갱신. spec §13.1 상태 머신 준수.

### 10.3 ModelProfilePage

Goal: create model profiles from loaded capability data and show only supported settings.

Structure:

1. ModelProfile list
2. Provider/model selector
3. Capability summary
4. Parameter form
5. Save validation panel

Rules:

- Unsupported parameters are hidden.
- Hidden unsupported parameters with non-null values produce a save-blocking error.
- LM Studio unknown token limits show a yellow warning and use fixed defaults.

> **구현 상태 (v0.1.3)**: `model_profile_page.py`에서 MVP 구현 완료.
> Provider 선택 → 캐시된 모델 선택 → context/max_output/temperature/top_p/top_k/frequency_penalty/presence_penalty 설정 → 저장.
> **DD-13 적용 (v0.1.3)**: 모델 변경 시 `supported_parameters_json` 조회 → 미지원 파라미터 자동 숨김.
> capability 정보 불완전 시 경고 표시 + 모든 파라미터 표시. SC-06 해소.

### 10.4 UserPersonaPage

Goal: create the user's self-description, speaking style, and boundaries.

Structure:

1. UserPersona list
2. Editor form
3. Validation summary

Fields:

- name — placeholder: `예: 차분한 소설가`
- description — placeholder: `예: 판타지 소설을 쓰는 작가입니다...`
- speaking_style — placeholder: `예: 존댓말을 사용합니다. 짧고 간결한 문장을 선호합니다.`
- boundaries (원치 않는 내용) — placeholder: `예: 폭력적이거나 선정적인 내용은 피해주세요...`
- enabled

### 10.5 AIPersonaPage

[v0.2.0] Vibe Fill Phase 1에서 전면 개편됨.

목표: AI 캐릭터 페르소나를 14개 구조화된 필드로 정의하고, 바이브 텍스트로 AI가 자동 생성하는 기능을 제공한다.

구조:

1. 좌측: AI 페르소나 목록 (이름 — 역할 형식)
2. 우측: QScrollArea 기반 편집 영역
   - ✨ Vibe Fill 영역 (바이브 입력 + Provider/Model 드롭다운 + AI로 채우기)
   - 기본 정보 섹션 (이름*, 나이, 성별, 직업/역할*)
   - 외면 섹션 (외모)
   - 내면 섹션 (성격*, 말투*, 약점/두려움)
   - 서사 섹션 (배경 스토리, 인간관계)
   - 능력 섹션 (특기/능력, 취미/관심사)
   - 행동 규칙 섹션 (목표, 제한)
   - 저장 버튼

필드 (14개):

| # | 필드명 | DB 컬럼 | 필수 | 설명 |
|---|---|---|---|---|
| 1 | 이름 | name | ✅ | 캐릭터 이름 |
| 2 | 나이 | age | — | 나이 또는 나이대 |
| 3 | 성별 | gender | — | 성별 |
| 4 | 직업/역할 | role_name | ✅ | 세계 내 역할 |
| 5 | 외모 | appearance | — | 시각적 묘사 |
| 6 | 성격 | personality | ✅ | 핵심 성격 |
| 7 | 말투 | speaking_style | ✅ | 대화 패턴 |
| 8 | 약점/두려움 | weaknesses | — | 약점이나 공포 |
| 9 | 배경 스토리 | backstory | — | 과거 배경 |
| 10 | 인간관계 | relationships | — | 주요 관계 |
| 11 | 특기/능력 | skills | — | 능력/재능 |
| 12 | 취미/관심사 | interests | — | 여가 활동 |
| 13 | 목표 | goals | — | 행동 방향 |
| 14 | 제한 | restrictions | — | 금지 행동 |

Vibe Fill UX 흐름:

1. 사용자가 바이브 텍스트 입력
2. Provider + Model 선택
3. "✨ AI로 채우기" 클릭 → AsyncSignalBridge로 비동기 LLM 호출
4. 로딩 중: "🔄 캐릭터 생성 중..." 상태 표시, 버튼 비활성화
5. 성공 시: 14개 필드를 한꺼번에 채움
6. 사용자가 결과 검토 후 수정
7. "💾 저장" 클릭

### 10.6 LorebookPage

[v0.2.0] Vibe Fill Phase 2에서 전면 개편됨.

목표: 키워드 트리거 기반 로어 엔트리를 관리하고, 바이브 텍스트로 AI가 자동 생성하는 기능을 제공한다.

구조:

1. 좌측: 로어북 목록 + 로어북 편집
2. 중앙: 엔트리 목록 ([우선순위] 제목 형식)
3. 우측: QScrollArea 기반 편집 영역
   - ✨ Vibe Fill 패널 (AI Persona 선택 + 바이브 입력 + Provider/Model)
   - 생성 미리보기 체크리스트
   - 수동 엔트리 편집 폼

Vibe Fill UX 흐름:

1. 로어북 선택 (필수)
2. AI Persona 선택 (선택 — 캐릭터 맥락 주입)
3. 바이브 텍스트 입력 (예: "고서관의 유물, 비밀 장소, 저주된 책들")
4. Provider + Model 선택
5. "✨ AI로 엔트리 생성" 클릭 → 비동기 LLM 호출
6. 결과가 **미리보기 체크리스트**로 표시 (기본 전체 체크)
7. 사용자가 원치 않는 엔트리 체크 해제
8. "📥 선택 항목 추가 저장" 클릭 → 체크된 것만 DB에 Append
9. 반복 사용 가능 (기존 엔트리 유지, 새 바이브마다 중복 방지 컨텍스트 자동 주입)

규칙:

- 로어북 선택 없이 Vibe Fill 불가.
- 기존 수동 엔트리 편집/삭제 기능 유지.
- Save Entry는 title, 최소 1개 activation key, content 필수.
- Priority 범위: 0~1000.
- AI 생성 시 최대 10개 엔트리 제한.

### 10.7 WorldbookPage

[v0.2.0] Vibe Fill Phase 3에서 전면 개편됨.

목표: 항상 삽입되는 세계관 엔트리를 관리하고, 바이브 텍스트로 AI가 10개 카테고리별 세계관을 자동 생성하는 기능을 제공한다.

구조:

1. 좌측: 월드북 목록 + 월드북 편집
2. 중앙: 엔트리 목록 ([우선순위] 제목 형식)
3. 우측: QScrollArea 기반 편집 영역
   - ✨ Vibe Fill 패널 (AI Persona×2 + Lorebook×2 + 바이브 + 카테고리 체크박스 + Provider/Model)
   - QProgressBar 진행률 표시
   - 생성 미리보기 체크리스트
   - 수동 엔트리 편집 폼

카테고리 (10개):

역사, 지리, 세력/국가, 종족, 마법/기술, 경제, 종교/신화, 던전/위험지대, 일상/문화, 규칙/법칙

Vibe Fill UX 흐름:

1. 월드북 선택 (필수)
2. AI Persona 복수 선택 (선택)
3. Lorebook 복수 선택 (선택)
4. 바이브 텍스트 입력
5. 카테고리 체크박스 선택 (기본 전체 체크)
6. Provider + Model 선택
7. "✨ AI로 세계관 생성" 클릭
8. 진행률 표시: "████░░ 2/4 — 종족, 마법, 경제 생성 중..."
9. 전체 완료 → 미리보기 체크리스트
10. 체크 on/off → "📥 선택 항목 추가 저장"

청크 분할 알고리즘:

- 카테고리를 2~3개씩 4그룹으로 분할하여 LLM 4번 호출
- 이전 청크 엔트리 제목만 다음 청크에 넘겨 일관성 유지 + 토큰 절약
- 부분 실패 시 이전 청크 결과 유지

규칙:

- 월드북 선택 없이 Vibe Fill 불가.
- 기존 수동 엔트리 편집/삭제 기능 유지.
- Entry content limit: 6000 characters.

### 10.8 ChatProfilePage

Goal: assemble model, AI personas, lorebooks, worldbooks, system base, and prompt order into a reusable chat preset.

Structure:

1. ChatProfile list
2. Composition editor
3. Prompt block summary
4. Save validation panel

Rules:

- Save requires model_profile and at least 1 AI persona.
- AI persona selection max is 5.
- Lorebook and worldbook selection max is 10 each.
- System base max length is 4000.

> **구현 상태 (v0.1.1)**: `chat_profile_page.py`에서 태그 + [추가...] 다이얼로그 패턴으로 개선.
> AI 페르소나 / 로어북 / 월드북 각 영역에 `EntityPickerDialog` 모달 적용.
> 선택된 항목이 태그로 표시되며 [×]로 개별 해제 가능.
> 빈 상태일 때 안내 문구가 표시되어 사용자 행동을 유도함.
> 선택 개수 제한: AI persona max 5, Lorebook/Worldbook max 10 (spec.md §8.3 준수).

### 10.9 PromptOrderPage

Goal: let users reorder prompt blocks while protecting required blocks.

Structure:

1. Prompt block order list
2. Block detail panel
3. Preview message order
4. Reset/Save action bar

Rules:

- `Reset Default` is always enabled.
- Dragging updates visual order before save.
- Required block locks are visible.
- Disabled blocks remain in list with muted label.

> **구현 상태 (v0.1.2)**: 미구현. v0.1.3에서 신규 구현 예정.
> spec.md §12.2의 Default PromptOrder 기준으로 구현.
> DD-05 결정에 따른 차단된 블록 룰 적용.

## 11. Structural Section Maps

### 11.1 App Shell

- Page goal: keep all setup/edit/chat tasks in one predictable desktop shell.
- Primary user action: navigate to the next task and see global state.
- Block order:
  1. Sidebar navigation
  2. Top status bar
  3. Page content
  4. Toast stack
- CTA placement: page-level CTAs live in each page header or sticky bottom bar; global shell has no destructive CTA.
- Data density: medium; shell should not compete with editor pages.
- Desktop layout: sidebar fixed left, top bar across main area.
- Compact layout: sidebar becomes icon rail at 960–1119px and top nav strip below 960px.

### 11.2 ChatPage

- Page goal: send messages, stop streaming, inspect prompt snapshots.
- Primary user action: type message and press `Send`.
- Block order:
  1. Session list
  2. Chat header with selectors
  3. Message timeline
  4. Composer and Send/Stop controls
  5. Inspector panel
- CTA placement: `New Chat` at top of session list; `Send/Stop` at composer right; `Show Prompt` inside assistant message toolbar.
- Data density: high in Inspector, medium in timeline.
- Desktop layout: 260px session list, flexible timeline, 360px Inspector.
- Mobile/compact collapse: session list becomes dropdown, Inspector becomes full-height drawer, composer remains sticky bottom.

### 11.3 ProviderPage

- Page goal: complete Provider setup state machine.
- Primary user action: save Provider, save key, test, fetch models.
- Block order:
  1. Provider list
  2. Setup stepper
  3. Provider form
  4. Secret/key panel
  5. Health result
  6. Model cache table
- CTA placement: each step CTA appears at the end of its panel; disabled CTAs show reason.
- Data density: medium; model table dense after fetch.
- Desktop layout: left list + right stacked setup panels.
- Mobile/compact collapse: Provider list becomes top selector, panels stack in state order.

### 11.4 ModelProfilePage

- Page goal: save valid settings based on model capability.
- Primary user action: choose model, tune visible parameters, save profile.
- Block order:
  1. ModelProfile list
  2. Provider/model selector
  3. Capability summary chips
  4. Parameter controls
  5. Validation panel
- CTA placement: sticky bottom-right `Save Profile`.
- Data density: medium-high because parameter controls are technical.
- Desktop layout: left profiles, center form, right capability/validation panel.
- Mobile/compact collapse: selector first, parameter form second, validation third.

### 11.5 Persona Pages

- Page goal: create and maintain persona text assets.
- Primary user action: edit text and save.
- Block order:
  1. Persona list
  2. Editor title and enabled toggle
  3. Required fields
  4. Optional fields
  5. Validation summary
- CTA placement: sticky bottom-right `Save`.
- Data density: text-heavy but not table-heavy.
- Desktop layout: left list, right editor.
- Mobile/compact collapse: list becomes top dropdown, editor stacks full width.

### 11.6 LorebookPage

- Page goal: manage triggered lore entries with visible activation keys.
- Primary user action: select entry, edit keys/content, save.
- Block order:
  1. Lorebook selector/list
  2. Entry table
  3. Entry editor
  4. Match preview
- CTA placement: `Add Entry` above entry table; `Save Entry` sticky in editor footer.
- Data density: high due to keys, priority, content.
- Desktop layout: 240px book list, 360px entry table, flexible editor.
- Mobile/compact collapse: book selector, entry accordion list, editor, preview.

### 11.7 WorldbookPage

- Page goal: manage world entries inserted into prompt by selected ChatProfile.
- Primary user action: edit entry and save.
- Block order:
  1. Worldbook selector/list
  2. Entry table
  3. Entry editor
  4. Token preview
- CTA placement: `Save Entry` in editor footer.
- Data density: medium-high.
- Desktop layout: same as Lorebook without activation key column.
- Mobile/compact collapse: same as Lorebook.

### 11.8 ChatProfilePage

- Page goal: combine saved assets into one runnable chat preset.
- Primary user action: select model/personas/books and save.
- Block order:
  1. ChatProfile list
  2. ModelProfile selector
  3. AI Persona multi-select
  4. Lorebook/Worldbook selectors
  5. System base editor
  6. Prompt summary
  7. Validation panel
- CTA placement: sticky bottom-right `Save`.
- Data density: medium; summary panel uses chips and counts.
- Desktop layout: left profiles, center composition, right summary.
- Mobile/compact collapse: profile selector, composition sections, summary, save.

### 11.9 PromptOrderPage

- Page goal: configure prompt block order with locked required blocks.
- Primary user action: drag blocks and save order.
- Block order:
  1. Order list
  2. Selected block detail
  3. Preview order
  4. Reset/Save bar
- CTA placement: `Reset Default` left, `Save Order` right.
- Data density: medium.
- Desktop layout: two columns, list left and preview right.
- Mobile/compact collapse: order list first, preview below, action bar sticky bottom.

## 12. ASCII Wireframes

### 12.1 App Shell

```txt
┌─────────────────────────────────────────────────────────────────────────────┐
│ CHITCHAT      │ Chat                          Connected: OpenRouter  DB: ...│
│               ├─────────────────────────────────────────────────────────────┤
│ ▣ Chat        │                                                             │
│ ▣ Providers   │                 PAGE CONTENT AREA                           │
│ ▣ Models      │                                                             │
│ ▣ User        │                                                             │
│ ▣ AI Persona  │                                                             │
│ ▣ Lorebooks   │                                                             │
│ ▣ Worldbooks  │                                                             │
│ ▣ ChatProfile │                                                             │
│ ▣ PromptOrder │                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 12.2 ChatPage

```txt
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ Chat                                                                                     │
├───────────┬───────────────────────────────────────┬──────────────┬───────────────────────┤
│ Sessions  │ Nocturne Main Chat                    │ 🎭 캐릭터 상태 │ Prompt Inspector    │
│ [New Chat]│ User: Default Writer  Profile: Main   │              │ Tokens 5120/128000  │
│           ├───────────────────────────────────────┤ 턴 3 neutral │ ┌─────────────────┐ │
│ ▣ cs_001  │ ┌───────────────────────────────────┐ │ 신뢰    ████ 35│ │ Blocks          │ │
│ ▢ cs_002  │ │ User message                      │ │ 친밀도  ███  25│ │ system_base     │ │
│ ▢ archived│ │ token 42 · 12:00                  │ │ 감정의존 █   13│ │ ai_persona      │ │
│           │ └───────────────────────────────────┘ │ 침묵편안 ████ 40│ │ worldbook       │ │
│           │ ┌───────────────────────────────────┐ │ 다가감  ██   17│ │ lore matches 2  │ │
│           │ │ Assistant response                │ │ 거절공포 ███  47│ └─────────────────┘ │
│           │ │ [Show Prompt]                     │ │ 경계민감 ████ 60│                     │
│           │ └───────────────────────────────────┘ │ 회복력  ████ 42│                     │
│           │                                       │──────────────│                     │
│           │                                       │ 📝 기억       │                     │
│           │                                       │ [praise] 칭찬 │                     │
│           ├───────────────────────────────────────┤ [◀ 접기]     │                     │
│           │ [message input........................] [Send] [Stop]                       │
└───────────┴───────────────────────────────────────┴──────────────┴─────────────────────┘
```

> **[v1.0.0]** 동적 상태 패널이 채팅 메인과 Prompt Inspector 사이에 추가됨.
> 스트리밍 완료 시 `GET /api/sessions/{id}/dynamic-state`를 호출하여 관계 바 차트와 기억 로그를 자동 갱신한다.
> ◀/▶ 토글로 접기/펼치기 가능.

### 12.3 ProviderPage

```txt
┌─────────────────────────────────────────────────────────────────────────────┐
│ Providers                                                        [+ New]    │
├───────────────┬─────────────────────────────────────────────────────────────┤
│ Provider List │ Setup State                                                │
│ ▣ Gemini Main │ [Saved]──[Key]──[Tested]──[Models Fetched]                 │
│ ▢ OpenRouter  ├─────────────────────────────────────────────────────────────┤
│ ▢ LM Studio   │ Provider Form                                              │
│               │ Name *             [Gemini Main                         ]  │
│               │ Kind *             [gemini ▼]                              │
│               │ Base URL           [—                                  ]   │
│               │ Timeout            [60                                  ]  │
│               │ [Save Provider]                                            │
│               ├─────────────────────────────────────────────────────────────┤
│               │ Secret                                                     │
│               │ API Key            [••••••••••••••••] [Save Key]           │
│               │ secret_ref         chitchat:prov_gemini_main               │
│               ├─────────────────────────────────────────────────────────────┤
│               │ Health                                                     │
│               │ ✅ Connected · 243ms                         [Test Again]   │
│               │                                             [Fetch Models] │
│               ├─────────────────────────────────────────────────────────────┤
│               │ Model Cache                                                │
│               │ model_id              context     output     params         │
│               │ gemini-...            1,048,576   8192       temp top_p     │
└───────────────┴─────────────────────────────────────────────────────────────┘
```

### 12.4 ModelProfilePage

```txt
┌─────────────────────────────────────────────────────────────────────────────┐
│ Model Profiles                                                  [Save]      │
├───────────────┬───────────────────────────────────────┬─────────────────────┤
│ Profiles      │ Model Selection                        │ Capability          │
│ ▣ Roleplay    │ Provider [OpenRouter Main ▼]           │ model: gpt-4o-mini  │
│ ▢ Draft       │ Model    [openai/gpt-4o-mini ▼]        │ context 128000      │
│               ├───────────────────────────────────────┤ output 16384        │
│               │ Parameters                             │ streaming ✅        │
│               │ temperature       [0.85 ━━━━━━━]       │ system prompt ✅     │
│               │ top_p             [0.90 ━━━━━━━]       │ json mode ❌         │
│               │ max_output_tokens [1600        ]       ├─────────────────────┤
│               │ presence_penalty  [0.20        ]       │ Validation          │
│               │ frequency_penalty [0.10        ]       │ ✅ capability loaded │
│               │ seed              [empty       ]       │ ✅ settings valid    │
│               │ hidden: top_k, stop                    │                     │
└───────────────┴───────────────────────────────────────┴─────────────────────┘
```

### 12.5 Persona Editor

```txt
┌─────────────────────────────────────────────────────────────────────────────┐
│ User Personas                                                   [Save]      │
├────────────────────┬────────────────────────────────────────────────────────┤
│ Personas           │ Editor                                                 │
│ ▣ Default Writer   │ Name *        [Default Writer                       ]  │
│ ▢ New Persona      │ Enabled       [●]                                      │
│                    │ Description *                                          │
│                    │ ┌────────────────────────────────────────────────────┐ │
│                    │ │ 사용자는 차분한 문체를 선호하는 창작자다...       │ │
│                    │ └────────────────────────────────────────────────────┘ │
│                    │ Speaking Style                                         │
│                    │ ┌────────────────────────────────────────────────────┐ │
│                    │ └────────────────────────────────────────────────────┘ │
│                    │ Boundaries                                             │
│                    │ ┌────────────────────────────────────────────────────┐ │
│                    │ └────────────────────────────────────────────────────┘ │
│                    │ ✅ name valid · ✅ description valid                   │
└────────────────────┴────────────────────────────────────────────────────────┘
```

### 12.6 LorebookPage

```txt
┌─────────────────────────────────────────────────────────────────────────────┐
│ Lorebooks                                                     [Add Entry]   │
├───────────────┬──────────────────────────┬──────────────────────────────────┤
│ Lorebooks     │ Entries                  │ Entry Editor                     │
│ ▣ Nocturne    │ title       keys  prio   │ Title * [City Gate            ]  │
│ ▢ Draft       │ ▣ City Gate  3     200   │ Enabled [●] Priority [200]       │
│               │ ▢ Library    2     100   │ Activation Keys *                │
│               │                          │ [gate ×] [city ×] [entrance ×]  │
│               │                          │ Content *                        │
│               │                          │ ┌──────────────────────────────┐ │
│               │                          │ │ ...                          │ │
│               │                          │ └──────────────────────────────┘ │
│               │                          │ Match Preview                    │
│               │                          │ recent 8 messages + current msg  │
│               │                          │ [Save Entry]                     │
└───────────────┴──────────────────────────┴──────────────────────────────────┘
```

### 12.7 ChatProfilePage

```txt
┌─────────────────────────────────────────────────────────────────────────────┐
│ Chat Profiles                                                   [Save]      │
├───────────────┬───────────────────────────────────────┬─────────────────────┤
│ Profiles      │ Composition                            │ Prompt Summary      │
│ ▣ Nocturne    │ Name * [Nocturne Main Chat          ]  │ 7 blocks enabled    │
│ ▢ Draft       │ Model Profile [Roleplay Balanced ▼]    │ system_base         │
│               │                                        │ ai_persona x1       │
│               │ AI 페르소나              [+ 추가...]   │ worldbook x1        │
│               │ ┌──────────┐ ┌───────────────────┐    │ lorebook x1         │
│               │ │미라 [×]  │ │늑대인간 가이드 [×]│    │ user_persona        │
│               │ └──────────┘ └───────────────────┘    │ chat_history        │
│               │                                        │ current_user_msg    │
│               │ 로어북                   [+ 추가...]   ├─────────────────────┤
│               │ ┌──────────────┐                      │ Validation          │
│               │ │Nocturne [×]  │                      │ ✅ model profile     │
│               │ └──────────────┘                      │ ✅ 1 AI persona      │
│               │                                        │                     │
│               │ 월드북                   [+ 추가...]   │                     │
│               │ ┌──────────────────┐                  │                     │
│               │ │Nocturne Rules [×]│                  │                     │
│               │ └──────────────────┘                  │                     │
│               │ System Base                            │                     │
│               │ ┌───────────────────────────────────┐ │                     │
│               │ │ You are a helpful...              │ │                     │
│               │ └───────────────────────────────────┘ │                     │
└───────────────┴───────────────────────────────────────┴─────────────────────┘
```

### 12.8 PromptOrderPage

```txt
┌─────────────────────────────────────────────────────────────────────────────┐
│ Prompt Order                                      [Reset Default] [Save]    │
├───────────────────────────────────────┬─────────────────────────────────────┤
│ Order List                            │ Preview                             │
│ ≡ 🔒 system_base        on   index 0   │ 01 system_base                      │
│ ≡    ai_persona         on   index 10  │ 02 ai_persona                       │
│ ≡    worldbook          on   index 20  │ 03 worldbook                        │
│ ≡    lorebook_matches   on   index 30  │ 04 lorebook_matches                 │
│ ≡    user_persona       on   index 40  │ 05 user_persona                     │
│ ≡ 🔒 chat_history       on   index 50  │ 06 chat_history                     │
│ ≡ 🔒 current_user_msg   on   index 60  │ 07 current_user_message             │
│                                       │ Selected Block Detail               │
│                                       │ kind: lorebook_matches              │
│                                       │ enabled: true                       │
└───────────────────────────────────────┴─────────────────────────────────────┘
```

### 12.9 Prompt Inspector Drawer Compact

```txt
┌───────────────────────────────────────┐
│ Prompt Inspector                 [X]  │
├───────────────────────────────────────┤
│ Tokens 5120 / 128000                  │
│ [system][persona][world][lore][hist]  │
├───────────────────────────────────────┤
│ Tabs: Blocks | Messages | Lore | Raw  │
├───────────────────────────────────────┤
│ system_base                           │
│ token_estimate: 48                    │
│ source_ids: []                        │
│ ┌───────────────────────────────────┐ │
│ │ prompt block preview...           │ │
│ └───────────────────────────────────┘ │
└───────────────────────────────────────┘
```

## 13. Interaction and Motion

### General Timing

| Interaction | Timing | Behavior |
|---|---:|---|
| Button hover | 120ms | background and shadow state change |
| Panel open/close | 180ms | width or opacity transition |
| Toast enter/exit | 180ms | slide 8px + fade |
| Streaming cursor | 500ms interval | blink only while streaming |
| Drag reorder | immediate | placeholder row follows pointer |
| Validation update | 0ms after blur, 150ms after text input pause | inline error refresh |

### Keyboard Behavior

- `Ctrl/Cmd + N`: New Chat on ChatPage.
- `Ctrl/Cmd + Enter`: Send when composer is focused and session is active.
- `Esc`: close Inspector drawer or dialog.
- `Ctrl/Cmd + S`: save current editor page when the primary save CTA is enabled.
- Arrow keys move through list rows.
- Space toggles selected checkbox/toggle.

### Loading States

- Provider connection test shows blocking button spinner only on `Test Connection` button.
- Fetch Models shows progress in model cache panel and keeps existing cache visible until replacement completes.
- Streaming assistant message appends chunks without shifting previous messages.
- Saving forms disables only the current save CTA; navigation remains available.

### Error States

- Failed stream: keep user message, show red banner above composer, return session to `active` after acknowledgement.
- Keyring failure: show red banner in Secret panel and keep API key field contents until user changes page.
- Capability fetch failure: show error banner and leave previous cache table marked stale.
- Save validation failure: focus the first invalid field and list all blocking errors in validation panel.

### Sticky Behavior

- Page-level save bars stick to the bottom inside editor panels.
- Chat composer sticks to bottom of chat timeline.
- Inspector header sticks inside Inspector scroll area.
- Top status bar remains visible.

### Reduced Motion

When OS reduced-motion preference is detected:

- Panel transitions become instant.
- Toast slide becomes fade only.
- Streaming cursor remains visible but does not blink.

## 14. Accessibility

### Minimum Targets

- Interactive target size: `36px` minimum, `44px` preferred.
- Focus ring is always visible and never hidden by custom styling.
- Text input labels remain visible in all states.
- Required fields use text and icon, not color alone.

### Screen Reader / Accessible Names

Every interactive PySide6 widget must set accessible names:

```txt
Save Provider button
Test Connection button
Fetch Models button
Send Message button
Stop Streaming button
Show Prompt Snapshot button
Prompt Order Drag Handle: system_base
```

### Color and State

- Status chips include text labels: `Connected`, `Failed`, `Streaming`, `Stopped`, `Archived`.
- Error fields show message text below control.
- Success states include check icon and saved timestamp.
- Warnings include the applied default or exact blocked action.

### Forms

- Tab order follows visual order from top-left to bottom-right.
- Validation appears on blur and on save attempt.
- Save-blocking errors are summarized at the bottom validation panel.
- Password fields support copy only for `secret_ref`, not raw API key.

### Chat Accessibility

- Streaming updates should announce completion, not every token chunk.
- Message bubbles expose role, timestamp, and token estimate.
- `Stop` must be reachable by keyboard while streaming.
- Prompt Inspector tabs use keyboard navigation.

## 15. Stack / Implementation Notes

### PySide6 Widget Mapping

| UI Concept | PySide6 Implementation |
|---|---|
| App shell | `QMainWindow` + central `QWidget` layout |
| Sidebar | `QListWidget` or custom `QListView` with delegate |
| Page switching | `QStackedWidget` |
| Resizable columns | `QSplitter` |
| Lists | `QListView` + `QAbstractListModel` |
| Tables | `QTableView` + model/delegate |
| Forms | `QFormLayout` inside bordered panel widgets |
| Scrollable editors | `QScrollArea` |
| Inspector drawer | right-side widget in `QSplitter` or overlay panel |
| Toasts | lightweight top-right widget stack |
| Drag prompt order | `QListView` internal move mode or custom delegate |
| Token budget bar | custom `QWidget.paintEvent` |

### Styling Strategy

- Define design tokens in one Python module, e.g. `ui/theme.py`.
- Apply global Qt stylesheet from generated token values.
- Use object names for variants: `PrimaryButton`, `DangerButton`, `InspectorPanel`, `ErrorBanner`.
- Do not hardcode page-specific colors inside page files.
- Keep all SVG icons in a single local icon folder with consistent stroke width.

Example token structure:

```python
THEME = {
    "bg": "#F4F0E8",
    "surface": "#FFFDF7",
    "surface_alt": "#EFE7D3",
    "ink": "#111111",
    "primary": "#0057FF",
    "secondary": "#FFE500",
    "cta": "#FF5A1F",
    "success": "#1FA971",
    "warning": "#FFB000",
    "error": "#D72638",
    "info": "#00A6D6",
    "focus": "#00D1FF",
}
```

### ViewModel Boundaries

- `ProviderPage` binds to `ProviderVM` only.
- `ModelProfilePage`, `UserPersonaPage`, `AIPersonaPage`, `LorebookPage`, `WorldbookPage`, `ChatProfilePage`, `PromptOrderPage` bind to `ProfileVM` or dedicated sub-viewmodels.
- `ChatPage` binds to `ChatVM` only.
- UI components never import Provider adapters.
- Prompt Inspector reads `AssembledPrompt` and `prompt_snapshot_json`, not raw provider responses.

### Component File Responsibilities

| File | Responsibility |
|---|---|
| `ui/main_window.py` | Shell, status bar, page stack, global toast mount |
| `ui/navigation.py` | Sidebar state and page switching |
| `ui/pages/chat_page.py` | Session list, timeline, composer, Inspector host |
| `ui/pages/provider_page.py` | Provider setup stepper, secret panel, health/model cache UI |
| `ui/pages/model_profile_page.py` | Capability-bound parameter form |
| `ui/pages/persona_page.py` | User persona list/editor |
| `ui/pages/ai_persona_page.py` | AI persona list/editor |
| `ui/pages/lorebook_page.py` | Lorebook/entry management and key chips |
| `ui/pages/worldbook_page.py` | Worldbook/entry management |
| `ui/pages/chat_profile_page.py` | Chat profile composition UI |
| `ui/pages/prompt_order_page.py` | Drag reorder and block lock UI |
| `ui/widgets/model_parameter_form.py` | Capability-aware parameter controls |
| `ui/widgets/prompt_order_list.py` | Drag list with required block rules |
| `ui/widgets/chat_message_view.py` | Message bubble rendering and prompt CTA |
| `ui/widgets/token_budget_bar.py` | Segmented token budget visual |

### UI Acceptance Checks

- Provider setup shows invalid transitions as disabled CTAs with reasons.
- API key field never writes raw key into visible DB-bound labels.
- ModelProfile hides unsupported parameters from `supported_parameters`.
- LM Studio unknown token limits show fixed default warning.
- Chat streaming exposes Stop while session is `streaming`.
- Failed streaming creates an error banner and keeps user message.
- Prompt Inspector shows block order, lore matches, truncation IDs, token estimate, and raw snapshot.
- PromptOrder protects `system_base`, `chat_history`, and `current_user_message` according to required block rules.

## 16. Risks / Open Questions

### Risks

| Risk | Design Impact | Mitigation in UI |
|---|---|---|
| Provider metadata shape changes | Parameter UI could show stale controls | Display capability fetched timestamp and raw supported parameter chips |
| LM Studio token limits unavailable | Token budget may be inaccurate | Persistent yellow warning with fixed defaults 8192/2048 |
| Keyring backend unavailable | User cannot save Gemini/OpenRouter keys | Secret panel error with exact backend requirement |
| Large chat history slows timeline | UI may feel heavy | Virtualize message list or render visible message widgets only |
| Prompt preview length reaches 24000 chars | Inspector could become slow | Show truncated preview banner and keep raw snapshot accessible |
| Narrow desktop windows | Three-column pages become cramped | Use compact layout rules below 1120px |

### Open Questions

1. Whether `Delete` actions are allowed in v0.1 BETA is not defined. The UI must not expose permanent delete CTAs until the data deletion policy is specified.
2. Whether export/import UI is included in v0.1 BETA is not defined. The UI must reserve no navigation item for export/import in the first build.
3. Whether dark mode is required is not defined. v0.1 BETA ships one light theme to reduce styling and QA scope.
4. Whether multi-session search is required is not defined. ChatPage can include session list filtering only after search behavior is specified.
5. Whether prompt snapshot comparison between messages is required is not defined. Inspector shows one selected snapshot at a time in v0.1 BETA.

---

## 프론트엔드 구현 현황 (v1.0.0)

### SPA 라우터 구조

```
index.html
├── api.js (API 클라이언트: apiGet/apiPost/apiPut/apiDelete)
├── app.js (SPA 라우터: 9개 페이지 라우트)
└── pages/
    ├── chat.js .............. ✅ 3컬럼 레이아웃 + WebSocket 스트리밍 + 동적 상태 패널
    ├── providers.js ......... ✅ Provider CRUD + 연결 테스트 + 모델 캐시
    ├── models.js ............ ✅ ModelProfile CRUD (Provider 연동 모델 선택)
    ├── personas.js .......... ✅ VibeFill AI Persona 생성/관리
    ├── lorebooks.js ......... ✅ Lorebook + LoreEntry CRUD (activation_keys 쉼표 구분)
    ├── worldbooks.js ........ ✅ Worldbook + WorldEntry CRUD
    ├── chat_profiles.js ..... ✅ ChatProfile 조합 (ModelProfile + Persona + LB + WB)
    ├── prompt_order.js ...... ✅ 프롬프트 블록 순서 편집 (▲▼)
    └── settings.js .......... ✅ 사용자 설정 (i18n 로케일 등)
```

### 세션 생성 워크플로우

```
[채팅 페이지] → [+] 클릭 → 모달 표시
    ├── 세션 제목 입력
    ├── ChatProfile 선택 (드롭다운)
    ├── UserPersona 선택 (드롭다운 or 자동 생성)
    └── [생성] → POST /api/sessions → 세션 선택 → WebSocket 연결
```

### 구현 시 주의사항

1. **캐시 버스팅**: 정적 파일 캐시 문제 방지를 위해 `?v=N` 쿼리 파라미터 사용
2. **z-index 레이어**: 모달은 `document.body` 직속 + `z-index: 9999`로 최상위 레이어 보장
3. **escapeHtml**: `providers.js`에 전역 정의, 모든 페이지에서 공유
4. **API 에러 처리**: `apiGet/apiPost` 실패 시 `try/catch`로 사용자 친화적 에러 메시지 표시
