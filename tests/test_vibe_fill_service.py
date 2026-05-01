# tests/test_vibe_fill_service.py
# [v0.2.0] Vibe Fill 서비스 및 UI 통합 테스트

from unittest.mock import MagicMock

import pytest
from chitchat.domain.provider_contracts import ChatStreamChunk
from chitchat.services.vibe_fill_service import VibeFillService
from chitchat.ui.pages.lorebook_page import LorebookPage
from chitchat.ui.pages.worldbook_page import WorldbookPage


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

class DummyProfileService:
    def get_lore_entries(self, lb_id):
        mock_entry = MagicMock()
        mock_entry.title = "Existing Lore"
        return [mock_entry]

    def get_world_entries(self, wb_id):
        mock_entry = MagicMock()
        mock_entry.title = "Existing World"
        return [mock_entry]
        
    def save_lore_entry(self, **kwargs): pass
    def save_world_entry(self, **kwargs): pass

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
        category_keys=["history", "geography"], # 카테고리 2개면 1개 청크로 분할됨 (grouping logic)
        persona_ids=[],
        lorebook_ids=[],
        progress_callback=on_progress,
    )
    
    assert result.success is True
    assert len(progress_calls) > 0
    # 마지막 콜백은 100% 완료 상태여야 함 (1/1)
    assert progress_calls[-1][0] == progress_calls[-1][1]


def test_lorebook_page_append_duplicate_ignore(monkeypatch) -> None:
    """LorebookPage에서 Append 시 중복된 제목은 무시되는지 검증."""
    # QWidget 상속으로 인한 GUI 의존성 우회 (PySide6 QApplication 없이 테스트)
    # MagicMock으로 의존성 대체
    mock_svc = DummyProfileService()
    mock_save = MagicMock()
    mock_svc.save_lore_entry = mock_save

    # UI 위젯 인스턴스화를 피하기 위해 클래스 구조를 모방한 더미 객체 사용
    class DummyLorebookPage:
        def __init__(self, svc):
            self._svc = svc
            self._cur_lb = "lb_test"
            
            # 체크박스 모방 (isChecked()=True)
            class DummyCheck:
                def isChecked(self): return True
                
            self._pending_checks = [DummyCheck(), DummyCheck()]
            self._pending_entries = [
                {"title": "Existing Lore", "activation_keys": [], "content": "", "priority": 100}, # 중복 (무시돼야 함)
                {"title": "New Lore", "activation_keys": [], "content": "", "priority": 100},      # 신규 (저장돼야 함)
            ]
            self._st = MagicMock()
            self._preview_group = MagicMock()

        def _load_entries(self):
            pass
            
    page = DummyLorebookPage(mock_svc)
    # _on_append_entries 로직만 가져와서 몽키패치
    page._on_append_entries = LorebookPage._on_append_entries.__get__(page, DummyLorebookPage)
    
    page._on_append_entries()
    
    # save_lore_entry는 "New Lore"에 대해서만 1번 호출되어야 함
    mock_save.assert_called_once()
    assert mock_save.call_args[1]["title"] == "New Lore"


def test_worldbook_page_append_duplicate_ignore() -> None:
    """WorldbookPage에서 Append 시 중복된 제목은 무시되는지 검증."""
    mock_svc = DummyProfileService()
    mock_save = MagicMock()
    mock_svc.save_world_entry = mock_save

    class DummyWorldbookPage:
        def __init__(self, svc):
            self._svc = svc
            self._cur_wb = "wb_test"
            
            class DummyCheck:
                def isChecked(self): return True
                
            self._pending_checks = [DummyCheck(), DummyCheck()]
            self._pending_entries = [
                {"title": "Existing World", "content": "", "priority": 100}, # 중복
                {"title": "New World", "content": "", "priority": 100},      # 신규
            ]
            self._st = MagicMock()
            self._preview_group = MagicMock()

        def _load_entries(self):
            pass
            
    page = DummyWorldbookPage(mock_svc)
    page._on_append_entries = WorldbookPage._on_append_entries.__get__(page, DummyWorldbookPage)
    
    page._on_append_entries()
    
    # "New World" 1번만 저장돼야 함
    mock_save.assert_called_once()
    assert mock_save.call_args[1]["title"] == "New World"
