// frontend/js/pages/prompt_order.js
// [v1.0.0] 프롬프트 순서 편집 페이지
//
// ChatProfile의 prompt_order_json을 시각적으로 편집한다.
// 기본 프롬프트 블록 순서를 위/아래 버튼으로 조정할 수 있다.

import { apiGet, apiPost, apiPut, apiDelete, escapeHtml, showToast } from '../api.js';

// 기본 프롬프트 블록 목록
const DEFAULT_PROMPT_BLOCKS = [
  { key: 'system_base', label: '시스템 베이스', icon: '⚙️' },
  { key: 'ai_persona', label: 'AI 페르소나', icon: '🤖' },
  { key: 'user_persona', label: '사용자 페르소나', icon: '👤' },
  { key: 'worldbook', label: '월드북', icon: '🌍' },
  { key: 'lorebook', label: '로어북', icon: '📖' },
  { key: 'dynamic_state', label: '동적 상태', icon: '🎭' },
  { key: 'chat_history', label: '대화 히스토리', icon: '💬' },
  { key: 'user_message', label: '사용자 메시지', icon: '✉️' },
];

/**
 * 프롬프트 순서 페이지를 렌더링한다.
 */
export async function renderPromptOrder(container) {
  container.innerHTML = `
    <div class="card">
      <h2 class="card-title">📝 프롬프트 순서</h2>
      <p class="text-secondary" style="margin-bottom: 1rem;">
        채팅 프로필의 프롬프트 블록 순서를 설정합니다. 위/아래 버튼으로 순서를 변경하세요.
      </p>
      <div class="form-group">
        <label>채팅 프로필 선택</label>
        <select id="po-profile-select" class="input">
          <option value="">선택하세요</option>
        </select>
      </div>
      <div id="po-blocks" style="margin-top: 1rem;"></div>
      <div id="po-actions" style="display: none; margin-top: 1rem;">
        <button class="btn btn-primary" id="btn-save-order">순서 저장</button>
      </div>
    </div>
  `;

  // ChatProfile 목록 로드
  try {
    const profiles = await apiGet('/chat-profiles');
    const select = document.getElementById('po-profile-select');
    profiles.forEach(p => {
      const opt = document.createElement('option');
      opt.value = p.id;
      opt.textContent = p.name;
      select.appendChild(opt);
    });
  } catch { /* 무시 */ }

  document.getElementById('po-profile-select').addEventListener('change', async (e) => {
    const profileId = e.target.value;
    if (!profileId) {
      document.getElementById('po-blocks').innerHTML = '';
      document.getElementById('po-actions').style.display = 'none';
      return;
    }
    await loadPromptOrder(profileId);
  });

  // [v1.1.1] 이벤트 위임 — data-action 기반 핸들러
  container.addEventListener('click', (e) => {
    const el = e.target.closest('[data-action]');
    if (!el) return;
    e.stopPropagation();
    const actionId = el.dataset.id;
    switch (el.dataset.action) {
      case 'moveBlock': moveBlock(parseInt(el.dataset.index), parseInt(el.dataset.dir)); break;
    }
  });
}

// 현재 블록 순서 (상태)
let currentBlockOrder = [];
let currentProfileId = '';

async function loadPromptOrder(profileId) {
  currentProfileId = profileId;
  const blocksEl = document.getElementById('po-blocks');
  const actionsEl = document.getElementById('po-actions');

  try {
    const profiles = await apiGet('/chat-profiles');
    const profile = profiles.find(p => p.id === profileId);
    if (!profile) return;

    // 저장된 순서가 있으면 사용, 없으면 기본 순서
    let savedOrder = [];
    try { savedOrder = JSON.parse(profile.prompt_order_json); } catch { /* 무시 */ }

    if (savedOrder.length > 0) {
      // 저장된 순서 기반으로 블록 재배열
      currentBlockOrder = savedOrder.map(key =>
        DEFAULT_PROMPT_BLOCKS.find(b => b.key === key) || { key, label: key, icon: '📦' }
      );
      // 누락된 블록 추가
      DEFAULT_PROMPT_BLOCKS.forEach(b => {
        if (!currentBlockOrder.find(o => o.key === b.key)) {
          currentBlockOrder.push(b);
        }
      });
    } else {
      currentBlockOrder = [...DEFAULT_PROMPT_BLOCKS];
    }

    renderBlocks();
    actionsEl.style.display = 'block';

    // 저장 버튼 이벤트 (중복 방지)
    const saveBtn = document.getElementById('btn-save-order');
    saveBtn.replaceWith(saveBtn.cloneNode(true));
    document.getElementById('btn-save-order').addEventListener('click', savePromptOrder);
  } catch (err) {
    showToast(`로드 실패: ${err.message}`, 'error', 5000);
    blocksEl.innerHTML = '<p class="session-empty">데이터를 불러올 수 없습니다</p>';
  }
}

function renderBlocks() {
  const blocksEl = document.getElementById('po-blocks');
  blocksEl.innerHTML = currentBlockOrder.map((block, i) => `
    <div class="prompt-block-item">
      <span class="block-number">${i + 1}</span>
      <span class="block-icon">${block.icon}</span>
      <span class="block-label">${block.label}</span>
      <span class="block-key text-secondary">(${block.key})</span>
      <div class="block-controls">
        <button class="btn btn-sm" data-action="moveBlock" data-index="${i}" data-dir="-1" ${i === 0 ? 'disabled' : ''}>▲</button>
        <button class="btn btn-sm" data-action="moveBlock" data-index="${i}" data-dir="1" ${i === currentBlockOrder.length - 1 ? 'disabled' : ''}>▼</button>
      </div>
    </div>
  `).join('');
}

function moveBlock(index, direction) {
  const newIndex = index + direction;
  if (newIndex < 0 || newIndex >= currentBlockOrder.length) return;
  [currentBlockOrder[index], currentBlockOrder[newIndex]] =
    [currentBlockOrder[newIndex], currentBlockOrder[index]];
  renderBlocks();
}

async function savePromptOrder() {
  if (!currentProfileId) return;
  const orderJson = JSON.stringify(currentBlockOrder.map(b => b.key));
  try {
    // ChatProfile의 prompt_order_json만 업데이트
    const profiles = await apiGet('/chat-profiles');
    const profile = profiles.find(p => p.id === currentProfileId);
    if (!profile) return;

    await apiPut(`/chat-profiles/${currentProfileId}`, {
      name: profile.name,
      model_profile_id: profile.model_profile_id,
      ai_persona_ids: profile.ai_persona_ids,
      lorebook_ids: profile.lorebook_ids,
      worldbook_ids: profile.worldbook_ids,
      prompt_order_json: orderJson,
      system_base: profile.system_base,
    });
    showToast('프롬프트 순서가 저장되었습니다.', 'success');
  } catch (err) {
    showToast(`저장 실패: ${err.message}`, 'error', 5000);
  }
}
