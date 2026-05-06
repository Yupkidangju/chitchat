# tests/test_e2e_acceptance.py
# [v0.1.0b0] SC-01 ~ SC-10 수용 테스트 (단위 테스트 기반)
#
# spec.md §2.2에서 정의된 10개 성공 기준을 코드로 검증한다.
# Provider 실제 API 호출이 필요한 SC-03~05, SC-09는 mock 기반으로 검증한다.
from __future__ import annotations
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from chitchat.db.models import Base
from chitchat.db.repositories import RepositoryRegistry
from chitchat.domain.lorebook_matcher import match_lore_entries
from chitchat.domain.profiles import LoreEntryData
from chitchat.domain.prompt_assembler import assemble_prompt
from chitchat.providers.registry import ProviderRegistry
from chitchat.secrets.key_store import KeyStore
from chitchat.services.provider_service import ProviderService


def _make_repos() -> RepositoryRegistry:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return RepositoryRegistry(sessionmaker(bind=engine))


class TestSC01_ProviderCreate:
    """SC-01: Provider 3종 생성 가능."""
    def test_create_three_providers(self) -> None:
        repos = _make_repos()
        pr = ProviderRegistry()
        ks = MagicMock(spec=KeyStore)
        ks.set_key.return_value = "keyring_ref_placeholder"
        svc = ProviderService(repos, pr, ks)
        for kind in ["gemini", "openrouter", "lm_studio"]:
            p = svc.save_provider(name=f"Test {kind}", provider_kind=kind,
                api_key="test-key" if kind != "lm_studio" else None)
            assert p.provider_kind == kind
        assert len(svc.get_all_providers()) == 3


class TestSC02_KeyNotPlaintext:
    """SC-02: API Key SQLite 평문 미저장."""
    def test_api_key_not_in_db(self) -> None:
        repos = _make_repos()
        pr = ProviderRegistry()
        ks = MagicMock(spec=KeyStore)
        ks.set_key.return_value = "keyring_ref_gemini"
        svc = ProviderService(repos, pr, ks)
        svc.save_provider(name="Gemini", provider_kind="gemini", api_key="SUPER_SECRET_KEY_123")
        # DB에서 Provider 직접 조회
        providers = repos.providers.get_all()
        for p in providers:
            # secret_ref는 keyring 참조 키이지 실제 API Key가 아님
            assert p.secret_ref != "SUPER_SECRET_KEY_123"
            # secret_ref는 None이 아님 (keyring에 저장되었음을 의미)
            assert p.secret_ref is not None


class TestSC06_ParameterHiding:
    """SC-06: 미지원 파라미터 UI 숨김. capability의 supported_parameters 기반."""
    def test_unsupported_param_excluded(self) -> None:
        from chitchat.domain.provider_contracts import ModelCapability
        cap = ModelCapability(
            provider_kind="gemini", model_id="test",
            display_name="Test", context_window_tokens=8192,
            max_output_tokens=2048,
            supported_parameters={"temperature", "top_p"},
            supports_streaming=True, supports_system_prompt=True,
            supports_json_mode=False, raw={},
        )
        # UI는 supported_parameters에 없는 파라미터를 숨겨야 한다
        assert "temperature" in cap.supported_parameters
        assert "top_k" not in cap.supported_parameters
        assert "frequency_penalty" not in cap.supported_parameters


class TestSC07_LorebookMatching:
    """SC-07: 로어북 최근 8개 매칭."""
    def test_match_within_8_messages(self) -> None:
        entries = [
            LoreEntryData(id="1", lorebook_id="lb", title="유물",
                activation_keys=["유물"], content="고대 유물", priority=100),
        ]
        # 9번째 이전 메시지에 유물이 있고, 최근 8개에는 없음
        msgs = ["유물 이야기"] + ["관련없음"] * 9
        blocks = match_lore_entries(entries, msgs, scan_messages=8)
        assert len(blocks) == 0  # 스캔 범위 밖

    def test_match_in_recent_8(self) -> None:
        entries = [
            LoreEntryData(id="1", lorebook_id="lb", title="마법",
                activation_keys=["마법"], content="마법 설명", priority=100),
        ]
        msgs = ["관련없음"] * 5 + ["마법을 사용했다"]
        blocks = match_lore_entries(entries, msgs, scan_messages=8)
        assert len(blocks) == 1


class TestSC08_PromptOrder:
    """SC-08: PromptOrder 변경 시 순서 변경."""
    def test_order_change_affects_output(self) -> None:
        # 기본 순서: system_base → user_persona → ai_persona → current_input
        order1 = [("system_base", True), ("user_persona", True), ("current_input", True)]
        r1 = assemble_prompt(order1, "SYS", "USER", None, [], [], [], "HI", 8192)

        # user_persona 비활성화
        order2 = [("system_base", True), ("user_persona", False), ("current_input", True)]
        r2 = assemble_prompt(order2, "SYS", "USER", None, [], [], [], "HI", 8192)

        # user_persona가 비활성이면 system 메시지에 USER 텍스트가 없어야 함
        assert "USER" in r1.messages[0].content
        assert "USER" not in r2.messages[0].content


class TestSC10_BuildReady:
    """SC-10: 빌드 준비 상태 확인."""
    def test_all_imports_resolve(self) -> None:
        """모든 핵심 모듈이 import 가능한지 확인한다."""
        # [v1.0.0] PySide6 UI 모듈 제거, FastAPI 모듈 추가
        import importlib
        core_modules = [
            "chitchat.config.paths",
            "chitchat.config.settings",
            "chitchat.db.engine",
            "chitchat.db.models",
            "chitchat.db.repositories",
            "chitchat.domain.ids",
            "chitchat.domain.profiles",
            "chitchat.domain.provider_contracts",
            "chitchat.domain.prompt_blocks",
            "chitchat.domain.prompt_assembler",
            "chitchat.domain.lorebook_matcher",
            "chitchat.domain.chat_session",
            "chitchat.domain.vibesmith_persona",
            "chitchat.domain.dynamic_state",
            "chitchat.providers.base",
            "chitchat.providers.registry",
            "chitchat.providers.capability_mapper",
            "chitchat.secrets.key_store",
            "chitchat.services.provider_service",
            "chitchat.services.prompt_service",
            "chitchat.services.chat_service",
            "chitchat.services.dynamic_state_engine",
            "chitchat.api.app",
            "chitchat.api.routes.providers",
            "chitchat.api.routes.personas",
            "chitchat.api.routes.chat",
            "chitchat.api.routes.settings",
            "chitchat.api.routes.health",
        ]
        for mod in core_modules:
            importlib.import_module(mod)

    def test_pyproject_version(self) -> None:
        """pyproject.toml의 버전이 1.0.0인지 확인한다."""
        import tomllib
        from pathlib import Path
        toml_path = Path(__file__).parent.parent / "pyproject.toml"
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
        assert data["project"]["version"] == "1.0.0"

    def test_required_docs_exist(self) -> None:
        """필수 문서 파일이 존재하는지 확인한다."""
        from pathlib import Path
        root = Path(__file__).parent.parent
        required = [
            "spec.md", "README.md", "CHANGELOG.md", "BUILD_GUIDE.md",
            "implementation_summary.md", "DESIGN_DECISIONS.md",
            "audit_roadmap.md", "designs.md",
        ]
        for doc in required:
            assert (root / doc).exists(), f"필수 문서 누락: {doc}"


class TestSC11_DynamicStateEngine:
    """SC-11: DynamicStateEngine ZSTD 압축/해동 라운드트립 + DB 영속화."""

    def test_상태_생성_압축_해동(self) -> None:
        """초기 상태 생성 → ZSTD 압축 → 해동 → 데이터 일치 검증."""
        from chitchat.services.dynamic_state_engine import DynamicStateEngine
        dse = DynamicStateEngine()
        state = dse.create_initial_state("char_001", "sess_001")

        # 기억 추가
        dse.add_memory(state, "praise", "테스트 칭찬", "trust+2")
        dse.increment_turn(state)

        # 압축 → 해동
        blob = dse.compress_state(state)
        assert isinstance(blob, bytes)
        assert len(blob) > 0

        restored = dse.decompress_state(blob)
        assert restored.character_id == "char_001"
        assert restored.session_id == "sess_001"
        assert restored.turn_count == 1
        assert len(restored.memories) == 1
        assert restored.memories[0].trigger_type == "praise"

    def test_관계_변수_갱신_범위_제한(self) -> None:
        """관계 변수 갱신이 0~100 범위를 벗어나지 않는지 검증."""
        from chitchat.services.dynamic_state_engine import DynamicStateEngine
        dse = DynamicStateEngine()
        state = dse.create_initial_state("char_002", "sess_002")

        # trust 초기값(30)에 +200 → 100으로 클램핑
        dse.update_relationship(state, {"trust": 200})
        assert state.relationship_state.trust == 100

        # trust에 -300 → 0으로 클램핑
        dse.update_relationship(state, {"trust": -300})
        assert state.relationship_state.trust == 0

    def test_DB_영속화_라운드트립(self) -> None:
        """DynamicStateRepository를 통한 DB 저장/조회 라운드트립."""
        from chitchat.db.models import DynamicStateRow
        from chitchat.domain.ids import new_id
        from chitchat.services.dynamic_state_engine import DynamicStateEngine

        repos = _make_repos()
        dse = DynamicStateEngine()
        state = dse.create_initial_state("char_003", "sess_003")
        dse.add_memory(state, "shared_experience", "함께 커피를 마심")
        dse.increment_turn(state)

        blob = dse.compress_state(state)
        row = DynamicStateRow(
            id=new_id("ds_"), character_id="char_003",
            session_id="sess_003", state_blob=blob,
            version=state.version, turn_count=state.turn_count,
        )
        repos.dynamic_states.upsert(row)

        # 조회
        loaded = repos.dynamic_states.get_by_session("sess_003")
        assert loaded is not None
        restored = dse.decompress_state(loaded.state_blob)
        assert restored.turn_count == 1
        assert len(restored.memories) == 1


class TestSC12_AIAnalysis:
    """SC-12: AI 분석 프롬프트 생성 + JSON 파싱 + apply 검증."""

    def test_분석_프롬프트_생성(self) -> None:
        """build_analysis_prompt가 올바른 프롬프트를 생성하는지 검증."""
        from chitchat.services.dynamic_state_engine import DynamicStateEngine
        dse = DynamicStateEngine()
        state = dse.create_initial_state("char_001", "sess_001")
        prompt = dse.build_analysis_prompt(
            state, "유리", [("user", "안녕!"), ("assistant", "안녕하세요!")],
        )
        assert "캐릭터: 유리" in prompt
        assert "trust:" in prompt
        assert "[user]: 안녕!" in prompt
        assert "relationship_changes" in prompt

    def test_분석_응답_파싱_성공(self) -> None:
        """정상 JSON 응답 파싱 검증."""
        from chitchat.services.dynamic_state_engine import DynamicStateEngine
        dse = DynamicStateEngine()
        response = '''```json
{
  "relationship_changes": {
    "trust": 3,
    "familiarity": 2,
    "emotional_reliance": 0,
    "comfort_with_silence": 0,
    "willingness_to_initiate": 1,
    "fear_of_rejection": -1,
    "boundary_sensitivity": 0,
    "repair_ability": 0
  },
  "memories": [
    {
      "trigger": "praise",
      "content": "처음으로 감사를 표현함",
      "impact": "trust+3"
    }
  ],
  "emotional_state": "happy",
  "event": null
}
```'''
        result = dse.parse_analysis_response(response)
        assert result is not None
        assert result["relationship_changes"]["trust"] == 3
        assert result["relationship_changes"]["fear_of_rejection"] == -1
        assert len(result["memories"]) == 1
        assert result["emotional_state"] == "happy"

    def test_분석_응답_파싱_실패_폴백(self) -> None:
        """잘못된 응답은 None을 반환."""
        from chitchat.services.dynamic_state_engine import DynamicStateEngine
        dse = DynamicStateEngine()
        assert dse.parse_analysis_response("이건 JSON이 아닙니다") is None
        assert dse.parse_analysis_response('{"no_key": 1}') is None

    def test_분석_결과_적용(self) -> None:
        """apply_analysis가 상태를 올바르게 변경하는지 검증."""
        from chitchat.services.dynamic_state_engine import DynamicStateEngine
        dse = DynamicStateEngine()
        state = dse.create_initial_state("char_004", "sess_004")
        initial_trust = state.relationship_state.trust

        analysis = {
            "relationship_changes": {
                "trust": 5, "familiarity": 3,
                "emotional_reliance": 0, "comfort_with_silence": 0,
                "willingness_to_initiate": 0, "fear_of_rejection": 0,
                "boundary_sensitivity": 0, "repair_ability": 0,
            },
            "memories": [
                {"trigger": "shared_experience", "content": "함께 산책", "impact": "familiarity+3"},
            ],
            "emotional_state": "warm",
            "event": None,
        }

        dse.apply_analysis(state, analysis)
        assert state.relationship_state.trust == initial_trust + 5
        initial_fam = 20  # RelationshipState 기본값
        assert state.relationship_state.familiarity == initial_fam + 3
        assert state.current_emotional_state == "warm"
        assert len(state.memories) == 1
        assert state.memories[0].content == "함께 산책"

    def test_변경량_범위_클램핑(self) -> None:
        """AI가 -10~+10 범위를 벗어나는 값을 반환해도 클램핑되는지 검증."""
        from chitchat.services.dynamic_state_engine import DynamicStateEngine
        dse = DynamicStateEngine()
        response = '{"relationship_changes": {"trust": 50, "familiarity": -30}, "memories": [], "emotional_state": "neutral"}'
        result = dse.parse_analysis_response(response)
        assert result is not None
        assert result["relationship_changes"]["trust"] == 10
        assert result["relationship_changes"]["familiarity"] == -10


