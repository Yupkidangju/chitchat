// frontend/js/pages/settings.js
// [v1.0.0] 설정 페이지 — DD-12 범위 구현
//
// 언어 설정, 표시 설정 (테마, 폰트 크기), 일반 설정 (스트리밍, 기본 Provider),
// 데이터 관리 (앱 경로 표시, 설정 초기화) 섹션으로 구성된다.

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

  // Provider 목록과 설정을 병렬 로드
  let settings = {};
  let providers = [];
  try {
    [settings, providers] = await Promise.all([
      apiGet('/settings'),
      apiGet('/providers'),
    ]);
  } catch (err) {
    document.getElementById('settings-content').innerHTML =
      `<p style="color: var(--danger);">설정 로드 실패: ${err.message}</p>`;
    return;
  }

  // Provider 옵션 목록 생성
  const providerOptions = providers.map(p =>
    `<option value="${p.id}" ${settings.default_provider_id === p.id ? 'selected' : ''}>${escapeHtml(p.name)} (${p.provider_kind})</option>`
  ).join('');

  const contentEl = document.getElementById('settings-content');
  contentEl.innerHTML = `
    <!-- 언어 설정 섹션 -->
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
    </div>

    <!-- 표시 설정 섹션 -->
    <div class="settings-section" style="margin-top: 1.5rem;">
      <h3 class="settings-section-title">🎨 표시 설정</h3>
      <div class="form-group">
        <label>테마</label>
        <select id="set-theme" class="input">
          <option value="light" ${settings.theme === 'light' ? 'selected' : ''}>☀️ 라이트</option>
          <option value="dark" ${settings.theme === 'dark' ? 'selected' : ''}>🌙 다크 (향후 지원)</option>
        </select>
      </div>
      <div class="form-group">
        <label>폰트 크기</label>
        <select id="set-font-size" class="input">
          <option value="small" ${settings.font_size === 'small' ? 'selected' : ''}>작게 (13px)</option>
          <option value="medium" ${settings.font_size === 'medium' ? 'selected' : ''}>보통 (14px)</option>
          <option value="large" ${settings.font_size === 'large' ? 'selected' : ''}>크게 (16px)</option>
        </select>
      </div>
    </div>

    <!-- 일반 설정 섹션 -->
    <div class="settings-section" style="margin-top: 1.5rem;">
      <h3 class="settings-section-title">⚙️ 일반 설정</h3>
      <div class="form-group">
        <label>스트리밍 채팅</label>
        <select id="set-streaming" class="input">
          <option value="true" ${settings.streaming_enabled ? 'selected' : ''}>활성화</option>
          <option value="false" ${!settings.streaming_enabled ? 'selected' : ''}>비활성화</option>
        </select>
        <small style="color: var(--text-muted); font-size: 0.75rem; display: block; margin-top: 4px;">
          비활성화하면 AI 응답이 한 번에 표시됩니다.
        </small>
      </div>
      <div class="form-group">
        <label>기본 Provider</label>
        <select id="set-default-provider" class="input">
          <option value="">선택 안 함</option>
          ${providerOptions}
        </select>
      </div>
    </div>

    <!-- 저장 버튼 -->
    <div style="margin-top: 1.5rem; display: flex; gap: 0.5rem; align-items: center;">
      <button class="btn btn-primary" id="btn-save-settings">💾 저장</button>
      <span id="settings-status" style="color: var(--success); font-size: 0.85rem;"></span>
    </div>

    <!-- 데이터 관리 섹션 -->
    <div class="settings-section" style="margin-top: 2rem; padding-top: 1.5rem; border-top: 2px solid var(--border);">
      <h3 class="settings-section-title">🗂️ 데이터 관리</h3>
      <div class="form-group">
        <label>앱 데이터 경로</label>
        <input type="text" class="input" value="${escapeHtml(settings.app_data_dir)}" readonly
          style="background: var(--bg-secondary); cursor: default; font-family: var(--font-mono); font-size: 0.8rem;">
      </div>
      <div style="margin-top: 0.75rem;">
        <button class="btn btn-danger" id="btn-reset-settings">🔄 설정 초기화</button>
        <small style="color: var(--text-muted); font-size: 0.75rem; display: block; margin-top: 4px;">
          모든 설정을 기본값으로 되돌립니다. 프로필과 세션 데이터는 유지됩니다.
        </small>
      </div>
    </div>
  `;

  // 저장 버튼 이벤트
  document.getElementById('btn-save-settings').addEventListener('click', async () => {
    try {
      await apiPut('/settings', {
        ui_locale: document.getElementById('set-locale').value,
        vibe_output_language: document.getElementById('set-vibe-lang').value,
        theme: document.getElementById('set-theme').value,
        font_size: document.getElementById('set-font-size').value,
        streaming_enabled: document.getElementById('set-streaming').value === 'true',
        default_provider_id: document.getElementById('set-default-provider').value,
      });

      // [v1.0.0] 폰트 크기 즉시 적용
      applyFontSize(document.getElementById('set-font-size').value);

      document.getElementById('settings-status').textContent = '✅ 저장 완료';
      setTimeout(() => {
        const statusEl = document.getElementById('settings-status');
        if (statusEl) statusEl.textContent = '';
      }, 2000);
    } catch (err) {
      showToast(`저장 실패: ${err.message}`, 'error', 5000);
    }
  });

  // 설정 초기화 버튼 이벤트
  document.getElementById('btn-reset-settings').addEventListener('click', async () => {
    if (!confirm('모든 설정을 기본값으로 초기화하시겠습니까?')) return;
    try {
      await apiPost('/settings/reset', {});
      // 폰트 크기 기본값 적용
      applyFontSize('medium');
      // 페이지 새로고침하여 설정 반영
      await renderSettings(container);
    } catch (err) {
      showToast(`초기화 실패: ${err.message}`, 'error', 5000);
    }
  });
}

/**
 * [v1.0.0] 폰트 크기를 즉시 적용한다.
 * CSS 변수 --font-size-base를 동적으로 변경한다.
 */
function applyFontSize(size) {
  const sizeMap = { small: '13px', medium: '14px', large: '16px' };
  document.documentElement.style.setProperty('--font-size-base', sizeMap[size] || '14px');
}
