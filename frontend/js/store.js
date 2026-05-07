// frontend/js/store.js
// [v1.1.1] Pub-Sub 패턴 중앙 상태 관리자
//
// 전역 변수를 제거하고 모든 모듈 간 상태를
// 이 싱글톤 Store를 통해 관리한다.

// 스토어 내부 상태 (외부 직접 접근 금지)
const _state = {
  currentSessionId: null,
  currentPage: 'chat',
  isStreaming: false,
};

// 구독자 맵: key → Set<callback>
const _subscribers = {};

/**
 * 상태 값을 읽는다.
 * @param {string} key
 * @returns {any}
 */
export function getState(key) {
  return _state[key];
}

/**
 * 상태 값을 설정하고, 해당 키의 구독자에게 알린다.
 * @param {string} key
 * @param {any} value
 */
export function setState(key, value) {
  const prev = _state[key];
  _state[key] = value;
  if (_subscribers[key]) {
    for (const fn of _subscribers[key]) {
      fn(value, prev);
    }
  }
}

/**
 * 특정 키의 변경을 구독한다.
 * @param {string} key
 * @param {function} callback - (newValue, oldValue) => void
 * @returns {function} 구독 해제 함수
 */
export function subscribe(key, callback) {
  if (!_subscribers[key]) _subscribers[key] = new Set();
  _subscribers[key].add(callback);
  return () => _subscribers[key].delete(callback);
}
