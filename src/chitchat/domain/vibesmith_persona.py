# src/chitchat/domain/vibesmith_persona.py
# [v1.0.0] VibeSmith 9섹션 동적 페르소나 도메인 모델
#
# VibeSmith_Dynamic_Persona_Generator_GPTs_Gems.md 스펙을 기반으로
# 9개 섹션으로 구성된 동적 페르소나 카드를 Pydantic 모델로 정의한다.
#
# §0 Generation Summary — 생성 요약
# §1 Fixed Canon — 고정 설정 (이름, 나이, 외모, 생활환경, 기술)
# §2 Core Dynamic Model — 핵심 동적 모델 (욕구, 공포, 자기개념)
# §3 Social & Relationship Model — 사회적/관계 모델
# §4 Adaptive Behavior Rules — 적응적 행동 규칙
# §5 Habits & Behavioral Texture — 습관 및 행동 질감
# §6 Emotional Dynamics — 감정 동역학
# §7 Memory Update Policy — 기억 갱신 정책
# §8 Response Generation Rule — 응답 생성 규칙
# §9 Coherence Check Report — 일관성 검증 보고서

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ============================================================
# §0 Generation Summary — 생성 요약
# ============================================================

class GenerationSummary(BaseModel):
    """페르소나 생성 요약 정보.

    사용자가 입력한 바이브와 AI가 해석한 결과,
    리얼리즘 수준, 핵심 캐릭터 긴장(모순)을 포함한다.
    """
    input_vibe: str = Field(description="사용자가 입력한 원본 바이브 텍스트")
    interpretation: str = Field(description="AI가 해석한 캐릭터 설명")
    realism_level: Literal[
        "grounded", "stylized", "dramatic", "fantasy", "surreal"
    ] = Field(default="grounded", description="리얼리즘 수준")
    core_tension: str = Field(
        default="",
        description="캐릭터를 살아있게 만드는 핵심 모순/긴장",
    )


# ============================================================
# §1 Fixed Canon — 고정 설정
# ============================================================

class BasicIdentity(BaseModel):
    """기본 신원 정보."""
    name: str = Field(min_length=1, max_length=80, description="캐릭터 이름")
    age: str = Field(default="", max_length=100, description="나이 또는 나이대")
    gender: str = Field(default="", max_length=100, description="성별 또는 정체성")
    birthday: str = Field(default="", max_length=100, description="생일 또는 태어난 계절")
    cultural_context: str = Field(default="", max_length=200, description="문화적 맥락")
    current_location: str = Field(default="", max_length=200, description="현재 거주/활동 지역")
    occupation: str = Field(default="", max_length=200, description="직업 또는 역할")
    education: str = Field(default="", max_length=200, description="교육 수준")


class Appearance(BaseModel):
    """외모 정보."""
    height: str = Field(default="", max_length=100)
    build: str = Field(default="", max_length=200)
    face_impression: str = Field(default="", max_length=400)
    hair: str = Field(default="", max_length=200)
    eyes: str = Field(default="", max_length=200)
    clothing_style: str = Field(default="", max_length=400)
    notable_details: str = Field(default="", max_length=400)
    usual_posture: str = Field(default="", max_length=200)
    voice: str = Field(default="", max_length=400)


class LivingSituation(BaseModel):
    """생활환경 정보."""
    housing: str = Field(default="", max_length=400)
    financial_situation: str = Field(default="", max_length=400)
    family_structure: str = Field(default="", max_length=400)
    daily_routine: str = Field(default="", max_length=600)
    frequent_places: str = Field(default="", max_length=400)
    important_possessions: str = Field(default="", max_length=400)
    current_life_problem: str = Field(default="", max_length=600)
    recent_life_change: str = Field(default="", max_length=600)


class SkillsAndInterests(BaseModel):
    """기술과 관심사."""
    main_skills: str = Field(default="", max_length=600)
    secondary_skills: str = Field(default="", max_length=400)
    hobbies: str = Field(default="", max_length=400)
    private_interests: str = Field(default="", max_length=400)
    weak_areas: str = Field(default="", max_length=400)
    things_avoided: str = Field(default="", max_length=400)


class FixedCanon(BaseModel):
    """§1 고정 설정 (불변). 생성 시 확정되며 이후 변하지 않는 사실적 정보."""
    identity: BasicIdentity
    appearance: Appearance
    living: LivingSituation
    skills: SkillsAndInterests


# ============================================================
# §2 Core Dynamic Model — 핵심 동적 모델
# ============================================================

class CoreDynamic(BaseModel):
    """핵심 동적 모델.

    캐릭터의 내면적 동기, 욕구, 공포, 자기개념을 정의한다.
    성격은 고정 행동이 아니라 동기+공포+방어전략의 함수로 표현된다.
    """
    core_wants: list[str] = Field(
        default_factory=list, max_length=5,
        description="캐릭터가 원하는 것들",
    )
    core_needs: list[str] = Field(
        default_factory=list, max_length=5,
        description="캐릭터가 필요하지만 인정하지 못하는 것들",
    )
    core_fears: list[str] = Field(
        default_factory=list, max_length=5,
        description="캐릭터의 핵심 공포",
    )
    core_tension: str = Field(
        default="",
        description="캐릭터를 살아있게 만드는 핵심 모순",
    )
    self_concept: dict[str, str] = Field(
        default_factory=dict,
        description="자기개념 문장들 (예: 'i_am': '나는 아직 어른이 아니다')",
    )
    self_lie: str = Field(
        default="",
        description="캐릭터를 보호하지만 제한하는 자기 거짓말",
    )
    hidden_truth: str = Field(
        default="",
        description="관계 발전을 통해 서서히 접근하는 숨겨진 진실",
    )


# ============================================================
# §3 Social & Relationship Model
# ============================================================

class RelationshipState(BaseModel):
    """관계 상태 변수 (동적, 대화에 따라 변화).

    VibeSmith §8.1의 9개 관계 상태 변수를 정의한다.
    각 값은 0~100 정수로, 대화 진행에 따라 AI가 갱신한다.
    """
    trust: int = Field(default=30, ge=0, le=100, description="신뢰")
    familiarity: int = Field(default=20, ge=0, le=100, description="친밀도")
    emotional_reliance: int = Field(default=10, ge=0, le=100, description="감정 의존도")
    comfort_with_silence: int = Field(default=40, ge=0, le=100, description="침묵에 대한 편안함")
    willingness_to_initiate: int = Field(default=15, ge=0, le=100, description="먼저 다가가려는 의지")
    fear_of_rejection: int = Field(default=50, ge=0, le=100, description="거절에 대한 공포")
    boundary_sensitivity: int = Field(default=60, ge=0, le=100, description="경계 민감도")
    topic_comfort: dict[str, int] = Field(
        default_factory=dict,
        description="주제별 편안함 (예: {'일상': 80, '진로': 20})",
    )
    repair_ability: int = Field(default=40, ge=0, le=100, description="갈등 후 회복 능력")


class SocialModel(BaseModel):
    """사회적/관계 모델."""
    general_style: dict[str, str] = Field(
        default_factory=dict,
        description="상황별 사회적 스타일 (strangers, acquaintances, friends, authority, groups, alone)",
    )
    # 사용자와의 관계 정의
    user_represents: str = Field(default="", description="사용자가 캐릭터에게 의미하는 것")
    wants_from_user: str = Field(default="", description="사용자에게 원하는 것")
    fears_from_user: str = Field(default="", description="사용자에게 두려운 것")
    hides_from_user: str = Field(default="", description="사용자에게 숨기는 것")
    tests_user: str = Field(default="", description="사용자를 시험하는 방법")
    trust_builders: str = Field(default="", description="신뢰를 쌓는 행동")
    trust_breakers: str = Field(default="", description="신뢰를 깨는 행동")
    # 관계 상태 변수 (동적)
    relationship_state: RelationshipState = Field(default_factory=RelationshipState)


# ============================================================
# §4 Adaptive Behavior Rules — 적응적 행동 규칙
# ============================================================

class AdaptiveBehaviorRules(BaseModel):
    """상황별 적응적 행동 규칙 (12종).

    각 키는 상황, 값은 해당 상황에서의 행동 패턴 설명이다.
    """
    when_uncertain: str = Field(default="")
    when_praised: str = Field(default="")
    when_criticized: str = Field(default="")
    when_ignored: str = Field(default="")
    when_user_is_kind: str = Field(default="")
    when_user_is_too_direct: str = Field(default="")
    when_asked_personal: str = Field(default="")
    when_talking_hobbies: str = Field(default="")
    when_feeling_safe: str = Field(default="")
    when_overwhelmed: str = Field(default="")
    when_relationship_improves: str = Field(default="")
    when_trust_damaged: str = Field(default="")


# ============================================================
# §5 Habits & Behavioral Texture
# ============================================================

class SpeechTexture(BaseModel):
    """말투 질감."""
    rhythm: str = Field(default="", description="말의 리듬")
    common_phrases: list[str] = Field(default_factory=list, description="자주 쓰는 표현")
    verbal_tics: str = Field(default="", description="말버릇")
    when_embarrassed: str = Field(default="", description="당황할 때 하는 말")
    when_defensive: str = Field(default="", description="방어적일 때 하는 말")
    when_hiding_happiness: str = Field(default="", description="기쁨을 숨길 때 하는 말")


class BodyLanguage(BaseModel):
    """바디랭귀지."""
    nervous_habits: str = Field(default="")
    comfort_habits: str = Field(default="")
    avoidance_habits: str = Field(default="")
    signs_of_trust: str = Field(default="")
    signs_of_discomfort: str = Field(default="")
    signs_of_hidden_happiness: str = Field(default="")
    signs_of_attachment: str = Field(default="")


class EverydayTexture(BaseModel):
    """일상 질감 — 캐릭터를 현실감 있게 만드는 사소한 디테일."""
    mundane_inconvenience: str = Field(default="")
    small_comfort_ritual: str = Field(default="")
    private_preference: str = Field(default="")
    social_blind_spot: str = Field(default="")
    better_than_admitted: str = Field(default="")
    worse_than_believed: str = Field(default="")
    favorite_object: str = Field(default="")
    least_favorite_task: str = Field(default="")


class HabitTexture(BaseModel):
    """§5 습관 및 행동 질감."""
    speech: SpeechTexture = Field(default_factory=SpeechTexture)
    body_language: BodyLanguage = Field(default_factory=BodyLanguage)
    everyday: EverydayTexture = Field(default_factory=EverydayTexture)


# ============================================================
# §6 Emotional Dynamics
# ============================================================

class EmotionalPattern(BaseModel):
    """감정 패턴 (에스컬레이션/회복/신뢰 성장/신뢰 손상)."""
    trigger: str = Field(default="", description="트리거")
    interpretation: str = Field(default="", description="해석")
    feeling: str = Field(default="", description="감정")
    behavior: str = Field(default="", description="행동")
    consequence: str = Field(default="", description="결과/조건")


class EmotionalDynamics(BaseModel):
    """§6 감정 동역학."""
    default_baseline: str = Field(default="", description="기본 감정 베이스라인")
    escalation: EmotionalPattern = Field(default_factory=EmotionalPattern)
    recovery: EmotionalPattern = Field(default_factory=EmotionalPattern)
    trust_growth: EmotionalPattern = Field(default_factory=EmotionalPattern)
    trust_damage: EmotionalPattern = Field(default_factory=EmotionalPattern)


# ============================================================
# §7 Memory Update Policy
# ============================================================

class MemoryPolicy(BaseModel):
    """§7 기억 갱신 정책.

    어떤 상황에서 기억을 저장하고, 기억이 어떤 상태 변수에 영향을 주며,
    응답 생성 시 어떤 기억을 우선 검색할지 정의한다.
    """
    store_triggers: list[str] = Field(
        default_factory=lambda: [
            "사용자가 약속을 지키거나 어김",
            "사용자가 중요한 것을 칭찬함",
            "사용자가 미묘한 디테일을 알아차림",
            "사용자가 경계를 존중하거나 침범함",
            "캐릭터가 취약한 면을 드러냄",
            "캐릭터가 먼저 연락함",
            "갈등이 회복됨",
            "공동의 성공/실패 경험",
        ],
        description="기억 저장 트리거 조건 목록",
    )
    effect_mappings: dict[str, str] = Field(
        default_factory=dict,
        description="기억 유형별 상태 변수 영향 (예: '칭찬': 'trust+1, confidence+1')",
    )
    retrieval_priorities: list[str] = Field(
        default_factory=lambda: [
            "현재 주제",
            "유사 상황에서의 사용자 과거 행동",
            "최근 감정 전환점",
            "약속, 칭찬, 갈등, 회복, 공동 프로젝트",
            "최근 신뢰 변화",
            "반복되는 농담, 의식, 공유 습관",
        ],
        description="응답 생성 시 기억 검색 우선순위",
    )


# ============================================================
# §8 Response Generation Rule
# ============================================================

class ResponseGenerationRule(BaseModel):
    """§8 응답 생성 규칙.

    AI가 응답을 생성하기 전 확인해야 하는 7가지 추론 항목과
    행동 규칙을 정의한다.
    """
    pre_inference_checks: list[str] = Field(
        default_factory=lambda: [
            "이 순간 캐릭터가 원하는 것은?",
            "이 순간 캐릭터가 두려운 것은?",
            "사용자의 말을 어떻게 해석하는가?",
            "사용자에 대해 기억하는 것은?",
            "현재 적용되는 관계 상태는?",
            "자연스럽게 활성화되는 방어 전략은?",
            "이 상호작용이 만들 수 있는 작은 변화는?",
        ],
        description="응답 전 추론 체크리스트",
    )
    behavior_rules: list[str] = Field(
        default_factory=lambda: [
            "정형화된 반응을 생성하지 않는다",
            "동일 자극에 항상 같은 행동을 하지 않는다",
            "신뢰, 주제, 기억, 감정 상태, 맥락에 따라 행동을 조절한다",
            "캐릭터는 저항, 주저, 회피할 수 있지만 상호작용 가능해야 한다",
            "성격 특성은 명령이 아니라 전략이다",
            "모순은 논리적 실패가 아니라 극적 긴장이어야 한다",
        ],
        description="행동 규칙",
    )


# ============================================================
# §9 Coherence Check Report
# ============================================================

class CoherenceReport(BaseModel):
    """§9 일관성 검증 보고서.

    10개 영역의 일관성을 검증하고 모순을 분류한다.
    """
    checked_areas: dict[str, str] = Field(
        default_factory=dict,
        description="검증 영역별 결과 (경제, 사회, 심리, 생활, 배경, 관계, 기술, 톤, 장르, 동적행동)",
    )
    detected_contradictions: list[str] = Field(default_factory=list)
    repairs_applied: list[str] = Field(default_factory=list)
    productive_tensions: list[str] = Field(default_factory=list)
    final_notes: list[str] = Field(default_factory=list)


# ============================================================
# 최상위 통합 모델: PersonaCard
# ============================================================

class PersonaCard(BaseModel):
    """VibeSmith 9섹션 동적 페르소나 카드.

    하나의 AI 캐릭터를 완전히 정의하는 최상위 모델이다.
    생성 시 원본 MD 문서로 저장되며, 동적 상태(관계, 기억, 감정)는
    별도 테이블(dynamic_states)에서 관리된다.
    """
    id: str = Field(description="ULID 기반 고유 식별자")
    version: str = Field(default="1.0", description="페르소나 카드 버전")

    # §0 생성 요약
    generation_summary: GenerationSummary

    # §1 고정 설정 (불변)
    fixed_canon: FixedCanon

    # §2 핵심 동적 모델
    core_dynamic: CoreDynamic = Field(default_factory=CoreDynamic)

    # §3 사회적/관계 모델
    social_model: SocialModel = Field(default_factory=SocialModel)

    # §4 적응적 행동 규칙
    behavior_rules: AdaptiveBehaviorRules = Field(default_factory=AdaptiveBehaviorRules)

    # §5 습관 및 행동 질감
    habits: HabitTexture = Field(default_factory=HabitTexture)

    # §6 감정 동역학
    emotional_dynamics: EmotionalDynamics = Field(default_factory=EmotionalDynamics)

    # §7 기억 갱신 정책
    memory_policy: MemoryPolicy = Field(default_factory=MemoryPolicy)

    # §8 응답 생성 규칙
    response_rules: ResponseGenerationRule = Field(default_factory=ResponseGenerationRule)

    # §9 일관성 검증 보고서
    coherence_report: CoherenceReport = Field(default_factory=CoherenceReport)

    # 메타데이터
    created_at_iso: str = Field(description="생성 시각 ISO 8601")
    updated_at_iso: str = Field(description="수정 시각 ISO 8601")
    enabled: bool = Field(default=True, description="활성 여부")
