// frontend/js/app.js
// [v1.0.0] SPA 라우터 및 초기화
//
// 사이드바 네비게이션 클릭에 따라 페이지를 동적으로 로드한다.
// 각 페이지 모듈의 render() 함수를 호출하여 #page-container에 렌더링한다.

const pageContainer = document.getElementById('page-container');
const navItems = document.querySelectorAll('.nav-item');

// 현재 활성 페이지
let currentPage = 'chat';

/**
 * 페이지를 전환한다.
 * @param {string} pageName - 페이지 이름
 */
async function navigateTo(pageName) {
  // 네비게이션 활성 상태 갱신
  navItems.forEach(item => {
    item.classList.toggle('active', item.dataset.page === pageName);
  });

  currentPage = pageName;

  // 페이지별 렌더링 함수 호출
  switch (pageName) {
    case 'chat':
      await renderChat(pageContainer);
      break;
    case 'providers':
      await renderProviders(pageContainer);
      break;
    case 'models':
      await renderModels(pageContainer);
      break;
    case 'personas':
      await renderPersonas(pageContainer);
      break;
    case 'lorebooks':
      await renderLorebooks(pageContainer);
      break;
    case 'worldbooks':
      await renderWorldbooks(pageContainer);
      break;
    case 'chat-profiles':
      await renderChatProfiles(pageContainer);
      break;
    case 'prompt-order':
      await renderPromptOrder(pageContainer);
      break;
    case 'settings':
      await renderSettings(pageContainer);
      break;
    default:
      // 아직 구현되지 않은 페이지
      pageContainer.innerHTML = `
        <div class="card">
          <h2 class="card-title">${getPageTitle(pageName)}</h2>
          <p style="color: var(--text-secondary);">
            이 페이지는 v1.0.0 후속 업데이트에서 구현될 예정입니다.
          </p>
        </div>
      `;
  }
}

/**
 * 페이지 이름으로 타이틀을 반환한다.
 */
function getPageTitle(pageName) {
  const titles = {
    'chat': '💬 채팅',
    'providers': '🔌 공급자 관리',
    'models': '⚙️ 모델 설정',
    'personas': '🤖 VibeSmith 페르소나',
    'lorebooks': '📖 로어북',
    'worldbooks': '🌍 월드북',
    'chat-profiles': '🎯 채팅 프로필',
    'prompt-order': '📝 프롬프트 순서',
    'settings': '⚡ 설정',
  };
  return titles[pageName] || pageName;
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
  navigateTo(currentPage);
}

init();
