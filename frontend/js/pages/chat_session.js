// frontend/js/pages/chat_session.js
// [v1.1.1] 채팅 세션 관리 모듈 — ES6 모듈 전환
//
// 세션 목록 로드, 세션 선택, 세션 생성 모달을 담당한다.
// chat.js(오케스트레이터)에서 호출하며, chat_composer.js의 connectWebSocket을 사용한다.
// [v1.1.1] 전역 변수 제거 → store.js로 상태 관리 이전

import { apiGet, apiPost, apiPut, apiDelete, escapeHtml, showToast } from '../api.js';
import { getState, setState } from '../store.js';
import { renderMessageBubble } from './chat_utils.js'; // 사용 및 re-export 겸용

// [v1.1.1] 순환 import 방지: connectWebSocket은 동적 import로 가져온다
let _connectWebSocket = null;
async function getConnectWebSocket() {
  if (!_connectWebSocket) {
    const mod = await import('./chat_composer.js');
    _connectWebSocket = mod.connectWebSocket;
  }
  return _connectWebSocket;
}

/**
 * 세션 목록을 API에서 가져와 #session-list에 렌더링한다.
 * [v1.1.1] onclick 인라인 → data-session-id + 이벤트 위임으로 전환
 */
export async function loadSessions() {
  const listEl = document.getElementById('session-list');
  try {
    const sessions = await apiGet('/sessions');
    if (sessions.length === 0) {
      listEl.innerHTML = `<p class="session-empty">세션이 없습니다</p>`;
      return;
    }
    const currentId = getState('currentSessionId');
    listEl.innerHTML = sessions.map(s => `
      <div class="session-item ${s.id === currentId ? 'active' : ''}"
           data-session-id="${s.id}">
        <div class="session-title">${escapeHtml(s.title)}</div>
        <div class="session-status">${s.status}</div>
      </div>
    `).join('');

    // [v1.1.1] 이벤트 위임 — 세션 클릭 핸들러
    listEl.querySelectorAll('[data-session-id]').forEach(el => {
      el.addEventListener('click', () => {
        selectSession(el.dataset.sessionId);
      });
    });
  } catch (err) {
    showToast(`세션 목록 로딩 실패: ${err.message}`, 'error', 5000);
    listEl.innerHTML = `<p class="session-empty">세션을 불러올 수 없습니다</p>`;
  }
}

/**
 * 세션을 선택하여 메시지를 로드하고 WebSocket을 연결한다.
 * [v1.1.1] currentSessionId → setState('currentSessionId', ...)
 */
export async function selectSession(sessionId) {
  setState('currentSessionId', sessionId);
  document.getElementById('chat-input-area').style.display = 'flex';

  const messagesEl = document.getElementById('chat-messages');
  messagesEl.innerHTML = '<p style="color: var(--text-secondary); text-align: center;">메시지 로딩 중...</p>';

  try {
    const session = await apiGet(`/sessions/${sessionId}`);
    if (session.messages && session.messages.length > 0) {
      messagesEl.innerHTML = session.messages.map(m => renderMessageBubble(m)).join('');
      messagesEl.scrollTop = messagesEl.scrollHeight;
    } else {
      messagesEl.innerHTML = '<div class="chat-empty"><p>아직 메시지가 없습니다. 대화를 시작하세요!</p></div>';
    }
  } catch (err) {
    showToast(`세션 로드 실패: ${err.message}`, 'error', 5000);
    messagesEl.innerHTML = '<div class="chat-empty"><p>세션을 불러올 수 없습니다</p></div>';
  }

  // WebSocket 연결 (chat_composer.js — 동적 import로 순환 방지)
  const connectWs = await getConnectWebSocket();
  connectWs(sessionId);

  // 세션 목록 갱신 (활성 표시)
  await loadSessions();
}

/**
 * [v1.0.0] 메시지 버블 HTML을 생성한다.
 * assistant 메시지에는 프롬프트 보기 버튼을 추가한다.
 * [v1.1.1] onclick 인라인 → data-prompt-msg-id + 이벤트 위임으로 전환
 */
// [v1.1.1] renderMessageBubble → chat_utils.js로 이동 (순환 import 방지)
// chat.js 및 chat_composer.js에서 chat_utils.js를 직접 import

/**
 * 새 채팅 세션 생성 모달을 표시한다.
 * [v1.0.0] ChatProfile + UserPersona 선택 후 세션을 생성한다.
 * [v1.1.1] onclick 인라인 → addEventListener로 전환
 */
export async function showNewSessionModal() {
  // 기존 모달 제거 후 새로 생성 (body 직속, 최상위 레이어)
  let modal = document.getElementById('session-modal');
  if (modal) modal.remove();
  modal = document.createElement('div');
  modal.id = 'session-modal';
  modal.className = 'modal';
  modal.style.cssText = 'display:flex; position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.6); z-index:9999; justify-content:center; align-items:center;';
  document.body.appendChild(modal);

  // 의존 데이터 로드
  let chatProfiles = [];
  let userPersonas = [];
  try {
    [chatProfiles, userPersonas] = await Promise.all([
      apiGet('/chat-profiles'),
      apiGet('/user-personas'),
    ]);
  } catch { /* 빈 배열 유지 */ }

  const cpOptions = chatProfiles.map(p =>
    `<option value="${p.id}">${escapeHtml(p.name)}</option>`
  ).join('');

  // UserPersona가 없으면 자동 생성 옵션 제공
  let upOptions = userPersonas.map(p =>
    `<option value="${p.id}">${escapeHtml(p.name)}</option>`
  ).join('');
  const hasUserPersonas = userPersonas.length > 0;

  modal.innerHTML = `
    <div class="modal-content card">
      <h3 class="card-title">💬 새 채팅 세션</h3>
      <form id="new-session-form">
        <div class="form-group">
          <label>세션 제목</label>
          <input type="text" id="ns-title" class="input" placeholder="예: 유리와의 첫 대화" required>
        </div>
        <div class="form-group">
          <label>채팅 프로필</label>
          <select id="ns-chat-profile" class="input" required>
            <option value="">선택하세요</option>
            ${cpOptions}
          </select>
          ${chatProfiles.length === 0 ? '<p class="text-secondary" style="font-size: 0.8rem; margin-top: 0.3rem;">⚠️ 먼저 채팅 프로필을 생성하세요.</p>' : ''}
        </div>
        <div class="form-group">
          <label>사용자 페르소나</label>
          ${hasUserPersonas ? `
            <select id="ns-user-persona" class="input" required>
              <option value="">선택하세요</option>
              ${upOptions}
            </select>
          ` : `
            <p class="text-secondary" style="font-size: 0.8rem;">사용자 페르소나가 없습니다. 기본 페르소나를 자동으로 생성합니다.</p>
            <input type="hidden" id="ns-user-persona" value="__auto_create__">
          `}
        </div>
        <div class="form-actions">
          <button type="submit" class="btn btn-primary" ${chatProfiles.length === 0 ? 'disabled' : ''}>생성</button>
          <button type="button" class="btn" id="btn-cancel-session">취소</button>
        </div>
      </form>
    </div>
  `;

  // 취소 버튼 이벤트 (인라인 onclick 대체)
  document.getElementById('btn-cancel-session').addEventListener('click', () => {
    document.getElementById('session-modal')?.remove();
  });

  document.getElementById('new-session-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const title = document.getElementById('ns-title').value;
    const chatProfileId = document.getElementById('ns-chat-profile').value;
    let userPersonaId = document.getElementById('ns-user-persona').value;

    if (!chatProfileId) {
      showToast('채팅 프로필을 선택해주세요.', 'warning');
      return;
    }

    // 자동 UserPersona 생성
    if (userPersonaId === '__auto_create__' || !userPersonaId) {
      try {
        const up = await apiPost('/user-personas', {
          name: '기본 사용자',
          description: '기본 사용자 페르소나',
        });
        userPersonaId = up.id;
      } catch (err) {
        showToast(`사용자 페르소나 생성 실패: ${err.message}`, 'error', 5000);
        return;
      }
    }

    try {
      const session = await apiPost('/sessions', {
        title,
        chat_profile_id: chatProfileId,
        user_persona_id: userPersonaId,
      });
      modal.remove();
      await loadSessions();
      await selectSession(session.id);
    } catch (err) {
      showToast(`세션 생성 실패: ${err.message}`, 'error', 5000);
    }
  });
}
