// frontend/js/api.js
// [v1.0.0] API 클라이언트 유틸리티
//
// 백엔드 REST API와 WebSocket 통신을 위한 공통 함수를 제공한다.

const API_BASE = '/api';

/**
 * GET 요청을 보낸다.
 * @param {string} path - API 경로 (예: '/providers')
 * @returns {Promise<any>} JSON 응답
 */
async function apiGet(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

/**
 * POST 요청을 보낸다.
 * @param {string} path - API 경로
 * @param {object} body - 요청 본문
 * @returns {Promise<any>} JSON 응답
 */
async function apiPost(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

/**
 * PUT 요청을 보낸다.
 */
async function apiPut(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

/**
 * DELETE 요청을 보낸다.
 */
async function apiDelete(path) {
  const res = await fetch(`${API_BASE}${path}`, { method: 'DELETE' });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

/**
 * HTML 특수문자를 이스케이프한다.
 * [v1.0.0] providers.js에서 전역 모듈로 이동 (교훈 12번)
 * @param {string} str
 * @returns {string}
 */
function escapeHtml(str) {
  const el = document.createElement('span');
  el.textContent = str;
  return el.innerHTML;
}

/**
 * [v1.0.0] 토스트 알림을 표시한다.
 * 타입별 색상(success, error, info, warning)으로 구분하며,
 * 3초 후 자동으로 사라진다.
 * @param {string} message - 알림 메시지
 * @param {'success'|'error'|'info'|'warning'} type - 알림 타입 (기본: info)
 * @param {number} duration - 표시 시간(ms, 기본: 3000)
 */
function showToast(message, type = 'info', duration = 3000) {
  // 컨테이너가 없으면 생성
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  // 토스트 요소 생성
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;

  // 아이콘 매핑
  const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
  toast.textContent = `${icons[type] || 'ℹ️'} ${message}`;

  container.appendChild(toast);

  // 애니메이션 후 제거
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}
