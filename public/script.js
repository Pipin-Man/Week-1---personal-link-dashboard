const panelListEl = document.getElementById('panel-list');
const panelContentEl = document.getElementById('panel-content');

const openPanelDialogBtn = document.getElementById('open-panel-dialog');
const panelDialog = document.getElementById('panel-dialog');
const panelForm = document.getElementById('panel-form');
const panelNameInput = document.getElementById('panel-name');
const cancelPanelDialogBtn = document.getElementById('cancel-panel-dialog');

const openCategoryDialogBtn = document.getElementById('open-category-dialog');
const categoryDialog = document.getElementById('category-dialog');
const categoryForm = document.getElementById('category-form');
const categoryPanelSelect = document.getElementById('category-panel');
const categoryNameInput = document.getElementById('category-name');
const cancelCategoryDialogBtn = document.getElementById('cancel-category-dialog');

const searchForm = document.getElementById('search-form');
const searchInput = document.getElementById('search-input');
const searchResults = document.getElementById('search-results');

const noteForm = document.getElementById('note-form');
const noteContent = document.getElementById('note-content');
const notesList = document.getElementById('notes-list');

const linkDialog = document.getElementById('link-dialog');
const linkForm = document.getElementById('link-form');
const linkDialogTitle = document.getElementById('link-dialog-title');
const cancelLinkDialog = document.getElementById('cancel-link-dialog');
const linkIdInput = document.getElementById('link-id');
const linkCategorySelect = document.getElementById('link-category');
const linkNameInput = document.getElementById('link-name');
const linkUrlInput = document.getElementById('link-url');
const linkDescriptionInput = document.getElementById('link-description');

const categoryTemplate = document.getElementById('category-template');
const linkTemplate = document.getElementById('link-template');
const clockEl = document.getElementById('clock');

let dashboard = { panels: [], notes: [] };
let activePanelId = null;

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options
  });

  if (!response.ok) {
    let message = 'Request failed';
    try {
      const payload = await response.json();
      message = payload.error || message;
    } catch {
      // no-op
    }
    throw new Error(message);
  }

  if (response.status === 204) return null;
  return response.json();
}

function updateClock() {
  clockEl.textContent = new Date().toLocaleString();
}
setInterval(updateClock, 1000);
updateClock();

function flattenCategories() {
  return dashboard.panels.flatMap((panel) => panel.categories.map((c) => ({ ...c, panelId: panel.id, panelName: panel.name })));
}

function populateCategorySelectors(defaultCategoryId = null) {
  const categories = flattenCategories();
  linkCategorySelect.innerHTML = '';
  categoryPanelSelect.innerHTML = '';

  dashboard.panels.forEach((panel) => {
    const option = document.createElement('option');
    option.value = String(panel.id);
    option.textContent = panel.name;
    categoryPanelSelect.appendChild(option);
  });

  categories.forEach((category) => {
    const option = document.createElement('option');
    option.value = String(category.id);
    option.textContent = `${category.panelName} / ${category.name}`;
    linkCategorySelect.appendChild(option);
  });

  if (activePanelId) categoryPanelSelect.value = String(activePanelId);
  if (defaultCategoryId) linkCategorySelect.value = String(defaultCategoryId);
}

function renderPanels() {
  panelListEl.innerHTML = '';
  dashboard.panels.forEach((panel) => {
    const item = document.createElement('li');
    item.className = `panel-chip ${panel.id === activePanelId ? 'active' : ''}`;

    const openButton = document.createElement('button');
    openButton.className = 'icon-button';
    openButton.textContent = panel.name;
    openButton.addEventListener('click', () => {
      activePanelId = panel.id;
      renderPanels();
      renderPanelContent();
      populateCategorySelectors();
    });

    const delButton = document.createElement('button');
    delButton.className = 'icon-button';
    delButton.textContent = '✕';
    delButton.title = 'Delete panel';
    delButton.addEventListener('click', async () => {
      if (!confirm(`Delete panel "${panel.name}" and all data inside it?`)) return;
      try {
        await api(`/api/panels/${panel.id}`, { method: 'DELETE' });
        await loadDashboard();
      } catch (error) {
        alert(error.message);
      }
    });

    item.append(openButton, delButton);
    panelListEl.appendChild(item);
  });
}

function renderPanelContent() {
  panelContentEl.innerHTML = '';
  const panel = dashboard.panels.find((p) => p.id === activePanelId);
  if (!panel) {
    panelContentEl.innerHTML = '<p class="muted">Create a panel to get started.</p>';
    return;
  }

  if (panel.categories.length === 0) {
    panelContentEl.innerHTML = '<p class="muted">No categories yet.</p>';
    return;
  }

  panel.categories.forEach((category) => {
    const categoryNode = categoryTemplate.content.cloneNode(true);
    const nameEl = categoryNode.querySelector('.category-name');
    const addLinkBtn = categoryNode.querySelector('.add-link');
    const delCategoryBtn = categoryNode.querySelector('.delete-category');
    const linksList = categoryNode.querySelector('.links-list');

    nameEl.textContent = category.name;
    addLinkBtn.addEventListener('click', () => openLinkDialog({ categoryId: category.id }));

    delCategoryBtn.addEventListener('click', async () => {
      if (!confirm(`Delete category "${category.name}"? (must be empty)`)) return;
      try {
        await api(`/api/categories/${category.id}`, { method: 'DELETE' });
        await loadDashboard();
      } catch (error) {
        alert(error.message);
      }
    });

    if (category.links.length === 0) {
      const li = document.createElement('li');
      li.className = 'muted';
      li.textContent = 'No links yet.';
      linksList.appendChild(li);
    } else {
      category.links.forEach((link) => {
        const linkNode = linkTemplate.content.cloneNode(true);
        const anchor = linkNode.querySelector('.link-anchor');
        const desc = linkNode.querySelector('.link-description');
        const editBtn = linkNode.querySelector('.edit-link');
        const delBtn = linkNode.querySelector('.delete-link');

        anchor.href = link.url;
        anchor.textContent = link.name;
        anchor.title = link.url;
        desc.textContent = link.description || '—';

        editBtn.addEventListener('click', () => openLinkDialog({ link }));
        delBtn.addEventListener('click', async () => {
          if (!confirm(`Delete link "${link.name}"?`)) return;
          try {
            await api(`/api/links/${link.id}`, { method: 'DELETE' });
            await loadDashboard();
          } catch (error) {
            alert(error.message);
          }
        });

        linksList.appendChild(linkNode);
      });
    }

    panelContentEl.appendChild(categoryNode);
  });
}

function renderNotes() {
  notesList.innerHTML = '';
  dashboard.notes.forEach((note) => {
    const item = document.createElement('li');
    item.className = 'note-item';

    const preview = document.createElement('p');
    preview.className = 'note-preview';
    preview.textContent = note.content.split('\n').slice(0, 2).join('\n');

    const actions = document.createElement('div');
    actions.className = 'note-actions';

    const expandBtn = document.createElement('button');
    expandBtn.className = 'icon-button';
    expandBtn.textContent = '✎ Edit';
    expandBtn.addEventListener('click', async () => {
      const next = prompt('Edit note', note.content);
      if (next === null) return;
      const updated = next.trim();
      if (!updated) return alert('Note cannot be empty.');
      try {
        await api(`/api/notes/${note.id}`, { method: 'PUT', body: JSON.stringify({ content: updated }) });
        await loadDashboard();
      } catch (error) {
        alert(error.message);
      }
    });

    const delBtn = document.createElement('button');
    delBtn.className = 'icon-button';
    delBtn.textContent = '✕ Delete';
    delBtn.addEventListener('click', async () => {
      if (!confirm('Delete this note?')) return;
      try {
        await api(`/api/notes/${note.id}`, { method: 'DELETE' });
        await loadDashboard();
      } catch (error) {
        alert(error.message);
      }
    });

    actions.append(expandBtn, delBtn);
    item.append(preview, actions);
    notesList.appendChild(item);
  });
}

function openPanelDialog() {
  panelForm.reset();
  panelDialog.showModal();
}

function openCategoryDialog() {
  categoryForm.reset();
  populateCategorySelectors();
  if (activePanelId) categoryPanelSelect.value = String(activePanelId);
  categoryDialog.showModal();
}

function openLinkDialog({ categoryId = null, link = null } = {}) {
  linkForm.reset();

  if (link) {
    linkDialogTitle.textContent = 'Edit link';
    linkIdInput.value = String(link.id);
    linkNameInput.value = link.name;
    linkUrlInput.value = link.url;
    linkDescriptionInput.value = link.description || '';
    linkCategorySelect.value = String(link.categoryId);
  } else {
    linkDialogTitle.textContent = 'Add link';
    linkIdInput.value = '';
    if (categoryId) linkCategorySelect.value = String(categoryId);
  }

  linkDialog.showModal();
}

async function loadDashboard() {
  dashboard = await api('/api/dashboard');
  if (!activePanelId || !dashboard.panels.find((p) => p.id === activePanelId)) {
    activePanelId = dashboard.panels[0]?.id || null;
  }
  populateCategorySelectors();
  renderPanels();
  renderPanelContent();
  renderNotes();
}

openPanelDialogBtn.addEventListener('click', openPanelDialog);
openCategoryDialogBtn.addEventListener('click', openCategoryDialog);
cancelPanelDialogBtn.addEventListener('click', () => panelDialog.close());
cancelCategoryDialogBtn.addEventListener('click', () => categoryDialog.close());
cancelLinkDialog.addEventListener('click', () => linkDialog.close());

panelForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    await api('/api/panels', { method: 'POST', body: JSON.stringify({ name: panelNameInput.value.trim() }) });
    panelDialog.close();
    await loadDashboard();
  } catch (error) {
    alert(error.message);
  }
});

categoryForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const panelId = Number(categoryPanelSelect.value);
  if (Number.isNaN(panelId)) return alert('Select panel first.');

  try {
    await api('/api/categories', {
      method: 'POST',
      body: JSON.stringify({ panelId, name: categoryNameInput.value.trim() })
    });
    categoryDialog.close();
    await loadDashboard();
  } catch (error) {
    alert(error.message);
  }
});

linkForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const payload = {
    categoryId: Number(linkCategorySelect.value),
    name: linkNameInput.value.trim(),
    url: linkUrlInput.value.trim(),
    description: linkDescriptionInput.value.trim()
  };

  try {
    if (linkIdInput.value) {
      await api(`/api/links/${linkIdInput.value}`, { method: 'PUT', body: JSON.stringify(payload) });
    } else {
      await api('/api/links', { method: 'POST', body: JSON.stringify(payload) });
    }
    linkDialog.close();
    await loadDashboard();
  } catch (error) {
    alert(error.message);
  }
});

searchForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const term = searchInput.value.trim();
  if (!term) {
    searchResults.classList.add('hidden');
    searchResults.innerHTML = '';
    return;
  }

  try {
    const results = await api(`/api/search?q=${encodeURIComponent(term)}`);
    searchResults.classList.remove('hidden');

    if (results.length === 0) {
      searchResults.textContent = 'No matching links found.';
      return;
    }

    const ul = document.createElement('ul');
    results.forEach((link) => {
      const li = document.createElement('li');
      li.innerHTML = `<strong>${link.name}</strong> (${link.panelName} / ${link.categoryName})`;
      ul.appendChild(li);
    });
    searchResults.innerHTML = '';
    searchResults.appendChild(ul);
  } catch (error) {
    alert(error.message);
  }
});

noteForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    await api('/api/notes', { method: 'POST', body: JSON.stringify({ content: noteContent.value.trim() }) });
    noteForm.reset();
    await loadDashboard();
  } catch (error) {
    alert(error.message);
  }
});

loadDashboard().catch((error) => {
  panelContentEl.innerHTML = `<p class="muted">Failed to load: ${error.message}</p>`;
});
