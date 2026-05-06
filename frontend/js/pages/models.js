// frontend/js/pages/models.js
// [v1.0.0] 모델 설정 페이지
//
// Provider 선택 → 캐시된 모델 목록 → ModelProfile CRUD를 처리한다.

/**
 * 모델 설정 페이지를 렌더링한다.
 * @param {HTMLElement} container - #page-container
 */
async function renderModels(container) {
  container.innerHTML = `
    <div class="card">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
        <h2 class="card-title" style="margin: 0;">⚙️ 모델 설정</h2>
        <button class="btn btn-primary" id="btn-add-model-profile">+ 새 모델 프로필</button>
      </div>
      <div id="model-profile-list">
        <p style="color: var(--text-secondary);">로딩 중...</p>
      </div>
    </div>
    <div id="model-form-modal" class="modal" style="display: none;"></div>
  `;

  await loadModelProfiles();

  document.getElementById('btn-add-model-profile').addEventListener('click', () => {
    showModelProfileForm();
  });
}

/**
 * ModelProfile 목록을 API에서 가져와 렌더링한다.
 */
async function loadModelProfiles() {
  const listEl = document.getElementById('model-profile-list');
  try {
    const profiles = await apiGet('/model-profiles');
    if (profiles.length === 0) {
      listEl.innerHTML = `
        <div style="text-align: center; padding: 2rem; color: var(--text-secondary);">
          <p style="font-size: 1.2rem;">모델 프로필이 없습니다</p>
          <p>먼저 공급자를 등록하고 모델을 가져온 후, 모델 프로필을 추가하세요.</p>
        </div>
      `;
      return;
    }

    listEl.innerHTML = profiles.map(p => `
      <div class="profile-card" data-id="${p.id}">
        <div class="profile-info">
          <strong>${escapeHtml(p.name)}</strong>
          <span class="text-secondary" style="font-size: 0.8rem;">모델: ${escapeHtml(p.model_id)}</span>
        </div>
        <div class="profile-actions">
          <button class="btn btn-sm btn-danger" onclick="deleteModelProfile('${p.id}')">삭제</button>
        </div>
      </div>
    `).join('');
  } catch (err) {
    listEl.innerHTML = `<p style="color: var(--danger);">로드 실패: ${escapeHtml(err.message)}</p>`;
  }
}

/**
 * ModelProfile 생성 폼을 표시한다.
 */
async function showModelProfileForm() {
  const modal = document.getElementById('model-form-modal');
  modal.style.display = 'flex';

  // 공급자 목록 로드
  let providers = [];
  try {
    providers = await apiGet('/providers');
  } catch { /* 빈 배열 유지 */ }

  const providerOptions = providers.map(p =>
    `<option value="${p.id}">${escapeHtml(p.name)} (${p.provider_kind})</option>`
  ).join('');

  modal.innerHTML = `
    <div class="modal-content card">
      <h3 class="card-title">새 모델 프로필 추가</h3>
      <form id="model-profile-form">
        <div class="form-group">
          <label>이름</label>
          <input type="text" id="mp-name" class="input" placeholder="예: Gemini Flash 기본" required>
        </div>
        <div class="form-group">
          <label>공급자</label>
          <select id="mp-provider" class="input">
            <option value="">선택하세요</option>
            ${providerOptions}
          </select>
        </div>
        <div class="form-group">
          <label>모델</label>
          <select id="mp-model" class="input" disabled>
            <option value="">먼저 공급자를 선택하세요</option>
          </select>
        </div>
        <div class="form-group">
          <label>설정 (JSON)</label>
          <textarea id="mp-settings" class="input" rows="3" placeholder='{"temperature": 0.7}'>{}</textarea>
        </div>
        <div class="form-actions">
          <button type="submit" class="btn btn-primary">생성</button>
          <button type="button" class="btn" onclick="document.getElementById('model-form-modal').style.display='none'">취소</button>
        </div>
      </form>
    </div>
  `;

  // 공급자 선택 시 모델 목록 로드
  document.getElementById('mp-provider').addEventListener('change', async (e) => {
    const modelSelect = document.getElementById('mp-model');
    const providerId = e.target.value;
    if (!providerId) {
      modelSelect.disabled = true;
      modelSelect.innerHTML = '<option value="">먼저 공급자를 선택하세요</option>';
      return;
    }

    try {
      const models = await apiGet(`/providers/${providerId}/models`);
      if (models.length === 0) {
        modelSelect.innerHTML = '<option value="">캐시된 모델이 없습니다 — 먼저 모델을 가져오세요</option>';
        modelSelect.disabled = true;
      } else {
        modelSelect.innerHTML = models.map(m =>
          `<option value="${m.model_id}">${escapeHtml(m.display_name || m.model_id)}</option>`
        ).join('');
        modelSelect.disabled = false;
      }
    } catch {
      modelSelect.innerHTML = '<option value="">모델 로드 실패</option>';
      modelSelect.disabled = true;
    }
  });

  // 폼 제출
  document.getElementById('model-profile-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const body = {
      name: document.getElementById('mp-name').value,
      provider_profile_id: document.getElementById('mp-provider').value,
      model_id: document.getElementById('mp-model').value,
      settings_json: document.getElementById('mp-settings').value || '{}',
    };
    if (!body.provider_profile_id || !body.model_id) {
      alert('공급자와 모델을 선택해주세요.');
      return;
    }
    try {
      await apiPost('/model-profiles', body);
      modal.style.display = 'none';
      await loadModelProfiles();
    } catch (err) {
      alert(`오류: ${err.message}`);
    }
  });
}

async function deleteModelProfile(id) {
  if (!confirm('이 모델 프로필을 삭제하시겠습니까?')) return;
  try {
    await apiDelete(`/model-profiles/${id}`);
    await loadModelProfiles();
  } catch (err) {
    alert(`삭제 실패: ${err.message}`);
  }
}
