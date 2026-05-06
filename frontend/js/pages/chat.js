// frontend/js/pages/chat.js
// [v1.0.0] 채팅 페이지 — WebSocket 기반 실시간 대화 + 프롬프트 Inspector
//
// 세션 선택/생성, 메시지 표시, WebSocket 스트리밍, 프롬프트 스냅샷 Inspector를 처리한다.
// [v1.0.0] 우측 패널을 탭 방식(캐릭터 상태 | Inspector)으로 확장

let chatWebSocket = null;
let currentSessionId = null;

// [v1.0.0] 블록 종류별 색상 매핑 — 토큰 예산 바 세그먼트에 사용
const BLOCK_COLORS = {
  system_base: '#6366f1',
  ai_persona: '#f472b6',
  user_persona: '#60a5fa',
  worldbook: '#34d399',
  lorebook_match: '#fbbf24',
  chat_history: '#a78bfa',
  current_input: '#fb923c',
};

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
          <h4>📊 정보</h4>
          <button class="btn btn-sm" id="btn-toggle-panel" title="패널 접기">◀</button>
        </div>
        <div class="panel-tabs">
          <button class="panel-tab active" data-tab="state">🎭 상태</button>
          <button class="panel-tab" data-tab="inspector">🔍 Inspector</button>
        </div>
        <div class="panel-tab-body active" id="tab-state">
          <p class="text-secondary">세션을 선택하면 캐릭터 동적 상태가 표시됩니다.</p>
        </div>
        <div class="panel-tab-body" id="tab-inspector">
          <div class="inspector-empty">
            <div class="inspector-empty-icon">🔍</div>
            <p>AI 메시지의 [프롬프트] 버튼을 클릭하면<br>조립 결과가 표시됩니다.</p>
          </div>
        </div>
      </div>
    </div>
  `;

  // 세션 목록 로드
  await loadSessions();

  // 새 세션 버튼
  document.getElementById('btn-new-session').addEventListener('click', () => {
    showNewSessionModal();
  });

  // 메시지 전송
  document.getElementById('btn-send').addEventListener('click', sendMessage);
  document.getElementById('chat-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // 패널 접기/펼치기
  document.getElementById('btn-toggle-panel').addEventListener('click', () => {
    const panel = document.getElementById('dynamic-state-panel');
    panel.classList.toggle('collapsed');
    const btn = document.getElementById('btn-toggle-panel');
    btn.textContent = panel.classList.contains('collapsed') ? '▶' : '◀';
  });

  // [v1.0.0] 탭 전환
  document.querySelectorAll('.panel-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.panel-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.panel-tab-body').forEach(b => b.classList.remove('active'));
      tab.classList.add('active');
      const targetId = 'tab-' + tab.dataset.tab;
      document.getElementById(targetId)?.classList.add('active');
    });
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
      messagesEl.innerHTML = session.messages.map(m => renderMessageBubble(m)).join('');
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
 * [v1.0.0] 메시지 버블 HTML을 생성한다.
 * assistant 메시지에는 프롬프트 보기 버튼을 추가한다.
 */
function renderMessageBubble(m) {
  const roleLabel = m.role === 'user' ? '👤 나' : '🤖 AI';
  // [v1.0.0] assistant 메시지에 스냅샷이 있으면 프롬프트 보기 버튼 추가
  let promptBtn = '';
  if (m.role === 'assistant' && m.prompt_snapshot_json) {
    promptBtn = `<button class="btn-show-prompt" onclick="showPromptSnapshot('${m.id}')">🔍 프롬프트</button>`;
  }
  return `
    <div class="message message-${m.role}" data-msg-id="${m.id}">
      <div class="message-role">${roleLabel}</div>
      <div class="message-content">${escapeHtml(m.content)}</div>
      ${promptBtn}
    </div>
  `;
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
      // 스트리밍 완료 — 클래스 제거 + 프롬프트 버튼 추가
      const streamingMsg = messagesEl.querySelector('.message-streaming');
      if (streamingMsg) {
        streamingMsg.classList.remove('message-streaming');
        // [v1.0.0] done 메시지에 message_id가 포함되어 있으면 프롬프트 버튼 추가
        if (data.message_id) {
          streamingMsg.setAttribute('data-msg-id', data.message_id);
          const btn = document.createElement('button');
          btn.className = 'btn-show-prompt';
          btn.textContent = '🔍 프롬프트';
          btn.onclick = () => showPromptSnapshot(data.message_id);
          streamingMsg.appendChild(btn);
          // 자동으로 Inspector에 최신 스냅샷 표시
          showPromptSnapshot(data.message_id);
        }
      }
      // 동적 상태 갱신
      refreshDynamicState();
    } else if (data.type === 'error') {
      // 스트리밍 에러 — 에러 메시지 표시
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
  const body = document.getElementById('tab-state');
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

/**
 * [v1.0.0] 프롬프트 스냅샷을 Inspector 탭에 표시한다.
 * designs.md §9.9 프롬프트 Inspector 규격 준수.
 */
async function showPromptSnapshot(messageId) {
  // Inspector 탭으로 전환
  document.querySelectorAll('.panel-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.panel-tab-body').forEach(b => b.classList.remove('active'));
  document.querySelector('[data-tab="inspector"]')?.classList.add('active');
  document.getElementById('tab-inspector')?.classList.add('active');

  // 패널이 접혀있으면 펼침
  const panel = document.getElementById('dynamic-state-panel');
  if (panel?.classList.contains('collapsed')) {
    panel.classList.remove('collapsed');
    const btn = document.getElementById('btn-toggle-panel');
    if (btn) btn.textContent = '◀';
  }

  const inspectorBody = document.getElementById('tab-inspector');
  if (!inspectorBody) return;

  inspectorBody.innerHTML = '<p class="text-secondary" style="text-align:center;">스냅샷 로딩 중...</p>';

  try {
    const snapshot = await apiGet(`/sessions/${currentSessionId}/messages/${messageId}/snapshot`);
    inspectorBody.innerHTML = renderInspectorContent(snapshot);
  } catch (err) {
    inspectorBody.innerHTML = `
      <div class="inspector-empty">
        <div class="inspector-empty-icon">⚠️</div>
        <p>스냅샷 로드 실패<br><small>${escapeHtml(err.message)}</small></p>
      </div>
    `;
  }
}

/**
 * [v1.0.0] Inspector 콘텐츠 HTML을 생성한다.
 * 토큰 예산 바, 블록 구성, 로어 매칭, 잘림, 메타 정보를 표시한다.
 */
function renderInspectorContent(snapshot) {
  const totalTokens = snapshot.total_token_estimate || 0;
  const budgetTokens = snapshot.budget_tokens || 0;
  const blocks = snapshot.blocks || [];
  const loreIds = snapshot.matched_lore_entry_ids || [];
  const truncIds = snapshot.truncated_history_message_ids || [];
  const usage = budgetTokens > 0 ? Math.round((totalTokens / budgetTokens) * 100) : 0;

  // 토큰 예산 바 세그먼트 생성
  let segmentsHtml = '';
  let legendHtml = '';
  if (budgetTokens > 0) {
    for (const b of blocks) {
      const pct = (b.token_estimate / budgetTokens) * 100;
      const color = BLOCK_COLORS[b.kind] || '#94a3b8';
      segmentsHtml += `<div class="token-segment" style="width:${pct}%;background:${color};" title="${b.kind}: ${b.token_estimate}"></div>`;
    }
    // 범례 — 고유 kind만
    const seen = new Set();
    for (const b of blocks) {
      if (!seen.has(b.kind)) {
        seen.add(b.kind);
        const color = BLOCK_COLORS[b.kind] || '#94a3b8';
        legendHtml += `<span class="legend-item"><span class="legend-dot" style="background:${color};"></span>${b.kind}</span>`;
      }
    }
  }

  // 사용률에 따른 상태 색상
  let usageColor = 'var(--text-primary)';
  if (usage >= 95) usageColor = 'var(--accent-danger)';
  else if (usage >= 80) usageColor = '#f59e0b';

  let html = '';

  // ① 토큰 예산 바
  html += `
    <div class="token-budget-bar">
      <div class="token-budget-label">
        <span>토큰 사용</span>
        <span style="color:${usageColor};">${totalTokens.toLocaleString()} / ${budgetTokens.toLocaleString()} (${usage}%)</span>
      </div>
      <div class="token-budget-track">${segmentsHtml}</div>
      <div class="token-budget-legend">${legendHtml}</div>
    </div>
  `;

  // ② 블록 구성
  html += '<div class="inspector-section"><div class="inspector-section-title">📋 블록 구성</div>';
  for (const b of blocks) {
    html += `
      <div class="block-list-item">
        <span class="block-kind">${b.kind}</span>
        <span class="block-tokens">${b.token_estimate.toLocaleString()} 토큰</span>
      </div>
    `;
  }
  html += '</div>';

  // ③ 로어 매칭
  if (loreIds.length > 0) {
    html += `<div class="inspector-section"><div class="inspector-section-title">📖 로어 매칭 (${loreIds.length}건)</div>`;
    html += '<div class="id-chip-list">';
    for (const id of loreIds) {
      html += `<span class="id-chip lore" title="${escapeHtml(id)}">${escapeHtml(id)}</span>`;
    }
    html += '</div></div>';
  }

  // ④ 잘린 히스토리
  if (truncIds.length > 0) {
    html += `<div class="inspector-section"><div class="inspector-section-title">✂️ 잘린 히스토리 (${truncIds.length}건)</div>`;
    html += '<div class="id-chip-list">';
    for (const id of truncIds) {
      html += `<span class="id-chip truncated" title="${escapeHtml(id)}">${escapeHtml(id)}</span>`;
    }
    html += '</div></div>';
  }

  // ⑤ 메타 정보
  html += `
    <div class="inspector-section">
      <div class="inspector-section-title">ℹ️ 메타</div>
      <div class="inspector-meta">
        <div><strong>프로필:</strong> ${escapeHtml(snapshot.chat_profile_id || '—')}</div>
        <div><strong>모델:</strong> ${escapeHtml(snapshot.model_profile_id || '—')}</div>
        <div><strong>히스토리:</strong> ${snapshot.history_count || 0}건 (잘림 ${snapshot.truncated_count || 0}건)</div>
        <div><strong>생성:</strong> ${escapeHtml(snapshot.created_at_iso || '—')}</div>
      </div>
    </div>
  `;

  return html;
}

/**
 * 새 채팅 세션 생성 모달을 표시한다.
 * [v1.0.0] ChatProfile + UserPersona 선택 후 세션을 생성한다.
 */
async function showNewSessionModal() {
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
          <button type="button" class="btn" onclick="document.getElementById('session-modal').style.display='none'">취소</button>
        </div>
      </form>
    </div>
  `;

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
      modal.style.display = 'none';
      await loadSessions();
      await selectSession(session.id);
    } catch (err) {
      showToast(`세션 생성 실패: ${err.message}`, 'error', 5000);
    }
  });
}
