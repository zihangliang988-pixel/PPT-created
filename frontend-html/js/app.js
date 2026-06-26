/* ══════════════════════════════════════════
   PPT 智造 — 应用逻辑
   ══════════════════════════════════════════ */

// ── State ──
const state = {
  uploadedFiles: [],
  textContent: '',
  taskId: null,
  currentTemplate: 'modern',
  templates: [],
  outlinePages: [],
  previewPages: [],
  ws: null,
  status: 'idle', // idle | generating | outline | rendering | done | error
  pollTimer: null,
  outlineConfirmed: false, // 标记大纲是否已确认
};

// ── DOM refs ──
const $ = (id) => document.getElementById(id);

// ── Init ──
async function init() {
  try {
    const list = await API.getTemplates();
    state.templates = list;
    renderStyleGrid('styleGrid', list, 'modern');
    renderStyleGrid('restyleGrid', list, 'modern');
  } catch (e) {
    console.warn('Failed to load templates:', e);
  }

  // File drag & drop
  const fileZone = $('fileZone');
  fileZone.addEventListener('dragover', (e) => { e.preventDefault(); fileZone.classList.add('dragover'); });
  fileZone.addEventListener('dragleave', () => fileZone.classList.remove('dragover'));
  fileZone.addEventListener('drop', (e) => {
    e.preventDefault();
    fileZone.classList.remove('dragover');
    handleFiles(e.dataTransfer.files);
  });

  // File input
  $('fileInput').addEventListener('change', (e) => {
    handleFiles(e.target.files);
    e.target.value = '';
  });

  // Auto-resize textarea
  ['textInput', 'modifyInput'].forEach(id => {
    const el = $(id);
    el.addEventListener('input', () => {
      el.style.height = 'auto';
      el.style.height = Math.min(el.scrollHeight, 120) + 'px';
    });
  });

  // Enter to trigger
  $('textInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleGenerate();
    }
  });
  $('modifyInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleModify();
    }
  });
}

// ── File Handling ──
function handleFiles(files) {
  const MAX_SIZE = 20 * 1024 * 1024; // 20MB
  const ALLOWED = ['.pdf', '.docx', '.txt', '.md'];

  for (const file of files) {
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!ALLOWED.includes(ext)) {
      addAIMessage(`⚠️ 不支持的文件格式 \`${ext}\`，仅支持 PDF、DOCX、TXT、MD`);
      continue;
    }
    if (file.size > MAX_SIZE) {
      addAIMessage(`⚠️ 文件 \`${file.name}\` 超过 20MB 限制`);
      continue;
    }
    // Dedup
    if (state.uploadedFiles.some(f => f.name === file.name && f.size === file.size)) continue;
    state.uploadedFiles.push(file);
  }
  renderFileList();
}

function removeFile(index) {
  state.uploadedFiles.splice(index, 1);
  renderFileList();
}

function renderFileList() {
  const list = $('fileList');
  list.innerHTML = state.uploadedFiles.map((f, i) =>
    `<span class="file-tag">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
      ${f.name}
      <span class="file-remove" onclick="removeFile(${i})">&times;</span>
    </span>`
  ).join('');
}

// ── Messages ──
function addAIMessage(text) {
  const msg = document.createElement('div');
  msg.className = 'msg msg-ai';
  msg.innerHTML = `
    <div class="msg-avatar" style="background:linear-gradient(135deg,#6366f1,#8b5cf6)">P</div>
    <div class="msg-body"><div class="msg-text">${text}</div></div>`;
  $('chatMessages').appendChild(msg);
  msg.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  return msg;
}

function addUserMessage(text) {
  const msg = document.createElement('div');
  msg.className = 'msg msg-user';
  msg.innerHTML = `
    <div class="msg-avatar" style="background:linear-gradient(135deg,#818cf8,#6366f1)">你</div>
    <div class="msg-body"><div class="msg-text">${escapeHtml(text)}</div></div>`;
  $('chatMessages').appendChild(msg);
  msg.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  return msg;
}

function addProgressMessage(text, pct) {
  const msg = document.createElement('div');
  msg.className = 'msg msg-ai';
  msg.id = 'progressMsg';
  msg.innerHTML = `
    <div class="msg-avatar" style="background:linear-gradient(135deg,#6366f1,#8b5cf6)">P</div>
    <div class="msg-body">
      <div class="msg-text">${escapeHtml(text)}</div>
      <div class="msg-progress">
        <div class="progress-bar"><div class="progress-fill" style="width:${pct}%"></div></div>
        <span class="progress-text">${pct}%</span>
      </div>
    </div>`;
  $('chatMessages').appendChild(msg);
  msg.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  return msg;
}

function updateProgress(pct, text) {
  const el = $('progressMsg');
  if (!el) return;
  el.querySelector('.msg-text').textContent = text;
  const fill = el.querySelector('.progress-fill');
  if (fill) fill.style.width = pct + '%';
  const label = el.querySelector('.progress-text');
  if (label) label.textContent = pct + '%';
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// ── Generate Flow ──
async function handleGenerate() {
  const text = $('textInput').value.trim();
  if (state.uploadedFiles.length === 0 && !text) {
    addAIMessage('请上传文件或输入文字内容');
    return;
  }

  state.textContent = text;

  // Recommend pages
  let recommendedPages = 10;
  let recommendReason = '';
  try {
    const sample = text.slice(0, 3000) || '(上传文件)';
    const rec = await API.recommendPages(sample);
    recommendedPages = rec.recommended_pages || 10;
    recommendReason = rec.reason || '';
  } catch (e) {
    recommendedPages = Math.max(5, Math.min(20, Math.round(text.length / 500) + 3));
  }

  // Show param modal
  showParamModal(recommendedPages, recommendReason);
}

// ── Param Modal ──
let paramData = {};

function showParamModal(pages, reason) {
  paramData = { pages, reason };
  $('paramPages').value = pages;
  $('paramPagesHint').textContent = reason ? `${pages} 页，${reason}` : `${pages} 页`;
  $('paramTitle').value = '';
  // Reset detail
  document.querySelectorAll('#paramModal .btn-option').forEach(b => b.classList.remove('active'));
  document.querySelector('#paramModal .btn-option[data-value="moderate"]').classList.add('active');
  $('paramModal').style.display = 'flex';
}

function closeParamModal() {
  $('paramModal').style.display = 'none';
}

function selectDetail(el) {
  el.parentElement.querySelectorAll('.btn-option').forEach(b => b.classList.remove('active'));
  el.classList.add('active');
}

function toggleCustomStyle() {
  const wrap = $('customStyleWrap');
  wrap.style.display = wrap.style.display === 'none' ? 'block' : 'none';
}

function toggleCustomRestyle() {
  const wrap = $('customRestyleWrap');
  wrap.style.display = wrap.style.display === 'none' ? 'block' : 'none';
}

async function confirmGenerate() {
  closeParamModal();

  const title = $('paramTitle').value.trim();
  const pageCount = parseInt($('paramPages').value) || 10;
  const detailEl = document.querySelector('#paramModal .btn-option.active');
  const detail = detailEl ? detailEl.dataset.value : 'moderate';
  const templateId = paramData.templateId || state.currentTemplate;
  const customDesc = $('customStyleDesc').value.trim();

  // User message
  let userText = state.textContent;
  if (state.uploadedFiles.length > 0) {
    const names = state.uploadedFiles.map(f => f.name).join('、');
    userText = `[上传文件: ${names}]` + (userText ? '\n\n' + userText : '');
  }
  addUserMessage(userText);

  addProgressMessage('正在解析内容并生成大纲...', 5);

  setStatus('generating');

  // Build form data
  const formData = new FormData();
  for (const file of state.uploadedFiles) {
    formData.append('files', file);
  }
  formData.append('text_content', state.textContent);
  formData.append('page_count', String(pageCount));
  formData.append('detail', detail);
  formData.append('template_id', templateId);
  if (title) formData.append('title', title);
  if (customDesc) formData.append('custom_style_desc', customDesc);
  formData.append('animation_enabled', 'true');

  try {
    const result = await API.generateWithFiles(formData);
    state.taskId = result.task_id;

    // Connect WebSocket
    connectWS(state.taskId);
  } catch (e) {
    updateProgress(0, '❌ 提交失败');
    addAIMessage(`⚠️ 请求失败: ${e.message}`);
    setStatus('error');
  }
}

// ── WebSocket ──
function connectWS(taskId) {
  if (state.ws) {
    state.ws.close();
  }

  // Fallback: poll every 3s
  let pollCount = 0;
  state.pollTimer = setInterval(async () => {
    pollCount++;
    try {
      const task = await API.getTaskStatus(taskId);
      if (task.status === 'completed') {
        clearInterval(state.pollTimer);
        state.pollTimer = null;
        onTaskComplete(task);
      } else if (task.status === 'failed') {
        clearInterval(state.pollTimer);
        state.pollTimer = null;
        onTaskFailed(task);
      } else if (task.pages && task.pages.length > 0 && task.status === 'planned' && !state.outlineConfirmed) {
        // Show outline when status is 'planned' and pages are available
        showOutline(task.pages);
      }
    } catch(e) {}
  }, 3000);

  state.ws = API.createWebSocket(taskId, {
    onMessage: (msg) => {
      // 优先处理大纲预览消息
      if ((msg.event === 'outline_preview' || msg.event === 'planned') && msg.pages && !state.outlineConfirmed) {
        showOutline(msg.pages);
        // 同时显示进度
        if (msg.percentage !== undefined) {
          updateProgress(msg.percentage, msg.stage_name || '大纲已生成');
        }
        return; // 提前返回，不继续处理
      }
      
      // 处理进度更新
      if (msg.event === 'progress' || msg.stage) {
        const stageName = msg.stage_name || msg.detail || '处理中...';
        const detail = msg.detail ? `<span class="progress-detail">${msg.detail}</span>` : '';
        updateProgress(msg.percentage, `${stageName}${detail}`);
      }
      
      // 处理页面更新
      if ((msg.event === 'page_ready' || msg.event === 'polished') && state.outlineConfirmed && msg.pages) {
        state.outlinePages = msg.pages;
      }
      
      // 处理完成消息
      if (msg.event === 'complete' || msg.stage === 'completed') {
        updateProgress(100, `✅ PPT 生成完成${msg.detail ? ` - ${msg.detail}` : ''}`);
        clearInterval(state.pollTimer);
        state.pollTimer = null;
        onTaskComplete();
      }
      
      // 处理错误消息
      if (msg.event === 'error') {
        updateProgress(0, '❌ 生成失败');
        clearInterval(state.pollTimer);
        state.pollTimer = null;
        onTaskFailed(msg);
      }
    },
    onError: () => {
      // polling fallback handles it
    },
    onClose: () => {
      // polling fallback handles it
    },
  });
}

function showOutline(pages) {
  state.outlinePages = pages;
  renderOutline(pages);
  $('outlineModal').style.display = 'flex';
  setStatus('outline');
}

function closeOutlineModal() {
  $('outlineModal').style.display = 'none';
}

async function confirmOutline() {
  state.outlineConfirmed = true; // 标记大纲已确认，防止再次弹出
  closeOutlineModal();
  updateProgress(40, '正在渲染 PPT...');
  setStatus('rendering');

  try {
    const result = await API.confirmOutline(state.taskId, state.outlinePages);
    updateProgress(80, 'PPT 渲染中...');
    // Wait for completion via WS
  } catch (e) {
    state.outlineConfirmed = false; // 重置状态
    addAIMessage(`⚠️ 渲染失败: ${e.message}`);
    setStatus('error');
  }
}

function onTaskComplete(task) {
  setStatus('done');
  updateProgress(100, '✅ PPT 生成完成！');
  addAIMessage('🎉 PPT 已生成！你可以继续输入文字进行修改，或点击下载按钮保存。');

  // Show preview
  if (task && task.pages) {
    renderPreview(task.pages);
  } else {
    // fetch from server
    API.getTaskStatus(state.taskId).then(t => {
      if (t.pages) renderPreview(t.pages);
    });
  }

  // Show modify area
  $('modifyArea').style.display = 'block';
  $('previewToolbar').style.display = 'flex';
}

function onTaskFailed(msg) {
  setStatus('error');
  const detail = msg ? (msg.detail || '') : '未知错误';
  addAIMessage(`⚠️ 生成失败: ${detail}`);
}

// ── Outline Rendering ──
function renderOutline(pages) {
  const list = $('outlineList');
  $('outlineCount').textContent = `共 ${pages.length} 页`;

  list.innerHTML = pages.map((p, i) => {
    const typeLabel = { cover: '封面', content: '内容', cards: '卡片', chapter: '章节', summary: '总结' }[p.type] || p.type;
    const typeClass = p.type === 'chapter' ? 'is-chapter' : p.type === 'cover' ? 'is-cover' : p.type === 'summary' ? 'is-summary' : '';
    const hasChart = p.chart ? '<span class="outline-chart" title="包含图表">📊</span>' : '';
    return `
      <div class="outline-item" data-index="${i}" draggable="true">
        <span class="outline-drag">⠿</span>
        <span class="outline-type ${typeClass}">${typeLabel}</span>
        <div class="outline-main">
          <div class="outline-title-row">
            <input class="outline-title-input" value="${escapeHtml(p.title)}" 
                   onchange="updateOutlineTitle(${i}, this.value)" />
            ${hasChart}
          </div>
          <div class="outline-points-list">
            ${p.points.map((point, pi) => `
              <div class="outline-point-item">
                <input class="outline-point-input" value="${escapeHtml(point)}"
                       onchange="updateOutlinePoint(${i}, ${pi}, this.value)" />
                <button class="point-remove" onclick="removeOutlinePoint(${i}, ${pi})" title="删除要点">×</button>
              </div>
            `).join('')}
            <button class="add-point-btn" onclick="addOutlinePoint(${i})" title="添加要点">+ 添加要点</button>
          </div>
        </div>
        <div class="outline-actions">
          <button onclick="moveOutlinePage(${i}, -1)" title="上移" ${i === 0 ? 'disabled' : ''}>↑</button>
          <button onclick="moveOutlinePage(${i}, 1)" title="下移" ${i === pages.length - 1 ? 'disabled' : ''}>↓</button>
          <button onclick="duplicateOutlinePage(${i})" title="复制">⊕</button>
          <button onclick="removeOutlinePage(${i})" title="删除">✕</button>
        </div>
      </div>`;
  }).join('');

  // Drag support
  let dragSrc = null;
  list.querySelectorAll('.outline-item').forEach(el => {
    el.addEventListener('dragstart', () => {
      dragSrc = parseInt(el.dataset.index);
      el.classList.add('is-dragging');
    });
    el.addEventListener('dragend', () => el.classList.remove('is-dragging'));
    el.addEventListener('dragover', (e) => e.preventDefault());
    el.addEventListener('dragenter', () => el.classList.add('drag-over'));
    el.addEventListener('dragleave', () => el.classList.remove('drag-over'));
    el.addEventListener('drop', (e) => {
      e.preventDefault();
      el.classList.remove('drag-over');
      const targetIdx = parseInt(el.dataset.index);
      if (dragSrc !== null && dragSrc !== targetIdx) {
        const arr = state.outlinePages;
        const [removed] = arr.splice(dragSrc, 1);
        arr.splice(targetIdx, 0, removed);
        renderOutline(arr);
      }
    });
  });
}

function updateOutlineTitle(pageIndex, newTitle) {
  if (state.outlinePages[pageIndex]) {
    state.outlinePages[pageIndex].title = newTitle.trim();
  }
}

function updateOutlinePoint(pageIndex, pointIndex, newValue) {
  if (state.outlinePages[pageIndex] && state.outlinePages[pageIndex].points[pointIndex]) {
    state.outlinePages[pageIndex].points[pointIndex] = newValue.trim();
  }
}

function addOutlinePoint(pageIndex) {
  if (!state.outlinePages[pageIndex].points) {
    state.outlinePages[pageIndex].points = [];
  }
  state.outlinePages[pageIndex].points.push('新要点');
  renderOutline(state.outlinePages);
}

function removeOutlinePoint(pageIndex, pointIndex) {
  if (state.outlinePages[pageIndex] && state.outlinePages[pageIndex].points) {
    state.outlinePages[pageIndex].points.splice(pointIndex, 1);
    renderOutline(state.outlinePages);
  }
}

function moveOutlinePage(index, direction) {
  const newIndex = index + direction;
  if (newIndex >= 0 && newIndex < state.outlinePages.length) {
    const temp = state.outlinePages[index];
    state.outlinePages[index] = state.outlinePages[newIndex];
    state.outlinePages[newIndex] = temp;
    renderOutline(state.outlinePages);
  }
}

function duplicateOutlinePage(index) {
  const page = state.outlinePages[index];
  const copy = JSON.parse(JSON.stringify(page));
  copy.id = `page_${Date.now()}`;
  state.outlinePages.splice(index + 1, 0, copy);
  renderOutline(state.outlinePages);
}

function removeOutlinePage(index) {
  if (state.outlinePages.length > 1) {
    state.outlinePages.splice(index, 1);
    renderOutline(state.outlinePages);
  }
}

// ── Preview Rendering ──
function renderPreview(pages) {
  state.previewPages = pages;
  const list = $('previewList');
  $('previewEmpty').style.display = 'none';

  list.innerHTML = pages.map((p, i) => {
    const typeLabels = { cover: '封面', content: '内容', cards: '卡片', chapter: '章节', summary: '总结' };
    const pointsText = p.points ? p.points.slice(0, 2).join('·').slice(0, 40) : '';
    return `
      <div class="page-thumb" onclick="scrollToPage(${i})">
        <div class="page-thumb-num">${i + 1}</div>
        <div class="page-thumb-info">
          <div class="page-thumb-type">${typeLabels[p.type] || p.type}</div>
          <div class="page-thumb-title">${escapeHtml(p.title)}</div>
          ${pointsText ? `<div class="page-thumb-points">${escapeHtml(pointsText)}</div>` : ''}
        </div>
      </div>`;
  }).join('');
}

function scrollToPage(index) {
  // highlight
  $('previewList').querySelectorAll('.page-thumb').forEach((el, i) => {
    el.classList.toggle('is-active', i === index);
  });
}

// ── Modify ──
async function handleModify() {
  const text = $('modifyInput').value.trim();
  if (!text) return;
  if (!state.taskId) return;

  addUserMessage('[修改] ' + text);
  addProgressMessage('正在根据新要求调整 PPT...', 50);
  setStatus('generating');

  $('modifyInput').value = '';

  try {
    const result = await API.modifyPpt(state.taskId, text);
    updateProgress(90, '调整完成，正在刷新...');
    // Poll for result
    setTimeout(async () => {
      try {
        const task = await API.getTaskStatus(state.taskId);
        if (task.pages) {
          renderPreview(task.pages);
          updateProgress(100, '✅ 修改完成');
          addAIMessage('✅ PPT 已更新！');
          setStatus('done');
        }
      } catch(e) {
        addAIMessage('⚠️ 刷新状态失败，请检查任务');
      }
    }, 2000);
  } catch (e) {
    updateProgress(0, '❌ 修改失败');
    addAIMessage(`⚠️ 修改失败: ${e.message}`);
    setStatus('done');
  }
}

// ── Download ──
function downloadPPT() {
  if (!state.taskId) return;
  window.open(API.getDownloadUrl(state.taskId), '_blank');
}

// ── Restyle ──
async function restylePPT() {
  if (!state.taskId) return;
  $('restyleModal').style.display = 'flex';
}

function closeRestyleModal() {
  $('restyleModal').style.display = 'none';
}

async function confirmRestyle() {
  closeRestyleModal();
  const selected = document.querySelector('#restyleGrid .style-card.is-selected');
  const templateId = selected ? selected.dataset.id : state.currentTemplate;
  const customDesc = $('restyleDesc').value.trim();

  addProgressMessage('正在换风格...', 30);
  setStatus('generating');

  try {
    await API.restylePpt(state.taskId, templateId, customDesc || undefined);
    updateProgress(80, '风格更新中...');
    setTimeout(async () => {
      try {
        const task = await API.getTaskStatus(state.taskId);
        if (task.pages) renderPreview(task.pages);
        updateProgress(100, '✅ 风格已更新');
        addAIMessage('🎨 风格已切换！');
        setStatus('done');
      } catch(e) {
        addAIMessage('⚠️ 刷新状态失败');
      }
    }, 2000);
  } catch (e) {
    updateProgress(0, '❌ 换风格失败');
    addAIMessage(`⚠️ 换风格失败: ${e.message}`);
    setStatus('done');
  }
}

// ── Style Grid ──
function renderStyleGrid(containerId, templates, selectedId) {
  const grid = $(containerId);
  grid.innerHTML = templates.map(t =>
    `<div class="style-card ${t.id === selectedId ? 'is-selected' : ''}" data-id="${t.id}" onclick="selectStyle(this,'${containerId}')">
      <div class="style-thumb">
        <div class="style-color-bar" style="background:${getStyleColor(t.id)}"></div>
        <div class="style-check" style="display:${t.id === selectedId ? 'flex' : 'none'}">✓</div>
      </div>
      <span class="style-name">${t.name}</span>
    </div>`
  ).join('');
}

function selectStyle(el, gridId) {
  const grid = document.getElementById(gridId);
  grid.querySelectorAll('.style-card').forEach(c => {
    c.classList.remove('is-selected');
    c.querySelector('.style-check').style.display = 'none';
  });
  el.classList.add('is-selected');
  el.querySelector('.style-check').style.display = 'flex';

  if (gridId === 'styleGrid') {
    paramData.templateId = el.dataset.id;
  } else {
    state.currentTemplate = el.dataset.id;
  }
}

const STYLE_COLORS = {
  classic: '#1e3c72', modern: '#6366f1', tech: '#0096ff',
  creative: '#ff6b6b', minimal: '#323232', elegant: '#b49650',
  colorful: '#ff6b6b', dark: '#1c1c24'
};
function getStyleColor(id) { return STYLE_COLORS[id] || '#6366f1'; }

// ── Status ──
function setStatus(s) {
  state.status = s;
  const dot = $('statusDot');
  const text = $('statusText');
  dot.className = 'status-dot';
  switch(s) {
    case 'idle': dot.className = 'status-dot'; text.textContent = '就绪'; break;
    case 'generating':
    case 'outline':
    case 'rendering': dot.className = 'status-dot is-busy'; text.textContent = '处理中...'; break;
    case 'done': dot.className = 'status-dot'; text.textContent = '就绪'; break;
    case 'error': dot.className = 'status-dot is-error'; text.textContent = '失败'; break;
  }
}

// ── Start ──
document.addEventListener('DOMContentLoaded', init);
