// frontend/js/pages/providers.js
// [v1.0.0] 공급자(Provider) 관리 페이지
//
// Provider CRUD, 연결 테스트, 모델 목록 가져오기를 UI에서 처리한다.

/**
 * Provider 페이지를 렌더링한다.
 * @param {HTMLElement} container - #page-container
 */
async function renderProviders(container) {
  container.innerHTML = `
    <div class="card">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
        <h2 class="card-title" style="margin: 0;">🔌 공급자 관리</h2>
        <button class="btn btn-primary" id="btn-add-provider">+ 새 공급자</button>
      </div>
      <div id="provider-list" class="provider-list">
        <p style="color: var(--text-secondary);">로딩 중...</p>
      </div>
    </div>
    <div id="provider-form-modal" class="modal" style="display: none;"></div>
  `;

  // 공급자 목록 로드
  await loadProviders();

  // 새 공급자 추가 버튼
  document.getElementById('btn-add-provider').addEventListener('click', () => {
    showProviderForm();
  });
}

/**
 * 공급자 목록을 API에서 가져와 렌더링한다.
 */
async function loadProviders() {
  const listEl = document.getElementById('provider-list');
  try {
    const providers = await apiGet('/providers');
    if (providers.length === 0) {
      listEl.innerHTML = `
        <div style="text-align: center; padding: 2rem; color: var(--text-secondary);">
          <p style="font-size: 1.2rem;">공급자가 없습니다</p>
          <p>위의 '+ 새 공급자' 버튼으로 추가하세요.</p>
        </div>
      `;
      return;
    }

    listEl.innerHTML = providers.map(p => `
      <div class="provider-card" data-id="${p.id}">
        <div class="provider-info">
          <span class="provider-kind-badge">${getKindLabel(p.provider_kind)}</span>
          <strong>${escapeHtml(p.name)}</strong>
          <span class="provider-status ${p.enabled ? 'active' : 'inactive'}">
            ${p.enabled ? '● 활성' : '○ 비활성'}
          </span>
          ${p.has_api_key ? '<span class="key-indicator">🔑</span>' : ''}
        </div>
        <div class="provider-actions">
          <button class="btn btn-sm" onclick="testProvider('${p.id}')">테스트</button>
          <button class="btn btn-sm" onclick="fetchModels('${p.id}')">모델 가져오기</button>
          <button class="btn btn-sm btn-danger" onclick="deleteProvider('${p.id}')">삭제</button>
        </div>
      </div>
    `).join('');
  } catch (err) {
    listEl.innerHTML = `<p style="color: var(--danger);">로드 실패: ${escapeHtml(err.message)}</p>`;
  }
}

/**
 * 공급자 생성/수정 폼을 표시한다.
 */
function showProviderForm(existing = null) {
  const modal = document.getElementById('provider-form-modal');
  modal.style.display = 'flex';
  modal.innerHTML = `
    <div class="modal-content card">
      <h3 class="card-title">${existing ? '공급자 수정' : '새 공급자 추가'}</h3>
      <form id="provider-form">
        <div class="form-group">
          <label>이름</label>
          <input type="text" id="pf-name" class="input" value="${existing?.name || ''}" required>
        </div>
        <div class="form-group">
          <label>종류</label>
          <select id="pf-kind" class="input">
            <option value="gemini" ${existing?.provider_kind === 'gemini' ? 'selected' : ''}>Google Gemini</option>
            <option value="openrouter" ${existing?.provider_kind === 'openrouter' ? 'selected' : ''}>OpenRouter</option>
            <option value="lm_studio" ${existing?.provider_kind === 'lm_studio' ? 'selected' : ''}>LM Studio</option>
          </select>
        </div>
        <div class="form-group">
          <label>API Key (선택)</label>
          <input type="password" id="pf-apikey" class="input" placeholder="sk-...">
        </div>
        <div class="form-group">
          <label>Base URL (선택)</label>
          <input type="text" id="pf-baseurl" class="input" value="${existing?.base_url || ''}" placeholder="http://localhost:1234/v1">
        </div>
        <div class="form-group">
          <label>타임아웃 (초)</label>
          <input type="number" id="pf-timeout" class="input" value="${existing?.timeout_seconds || 60}" min="5" max="300">
        </div>
        <div class="form-actions">
          <button type="submit" class="btn btn-primary">${existing ? '수정' : '생성'}</button>
          <button type="button" class="btn" onclick="closeProviderForm()">취소</button>
        </div>
      </form>
    </div>
  `;

  document.getElementById('provider-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const body = {
      name: document.getElementById('pf-name').value,
      provider_kind: document.getElementById('pf-kind').value,
      api_key: document.getElementById('pf-apikey').value || null,
      base_url: document.getElementById('pf-baseurl').value || null,
      timeout_seconds: parseInt(document.getElementById('pf-timeout').value),
    };
    try {
      if (existing) {
        await apiPut(`/providers/${existing.id}`, body);
      } else {
        await apiPost('/providers', body);
      }
      closeProviderForm();
      await loadProviders();
    } catch (err) {
      alert(`오류: ${err.message}`);
    }
  });
}

function closeProviderForm() {
  document.getElementById('provider-form-modal').style.display = 'none';
}

async function testProvider(id) {
  try {
    const result = await apiPost(`/providers/${id}/test`, {});
    alert(result.ok ? `✅ 연결 성공: ${result.message || 'OK'}` : `❌ 연결 실패: ${result.message}`);
  } catch (err) {
    alert(`테스트 실패: ${err.message}`);
  }
}

async function fetchModels(id) {
  try {
    const models = await apiPost(`/providers/${id}/fetch-models`, {});
    alert(`✅ ${models.length}개 모델을 가져왔습니다.`);
  } catch (err) {
    alert(`모델 가져오기 실패: ${err.message}`);
  }
}

async function deleteProvider(id) {
  if (!confirm('이 공급자를 삭제하시겠습니까?')) return;
  try {
    await apiDelete(`/providers/${id}`);
    await loadProviders();
  } catch (err) {
    alert(`삭제 실패: ${err.message}`);
  }
}

function getKindLabel(kind) {
  return { gemini: 'Gemini', openrouter: 'OpenRouter', lm_studio: 'LM Studio' }[kind] || kind;
}

function escapeHtml(str) {
  const el = document.createElement('span');
  el.textContent = str;
  return el.innerHTML;
}
