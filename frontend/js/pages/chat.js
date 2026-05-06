// frontend/js/pages/chat.js
// [v1.0.0] 채팅 페이지 오케스트레이터 — DD-11 모듈 분리
//
// 레이아웃 렌더링 + 이벤트 바인딩만 담당한다.
// 실제 비즈니스 로직은 하위 모듈에 위임:
//   - chat_session.js: 세션 CRUD + 모달
//   - chat_composer.js: WebSocket + 메시지 전송 + Inspector

// 전역 공유 상태 — chat_session.js, chat_composer.js에서 참조
let currentSessionId = null;

/**
 * 채팅 페이지를 렌더링한다.
 * 레이아웃 HTML을 생성하고, 이벤트 핸들러를 바인딩한다.
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

  // 세션 목록 로드 (chat_session.js)
  await loadSessions();

  // --- 이벤트 바인딩 ---

  // 새 세션 버튼 (chat_session.js)
  document.getElementById('btn-new-session').addEventListener('click', () => {
    showNewSessionModal();
  });

  // 메시지 전송 (chat_composer.js)
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
