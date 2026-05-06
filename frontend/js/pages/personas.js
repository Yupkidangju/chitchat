// frontend/js/pages/personas.js
// [v1.0.0] VibeSmith 페르소나 관리 페이지
//
// 9섹션 동적 페르소나 카드 목록 조회 + Vibe Fill 생성 UI를 제공한다.

/**
 * 페르소나 페이지를 렌더링한다.
 * @param {HTMLElement} container
 */
async function renderPersonas(container) {
  container.innerHTML = `
    <div class="card">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
        <h2 class="card-title" style="margin: 0;">🤖 VibeSmith 페르소나</h2>
        <button class="btn btn-primary" id="btn-vibe-fill">✨ Vibe Fill</button>
      </div>
      <div id="persona-list"></div>
    </div>
    <div id="vibe-fill-modal" class="modal" style="display: none;"></div>
  `;

  await loadPersonas();

  document.getElementById('btn-vibe-fill').addEventListener('click', showVibeFillForm);
}

/**
 * 페르소나 목록을 API에서 가져와 렌더링한다.
 */
async function loadPersonas() {
  const listEl = document.getElementById('persona-list');
  try {
    const personas = await apiGet('/personas');
    if (personas.length === 0) {
      listEl.innerHTML = `
        <div style="text-align: center; padding: 3rem; color: var(--text-secondary);">
          <div style="font-size: 3rem; margin-bottom: 1rem;">🎭</div>
          <p style="font-size: 1.2rem;">페르소나가 없습니다</p>
          <p>'✨ Vibe Fill' 버튼으로 바이브만 입력하면<br>AI가 9섹션 캐릭터를 자동 생성합니다.</p>
        </div>
      `;
      return;
    }

    listEl.innerHTML = personas.map(p => `
      <div class="persona-card" data-id="${p.id}">
        <div class="persona-header">
          <strong class="persona-name">${escapeHtml(p.name)}</strong>
          <span class="persona-meta">${escapeHtml(p.age)} · ${escapeHtml(p.gender)} · ${escapeHtml(p.occupation)}</span>
        </div>
        <div class="persona-tension">
          <span class="label">핵심 긴장:</span> ${escapeHtml(p.core_tension)}
        </div>
        <div class="persona-footer">
          <span class="realism-badge">${p.realism_level}</span>
          <span class="persona-status ${p.enabled ? '' : 'disabled'}">${p.enabled ? '활성' : '비활성'}</span>
        </div>
      </div>
    `).join('');
  } catch (err) {
    listEl.innerHTML = `<p style="color: var(--danger);">로드 실패: ${err.message}</p>`;
  }
}

/**
 * Vibe Fill 생성 폼을 표시한다.
 */
function showVibeFillForm() {
  const modal = document.getElementById('vibe-fill-modal');
  modal.style.display = 'flex';
  modal.innerHTML = `
    <div class="modal-content card" style="max-width: 600px;">
      <h3 class="card-title">✨ Vibe Fill — 캐릭터 생성</h3>
      <p style="color: var(--text-secondary); margin-bottom: 1.5rem;">
        캐릭터의 분위기, 느낌, 키워드를 자유롭게 입력하세요.<br>
        AI가 9섹션의 살아있는 캐릭터를 자동 생성합니다.
      </p>
      <form id="vibe-fill-form">
        <div class="form-group">
          <label>바이브 텍스트</label>
          <textarea id="vf-text" class="input" rows="6"
            placeholder="예: 미대 지망생, 소심하지만 그림에 대해서는 열정적, 카페에서 아르바이트, 약간의 사회불안"
          ></textarea>
        </div>
        <div class="form-group">
          <label>출력 언어</label>
          <select id="vf-lang" class="input">
            <option value="ko">한국어</option>
            <option value="en">English</option>
          </select>
        </div>
        <div class="form-actions">
          <button type="submit" class="btn btn-primary" id="vf-submit">
            🎨 캐릭터 생성
          </button>
          <button type="button" class="btn" onclick="closeVibeFillForm()">취소</button>
        </div>
      </form>
      <div id="vf-result" style="margin-top: 1.5rem; display: none;"></div>
    </div>
  `;

  document.getElementById('vibe-fill-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = document.getElementById('vf-text').value.trim();
    if (!text) return;

    const submitBtn = document.getElementById('vf-submit');
    submitBtn.disabled = true;
    submitBtn.textContent = '⏳ 생성 중...';

    try {
      const result = await apiPost('/personas/vibe-fill', {
        vibe_text: text,
        output_language: document.getElementById('vf-lang').value,
      });

      const resultEl = document.getElementById('vf-result');
      resultEl.style.display = 'block';
      resultEl.innerHTML = `
        <div class="card" style="background: var(--surface-elevated);">
          <h4>생성 결과 미리보기</h4>
          <div class="result-grid">
            <div><strong>이름:</strong> ${escapeHtml(result.name)}</div>
            <div><strong>해석:</strong> ${escapeHtml(result.interpretation)}</div>
            <div><strong>리얼리즘:</strong> ${result.realism_level}</div>
            <div><strong>핵심 긴장:</strong> ${escapeHtml(result.core_tension)}</div>
          </div>
        </div>
      `;
    } catch (err) {
      showToast(`생성 실패: ${err.message}`, 'error', 5000);
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = '🎨 캐릭터 생성';
    }
  });
}

function closeVibeFillForm() {
  document.getElementById('vibe-fill-modal').style.display = 'none';
}
