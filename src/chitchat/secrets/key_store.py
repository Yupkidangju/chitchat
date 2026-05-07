# src/chitchat/secrets/key_store.py
# [v1.0.0] OS Keyring 래퍼
#
# spec.md §4 D-05에서 동결: API Key는 OS keyring에 저장하고 DB에는 secret_ref만 저장.
# service name: "chitchat:{provider_profile_id}"
# username: provider_kind (예: "gemini", "openrouter")
#
# LM Studio는 secret이 불필요하므로 secret_ref가 None이다.

from __future__ import annotations

import logging

import keyring
from keyring.errors import KeyringError

logger = logging.getLogger(__name__)

# 키링 서비스명 접두사
_SERVICE_PREFIX = "chitchat"


class KeyStoreError(Exception):
    """키링 관련 에러. 백엔드 미사용 등의 이유로 발생한다."""
    pass


class KeyStore:
    """OS 키링을 통한 API Key 관리 클래스.

    set_key/get_key/delete_key로 키링에 접근한다.
    키링 백엔드가 없으면 KeyStoreError를 발생시킨다.
    """

    @staticmethod
    def _service_name(provider_profile_id: str) -> str:
        """provider_profile_id로부터 키링 서비스명을 생성한다.

        예: "chitchat:prov_gemini_main"
        """
        return f"{_SERVICE_PREFIX}:{provider_profile_id}"

    @staticmethod
    def _make_secret_ref(provider_profile_id: str) -> str:
        """DB에 저장할 secret_ref 문자열을 생성한다.

        secret_ref는 키링의 서비스명과 동일한 형식이다.
        """
        return f"{_SERVICE_PREFIX}:{provider_profile_id}"

    def set_key(
        self,
        provider_profile_id: str,
        provider_kind: str,
        api_key: str,
    ) -> str:
        """API Key를 키링에 저장하고 secret_ref를 반환한다.

        Args:
            provider_profile_id: Provider 프로필 ID.
            provider_kind: Provider 종류 (예: "gemini", "openrouter").
            api_key: 저장할 API Key 문자열.

        Returns:
            DB에 저장할 secret_ref 문자열.

        Raises:
            KeyStoreError: 키링 백엔드 접근 실패 시.
        """
        service = self._service_name(provider_profile_id)
        try:
            keyring.set_password(service, provider_kind, api_key)
            logger.info("API Key 저장 완료: service=%s, username=%s", service, provider_kind)
            return self._make_secret_ref(provider_profile_id)
        except KeyringError as e:
            raise KeyStoreError(
                f"키링에 API Key를 저장할 수 없습니다. "
                f"시스템 키링 백엔드(SecretService 등)가 설치되어 있는지 확인하세요: {e}"
            ) from e

    def get_key(
        self,
        provider_profile_id: str,
        provider_kind: str,
    ) -> str | None:
        """키링에서 API Key를 조회한다.

        Args:
            provider_profile_id: Provider 프로필 ID.
            provider_kind: Provider 종류.

        Returns:
            API Key 문자열 또는 None (키가 없을 때).

        Raises:
            KeyStoreError: 키링 백엔드 접근 실패 시.
        """
        service = self._service_name(provider_profile_id)
        try:
            return keyring.get_password(service, provider_kind)
        except KeyringError as e:
            raise KeyStoreError(
                f"키링에서 API Key를 조회할 수 없습니다: {e}"
            ) from e

    def delete_key(
        self,
        provider_profile_id: str,
        provider_kind: str,
    ) -> bool:
        """키링에서 API Key를 삭제한다.

        Args:
            provider_profile_id: Provider 프로필 ID.
            provider_kind: Provider 종류.

        Returns:
            삭제 성공 시 True, 키가 없었으면 False.

        Raises:
            KeyStoreError: 키링 백엔드 접근 실패 시.
        """
        service = self._service_name(provider_profile_id)
        try:
            keyring.delete_password(service, provider_kind)
            logger.info("API Key 삭제 완료: service=%s, username=%s", service, provider_kind)
            return True
        except keyring.errors.PasswordDeleteError:
            logger.warning("삭제할 API Key가 없음: service=%s, username=%s", service, provider_kind)
            return False
        except KeyringError as e:
            raise KeyStoreError(
                f"키링에서 API Key를 삭제할 수 없습니다: {e}"
            ) from e
