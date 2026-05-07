// frontend/js/pages/worldbooks.js
// [v1.1.0] 월드북 관리 페이지
//
// Worldbook CRUD + WorldEntry 관리 + AI Vibe Fill 생성 + 수동 편집 UI.
// [v1.1.0 변경사항]
// - AI 생성 모달: 캐릭터/로어북 복수 선택 + 카테고리 선택 + 바이브 입력 → 엔트리 자동 생성
// - 엔트리 편집 모달: 제목, 내용, 우선순위 필드 수정

import { apiGet, apiPost, apiPut, apiDelete, escapeHtml, showToast } from '../api.js';

/**
 * 월드북 페이지를 렌더링한다.
 */
export async function renderWorldbooks(container) {
  container.innerHTML = `
    <div class="card">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
        <h2 class="card-title" style="margin: 0;">🌍 월드북</h2>
        <button class="btn btn-primary" id="btn-add-worldbook">+ 새 월드북</button>
      </div>
      <div id="worldbook-list">
        <p style="color: var(--text-secondary);">로딩 중...</p>
      </div>
    </div>
    <div id="wb-detail" class="card" style="display: none; margin-top: 1rem;"></div>
    <div id="wb-modal" class="modal" style="display: none;"></div>
  `;

  await loadWorldbooks();

  document.getElementById('btn-add-worldbook').addEventListener('click', () => {
    showWorldbookCreateModal();
  });

  // [v1.1.1] 이벤트 위임 — data-action 기반 핸들러
  container.addEventListener('click', (e) => {
    const el = e.target.closest('[data-action]');
    if (!el) return;
    e.stopPropagation();
    const actionId = el.dataset.id;
    switch (el.dataset.action) {
      case 'showWorldEntries': showWorldEntries(actionId, el.dataset.extra1); break;
      case 'deleteWorldbook': deleteWorldbook(actionId); break;
      case 'showWorldVibeFillModal': showWorldVibeFillModal(actionId, el.dataset.extra1); break;
      case 'showWorldEntryForm': showWorldEntryForm(actionId); break;
      case 'deleteWorldEntry': deleteWorldEntry(actionId, el.dataset.extra1, el.dataset.extra2); break;
      case 'showWorldEntryEditModal': { apiGet(`/worldbooks/entries/${actionId}`).then(e => showWorldEntryEditModal(e)).catch(() => {}) }; break;
      case 'closeModal': {
        const mid = el.dataset.modalId;
        if (mid) { const modal = document.getElementById(mid); if (modal) modal.style.display = 'none'; }
        break;
      }
    }
  });
}

async function loadWorldbooks() {
  const listEl = document.getElementById('worldbook-list');
  try {
    const books = await apiGet('/worldbooks');
    if (books.length === 0) {
      listEl.innerHTML = '<div style="text-align: center; padding: 2rem; color: var(--text-secondary);"><p>월드북이 없습니다</p></div>';
      return;
    }
    listEl.innerHTML = books.map(b => `
      <div class="profile-card" data-id="${b.id}">
        <div class="profile-info" style="cursor: pointer;" data-action="showWorldEntries" data-id="${b.id}" data-extra1="${escapeHtml(b.name)}">
          <strong>${escapeHtml(b.name)}</strong>
          <span class="text-secondary" style="font-size: 0.8rem;">${escapeHtml(b.description || '설명 없음')}</span>
        </div>
        <div class="profile-actions">
          <button class="btn btn-sm btn-danger" data-action="deleteWorldbook" data-id="${b.id}">삭제</button>
        </div>
      </div>
    `).join('');
  } catch (err) {
    showToast(`로드 실패: ${err.message}`, 'error', 5000);
    listEl.innerHTML = '<p class="session-empty">데이터를 불러올 수 없습니다</p>';
  }
}

function showWorldbookCreateModal() {
  const modal = document.getElementById('wb-modal');
  modal.style.display = 'flex';
  modal.innerHTML = `
    <div class="modal-content card">
      <h3 class="card-title">새 월드북</h3>
      <form id="wb-create-form">
        <div class="form-group">
          <label>이름</label>
          <input type="text" id="wb-name" class="input" required>
        </div>
        <div class="form-group">
          <label>설명</label>
          <textarea id="wb-desc" class="input" rows="2"></textarea>
        </div>
        <div class="form-actions">
          <button type="submit" class="btn btn-primary">생성</button>
          <button type="button" class="btn" data-action="closeModal" data-modal-id="wb-modal">취소</button>
        </div>
      </form>
    </div>
  `;
  document.getElementById('wb-create-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await apiPost('/worldbooks', {
        name: document.getElementById('wb-name').value,
        description: document.getElementById('wb-desc').value,
      });
      modal.style.display = 'none';
      await loadWorldbooks();
    } catch (err) { showToast(`오류: ${err.message}`, 'error', 5000); }
  });
}

async function deleteWorldbook(id) {
  if (!confirm('이 월드북을 삭제하시겠습니까?')) return;
  try {
    await apiDelete(`/worldbooks/${id}`);
    showToast('월드북이 삭제되었습니다.', 'success');
    await loadWorldbooks();
    document.getElementById('wb-detail').style.display = 'none';
  } catch (err) { showToast(`삭제 실패: ${err.message}`, 'error', 5000); }
}

/**
 * [v1.1.0] 월드북의 WorldEntry 목록을 표시한다.
 * AI 생성 버튼과 엔트리별 편집/삭제 버튼을 포함한다.
 */
async function showWorldEntries(worldbookId, bookName) {
  const detail = document.getElementById('wb-detail');
  detail.style.display = 'block';
  detail.innerHTML = '<p style="color: var(--text-secondary);">로딩 중...</p>';

  try {
    const entries = await apiGet(`/worldbooks/${worldbookId}/entries`);
    let html = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
        <h3 class="card-title" style="margin: 0;">🌐 ${escapeHtml(bookName)} 항목</h3>
        <div style="display: flex; gap: 0.5rem;">
          <button class="btn btn-primary btn-sm" data-action="showWorldVibeFillModal" data-id="${worldbookId}" data-extra1="${escapeHtml(bookName)}">✨ AI 생성</button>
          <button class="btn btn-sm" data-action="showWorldEntryForm" data-id="${worldbookId}">+ 수동 추가</button>
        </div>
      </div>
    `;

    if (entries.length === 0) {
      html += '<p class="text-secondary">항목이 없습니다. "✨ AI 생성"으로 세계관 엔트리를 자동 생성하세요.</p>';
    } else {
      html += entries.map(e => `
        <div class="entry-item">
          <div><strong>${escapeHtml(e.title)}</strong></div>
          <div class="text-secondary" style="font-size: 0.8rem; margin: 0.25rem 0;">${escapeHtml(e.content.substring(0, 120))}${e.content.length > 120 ? '...' : ''}</div>
          <div style="display: flex; gap: 0.5rem; margin-top: 0.25rem;">
            <button class="btn btn-sm" data-action="showWorldEntryEditModal" data-id="${e.id}">편집</button>
            <button class="btn btn-sm btn-danger" data-action="deleteWorldEntry" data-id="${e.id}" data-extra1="${worldbookId}" data-extra2="${escapeHtml(bookName)}">삭제</button>
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

function showWorldEntryForm(worldbookId) {
  const modal = document.getElementById('wb-modal');
  modal.style.display = 'flex';
  modal.innerHTML = `
    <div class="modal-content card">
      <h3 class="card-title">새 월드 항목</h3>
      <form id="we-form">
        <div class="form-group"><label>제목</label><input type="text" id="we-title" class="input" required></div>
        <div class="form-group"><label>내용</label><textarea id="we-content" class="input" rows="4"></textarea></div>
        <div class="form-group"><label>우선순위</label><input type="number" id="we-priority" class="input" value="100" min="0" max="1000"></div>
        <div class="form-actions">
          <button type="submit" class="btn btn-primary">추가</button>
          <button type="button" class="btn" data-action="closeModal" data-modal-id="wb-modal">취소</button>
        </div>
      </form>
    </div>
  `;
  document.getElementById('we-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await apiPost(`/worldbooks/${worldbookId}/entries`, {
        title: document.getElementById('we-title').value,
        content: document.getElementById('we-content').value,
        priority: parseInt(document.getElementById('we-priority').value),
        enabled: true,
      });
      modal.style.display = 'none';
      await showWorldEntries(worldbookId, '월드북');
    } catch (err) { showToast(`오류: ${err.message}`, 'error', 5000); }
  });
}

// ━━━ [v1.1.0] 엔트리 편집 모달 ━━━

/**
 * WorldEntry 편집 모달을 표시한다.
 * @param {object} entry - WorldEntryResponse 객체
 */
function showWorldEntryEditModal(entry) {
  const modal = document.getElementById('wb-modal');
  modal.style.display = 'flex';
  modal.innerHTML = `
    <div class="modal-content card">
      <h3 class="card-title">✏️ 월드 항목 편집</h3>
      <form id="we-edit-form">
        <div class="form-group">
          <label>제목</label>
          <input type="text" id="we-edit-title" class="input" value="${escapeHtml(entry.title)}" required>
        </div>
        <div class="form-group">
          <label>내용</label>
          <textarea id="we-edit-content" class="input" rows="6">${escapeHtml(entry.content)}</textarea>
        </div>
        <div class="form-group">
          <label>우선순위</label>
          <input type="number" id="we-edit-priority" class="input" value="${entry.priority}" min="0" max="1000">
        </div>
        <div class="form-group">
          <label style="display: flex; align-items: center; gap: 0.5rem;">
            <input type="checkbox" id="we-edit-enabled" ${entry.enabled ? 'checked' : ''}>
            활성화
          </label>
        </div>
        <div class="form-actions">
          <button type="submit" class="btn btn-primary">저장</button>
          <button type="button" class="btn" data-action="closeModal" data-modal-id="wb-modal">취소</button>
        </div>
      </form>
    </div>
  `;
  document.getElementById('we-edit-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await apiPut(`/world-entries/${entry.id}`, {
        title: document.getElementById('we-edit-title').value,
        content: document.getElementById('we-edit-content').value,
        priority: parseInt(document.getElementById('we-edit-priority').value),
        enabled: document.getElementById('we-edit-enabled').checked,
      });
      modal.style.display = 'none';
      showToast('항목이 수정되었습니다.', 'success');
      await showWorldEntries(entry.worldbook_id, '월드북');
    } catch (err) { showToast(`수정 실패: ${err.message}`, 'error', 5000); }
  });
}

// ━━━ [v1.1.0] AI Vibe Fill 모달 ━━━

// 세계관 카테고리 정의 (domain/vibe_fill.py의 WORLD_CATEGORIES와 동기화)
const WORLD_CATEGORIES = [
  { key: 'history', label: '역사', desc: '주요 사건, 전쟁, 전환점' },
  { key: 'geography', label: '지리', desc: '대륙, 지형, 기후, 지역' },
  { key: 'factions', label: '세력/국가', desc: '국가, 조직, 파벌' },
  { key: 'races', label: '종족', desc: '종족과 특성, 문화적 차이' },
  { key: 'magic_tech', label: '마법/기술', desc: '마법 체계, 기술 수준' },
  { key: 'economy', label: '경제', desc: '화폐, 교역, 자원' },
  { key: 'religion', label: '종교/신화', desc: '신앙, 신, 의식' },
  { key: 'dungeons', label: '던전/위험지대', desc: '위험한 장소, 금지 구역' },
  { key: 'culture', label: '일상/문화', desc: '생활, 축제, 풍습' },
  { key: 'rules', label: '규칙/법칙', desc: '물리 법칙, 특수 규칙' },
];

/**
 * 월드북 AI 생성 모달을 표시한다.
 * 캐릭터/로어북 복수 선택 + 카테고리 선택 + 바이브 입력 + Provider/Model 선택.
 */
async function showWorldVibeFillModal(worldbookId, bookName) {
  const modal = document.getElementById('wb-modal');
  modal.style.display = 'flex';
  modal.innerHTML = '<div class="modal-content card"><p style="color: var(--text-secondary);">로딩 중...</p></div>';

  try {
    // 병렬로 페르소나, 로어북, 프로바이더 목록 로드
    const [personas, lorebooks, providers] = await Promise.all([
      apiGet('/personas'),
      apiGet('/lorebooks'),
      apiGet('/providers'),
    ]);

    // 프로바이더별 모델 목록
    const providerModels = {};
    for (const prov of providers) {
      try {
        const models = await apiGet(`/providers/${prov.id}/models`);
        providerModels[prov.id] = models;
      } catch { providerModels[prov.id] = []; }
    }

    // 캐릭터 체크박스
    let personaCheckboxes = '';
    if (personas.length === 0) {
      personaCheckboxes = '<p class="text-secondary" style="font-size: 0.85rem;">페르소나 없음</p>';
    } else {
      personaCheckboxes = personas.map(p => `
        <label style="display: flex; align-items: center; gap: 0.5rem; padding: 0.2rem 0; cursor: pointer;">
          <input type="checkbox" class="world-vf-persona" value="${p.id}">
          <span>${escapeHtml(p.name)}</span>
        </label>
      `).join('');
    }

    // 로어북 체크박스
    let lorebookCheckboxes = '';
    if (lorebooks.length === 0) {
      lorebookCheckboxes = '<p class="text-secondary" style="font-size: 0.85rem;">로어북 없음</p>';
    } else {
      lorebookCheckboxes = lorebooks.map(lb => `
        <label style="display: flex; align-items: center; gap: 0.5rem; padding: 0.2rem 0; cursor: pointer;">
          <input type="checkbox" class="world-vf-lorebook" value="${lb.id}">
          <span>${escapeHtml(lb.name)}</span>
        </label>
      `).join('');
    }

    // 카테고리 체크박스 (기본 전체 선택)
    const categoryCheckboxes = WORLD_CATEGORIES.map(c => `
      <label style="display: flex; align-items: center; gap: 0.5rem; padding: 0.2rem 0; cursor: pointer;">
        <input type="checkbox" class="world-vf-category" value="${c.key}" checked>
        <span><strong>${c.label}</strong> <span class="text-secondary" style="font-size: 0.8rem;">${c.desc}</span></span>
      </label>
    `).join('');

    // Provider 옵션
    let providerOptions = providers.map(p =>
      `<option value="${p.id}">${escapeHtml(p.name)} (${p.provider_kind})</option>`
    ).join('');

    modal.innerHTML = `
      <div class="modal-content card" style="max-width: 700px; max-height: 85vh; overflow-y: auto;">
        <h3 class="card-title">✨ AI 세계관 엔트리 생성</h3>
        <p style="color: var(--text-secondary); margin-bottom: 1rem;">
          캐릭터/로어북을 참조하고 카테고리를 선택하면 AI가 세계관 엔트리를 자동 생성합니다.
          <br><span class="text-secondary" style="font-size: 0.8rem;">카테고리는 2~3개씩 나눠 여러 번 호출되므로 시간이 걸릴 수 있습니다.</span>
        </p>
        <form id="world-vf-form">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
            <div class="form-group">
              <label>참조 캐릭터 (선택)</label>
              <div style="max-height: 120px; overflow-y: auto; border: 1px solid var(--border); border-radius: 6px; padding: 0.5rem;">
                ${personaCheckboxes}
              </div>
            </div>
            <div class="form-group">
              <label>참조 로어북 (선택)</label>
              <div style="max-height: 120px; overflow-y: auto; border: 1px solid var(--border); border-radius: 6px; padding: 0.5rem;">
                ${lorebookCheckboxes}
              </div>
            </div>
          </div>
          <div class="form-group">
            <label>생성 카테고리</label>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0; max-height: 200px; overflow-y: auto; border: 1px solid var(--border); border-radius: 6px; padding: 0.5rem;">
              ${categoryCheckboxes}
            </div>
          </div>
          <div class="form-group">
            <label>바이브 텍스트</label>
            <textarea id="world-vf-text" class="input" rows="3"
              placeholder="예: 어둠의 마법이 지배하는 황폐한 대륙, 빛을 되찾으려는 저항 세력"
            ></textarea>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
            <div class="form-group">
              <label>Provider</label>
              <select id="world-vf-provider" class="input">
                ${providerOptions}
              </select>
            </div>
            <div class="form-group">
              <label>Model</label>
              <select id="world-vf-model" class="input">
                <option value="">Provider를 선택하세요</option>
              </select>
            </div>
          </div>
          <div class="form-actions">
            <button type="submit" class="btn btn-primary" id="world-vf-submit">🌍 생성</button>
            <button type="button" class="btn" data-action="closeModal" data-modal-id="wb-modal">취소</button>
          </div>
        </form>
        <div id="world-vf-result" style="margin-top: 1rem; display: none;"></div>
      </div>
    `;

    // Provider 변경 시 Model 목록 갱신
    const provSelect = document.getElementById('world-vf-provider');
    const modelSelect = document.getElementById('world-vf-model');
    const updateModels = () => {
      const models = providerModels[provSelect.value] || [];
      modelSelect.innerHTML = models.length === 0
        ? '<option value="">모델 없음</option>'
        : models.map(m => `<option value="${m.id}">${escapeHtml(m.name || m.id)}</option>`).join('');
    };
    provSelect.addEventListener('change', updateModels);
    if (providers.length > 0) updateModels();

    // 제출 핸들러
    document.getElementById('world-vf-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const vibeText = document.getElementById('world-vf-text').value.trim();
      if (!vibeText) { showToast('바이브 텍스트를 입력하세요.', 'warning'); return; }
      const modelId = modelSelect.value;
      if (!modelId) { showToast('모델을 선택하세요.', 'warning'); return; }

      const personaIds = [...document.querySelectorAll('.world-vf-persona:checked')].map(cb => cb.value);
      const lorebookIds = [...document.querySelectorAll('.world-vf-lorebook:checked')].map(cb => cb.value);
      const categoryKeys = [...document.querySelectorAll('.world-vf-category:checked')].map(cb => cb.value);

      if (categoryKeys.length === 0) { showToast('최소 1개 카테고리를 선택하세요.', 'warning'); return; }

      const submitBtn = document.getElementById('world-vf-submit');
      submitBtn.disabled = true;
      submitBtn.textContent = '⏳ 생성 중... (카테고리 청크별 호출)';

      try {
        const entries = await apiPost(`/worldbooks/${worldbookId}/vibe-fill`, {
          vibe_text: vibeText,
          persona_ids: personaIds,
          lorebook_ids: lorebookIds,
          category_keys: categoryKeys,
          provider_profile_id: provSelect.value,
          model_id: modelId,
        });

        const resultEl = document.getElementById('world-vf-result');
        resultEl.style.display = 'block';
        resultEl.innerHTML = `
          <div class="card" style="background: var(--surface-elevated);">
            <h4>✅ ${entries.length}개 엔트리 생성 완료!</h4>
            <div style="max-height: 200px; overflow-y: auto;">
              ${entries.map(e => `
                <div style="padding: 0.5rem 0; border-bottom: 1px solid var(--border);">
                  <strong>${escapeHtml(e.title)}</strong>
                  <div class="text-secondary" style="font-size: 0.8rem;">${escapeHtml(e.content.substring(0, 80))}...</div>
                </div>
              `).join('')}
            </div>
          </div>
        `;
        showToast(`${entries.length}개 세계관 엔트리가 생성되었습니다!`, 'success');
        await showWorldEntries(worldbookId, bookName);
      } catch (err) {
        showToast(`생성 실패: ${err.message}`, 'error', 5000);
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = '🌍 생성';
      }
    });

  } catch (err) {
    showToast(`로드 실패: ${err.message}`, 'error', 5000);
    modal.innerHTML = '<div class="modal-content card"><p class="session-empty">데이터를 불러올 수 없습니다</p></div>';
  }
}

async function deleteWorldEntry(entryId, worldbookId, bookName) {
  if (!confirm('이 항목을 삭제하시겠습니까?')) return;
  try {
    await apiDelete(`/world-entries/${entryId}`);
    showToast('항목이 삭제되었습니다.', 'success');
    await showWorldEntries(worldbookId, bookName);
  } catch (err) { showToast(`삭제 실패: ${err.message}`, 'error', 5000); }
}

