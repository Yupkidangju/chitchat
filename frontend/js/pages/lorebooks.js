// frontend/js/pages/lorebooks.js
// [v1.1.0] 로어북 관리 페이지
//
// Lorebook CRUD + LoreEntry 관리 + AI Vibe Fill 생성 + 수동 편집 UI.
// [v1.1.0 변경사항]
// - AI 생성 모달: 캐릭터 복수 선택 + 바이브 입력 + Provider/Model 선택 → 엔트리 자동 생성
// - 엔트리 편집 모달: 제목, 키워드, 내용, 우선순위 필드 수정

import { apiGet, apiPost, apiPut, apiDelete, escapeHtml, showToast } from '../api.js';

/**
 * 로어북 페이지를 렌더링한다.
 */
export async function renderLorebooks(container) {
  container.innerHTML = `
    <div class="card">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
        <h2 class="card-title" style="margin: 0;">📖 로어북</h2>
        <button class="btn btn-primary" id="btn-add-lorebook">+ 새 로어북</button>
      </div>
      <div id="lorebook-list">
        <p style="color: var(--text-secondary);">로딩 중...</p>
      </div>
    </div>
    <div id="lb-detail" class="card" style="display: none; margin-top: 1rem;"></div>
    <div id="lb-modal" class="modal" style="display: none;"></div>
  `;

  await loadLorebooks();

  document.getElementById('btn-add-lorebook').addEventListener('click', () => {
    showLorebookCreateModal();
  });

  // [v1.1.1] 이벤트 위임 — data-action 기반 핸들러
  container.addEventListener('click', (e) => {
    const el = e.target.closest('[data-action]');
    if (!el) return;
    e.stopPropagation();
    const actionId = el.dataset.id;
    switch (el.dataset.action) {
      case 'showLoreEntries': showLoreEntries(actionId, el.dataset.extra1); break;
      case 'deleteLorebook': deleteLorebook(actionId); break;
      case 'showLoreVibeFillModal': showLoreVibeFillModal(actionId, el.dataset.extra1); break;
      case 'showLoreEntryForm': showLoreEntryForm(actionId); break;
      case 'deleteLoreEntry': deleteLoreEntry(actionId, el.dataset.extra1, el.dataset.extra2); break;
      case 'showLoreEntryEditModal': { apiGet(`/lorebooks/entries/${actionId}`).then(e => showLoreEntryEditModal(e)).catch(() => {}) }; break;
      case 'closeModal': {
        const mid = el.dataset.modalId;
        if (mid) { const modal = document.getElementById(mid); if (modal) modal.style.display = 'none'; }
        break;
      }
    }
  });
}

async function loadLorebooks() {
  const listEl = document.getElementById('lorebook-list');
  try {
    const books = await apiGet('/lorebooks');
    if (books.length === 0) {
      listEl.innerHTML = '<div style="text-align: center; padding: 2rem; color: var(--text-secondary);"><p>로어북이 없습니다</p></div>';
      return;
    }
    listEl.innerHTML = books.map(b => `
      <div class="profile-card" data-id="${b.id}">
        <div class="profile-info" style="cursor: pointer;" data-action="showLoreEntries" data-id="${b.id}" data-extra1="${escapeHtml(b.name)}">
          <strong>${escapeHtml(b.name)}</strong>
          <span class="text-secondary" style="font-size: 0.8rem;">${escapeHtml(b.description || '설명 없음')}</span>
        </div>
        <div class="profile-actions">
          <button class="btn btn-sm btn-danger" data-action="deleteLorebook" data-id="${b.id}">삭제</button>
        </div>
      </div>
    `).join('');
  } catch (err) {
    showToast(`로드 실패: ${err.message}`, 'error', 5000);
    listEl.innerHTML = '<p class="session-empty">데이터를 불러올 수 없습니다</p>';
  }
}

function showLorebookCreateModal() {
  const modal = document.getElementById('lb-modal');
  modal.style.display = 'flex';
  modal.innerHTML = `
    <div class="modal-content card">
      <h3 class="card-title">새 로어북</h3>
      <form id="lb-create-form">
        <div class="form-group">
          <label>이름</label>
          <input type="text" id="lb-name" class="input" required>
        </div>
        <div class="form-group">
          <label>설명</label>
          <textarea id="lb-desc" class="input" rows="2"></textarea>
        </div>
        <div class="form-actions">
          <button type="submit" class="btn btn-primary">생성</button>
          <button type="button" class="btn" data-action="closeModal" data-modal-id="lb-modal">취소</button>
        </div>
      </form>
    </div>
  `;
  document.getElementById('lb-create-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await apiPost('/lorebooks', {
        name: document.getElementById('lb-name').value,
        description: document.getElementById('lb-desc').value,
      });
      modal.style.display = 'none';
      await loadLorebooks();
    } catch (err) { showToast(`오류: ${err.message}`, 'error', 5000); }
  });
}

async function deleteLorebook(id) {
  if (!confirm('이 로어북을 삭제하시겠습니까?')) return;
  try {
    await apiDelete(`/lorebooks/${id}`);
    showToast('로어북이 삭제되었습니다.', 'success');
    await loadLorebooks();
    document.getElementById('lb-detail').style.display = 'none';
  } catch (err) { showToast(`삭제 실패: ${err.message}`, 'error', 5000); }
}

/**
 * [v1.1.0] 로어북의 LoreEntry 목록을 표시한다.
 * AI 생성 버튼과 엔트리별 편집/삭제 버튼을 포함한다.
 */
async function showLoreEntries(lorebookId, bookName) {
  const detail = document.getElementById('lb-detail');
  detail.style.display = 'block';
  detail.innerHTML = '<p style="color: var(--text-secondary);">로딩 중...</p>';

  try {
    const entries = await apiGet(`/lorebooks/${lorebookId}/entries`);
    let html = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
        <h3 class="card-title" style="margin: 0;">📝 ${escapeHtml(bookName)} 항목</h3>
        <div style="display: flex; gap: 0.5rem;">
          <button class="btn btn-primary btn-sm" data-action="showLoreVibeFillModal" data-id="${lorebookId}" data-extra1="${escapeHtml(bookName)}">✨ AI 생성</button>
          <button class="btn btn-sm" data-action="showLoreEntryForm" data-id="${lorebookId}">+ 수동 추가</button>
        </div>
      </div>
    `;

    if (entries.length === 0) {
      html += '<p class="text-secondary">항목이 없습니다. "✨ AI 생성"으로 캐릭터 기반 엔트리를 자동 생성하세요.</p>';
    } else {
      html += entries.map(e => `
        <div class="entry-item">
          <div><strong>${escapeHtml(e.title)}</strong> <span class="text-secondary">[${e.activation_keys.join(', ')}]</span></div>
          <div class="text-secondary" style="font-size: 0.8rem; margin: 0.25rem 0;">${escapeHtml(e.content.substring(0, 120))}${e.content.length > 120 ? '...' : ''}</div>
          <div style="display: flex; gap: 0.5rem; margin-top: 0.25rem;">
            <button class="btn btn-sm" data-action="showLoreEntryEditModal" data-id="${e.id}">편집</button>
            <button class="btn btn-sm btn-danger" data-action="deleteLoreEntry" data-id="${e.id}" data-extra1="${lorebookId}" data-extra2="${escapeHtml(bookName)}">삭제</button>
          </div>
        </div>
      `).join('');
    }
    detail.innerHTML = html;
  } catch (err) {
    showToast(`로드 실패: ${err.message}`, 'error', 5000);
    detail.innerHTML = '<p class="session-empty">데이터를 불러올 수 없습니다</p>';
  }
}

// ━━━ 수동 엔트리 추가 모달 ━━━

function showLoreEntryForm(lorebookId) {
  const modal = document.getElementById('lb-modal');
  modal.style.display = 'flex';
  modal.innerHTML = `
    <div class="modal-content card">
      <h3 class="card-title">새 로어 항목</h3>
      <form id="le-form">
        <div class="form-group"><label>제목</label><input type="text" id="le-title" class="input" required></div>
        <div class="form-group"><label>활성화 키워드 (쉼표 구분)</label><input type="text" id="le-keys" class="input" placeholder="검, 마법, 성문"></div>
        <div class="form-group"><label>내용</label><textarea id="le-content" class="input" rows="4"></textarea></div>
        <div class="form-group"><label>우선순위</label><input type="number" id="le-priority" class="input" value="100" min="0" max="1000"></div>
        <div class="form-actions">
          <button type="submit" class="btn btn-primary">추가</button>
          <button type="button" class="btn" data-action="closeModal" data-modal-id="lb-modal">취소</button>
        </div>
      </form>
    </div>
  `;
  document.getElementById('le-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const keys = document.getElementById('le-keys').value.split(',').map(k => k.trim()).filter(Boolean);
    try {
      await apiPost(`/lorebooks/${lorebookId}/entries`, {
        title: document.getElementById('le-title').value,
        activation_keys: keys,
        content: document.getElementById('le-content').value,
        priority: parseInt(document.getElementById('le-priority').value),
        enabled: true,
      });
      modal.style.display = 'none';
      await showLoreEntries(lorebookId, '로어북');
    } catch (err) { showToast(`오류: ${err.message}`, 'error', 5000); }
  });
}

// ━━━ [v1.1.0] 엔트리 편집 모달 ━━━

/**
 * LoreEntry 편집 모달을 표시한다.
 * @param {object} entry - LoreEntryResponse 객체
 */
function showLoreEntryEditModal(entry) {
  const modal = document.getElementById('lb-modal');
  modal.style.display = 'flex';
  modal.innerHTML = `
    <div class="modal-content card">
      <h3 class="card-title">✏️ 로어 항목 편집</h3>
      <form id="le-edit-form">
        <div class="form-group">
          <label>제목</label>
          <input type="text" id="le-edit-title" class="input" value="${escapeHtml(entry.title)}" required>
        </div>
        <div class="form-group">
          <label>활성화 키워드 (쉼표 구분)</label>
          <input type="text" id="le-edit-keys" class="input" value="${escapeHtml(entry.activation_keys.join(', '))}">
        </div>
        <div class="form-group">
          <label>내용</label>
          <textarea id="le-edit-content" class="input" rows="6">${escapeHtml(entry.content)}</textarea>
        </div>
        <div class="form-group">
          <label>우선순위</label>
          <input type="number" id="le-edit-priority" class="input" value="${entry.priority}" min="0" max="1000">
        </div>
        <div class="form-group">
          <label style="display: flex; align-items: center; gap: 0.5rem;">
            <input type="checkbox" id="le-edit-enabled" ${entry.enabled ? 'checked' : ''}>
            활성화
          </label>
        </div>
        <div class="form-actions">
          <button type="submit" class="btn btn-primary">저장</button>
          <button type="button" class="btn" data-action="closeModal" data-modal-id="lb-modal">취소</button>
        </div>
      </form>
    </div>
  `;
  document.getElementById('le-edit-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const keys = document.getElementById('le-edit-keys').value.split(',').map(k => k.trim()).filter(Boolean);
    try {
      await apiPut(`/lore-entries/${entry.id}`, {
        title: document.getElementById('le-edit-title').value,
        activation_keys: keys,
        content: document.getElementById('le-edit-content').value,
        priority: parseInt(document.getElementById('le-edit-priority').value),
        enabled: document.getElementById('le-edit-enabled').checked,
      });
      modal.style.display = 'none';
      showToast('항목이 수정되었습니다.', 'success');
      await showLoreEntries(entry.lorebook_id, '로어북');
    } catch (err) { showToast(`수정 실패: ${err.message}`, 'error', 5000); }
  });
}

// ━━━ [v1.1.0] AI Vibe Fill 모달 ━━━

/**
 * 로어북 AI 생성 모달을 표시한다.
 * 캐릭터(페르소나) 복수 선택 + 바이브 입력 + Provider/Model 선택 기능을 제공한다.
 */
async function showLoreVibeFillModal(lorebookId, bookName) {
  const modal = document.getElementById('lb-modal');
  modal.style.display = 'flex';
  modal.innerHTML = '<div class="modal-content card"><p style="color: var(--text-secondary);">로딩 중...</p></div>';

  try {
    // 병렬로 페르소나 목록, 프로바이더 목록 로드
    const [personas, providers] = await Promise.all([
      apiGet('/personas'),
      apiGet('/providers'),
    ]);

    // 프로바이더별 모델 목록을 미리 로드
    const providerModels = {};
    for (const prov of providers) {
      try {
        const models = await apiGet(`/providers/${prov.id}/models`);
        providerModels[prov.id] = models;
      } catch { providerModels[prov.id] = []; }
    }

    // 모달 UI 구성
    let personaCheckboxes = '';
    if (personas.length === 0) {
      personaCheckboxes = '<p class="text-secondary" style="font-size: 0.85rem;">페르소나가 없습니다. 먼저 캐릭터를 생성하세요.</p>';
    } else {
      personaCheckboxes = personas.map(p => `
        <label style="display: flex; align-items: center; gap: 0.5rem; padding: 0.3rem 0; cursor: pointer;">
          <input type="checkbox" class="lore-vf-persona" value="${p.id}">
          <span><strong>${escapeHtml(p.name)}</strong> <span class="text-secondary">${escapeHtml(p.occupation || '')}</span></span>
        </label>
      `).join('');
    }

    let providerOptions = providers.map(p =>
      `<option value="${p.id}">${escapeHtml(p.name)} (${p.provider_kind})</option>`
    ).join('');

    modal.innerHTML = `
      <div class="modal-content card" style="max-width: 650px;">
        <h3 class="card-title">✨ AI 로어 엔트리 생성</h3>
        <p style="color: var(--text-secondary); margin-bottom: 1rem;">
          캐릭터를 선택하고 바이브를 입력하면 AI가 로어 엔트리를 자동 생성합니다.
        </p>
        <form id="lore-vf-form">
          <div class="form-group">
            <label>참조 캐릭터 (선택, 복수 가능)</label>
            <div style="max-height: 150px; overflow-y: auto; border: 1px solid var(--border); border-radius: 6px; padding: 0.5rem;">
              ${personaCheckboxes}
            </div>
          </div>
          <div class="form-group">
            <label>바이브 텍스트</label>
            <textarea id="lore-vf-text" class="input" rows="4"
              placeholder="예: 중세 판타지 세계의 마법 아이템과 전설적인 장소들"
            ></textarea>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
            <div class="form-group">
              <label>Provider</label>
              <select id="lore-vf-provider" class="input">
                ${providerOptions}
              </select>
            </div>
            <div class="form-group">
              <label>Model</label>
              <select id="lore-vf-model" class="input">
                <option value="">Provider를 선택하세요</option>
              </select>
            </div>
          </div>
          <div class="form-actions">
            <button type="submit" class="btn btn-primary" id="lore-vf-submit">🎨 생성</button>
            <button type="button" class="btn" data-action="closeModal" data-modal-id="lb-modal">취소</button>
          </div>
        </form>
        <div id="lore-vf-result" style="margin-top: 1rem; display: none;"></div>
      </div>
    `;

    // Provider 변경 시 Model 목록 갱신
    const provSelect = document.getElementById('lore-vf-provider');
    const modelSelect = document.getElementById('lore-vf-model');
    const updateModels = () => {
      const models = providerModels[provSelect.value] || [];
      modelSelect.innerHTML = models.length === 0
        ? '<option value="">모델 없음</option>'
        : models.map(m => `<option value="${m.id}">${escapeHtml(m.name || m.id)}</option>`).join('');
    };
    provSelect.addEventListener('change', updateModels);
    if (providers.length > 0) updateModels();

    // 제출 핸들러
    document.getElementById('lore-vf-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const vibeText = document.getElementById('lore-vf-text').value.trim();
      if (!vibeText) { showToast('바이브 텍스트를 입력하세요.', 'warning'); return; }
      const modelId = modelSelect.value;
      if (!modelId) { showToast('모델을 선택하세요.', 'warning'); return; }

      const personaIds = [...document.querySelectorAll('.lore-vf-persona:checked')].map(cb => cb.value);
      const submitBtn = document.getElementById('lore-vf-submit');
      submitBtn.disabled = true;
      submitBtn.textContent = '⏳ 생성 중...';

      try {
        const entries = await apiPost(`/lorebooks/${lorebookId}/vibe-fill`, {
          vibe_text: vibeText,
          persona_ids: personaIds,
          provider_profile_id: provSelect.value,
          model_id: modelId,
        });

        const resultEl = document.getElementById('lore-vf-result');
        resultEl.style.display = 'block';
        resultEl.innerHTML = `
          <div class="card" style="background: var(--surface-elevated);">
            <h4>✅ ${entries.length}개 엔트리 생성 완료!</h4>
            <div style="max-height: 200px; overflow-y: auto;">
              ${entries.map(e => `
                <div style="padding: 0.5rem 0; border-bottom: 1px solid var(--border);">
                  <strong>${escapeHtml(e.title)}</strong>
                  <span class="text-secondary"> [${e.activation_keys.join(', ')}]</span>
                  <div class="text-secondary" style="font-size: 0.8rem;">${escapeHtml(e.content.substring(0, 80))}...</div>
                </div>
              `).join('')}
            </div>
          </div>
        `;
        showToast(`${entries.length}개 로어 엔트리가 생성되었습니다!`, 'success');
        await showLoreEntries(lorebookId, bookName);
      } catch (err) {
        showToast(`생성 실패: ${err.message}`, 'error', 5000);
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = '🎨 생성';
      }
    });

  } catch (err) {
    showToast(`로드 실패: ${err.message}`, 'error', 5000);
    modal.innerHTML = '<div class="modal-content card"><p class="session-empty">데이터를 불러올 수 없습니다</p></div>';
  }
}

async function deleteLoreEntry(entryId, lorebookId, bookName) {
  if (!confirm('이 항목을 삭제하시겠습니까?')) return;
  try {
    await apiDelete(`/lore-entries/${entryId}`);
    showToast('항목이 삭제되었습니다.', 'success');
    await showLoreEntries(lorebookId, bookName);
  } catch (err) { showToast(`삭제 실패: ${err.message}`, 'error', 5000); }
}

