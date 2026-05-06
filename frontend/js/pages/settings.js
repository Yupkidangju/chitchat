// frontend/js/pages/settings.js
// [v1.0.0] 설정 페이지 — 언어 설정 관리

/**
 * 설정 페이지를 렌더링한다.
 * @param {HTMLElement} container
 */
async function renderSettings(container) {
  container.innerHTML = `
    <div class="card">
      <h2 class="card-title">⚡ 설정</h2>
      <div id="settings-content">
        <p style="color: var(--text-secondary);">설정 로딩 중...</p>
      </div>
    </div>
  `;

  try {
    const settings = await apiGet('/settings');
    const contentEl = document.getElementById('settings-content');
    contentEl.innerHTML = `
      <div class="settings-section">
        <h3 class="settings-section-title">🌐 언어 설정</h3>
        <div class="form-group">
          <label>UI 표시 언어</label>
          <select id="set-locale" class="input">
            <option value="ko" ${settings.ui_locale === 'ko' ? 'selected' : ''}>한국어</option>
            <option value="en" ${settings.ui_locale === 'en' ? 'selected' : ''}>English</option>
            <option value="ja" ${settings.ui_locale === 'ja' ? 'selected' : ''}>日本語</option>
            <option value="zh_tw" ${settings.ui_locale === 'zh_tw' ? 'selected' : ''}>繁體中文</option>
            <option value="zh_cn" ${settings.ui_locale === 'zh_cn' ? 'selected' : ''}>简体中文</option>
          </select>
        </div>
        <div class="form-group">
          <label>Vibe Fill 출력 언어</label>
          <select id="set-vibe-lang" class="input">
            <option value="ko" ${settings.vibe_output_language === 'ko' ? 'selected' : ''}>한국어</option>
            <option value="en" ${settings.vibe_output_language === 'en' ? 'selected' : ''}>English</option>
          </select>
        </div>
        <button class="btn btn-primary" id="btn-save-settings">저장</button>
        <span id="settings-status" style="margin-left: 1rem; color: var(--success);"></span>
      </div>
    `;

    document.getElementById('btn-save-settings').addEventListener('click', async () => {
      try {
        await apiPut('/settings', {
          ui_locale: document.getElementById('set-locale').value,
          vibe_output_language: document.getElementById('set-vibe-lang').value,
        });
        document.getElementById('settings-status').textContent = '✅ 저장 완료';
        setTimeout(() => {
          document.getElementById('settings-status').textContent = '';
        }, 2000);
      } catch (err) {
        alert(`저장 실패: ${err.message}`);
      }
    });
  } catch (err) {
    document.getElementById('settings-content').innerHTML =
      `<p style="color: var(--danger);">설정 로드 실패: ${err.message}</p>`;
  }
}
