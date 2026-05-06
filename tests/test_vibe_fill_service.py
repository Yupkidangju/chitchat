# tests/test_vibe_fill_service.py
# [v1.0.0] Vibe Fill 서비스 테스트
#
# [v0.2.0 → v1.0.0 변경사항]
# - PySide6 UI 통합 테스트(LorebookPage, WorldbookPage) 제거
#   삭제 사유: PySide6 UI 레이어가 v1.0.0에서 완전 제거됨
#   삭제 버전: v1.0.0
# - VibeFillService 서비스 레벨 테스트만 유지

from unittest.mock import MagicMock

import pytest
from chitchat.domain.provider_contracts import ChatStreamChunk
from chitchat.services.vibe_fill_service import VibeFillService


class DummyProvider:
    async def stream_chat(self, profile, request, api_key):
        yield ChatStreamChunk(delta='[{"title": "Test Entry", "content": "test", "priority": 100}]')

class DummyRegistry:
    def get_provider(self, kind):
        return DummyProvider()
        
    def get(self, kind):
        return DummyProvider()

class DummyProv:
    id = "prov_test"
    name = "test_provider"
    provider_kind = "gemini"
    base_url = "http://test"
    secret_ref = "test_ref"
    enabled = True
    timeout_seconds = 30

class DummyRepos:
    def __init__(self):
        self.providers = MagicMock()
        self.providers.get_by_id = lambda pid: DummyProv()
        self.ai_personas = MagicMock()
        self.lorebooks = MagicMock()
        self.lore_entries = MagicMock()
        self.world_entries = MagicMock()

    def get_by_id(self, pid):
        return DummyProv()


@pytest.mark.asyncio
async def test_generate_world_entries_progress_callback() -> None:
    """Worldbook 연쇄 호출 시 progress_callback이 정상 호출되는지 검증."""
    mock_key_store = MagicMock()
    mock_key_store.get_key.return_value = "fake_key"
    svc = VibeFillService(DummyRepos(), DummyRegistry(), mock_key_store)  # type: ignore
    
    progress_calls = []
    def on_progress(current: int, total: int, status: str) -> None:
        progress_calls.append((current, total, status))
        
    result = await svc.generate_world_entries(
        vibe_text="test vibe",
        worldbook_id="wb_test",
        provider_profile_id="prov_test",
        model_id="mod_test",
        category_keys=["history", "geography"],
        persona_ids=[],
        lorebook_ids=[],
        progress_callback=on_progress,
    )
    
    assert result.success is True
    assert len(progress_calls) > 0
    # 마지막 콜백은 100% 완료 상태여야 함 (1/1)
    assert progress_calls[-1][0] == progress_calls[-1][1]
