// frontend/js/pages/worldbooks.js
// [v1.0.0] 월드북 관리 페이지
//
// Worldbook CRUD + WorldEntry 관리 UI.

/**
 * 월드북 페이지를 렌더링한다.
 */
async function renderWorldbooks(container) {
  container.innerHTML = `
    <div class="card">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
        <h2 class="card-title" style="margin: 0;">🌍 월드북</h2>
        <button class="btn btn-primary" id="btn-add-worldbook">+ 새 월드북</button>
      </div>
      <div id="worldbook-list">
        <p style="color: var(--text-secondary);">로딩 중...</p>
      </div>
    </div>
    <div id="wb-detail" class="card" style="display: none; margin-top: 1rem;"></div>
    <div id="wb-modal" class="modal" style="display: none;"></div>
  `;

  await loadWorldbooks();

  document.getElementById('btn-add-worldbook').addEventListener('click', () => {
    showWorldbookCreateModal();
  });
}

async function loadWorldbooks() {
  const listEl = document.getElementById('worldbook-list');
  try {
    const books = await apiGet('/worldbooks');
    if (books.length === 0) {
      listEl.innerHTML = '<div style="text-align: center; padding: 2rem; color: var(--text-secondary);"><p>월드북이 없습니다</p></div>';
      return;
    }
    listEl.innerHTML = books.map(b => `
      <div class="profile-card" data-id="${b.id}">
        <div class="profile-info" style="cursor: pointer;" onclick="showWorldEntries('${b.id}', '${escapeHtml(b.name)}')">
          <strong>${escapeHtml(b.name)}</strong>
          <span class="text-secondary" style="font-size: 0.8rem;">${escapeHtml(b.description || '설명 없음')}</span>
        </div>
        <div class="profile-actions">
          <button class="btn btn-sm btn-danger" onclick="deleteWorldbook('${b.id}')">삭제</button>
        </div>
      </div>
    `).join('');
  } catch (err) {
    listEl.innerHTML = `<p style="color: var(--danger);">로드 실패: ${escapeHtml(err.message)}</p>`;
  }
}

function showWorldbookCreateModal() {
  const modal = document.getElementById('wb-modal');
  modal.style.display = 'flex';
  modal.innerHTML = `
    <div class="modal-content card">
      <h3 class="card-title">새 월드북</h3>
      <form id="wb-create-form">
        <div class="form-group">
          <label>이름</label>
          <input type="text" id="wb-name" class="input" required>
        </div>
        <div class="form-group">
          <label>설명</label>
          <textarea id="wb-desc" class="input" rows="2"></textarea>
        </div>
        <div class="form-actions">
          <button type="submit" class="btn btn-primary">생성</button>
          <button type="button" class="btn" onclick="document.getElementById('wb-modal').style.display='none'">취소</button>
        </div>
      </form>
    </div>
  `;
  document.getElementById('wb-create-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await apiPost('/worldbooks', {
        name: document.getElementById('wb-name').value,
        description: document.getElementById('wb-desc').value,
      });
      modal.style.display = 'none';
      await loadWorldbooks();
    } catch (err) { showToast(`오류: ${err.message}`, 'error', 5000); }
  });
}

async function deleteWorldbook(id) {
  if (!confirm('이 월드북을 삭제하시겠습니까?')) return;
  try {
    await apiDelete(`/worldbooks/${id}`);
    showToast('월드북이 삭제되었습니다.', 'success');
    await loadWorldbooks();
    document.getElementById('wb-detail').style.display = 'none';
  } catch (err) { showToast(`삭제 실패: ${err.message}`, 'error', 5000); }
}

async function showWorldEntries(worldbookId, bookName) {
  const detail = document.getElementById('wb-detail');
  detail.style.display = 'block';
  detail.innerHTML = '<p style="color: var(--text-secondary);">로딩 중...</p>';

  try {
    const entries = await apiGet(`/worldbooks/${worldbookId}/entries`);
    let html = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
        <h3 class="card-title" style="margin: 0;">🌐 ${escapeHtml(bookName)} 항목</h3>
        <button class="btn btn-primary btn-sm" onclick="showWorldEntryForm('${worldbookId}')">+ 항목 추가</button>
      </div>
    `;

    if (entries.length === 0) {
      html += '<p class="text-secondary">항목이 없습니다.</p>';
    } else {
      html += entries.map(e => `
        <div class="entry-item">
          <div><strong>${escapeHtml(e.title)}</strong></div>
          <div class="text-secondary" style="font-size: 0.8rem; margin: 0.25rem 0;">${escapeHtml(e.content.substring(0, 100))}${e.content.length > 100 ? '...' : ''}</div>
          <button class="btn btn-sm btn-danger" onclick="deleteWorldEntry('${e.id}', '${worldbookId}', '${escapeHtml(bookName)}')">삭제</button>
        </div>
      `).join('');
    }
    detail.innerHTML = html;
  } catch (err) {
    detail.innerHTML = `<p style="color: var(--danger);">로드 실패: ${err.message}</p>`;
  }
}

function showWorldEntryForm(worldbookId) {
  const modal = document.getElementById('wb-modal');
  modal.style.display = 'flex';
  modal.innerHTML = `
    <div class="modal-content card">
      <h3 class="card-title">새 월드 항목</h3>
      <form id="we-form">
        <div class="form-group"><label>제목</label><input type="text" id="we-title" class="input" required></div>
        <div class="form-group"><label>내용</label><textarea id="we-content" class="input" rows="4"></textarea></div>
        <div class="form-group"><label>우선순위</label><input type="number" id="we-priority" class="input" value="100" min="0" max="1000"></div>
        <div class="form-actions">
          <button type="submit" class="btn btn-primary">추가</button>
          <button type="button" class="btn" onclick="document.getElementById('wb-modal').style.display='none'">취소</button>
        </div>
      </form>
    </div>
  `;
  document.getElementById('we-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await apiPost(`/worldbooks/${worldbookId}/entries`, {
        title: document.getElementById('we-title').value,
        content: document.getElementById('we-content').value,
        priority: parseInt(document.getElementById('we-priority').value),
        enabled: true,
      });
      modal.style.display = 'none';
      await showWorldEntries(worldbookId, '월드북');
    } catch (err) { showToast(`오류: ${err.message}`, 'error', 5000); }
  });
}

async function deleteWorldEntry(entryId, worldbookId, bookName) {
  if (!confirm('이 항목을 삭제하시겠습니까?')) return;
  try {
    await apiDelete(`/world-entries/${entryId}`);
    showToast('항목이 삭제되었습니다.', 'success');
    await showWorldEntries(worldbookId, bookName);
  } catch (err) { showToast(`삭제 실패: ${err.message}`, 'error', 5000); }
}
