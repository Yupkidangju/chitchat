// frontend/js/pages/chat_composer.js
// [v1.0.0] 채팅 메시지 전송 + 스트리밍 + Inspector 모듈 — DD-11 모듈 분리
//
// WebSocket 연결, 메시지 전송/수신, 동적 상태 갱신,
// 프롬프트 Inspector 렌더링을 담당한다.
// chat_session.js의 selectSession()에서 connectWebSocket()을 호출한다.

// WebSocket 인스턴스 — 모듈 스코프
let chatWebSocket = null;

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
 * WebSocket으로 채팅 서버에 연결한다.
 * 기존 연결이 있으면 닫고 새로 연결한다.
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
 * WebSocket이 열려있지 않으면 무시한다.
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
 * 전역 currentSessionId를 참조한다.
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
