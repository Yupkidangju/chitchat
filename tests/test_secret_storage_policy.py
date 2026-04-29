# tests/test_secret_storage_policy.py
# [v0.1.0b0] 키링 저장 정책 테스트
#
# spec.md §4 D-05에서 동결: API Key는 OS keyring에 저장하고 DB에 평문 미저장.
# KeyStore의 set/get/delete 호출 패턴과 secret_ref 생성을 검증한다.

from __future__ import annotations

from unittest.mock import MagicMock, patch


from chitchat.secrets.key_store import KeyStore


class TestKeyStoreOperations:
    """KeyStore의 set/get/delete 동작 검증."""

    def setup_method(self) -> None:
        """각 테스트 전 KeyStore 인스턴스를 생성한다."""
        self.store = KeyStore()

    @patch("chitchat.secrets.key_store.keyring")
    def test_set_key_returns_secret_ref(self, mock_keyring: MagicMock) -> None:
        """set_key가 올바른 secret_ref를 반환하는지 확인한다."""
        ref = self.store.set_key("prov_test", "gemini", "sk-fake-key")
        assert ref == "chitchat:prov_test"
        mock_keyring.set_password.assert_called_once_with(
            "chitchat:prov_test", "gemini", "sk-fake-key"
        )

    @patch("chitchat.secrets.key_store.keyring")
    def test_get_key_returns_stored_value(self, mock_keyring: MagicMock) -> None:
        """get_key가 키링에 저장된 값을 반환하는지 확인한다."""
        mock_keyring.get_password.return_value = "sk-fake-key"
        result = self.store.get_key("prov_test", "gemini")
        assert result == "sk-fake-key"
        mock_keyring.get_password.assert_called_once_with("chitchat:prov_test", "gemini")

    @patch("chitchat.secrets.key_store.keyring")
    def test_get_key_returns_none_when_not_found(self, mock_keyring: MagicMock) -> None:
        """키가 없을 때 None을 반환하는지 확인한다."""
        mock_keyring.get_password.return_value = None
        result = self.store.get_key("prov_nonexist", "gemini")
        assert result is None

    @patch("chitchat.secrets.key_store.keyring")
    def test_delete_key_success(self, mock_keyring: MagicMock) -> None:
        """delete_key 성공 시 True를 반환하는지 확인한다."""
        result = self.store.delete_key("prov_test", "gemini")
        assert result is True
        mock_keyring.delete_password.assert_called_once_with("chitchat:prov_test", "gemini")

    @patch("chitchat.secrets.key_store.keyring")
    def test_delete_key_not_found(self, mock_keyring: MagicMock) -> None:
        """삭제할 키가 없을 때 False를 반환하는지 확인한다."""
        import keyring.errors
        mock_keyring.delete_password.side_effect = keyring.errors.PasswordDeleteError("not found")
        mock_keyring.errors = keyring.errors
        result = self.store.delete_key("prov_nonexist", "openrouter")
        assert result is False


class TestSecretRefPolicy:
    """secret_ref 생성 정책 검증."""

    def test_secret_ref_format(self) -> None:
        """secret_ref가 'chitchat:{provider_profile_id}' 형식인지 확인한다."""
        ref = KeyStore._make_secret_ref("prov_abc123")
        assert ref == "chitchat:prov_abc123"

    def test_service_name_format(self) -> None:
        """키링 서비스명이 올바른 형식인지 확인한다."""
        svc = KeyStore._service_name("prov_xyz")
        assert svc == "chitchat:prov_xyz"


class TestApiKeyNotInDb:
    """DB에 API Key 평문이 저장되지 않음을 검증한다.

    이 테스트는 ProviderProfileData의 필드 구조를 검사하여
    api_key 또는 password 같은 평문 필드가 없는지 확인한다.
    """

    def test_provider_profile_has_no_plaintext_key_field(self) -> None:
        """ProviderProfileData에 평문 키 필드가 없는지 확인한다."""
        from chitchat.domain.provider_contracts import ProviderProfileData

        fields = set(ProviderProfileData.model_fields.keys())
        # 평문 키를 의미하는 필드명이 없어야 한다
        dangerous_names = {"api_key", "password", "secret", "token", "credential"}
        overlap = fields & dangerous_names
        assert overlap == set(), f"ProviderProfileData에 평문 키 필드가 있음: {overlap}"

    def test_provider_profile_has_secret_ref(self) -> None:
        """ProviderProfileData에 secret_ref 필드가 있는지 확인한다."""
        from chitchat.domain.provider_contracts import ProviderProfileData

        assert "secret_ref" in ProviderProfileData.model_fields
