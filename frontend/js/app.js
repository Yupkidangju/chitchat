// frontend/js/app.js
// [v1.0.0] SPA 라우터 및 초기화
//
// 사이드바 네비게이션 클릭에 따라 페이지를 동적으로 로드한다.
// 각 페이지 모듈은 render() 함수를 export하여 #page-container에 렌더링한다.

const pageContainer = document.getElementById('page-container');
const navItems = document.querySelectorAll('.nav-item');

// 현재 활성 페이지
let currentPage = 'chat';

// 페이지 모듈 맵
const pageModules = {};

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

  // 페이지 콘텐츠 렌더링
  pageContainer.innerHTML = `
    <div class="card">
      <h2 class="card-title">${getPageTitle(pageName)}</h2>
      <p style="color: var(--text-secondary);">
        이 페이지는 v1.0.0 리팩토링 중 구현될 예정입니다.
      </p>
    </div>
  `;
}

/**
 * 페이지 이름으로 타이틀을 반환한다.
 * @param {string} pageName
 * @returns {string}
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

// 초기 헬스체크
async function init() {
  try {
    const res = await fetch('/api/health');
    const data = await res.json();
    console.log('chitchat 서버 연결 성공:', data);
  } catch (err) {
    console.error('서버 연결 실패:', err);
  }
}

init();
