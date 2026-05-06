// frontend/js/pages/lorebooks.js
// [v1.0.0] 로어북 관리 페이지
//
// Lorebook CRUD + LoreEntry 관리 UI.
// LoreEntry는 activation_keys를 쉼표 구분으로 입력받는다.

/**
 * 로어북 페이지를 렌더링한다.
 */
async function renderLorebooks(container) {
  container.innerHTML = `
    <div class="card">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
        <h2 class="card-title" style="margin: 0;">📖 로어북</h2>
        <button class="btn btn-primary" id="btn-add-lorebook">+ 새 로어북</button>
      </div>
      <div id="lorebook-list">
        <p style="color: var(--text-secondary);">로딩 중...</p>
      </div>
    </div>
    <div id="lb-detail" class="card" style="display: none; margin-top: 1rem;"></div>
    <div id="lb-modal" class="modal" style="display: none;"></div>
  `;

  await loadLorebooks();

  document.getElementById('btn-add-lorebook').addEventListener('click', () => {
    showLorebookCreateModal();
  });
}

async function loadLorebooks() {
  const listEl = document.getElementById('lorebook-list');
  try {
    const books = await apiGet('/lorebooks');
    if (books.length === 0) {
      listEl.innerHTML = '<div style="text-align: center; padding: 2rem; color: var(--text-secondary);"><p>로어북이 없습니다</p></div>';
      return;
    }
    listEl.innerHTML = books.map(b => `
      <div class="profile-card" data-id="${b.id}">
        <div class="profile-info" style="cursor: pointer;" onclick="showLoreEntries('${b.id}', '${escapeHtml(b.name)}')">
          <strong>${escapeHtml(b.name)}</strong>
          <span class="text-secondary" style="font-size: 0.8rem;">${escapeHtml(b.description || '설명 없음')}</span>
        </div>
        <div class="profile-actions">
          <button class="btn btn-sm btn-danger" onclick="deleteLorebook('${b.id}')">삭제</button>
        </div>
      </div>
    `).join('');
  } catch (err) {
    listEl.innerHTML = `<p style="color: var(--danger);">로드 실패: ${escapeHtml(err.message)}</p>`;
  }
}

function showLorebookCreateModal() {
  const modal = document.getElementById('lb-modal');
  modal.style.display = 'flex';
  modal.innerHTML = `
    <div class="modal-content card">
      <h3 class="card-title">새 로어북</h3>
      <form id="lb-create-form">
        <div class="form-group">
          <label>이름</label>
          <input type="text" id="lb-name" class="input" required>
        </div>
        <div class="form-group">
          <label>설명</label>
          <textarea id="lb-desc" class="input" rows="2"></textarea>
        </div>
        <div class="form-actions">
          <button type="submit" class="btn btn-primary">생성</button>
          <button type="button" class="btn" onclick="document.getElementById('lb-modal').style.display='none'">취소</button>
        </div>
      </form>
    </div>
  `;
  document.getElementById('lb-create-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await apiPost('/lorebooks', {
        name: document.getElementById('lb-name').value,
        description: document.getElementById('lb-desc').value,
      });
      modal.style.display = 'none';
      await loadLorebooks();
    } catch (err) { showToast(`오류: ${err.message}`, 'error', 5000); }
  });
}

async function deleteLorebook(id) {
  if (!confirm('이 로어북을 삭제하시겠습니까?')) return;
  try {
    await apiDelete(`/lorebooks/${id}`);
    showToast('로어북이 삭제되었습니다.', 'success');
    await loadLorebooks();
    document.getElementById('lb-detail').style.display = 'none';
  } catch (err) { showToast(`삭제 실패: ${err.message}`, 'error', 5000); }
}

/**
 * 로어북의 LoreEntry 목록을 표시한다.
 */
async function showLoreEntries(lorebookId, bookName) {
  const detail = document.getElementById('lb-detail');
  detail.style.display = 'block';
  detail.innerHTML = '<p style="color: var(--text-secondary);">로딩 중...</p>';

  try {
    const entries = await apiGet(`/lorebooks/${lorebookId}/entries`);
    let html = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
        <h3 class="card-title" style="margin: 0;">📝 ${escapeHtml(bookName)} 항목</h3>
        <button class="btn btn-primary btn-sm" onclick="showLoreEntryForm('${lorebookId}')">+ 항목 추가</button>
      </div>
    `;

    if (entries.length === 0) {
      html += '<p class="text-secondary">항목이 없습니다.</p>';
    } else {
      html += entries.map(e => `
        <div class="entry-item">
          <div><strong>${escapeHtml(e.title)}</strong> <span class="text-secondary">[${e.activation_keys.join(', ')}]</span></div>
          <div class="text-secondary" style="font-size: 0.8rem; margin: 0.25rem 0;">${escapeHtml(e.content.substring(0, 100))}${e.content.length > 100 ? '...' : ''}</div>
          <button class="btn btn-sm btn-danger" onclick="deleteLoreEntry('${e.id}', '${lorebookId}', '${escapeHtml(bookName)}')">삭제</button>
        </div>
      `).join('');
    }
    detail.innerHTML = html;
  } catch (err) {
    detail.innerHTML = `<p style="color: var(--danger);">로드 실패: ${err.message}</p>`;
  }
}

function showLoreEntryForm(lorebookId) {
  const modal = document.getElementById('lb-modal');
  modal.style.display = 'flex';
  modal.innerHTML = `
    <div class="modal-content card">
      <h3 class="card-title">새 로어 항목</h3>
      <form id="le-form">
        <div class="form-group"><label>제목</label><input type="text" id="le-title" class="input" required></div>
        <div class="form-group"><label>활성화 키워드 (쉼표 구분)</label><input type="text" id="le-keys" class="input" placeholder="검, 마법, 성문"></div>
        <div class="form-group"><label>내용</label><textarea id="le-content" class="input" rows="4"></textarea></div>
        <div class="form-group"><label>우선순위</label><input type="number" id="le-priority" class="input" value="100" min="0" max="1000"></div>
        <div class="form-actions">
          <button type="submit" class="btn btn-primary">추가</button>
          <button type="button" class="btn" onclick="document.getElementById('lb-modal').style.display='none'">취소</button>
        </div>
      </form>
    </div>
  `;
  document.getElementById('le-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const keys = document.getElementById('le-keys').value.split(',').map(k => k.trim()).filter(Boolean);
    try {
      await apiPost(`/lorebooks/${lorebookId}/entries`, {
        title: document.getElementById('le-title').value,
        activation_keys: keys,
        content: document.getElementById('le-content').value,
        priority: parseInt(document.getElementById('le-priority').value),
        enabled: true,
      });
      modal.style.display = 'none';
      await showLoreEntries(lorebookId, '로어북');
    } catch (err) { showToast(`오류: ${err.message}`, 'error', 5000); }
  });
}

async function deleteLoreEntry(entryId, lorebookId, bookName) {
  if (!confirm('이 항목을 삭제하시겠습니까?')) return;
  try {
    await apiDelete(`/lore-entries/${entryId}`);
    showToast('항목이 삭제되었습니다.', 'success');
    await showLoreEntries(lorebookId, bookName);
  } catch (err) { showToast(`삭제 실패: ${err.message}`, 'error', 5000); }
}
