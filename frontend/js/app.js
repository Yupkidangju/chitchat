// frontend/js/app.js
// [v1.1.1] ES6 모듈 기반 SPA 라우터 및 초기화
//
// 단일 진입점으로 모든 페이지 모듈을 import하고,
// 사이드바 네비게이션에 따라 페이지를 동적으로 로드한다.
// 전역 변수를 사용하지 않고 store.js를 통해 상태를 관리한다.

import { apiGet } from './api.js';
import { setState } from './store.js';
import { renderChat } from './pages/chat.js';
import { renderProviders } from './pages/providers.js';
import { renderModels } from './pages/models.js';
import { renderPersonas } from './pages/personas.js';
import { renderLorebooks } from './pages/lorebooks.js';
import { renderWorldbooks } from './pages/worldbooks.js';
import { renderChatProfiles } from './pages/chat_profiles.js';
import { renderPromptOrder } from './pages/prompt_order.js';
import { renderSettings, applyFontSize, applyTheme } from './pages/settings.js';

const pageContainer = document.getElementById('page-container');
const navItems = document.querySelectorAll('.nav-item');

/**
 * 페이지를 전환한다.
 * @param {string} pageName - 페이지 이름
 */
async function navigateTo(pageName) {
  // 네비게이션 활성 상태 갱신
  navItems.forEach(item => {
    item.classList.toggle('active', item.dataset.page === pageName);
  });

  setState('currentPage', pageName);

  // 페이지별 렌더링 함수 호출
  const renderers = {
    'chat': renderChat,
    'providers': renderProviders,
    'models': renderModels,
    'personas': renderPersonas,
    'lorebooks': renderLorebooks,
    'worldbooks': renderWorldbooks,
    'chat-profiles': renderChatProfiles,
    'prompt-order': renderPromptOrder,
    'settings': renderSettings,
  };

  const render = renderers[pageName];
  if (render) {
    await render(pageContainer);
  } else {
    pageContainer.innerHTML = `
      <div class="card">
        <h2 class="card-title">${pageName}</h2>
        <p style="color: var(--text-secondary);">
          이 페이지는 후속 업데이트에서 구현될 예정입니다.
        </p>
      </div>
    `;
  }
}

// 네비게이션 이벤트 바인딩
navItems.forEach(item => {
  item.addEventListener('click', () => {
    navigateTo(item.dataset.page);
  });
});

// 초기화
async function init() {
  try {
    const res = await fetch('/api/health');
    const data = await res.json();
    console.log('chitchat 서버 연결 성공:', data);
  } catch (err) {
    console.error('서버 연결 실패:', err);
  }

  // [v1.0.0] 저장된 설정(테마, 폰트)을 로드하여 즉시 적용
  try {
    const settings = await apiGet('/settings');
    if (settings.theme) applyTheme(settings.theme);
    if (settings.font_size) applyFontSize(settings.font_size);
  } catch {
    // 설정 로드 실패 시 기본값 유지 (다크 테마, medium 폰트)
  }

  // 기본 페이지 렌더링
  try {
    await navigateTo('chat');
  } catch (err) {
    console.error('초기 페이지 렌더링 실패:', err);
    pageContainer.innerHTML = `<div class="card"><h2>⚠️ 초기화 오류</h2><pre style="color: var(--danger);">${err.stack || err.message}</pre></div>`;
  }
}

init().catch(err => {
  console.error('init() 전체 실패:', err);
});
