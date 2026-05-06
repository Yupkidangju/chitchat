// frontend/js/pages/chat_profiles.js
// [v1.0.0] 채팅 프로필 관리 페이지
//
// ModelProfile + AI Persona + Lorebook + Worldbook 조합으로 ChatProfile을 구성한다.
// ChatProfile이 있어야 채팅 세션을 생성할 수 있다.

/**
 * 채팅 프로필 페이지를 렌더링한다.
 * @param {HTMLElement} container - #page-container
 */
async function renderChatProfiles(container) {
  container.innerHTML = `
    <div class="card">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
        <h2 class="card-title" style="margin: 0;">🎯 채팅 프로필</h2>
        <button class="btn btn-primary" id="btn-add-chat-profile">+ 새 채팅 프로필</button>
      </div>
      <div id="chat-profile-list">
        <p style="color: var(--text-secondary);">로딩 중...</p>
      </div>
    </div>
    <div id="cp-form-modal" class="modal" style="display: none;"></div>
  `;

  await loadChatProfiles();

  document.getElementById('btn-add-chat-profile').addEventListener('click', () => {
    showChatProfileForm();
  });
}

/**
 * ChatProfile 목록을 로드한다.
 */
async function loadChatProfiles() {
  const listEl = document.getElementById('chat-profile-list');
  try {
    const profiles = await apiGet('/chat-profiles');
    if (profiles.length === 0) {
      listEl.innerHTML = `
        <div style="text-align: center; padding: 2rem; color: var(--text-secondary);">
          <p style="font-size: 1.2rem;">채팅 프로필이 없습니다</p>
          <p>모델 프로필과 AI 페르소나를 먼저 등록한 후, 채팅 프로필을 만드세요.</p>
        </div>
      `;
      return;
    }

    listEl.innerHTML = profiles.map(p => `
      <div class="profile-card" data-id="${p.id}">
        <div class="profile-info">
          <strong>${escapeHtml(p.name)}</strong>
          <span class="text-secondary" style="font-size: 0.8rem;">
            AI: ${p.ai_persona_ids.length}명 · LB: ${p.lorebook_ids.length} · WB: ${p.worldbook_ids.length}
          </span>
        </div>
        <div class="profile-actions">
          <button class="btn btn-sm btn-danger" onclick="deleteChatProfile('${p.id}')">삭제</button>
        </div>
      </div>
    `).join('');
  } catch (err) {
    listEl.innerHTML = `<p style="color: var(--danger);">로드 실패: ${escapeHtml(err.message)}</p>`;
  }
}

/**
 * ChatProfile 생성 폼을 표시한다.
 */
async function showChatProfileForm() {
  const modal = document.getElementById('cp-form-modal');
  modal.style.display = 'flex';

  // 의존 데이터 병렬 로드
  let [modelProfiles, personas, lorebooks, worldbooks] = [[], [], [], []];
  try {
    [modelProfiles, personas, lorebooks, worldbooks] = await Promise.all([
      apiGet('/model-profiles'),
      apiGet('/personas'),
      apiGet('/lorebooks'),
      apiGet('/worldbooks'),
    ]);
  } catch { /* 빈 배열 유지 */ }

  const mpOptions = modelProfiles.map(m =>
    `<option value="${m.id}">${escapeHtml(m.name)} (${escapeHtml(m.model_id)})</option>`
  ).join('');

  const personaChecks = personas.map(p =>
    `<label class="checkbox-item"><input type="checkbox" value="${p.id}"> ${escapeHtml(p.name)}</label>`
  ).join('');

  const lbChecks = lorebooks.map(l =>
    `<label class="checkbox-item"><input type="checkbox" value="${l.id}"> ${escapeHtml(l.name)}</label>`
  ).join('');

  const wbChecks = worldbooks.map(w =>
    `<label class="checkbox-item"><input type="checkbox" value="${w.id}"> ${escapeHtml(w.name)}</label>`
  ).join('');

  modal.innerHTML = `
    <div class="modal-content card" style="max-height: 85vh; overflow-y: auto;">
      <h3 class="card-title">새 채팅 프로필 추가</h3>
      <form id="chat-profile-form">
        <div class="form-group">
          <label>프로필 이름</label>
          <input type="text" id="cp-name" class="input" placeholder="예: 유리와의 대화" required>
        </div>
        <div class="form-group">
          <label>모델 프로필</label>
          <select id="cp-model" class="input">
            <option value="">선택하세요</option>
            ${mpOptions}
          </select>
        </div>
        <div class="form-group">
          <label>AI 페르소나 (다중 선택)</label>
          <div id="cp-personas" class="checkbox-group">${personaChecks || '<p class="text-secondary">등록된 페르소나가 없습니다</p>'}</div>
        </div>
        <div class="form-group">
          <label>로어북 (다중 선택)</label>
          <div id="cp-lorebooks" class="checkbox-group">${lbChecks || '<p class="text-secondary">등록된 로어북이 없습니다</p>'}</div>
        </div>
        <div class="form-group">
          <label>월드북 (다중 선택)</label>
          <div id="cp-worldbooks" class="checkbox-group">${wbChecks || '<p class="text-secondary">등록된 월드북이 없습니다</p>'}</div>
        </div>
        <div class="form-group">
          <label>시스템 베이스 프롬프트</label>
          <textarea id="cp-system-base" class="input" rows="4" placeholder="시스템 기본 지시사항..."></textarea>
        </div>
        <div class="form-actions">
          <button type="submit" class="btn btn-primary">생성</button>
          <button type="button" class="btn" onclick="document.getElementById('cp-form-modal').style.display='none'">취소</button>
        </div>
      </form>
    </div>
  `;

  // 폼 제출
  document.getElementById('chat-profile-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const modelId = document.getElementById('cp-model').value;
    if (!modelId) {
      showToast('모델 프로필을 선택해주세요.', 'warning');
      return;
    }

    // 체크박스에서 선택된 ID 수집
    const getChecked = (containerId) =>
      [...document.querySelectorAll(`#${containerId} input[type="checkbox"]:checked`)]
        .map(cb => cb.value);

    const body = {
      name: document.getElementById('cp-name').value,
      model_profile_id: modelId,
      ai_persona_ids: getChecked('cp-personas'),
      lorebook_ids: getChecked('cp-lorebooks'),
      worldbook_ids: getChecked('cp-worldbooks'),
      prompt_order_json: '[]',
      system_base: document.getElementById('cp-system-base').value,
    };

    try {
      await apiPost('/chat-profiles', body);
      modal.style.display = 'none';
      await loadChatProfiles();
    } catch (err) {
      showToast(`오류: ${err.message}`, 'error', 5000);
    }
  });
}

async function deleteChatProfile(id) {
  if (!confirm('이 채팅 프로필을 삭제하시겠습니까?')) return;
  try {
    await apiDelete(`/chat-profiles/${id}`);
    showToast('채팅 프로필이 삭제되었습니다.', 'success');
    await loadChatProfiles();
  } catch (err) {
    showToast(`삭제 실패: ${err.message}`, 'error', 5000);
  }
}
