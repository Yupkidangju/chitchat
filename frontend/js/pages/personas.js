// frontend/js/pages/personas.js
// [v1.1.0] VibeSmith 페르소나 관리 페이지
//
// 9섹션 동적 페르소나 카드 목록 조회 + Vibe Fill 생성 + 수동 편집 UI.
// [v1.1.0 변경사항]
// - 편집 모달: 섹션별 접이식 UI + JSON 원문 편집 토글 (C안 하이브리드)
// - 카드 클릭 시 상세 보기 + 편집 기능

import { apiGet, apiPost, apiPut, apiDelete, escapeHtml, showToast } from '../api.js';

/**
 * 페르소나 페이지를 렌더링한다.
 * @param {HTMLElement} container
 */
export async function renderPersonas(container) {
  container.innerHTML = `
    <div class="card">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
        <h2 class="card-title" style="margin: 0;">🤖 VibeSmith 페르소나</h2>
        <button class="btn btn-primary" id="btn-vibe-fill">✨ Vibe Fill</button>
      </div>
      <div id="persona-list"></div>
    </div>
    <div id="vibe-fill-modal" class="modal" style="display: none;"></div>
    <div id="persona-edit-modal" class="modal" style="display: none;"></div>
  `;

  await loadPersonas();

  document.getElementById('btn-vibe-fill').addEventListener('click', showVibeFillForm);

  // [v1.1.1] 이벤트 위임 — data-action 기반 핸들러
  container.addEventListener('click', (e) => {
    const el = e.target.closest('[data-action]');
    if (!el) return;
    e.stopPropagation();
    const actionId = el.dataset.id;
    switch (el.dataset.action) {
      case 'showPersonaEditModal': showPersonaEditModal(actionId); break;
      case 'deletePersona': deletePersona(actionId); break;
      case 'closeVibeFillForm': closeVibeFillForm(); break;
      case 'closeModal': {
        const mid = el.dataset.modalId;
        if (mid) { const modal = document.getElementById(mid); if (modal) modal.style.display = 'none'; }
        break;
      }
    }
  });
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
      <div class="persona-card" data-id="${p.id}" style="cursor: pointer;" data-action="showPersonaEditModal" data-id="${p.id}">
        <div class="persona-header">
          <strong class="persona-name">${escapeHtml(p.name)}</strong>
          <span class="persona-meta">${escapeHtml(p.age)} · ${escapeHtml(p.gender)} · ${escapeHtml(p.occupation)}</span>
        </div>
        <div class="persona-tension">
          <span class="label">핵심 긴장:</span> ${escapeHtml(p.core_tension)}
        </div>
        <div class="persona-footer">
          <div>
            <span class="realism-badge">${p.realism_level}</span>
            <span class="persona-status ${p.enabled ? '' : 'disabled'}">${p.enabled ? '활성' : '비활성'}</span>
          </div>
          <div style="display: flex; gap: 0.5rem;">
            <button class="btn btn-sm" data-action="showPersonaEditModal" data-id="${p.id}">편집</button>
            <button class="btn btn-sm btn-danger" data-action="deletePersona" data-id="${p.id}">삭제</button>
          </div>
        </div>
      </div>
    `).join('');
  } catch (err) {
    showToast(`로드 실패: ${err.message}`, 'error', 5000);
    listEl.innerHTML = '<p class="session-empty">데이터를 불러올 수 없습니다</p>';
  }
}

/**
 * [v1.0.0] 페르소나를 삭제한다.
 * 참조 무결성 오류(409) 시 에러 토스트를 표시한다.
 */
async function deletePersona(id) {
  if (!confirm('이 페르소나를 삭제하시겠습니까?')) return;
  try {
    await apiDelete(`/personas/${id}`);
    showToast('페르소나가 삭제되었습니다.', 'success');
    await loadPersonas();
  } catch (err) {
    showToast(`삭제 실패: ${err.message}`, 'error', 5000);
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
          <button type="button" class="btn" data-action="closeVibeFillForm">취소</button>
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
      showToast('캐릭터가 생성되었습니다!', 'success');
      await loadPersonas();
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

// ━━━ [v1.1.0] 페르소나 편집 모달 (섹션별 접이식 + JSON 토글) ━━━

// VibeSmith 9섹션 구조의 한국어 라벨 정의
const PERSONA_SECTIONS = [
  { key: 'generation_summary', label: '📋 생성 요약', fields: ['input_vibe', 'interpretation', 'realism_level', 'core_tension'] },
  { key: 'fixed_canon', label: '📌 고정 설정', subsections: [
    { key: 'identity', label: '신원', fields: ['name', 'age', 'gender', 'birthday', 'cultural_context', 'current_location', 'occupation', 'education'] },
    { key: 'appearance', label: '외모', fields: ['height', 'build', 'face_impression', 'hair', 'eyes', 'clothing_style', 'notable_details', 'usual_posture', 'voice'] },
    { key: 'living', label: '생활', fields: ['housing', 'financial_situation', 'family_structure', 'daily_routine', 'frequent_places', 'important_possessions', 'current_life_problem', 'recent_life_change'] },
    { key: 'skills', label: '능력', fields: ['main_skills', 'secondary_skills', 'hobbies', 'private_interests', 'weak_areas', 'things_avoided'] },
  ]},
  { key: 'core_dynamic', label: '💫 핵심 동력' },
  { key: 'social_model', label: '🤝 사회적 모델' },
  { key: 'behavior_rules', label: '📏 행동 규칙' },
  { key: 'habits', label: '🔄 습관' },
  { key: 'emotional_dynamics', label: '💭 감정 역학' },
  { key: 'memory_policy', label: '🧠 기억 정책' },
  { key: 'response_rules', label: '📜 응답 규칙' },
  { key: 'coherence_report', label: '✅ 일관성 보고서' },
];

/**
 * 페르소나 편집 모달을 표시한다.
 * 섹션별 접이식 UI와 JSON 원문 편집 모드를 지원한다.
 * @param {string} personaId - 편집할 페르소나 ID
 */
async function showPersonaEditModal(personaId) {
  const modal = document.getElementById('persona-edit-modal');
  modal.style.display = 'flex';
  modal.innerHTML = '<div class="modal-content card"><p style="color: var(--text-secondary);">로딩 중...</p></div>';

  try {
    const persona = await apiGet(`/personas/${personaId}`);
    const data = persona.persona_json || {};

    modal.innerHTML = `
      <div class="modal-content card" style="max-width: 750px; max-height: 85vh; overflow-y: auto;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
          <h3 class="card-title" style="margin: 0;">✏️ 페르소나 편집 — ${escapeHtml(persona.name)}</h3>
          <label style="display: flex; align-items: center; gap: 0.5rem; font-size: 0.85rem; cursor: pointer;">
            <input type="checkbox" id="pe-json-toggle">
            JSON 모드
          </label>
        </div>

        <form id="pe-edit-form">
          <div class="form-group">
            <label>이름</label>
            <input type="text" id="pe-name" class="input" value="${escapeHtml(persona.name)}" required>
          </div>
          <div class="form-group">
            <label style="display: flex; align-items: center; gap: 0.5rem;">
              <input type="checkbox" id="pe-enabled" ${persona.enabled ? 'checked' : ''}>
              활성화
            </label>
          </div>

          <!-- 섹션별 편집 UI -->
          <div id="pe-sections-view">
            ${renderPersonaSections(data)}
          </div>

          <!-- JSON 원문 편집 (기본 숨김) -->
          <div id="pe-json-view" style="display: none;">
            <div class="form-group">
              <label>Persona JSON (원문 편집)</label>
              <textarea id="pe-json-editor" class="input" rows="20" style="font-family: monospace; font-size: 0.85rem;">${escapeHtml(JSON.stringify(data, null, 2))}</textarea>
            </div>
          </div>

          <div class="form-actions">
            <button type="submit" class="btn btn-primary">💾 저장</button>
            <button type="button" class="btn" data-action="closeModal" data-modal-id="persona-edit-modal">취소</button>
          </div>
        </form>
      </div>
    `;

    // JSON 모드 토글
    document.getElementById('pe-json-toggle').addEventListener('change', (e) => {
      const sectionsView = document.getElementById('pe-sections-view');
      const jsonView = document.getElementById('pe-json-view');
      if (e.target.checked) {
        // 섹션 → JSON: 섹션에서 수집한 데이터를 JSON 에디터에 반영
        const collected = collectSectionsData(data);
        document.getElementById('pe-json-editor').value = JSON.stringify(collected, null, 2);
        sectionsView.style.display = 'none';
        jsonView.style.display = 'block';
      } else {
        jsonView.style.display = 'none';
        sectionsView.style.display = 'block';
      }
    });

    // 저장 핸들러
    document.getElementById('pe-edit-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const isJsonMode = document.getElementById('pe-json-toggle').checked;
      let personaJson;

      if (isJsonMode) {
        try {
          personaJson = JSON.parse(document.getElementById('pe-json-editor').value);
        } catch (err) {
          showToast('JSON 파싱 오류: ' + err.message, 'error', 5000);
          return;
        }
      } else {
        personaJson = collectSectionsData(data);
      }

      try {
        await apiPut(`/personas/${personaId}`, {
          name: document.getElementById('pe-name').value,
          persona_json: personaJson,
          enabled: document.getElementById('pe-enabled').checked,
        });
        modal.style.display = 'none';
        showToast('페르소나가 수정되었습니다.', 'success');
        await loadPersonas();
      } catch (err) {
        showToast(`수정 실패: ${err.message}`, 'error', 5000);
      }
    });

  } catch (err) {
    showToast(`로드 실패: ${err.message}`, 'error', 5000);
    modal.innerHTML = '<div class="modal-content card"><p class="session-empty">데이터를 불러올 수 없습니다</p></div>';
  }
}

/**
 * 섹션별 접이식 UI를 HTML로 렌더링한다.
 * @param {object} data - persona_json 데이터
 * @returns {string} HTML 문자열
 */
function renderPersonaSections(data) {
  let html = '';
  for (const section of PERSONA_SECTIONS) {
    const sectionData = data[section.key] || {};
    html += `
      <details class="pe-section" style="margin-bottom: 0.5rem; border: 1px solid var(--border); border-radius: 6px;">
        <summary style="padding: 0.6rem 0.8rem; cursor: pointer; font-weight: 600; user-select: none;">
          ${section.label}
        </summary>
        <div style="padding: 0.5rem 0.8rem;">
    `;

    if (section.subsections) {
      // fixed_canon의 경우 하위 섹션별로 나누어 표시
      for (const sub of section.subsections) {
        const subData = sectionData[sub.key] || {};
        html += `<div style="margin-bottom: 0.75rem;"><strong style="font-size: 0.9rem;">${sub.label}</strong></div>`;
        if (sub.fields) {
          for (const field of sub.fields) {
            const value = subData[field] || '';
            const strVal = typeof value === 'object' ? JSON.stringify(value) : String(value);
            html += `
              <div class="form-group" style="margin-bottom: 0.4rem;">
                <label style="font-size: 0.8rem; color: var(--text-secondary);">${field}</label>
                <input type="text" class="input pe-field" data-section="${section.key}" data-sub="${sub.key}" data-field="${field}" value="${escapeHtml(strVal)}" style="font-size: 0.85rem;">
              </div>
            `;
          }
        }
      }
    } else if (section.fields) {
      // generation_summary 등 플랫 필드
      for (const field of section.fields) {
        const value = sectionData[field] || '';
        const strVal = typeof value === 'object' ? JSON.stringify(value) : String(value);
        html += `
          <div class="form-group" style="margin-bottom: 0.4rem;">
            <label style="font-size: 0.8rem; color: var(--text-secondary);">${field}</label>
            <input type="text" class="input pe-field" data-section="${section.key}" data-field="${field}" value="${escapeHtml(strVal)}" style="font-size: 0.85rem;">
          </div>
        `;
      }
    } else {
      // 복잡한 중첩 구조 — JSON 문자열로 편집
      const jsonStr = JSON.stringify(sectionData, null, 2);
      html += `
        <div class="form-group">
          <textarea class="input pe-json-section" data-section="${section.key}" rows="6" style="font-family: monospace; font-size: 0.8rem;">${escapeHtml(jsonStr)}</textarea>
        </div>
      `;
    }

    html += `</div></details>`;
  }
  return html;
}

/**
 * 섹션별 편집 UI에서 데이터를 수집하여 persona_json 객체로 반환한다.
 * @param {object} originalData - 원본 persona_json
 * @returns {object} 갱신된 persona_json
 */
function collectSectionsData(originalData) {
  const result = JSON.parse(JSON.stringify(originalData));

  // 플랫 필드 수집 (pe-field)
  document.querySelectorAll('.pe-field').forEach(input => {
    const section = input.dataset.section;
    const sub = input.dataset.sub;
    const field = input.dataset.field;
    let value = input.value;

    // JSON 값 시도 파싱
    try {
      const parsed = JSON.parse(value);
      if (typeof parsed === 'object') value = parsed;
    } catch { /* 문자열 유지 */ }

    if (sub) {
      if (!result[section]) result[section] = {};
      if (!result[section][sub]) result[section][sub] = {};
      result[section][sub][field] = value;
    } else {
      if (!result[section]) result[section] = {};
      result[section][field] = value;
    }
  });

  // JSON 섹션 수집 (pe-json-section)
  document.querySelectorAll('.pe-json-section').forEach(textarea => {
    const section = textarea.dataset.section;
    try {
      result[section] = JSON.parse(textarea.value);
    } catch {
      // 파싱 실패 시 원본 유지
    }
  });

  return result;
}


