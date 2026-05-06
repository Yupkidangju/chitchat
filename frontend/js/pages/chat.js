// frontend/js/pages/chat.js
// [v1.0.0] 채팅 페이지 — WebSocket 기반 실시간 대화
//
// 세션 선택/생성, 메시지 표시, WebSocket 스트리밍을 처리한다.

let chatWebSocket = null;
let currentSessionId = null;

/**
 * 채팅 페이지를 렌더링한다.
 * @param {HTMLElement} container
 */
async function renderChat(container) {
  container.innerHTML = `
    <div class="chat-layout">
      <div class="chat-sidebar">
        <div class="chat-sidebar-header">
          <h3>💬 세션 목록</h3>
          <button class="btn btn-sm btn-primary" id="btn-new-session">+</button>
        </div>
        <div id="session-list" class="session-list"></div>
      </div>
      <div class="chat-main">
        <div class="chat-messages" id="chat-messages">
          <div class="chat-empty">
            <div style="font-size: 3rem;">💬</div>
            <p>세션을 선택하거나 새로 생성하세요.</p>
          </div>
        </div>
        <div class="chat-input-area" id="chat-input-area" style="display: none;">
          <div class="chat-input-wrapper">
            <textarea id="chat-input" class="input chat-textarea"
              placeholder="메시지를 입력하세요..." rows="1"></textarea>
            <button class="btn btn-primary" id="btn-send">전송</button>
          </div>
        </div>
      </div>
      <div class="dynamic-state-panel" id="dynamic-state-panel">
        <div class="panel-header">
          <h4>🎭 캐릭터 상태</h4>
          <button class="btn btn-sm" id="btn-toggle-panel" title="패널 접기">◀</button>
        </div>
        <div class="panel-body" id="dynamic-state-body">
          <p class="text-secondary">세션을 선택하면 캐릭터 동적 상태가 표시됩니다.</p>
        </div>
      </div>
    </div>
  `;

  // 세션 목록 로드
  await loadSessions();

  // 새 세션 버튼
  document.getElementById('btn-new-session').addEventListener('click', () => {
    // TODO: 세션 생성 폼
    alert('채팅 세션 생성은 ChatProfile/UserPersona 선택 후 가능합니다.\n(Phase 6에서 구현 예정)');
  });

  // 메시지 전송
  document.getElementById('btn-send').addEventListener('click', sendMessage);
  document.getElementById('chat-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // 동적 상태 패널 토글
  document.getElementById('btn-toggle-panel').addEventListener('click', () => {
    const panel = document.getElementById('dynamic-state-panel');
    panel.classList.toggle('collapsed');
    const btn = document.getElementById('btn-toggle-panel');
    btn.textContent = panel.classList.contains('collapsed') ? '▶' : '◀';
  });
}

/**
 * 세션 목록을 로드한다.
 */
async function loadSessions() {
  const listEl = document.getElementById('session-list');
  try {
    const sessions = await apiGet('/sessions');
    if (sessions.length === 0) {
      listEl.innerHTML = `<p class="session-empty">세션이 없습니다</p>`;
      return;
    }
    listEl.innerHTML = sessions.map(s => `
      <div class="session-item ${s.id === currentSessionId ? 'active' : ''}"
           onclick="selectSession('${s.id}')">
        <div class="session-title">${escapeHtml(s.title)}</div>
        <div class="session-status">${s.status}</div>
      </div>
    `).join('');
  } catch (err) {
    listEl.innerHTML = `<p style="color: var(--danger);">${err.message}</p>`;
  }
}

/**
 * 세션을 선택하여 메시지를 로드한다.
 */
async function selectSession(sessionId) {
  currentSessionId = sessionId;
  document.getElementById('chat-input-area').style.display = 'flex';

  const messagesEl = document.getElementById('chat-messages');
  messagesEl.innerHTML = '<p style="color: var(--text-secondary); text-align: center;">메시지 로딩 중...</p>';

  try {
    const session = await apiGet(`/sessions/${sessionId}`);
    if (session.messages && session.messages.length > 0) {
      messagesEl.innerHTML = session.messages.map(m => `
        <div class="message message-${m.role}">
          <div class="message-role">${m.role === 'user' ? '👤 나' : '🤖 AI'}</div>
          <div class="message-content">${escapeHtml(m.content)}</div>
        </div>
      `).join('');
      messagesEl.scrollTop = messagesEl.scrollHeight;
    } else {
      messagesEl.innerHTML = '<div class="chat-empty"><p>아직 메시지가 없습니다. 대화를 시작하세요!</p></div>';
    }
  } catch (err) {
    messagesEl.innerHTML = `<div class="chat-empty"><p>세션 로드 실패: ${err.message}</p></div>`;
  }

  // WebSocket 연결
  connectWebSocket(sessionId);

  // 세션 목록 갱신 (활성 표시)
  await loadSessions();
}

/**
 * WebSocket으로 채팅 서버에 연결한다.
 */
function connectWebSocket(sessionId) {
  if (chatWebSocket) {
    chatWebSocket.close();
  }

  const wsUrl = `ws://${window.location.host}/api/ws/chat/${sessionId}`;
  chatWebSocket = new WebSocket(wsUrl);

  chatWebSocket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    const messagesEl = document.getElementById('chat-messages');

    if (data.type === 'chunk') {
      // 스트리밍 청크 — AI 메시지에 추가
      let aiMsg = messagesEl.querySelector('.message-streaming');
      if (!aiMsg) {
        aiMsg = document.createElement('div');
        aiMsg.className = 'message message-assistant message-streaming';
        aiMsg.innerHTML = '<div class="message-role">🤖 AI</div><div class="message-content"></div>';
        messagesEl.appendChild(aiMsg);
      }
      aiMsg.querySelector('.message-content').textContent += data.content;
      messagesEl.scrollTop = messagesEl.scrollHeight;
    } else if (data.type === 'done') {
      // 스트리밍 완료 — 클래스 제거
      const streamingMsg = messagesEl.querySelector('.message-streaming');
      if (streamingMsg) {
        streamingMsg.classList.remove('message-streaming');
      }
      // [v1.0.0] 동적 상태 갱신
      refreshDynamicState();
    } else if (data.type === 'error') {
      // [v1.0.0] 스트리밍 에러 — 에러 메시지 표시
      const streamingMsg = messagesEl.querySelector('.message-streaming');
      if (streamingMsg) {
        streamingMsg.classList.remove('message-streaming');
        streamingMsg.classList.add('message-error');
        streamingMsg.querySelector('.message-content').textContent = `⚠️ ${data.content}`;
      } else {
        const errMsg = document.createElement('div');
        errMsg.className = 'message message-assistant message-error';
        errMsg.innerHTML = `<div class="message-role">⚠️ 오류</div><div class="message-content">${escapeHtml(data.content)}</div>`;
        messagesEl.appendChild(errMsg);
      }
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }
  };

  chatWebSocket.onerror = () => {
    console.error('WebSocket 연결 오류');
  };
}

/**
 * 메시지를 전송한다.
 */
function sendMessage() {
  const input = document.getElementById('chat-input');
  const text = input.value.trim();
  if (!text || !chatWebSocket || chatWebSocket.readyState !== WebSocket.OPEN) return;

  // 사용자 메시지 표시
  const messagesEl = document.getElementById('chat-messages');
  const emptyMsg = messagesEl.querySelector('.chat-empty');
  if (emptyMsg) emptyMsg.remove();

  const userMsg = document.createElement('div');
  userMsg.className = 'message message-user';
  userMsg.innerHTML = `<div class="message-role">👤 나</div><div class="message-content">${escapeHtml(text)}</div>`;
  messagesEl.appendChild(userMsg);
  messagesEl.scrollTop = messagesEl.scrollHeight;

  // WebSocket으로 전송
  chatWebSocket.send(text);
  input.value = '';
}

/**
 * 현재 세션의 동적 상태를 새로고침한다.
 */
async function refreshDynamicState() {
  if (!currentSessionId) return;
  const body = document.getElementById('dynamic-state-body');
  if (!body) return;

  try {
    const state = await apiGet(`/sessions/${currentSessionId}/dynamic-state`);
    if (!state.exists) {
      body.innerHTML = '<p class="text-secondary">동적 상태가 아직 생성되지 않았습니다.</p>';
      return;
    }

    const r = state.relationship;
    const bars = [
      { label: '신뢰', value: r.trust, color: '#4ade80' },
      { label: '친밀도', value: r.familiarity, color: '#60a5fa' },
      { label: '감정 의존', value: r.emotional_reliance, color: '#f472b6' },
      { label: '침묵 편안함', value: r.comfort_with_silence, color: '#a78bfa' },
      { label: '다가감', value: r.willingness_to_initiate, color: '#fbbf24' },
      { label: '거절 공포', value: r.fear_of_rejection, color: '#f87171' },
      { label: '경계 민감', value: r.boundary_sensitivity, color: '#fb923c' },
      { label: '회복력', value: r.repair_ability, color: '#34d399' },
    ];

    let html = `
      <div class="state-meta">
        <span class="badge">턴 ${state.turn_count}</span>
        <span class="badge">${state.emotional_state}</span>
      </div>
      <div class="relationship-bars">
    `;

    for (const bar of bars) {
      html += `
        <div class="rel-bar">
          <span class="rel-label">${bar.label}</span>
          <div class="rel-track">
            <div class="rel-fill" style="width: ${bar.value}%; background: ${bar.color};"></div>
          </div>
          <span class="rel-value">${bar.value}</span>
        </div>
      `;
    }
    html += '</div>';

    // 기억 목록
    if (state.memories.length > 0) {
      html += '<div class="state-section"><h5>📝 기억</h5>';
      for (const m of state.memories) {
        html += `<div class="memory-item"><span class="memory-trigger">[${m.trigger}]</span> ${escapeHtml(m.content)}</div>`;
      }
      html += '</div>';
    }

    body.innerHTML = html;
  } catch {
    body.innerHTML = '<p class="text-secondary">동적 상태 로드 실패</p>';
  }
}
