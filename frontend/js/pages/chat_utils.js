// frontend/js/pages/chat_utils.js
// [v1.1.1] 채팅 공용 유틸리티 — 순환 import 방지용 분리 모듈
//
// chat_session.js와 chat_composer.js 모두에서 사용하는 공용 함수를
// 이 모듈에 분리하여 순환 의존성(Circular Dependency)을 방지한다.

import { escapeHtml } from '../api.js';

/**
 * [v1.0.0] 메시지 버블 HTML을 생성한다.
 * assistant 메시지에는 프롬프트 보기 버튼을 추가한다.
 * [v1.1.1] data-prompt-msg-id 이벤트 위임 방식
 */
export function renderMessageBubble(m) {
  const roleLabel = m.role === 'user' ? '👤 나' : '🤖 AI';
  // [v1.0.0] assistant 메시지에 스냅샷이 있으면 프롬프트 보기 버튼 추가
  let promptBtn = '';
  if (m.role === 'assistant' && m.prompt_snapshot_json) {
    promptBtn = `<button class="btn-show-prompt" data-prompt-msg-id="${m.id}">🔍 프롬프트</button>`;
  }
  return `
    <div class="message message-${m.role}" data-msg-id="${m.id}">
      <div class="message-role">${roleLabel}</div>
      <div class="message-content">${escapeHtml(m.content)}</div>
      ${promptBtn}
    </div>
  `;
}
