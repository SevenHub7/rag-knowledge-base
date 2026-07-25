/* RAG 企业知识库 - 前端逻辑 */

// ── 状态 ──
let currentView = 'chat';
let currentKB = null;
let currentConvId = null;
let selectedKBIds = [];
let allKBs = [];
let isLoading = false;

// ── 初始化 ──
document.addEventListener('DOMContentLoaded', () => {
    loadKnowledgeBases();
    loadConversations();
    setupDragDrop();
});

// ── 视图切换 ──
function switchView(view) {
    currentView = view;
    document.querySelectorAll('.view-panel').forEach(p => p.style.display = 'none');
    document.getElementById(`view-${view}`).style.display = view === 'chat' ? 'flex' : 'block';
    document.querySelectorAll('.nav-item[data-view]').forEach(n => n.classList.remove('active'));
    document.querySelector(`.nav-item[data-view="${view}"]`).classList.add('active');

    if (view === 'knowledge') loadKnowledgeBases();
    if (view === 'dashboard') loadStats();
    if (view === 'chat') updateKBSelector();
}

// ── 知识库 ──
async function loadKnowledgeBases() {
    try {
        const res = await fetch('/api/knowledge/');
        allKBs = await res.json();
        renderKBGrid();
        updateKBSelector();
    } catch (e) {
        console.error('加载知识库失败:', e);
    }
}

function renderKBGrid() {
    const grid = document.getElementById('kb-grid');
    if (!allKBs.length) {
        grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1;"><i class="fas fa-folder-open"></i><p>还没有知识库，点击右上角创建</p></div>`;
        return;
    }
    const colors = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4'];
    grid.innerHTML = allKBs.map((kb, i) => `
        <div class="kb-card" onclick="openKB('${kb.id}')">
            <div class="kb-card-header">
                <div class="kb-icon" style="background:${colors[i % colors.length]}20;color:${colors[i % colors.length]};">
                    <i class="fas fa-database"></i>
                </div>
                <div>
                    <div style="font-weight:600;font-size:15px;">${kb.name}</div>
                    <div style="font-size:12px;color:var(--text-secondary);margin-top:2px;">${kb.description || '暂无描述'}</div>
                </div>
            </div>
            <div class="kb-card-stats">
                <span><i class="fas fa-file-alt"></i> ${kb.doc_count} 个文档</span>
                <span><i class="fas fa-puzzle-piece"></i> ${kb.chunk_count} 个分块</span>
            </div>
            <div class="kb-card-actions">
                <button class="btn btn-outline btn-sm" onclick="event.stopPropagation();openKB('${kb.id}')"><i class="fas fa-folder-open"></i> 管理</button>
                <button class="btn btn-danger btn-sm" onclick="event.stopPropagation();deleteKB('${kb.id}','${kb.name}')"><i class="fas fa-trash"></i></button>
            </div>
        </div>
    `).join('');
}

function openKB(kbId) {
    currentKB = allKBs.find(k => k.id === kbId);
    if (!currentKB) return;
    document.getElementById('kb-list-view').style.display = 'none';
    document.getElementById('kb-detail-view').style.display = 'block';
    document.getElementById('kb-detail-name').textContent = currentKB.name;
    document.getElementById('kb-detail-desc').textContent = currentKB.description || '';
    loadDocuments(kbId);
}

function backToKBList() {
    currentKB = null;
    document.getElementById('kb-list-view').style.display = 'block';
    document.getElementById('kb-detail-view').style.display = 'none';
    loadKnowledgeBases();
}

function showCreateKBModal() {
    document.getElementById('modal-content').innerHTML = `
        <h3>新建知识库</h3>
        <div class="form-group">
            <label>知识库名称</label>
            <input id="kb-name" placeholder="例如：产品文档、技术规范..." autofocus>
        </div>
        <div class="form-group">
            <label>描述（可选）</label>
            <textarea id="kb-desc" rows="3" placeholder="描述知识库的用途和范围"></textarea>
        </div>
        <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:20px;">
            <button class="btn btn-outline" onclick="closeModal()">取消</button>
            <button class="btn btn-primary" onclick="createKB()">创建</button>
        </div>
    `;
    showModal();
}

async function createKB() {
    const name = document.getElementById('kb-name').value.trim();
    if (!name) return alert('请输入名称');
    const desc = document.getElementById('kb-desc').value.trim();
    await fetch('/api/knowledge/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description: desc }),
    });
    closeModal();
    loadKnowledgeBases();
}

async function deleteKB(id, name) {
    if (!confirm(`确定删除知识库「${name}」？所有文档和向量数据将被清除。`)) return;
    await fetch(`/api/knowledge/${id}`, { method: 'DELETE' });
    if (currentKB && currentKB.id === id) backToKBList();
    else loadKnowledgeBases();
}

// ── 文档管理 ──
async function loadDocuments(kbId) {
    const res = await fetch(`/api/knowledge/${kbId}/documents`);
    const docs = await res.json();
    const tbody = document.getElementById('doc-table-body');
    if (!docs.length) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:var(--text-secondary);padding:30px;">暂无文档，请上传文件</td></tr>`;
        return;
    }
    tbody.innerHTML = docs.map(d => `
        <tr>
            <td><i class="fas ${getFileIcon(d.file_type)}" style="margin-right:6px;color:var(--primary);"></i>${d.filename}</td>
            <td>${d.file_type}</td>
            <td>${formatSize(d.file_size)}</td>
            <td>${d.chunk_count || '-'}</td>
            <td><span class="status-badge status-${d.status}">${statusText(d.status)}</span></td>
            <td><button class="btn btn-danger btn-sm" onclick="deleteDoc('${d.id}')"><i class="fas fa-trash"></i></button></td>
        </tr>
    `).join('');
}

function setupDragDrop() {
    const zone = document.getElementById('upload-zone');
    if (!zone) return;
    zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragover'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
    zone.addEventListener('drop', e => {
        e.preventDefault();
        zone.classList.remove('dragover');
        handleFileUpload(e.dataTransfer.files);
    });
}

async function handleFileUpload(files) {
    if (!currentKB || !files.length) return;
    const progress = document.getElementById('upload-progress');
    for (const file of files) {
        const item = document.createElement('div');
        item.style.cssText = 'padding:8px 12px;background:#f8fafc;border-radius:8px;margin-bottom:8px;font-size:13px;display:flex;align-items:center;gap:8px;';
        item.innerHTML = `<i class="fas fa-spinner fa-spin" style="color:var(--primary);"></i> ${file.name} <span style="color:var(--text-secondary);">处理中...</span>`;
        progress.appendChild(item);

        const formData = new FormData();
        formData.append('file', file);
        try {
            const res = await fetch(`/api/documents/upload/${currentKB.id}`, { method: 'POST', body: formData });
            const data = await res.json();
            if (res.ok) {
                item.innerHTML = `<i class="fas fa-check-circle" style="color:#10b981;"></i> ${file.name} <span style="color:#10b981;">上传成功</span>`;
                pollDocStatus(data.doc_id, item);
            } else {
                item.innerHTML = `<i class="fas fa-times-circle" style="color:#ef4444;"></i> ${file.name} <span style="color:#ef4444;">${data.detail || '上传失败'}</span>`;
            }
        } catch (e) {
            item.innerHTML = `<i class="fas fa-times-circle" style="color:#ef4444;"></i> ${file.name} <span style="color:#ef4444;">网络错误</span>`;
        }
    }
    document.getElementById('file-input').value = '';
    setTimeout(() => loadDocuments(currentKB.id), 1000);
}

async function pollDocStatus(docId, element) {
    for (let i = 0; i < 30; i++) {
        await new Promise(r => setTimeout(r, 2000));
        try {
            const res = await fetch(`/api/documents/status/${docId}`);
            const data = await res.json();
            if (data.status === 'completed') {
                element.innerHTML = `<i class="fas fa-check-circle" style="color:#10b981;"></i> ${data.filename} <span style="color:#10b981;">处理完成 (${data.chunk_count} 块)</span>`;
                loadDocuments(currentKB.id);
                return;
            } else if (data.status === 'failed') {
                element.innerHTML = `<i class="fas fa-times-circle" style="color:#ef4444;"></i> ${data.filename} <span style="color:#ef4444;">${data.error_message || '处理失败'}</span>`;
                return;
            }
        } catch (e) { /* continue polling */ }
    }
}

async function deleteDoc(docId) {
    if (!currentKB || !confirm('确定删除此文档？')) return;
    await fetch(`/api/knowledge/${currentKB.id}/documents/${docId}`, { method: 'DELETE' });
    loadDocuments(currentKB.id);
}

// ── 聊天 ──
function updateKBSelector() {
    const container = document.getElementById('chat-kb-selector');
    if (!allKBs.length) {
        container.innerHTML = '<span style="font-size:12px;color:var(--text-secondary);">暂无知识库，请先创建</span>';
        return;
    }
    if (!selectedKBIds.length) selectedKBIds = allKBs.map(k => k.id);
    container.innerHTML = allKBs.map(kb => `
        <span class="kb-chip ${selectedKBIds.includes(kb.id) ? 'selected' : ''}" onclick="toggleKB('${kb.id}')">${kb.name}</span>
    `).join('');
}

function toggleKB(kbId) {
    const idx = selectedKBIds.indexOf(kbId);
    if (idx >= 0) selectedKBIds.splice(idx, 1);
    else selectedKBIds.push(kbId);
    updateKBSelector();
}

async function sendMessage() {
    const input = document.getElementById('chat-input');
    const msg = input.value.trim();
    if (!msg || isLoading) return;

    // 隐藏空状态
    const empty = document.getElementById('chat-empty');
    if (empty) empty.style.display = 'none';

    // 添加用户消息
    appendMessage('user', msg);
    input.value = '';
    input.style.height = 'auto';
    isLoading = true;
    document.getElementById('send-btn').disabled = true;

    // 显示加载
    const loadingEl = appendLoading();

    try {
        const res = await fetch('/api/chat/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: msg,
                conversation_id: currentConvId,
                kb_ids: selectedKBIds,
            }),
        });
        const data = await res.json();
        loadingEl.remove();

        if (res.ok) {
            currentConvId = data.conversation_id;
            appendMessage('assistant', data.answer, data.sources);
            loadConversations();
        } else {
            appendMessage('assistant', `错误：${data.detail || '请求失败'}`);
        }
    } catch (e) {
        loadingEl.remove();
        appendMessage('assistant', `网络错误：${e.message}`);
    }

    isLoading = false;
    document.getElementById('send-btn').disabled = false;
}

function appendMessage(role, content, sources) {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = `chat-message ${role}`;

    const avatar = role === 'user' ? '<i class="fas fa-user"></i>' : '<i class="fas fa-robot"></i>';
    let html = `<div class="msg-avatar">${avatar}</div><div class="msg-bubble">${escapeHtml(content)}`;

    if (sources && sources.length) {
        html += `<div class="msg-sources"><details><summary><i class="fas fa-link"></i> 参考来源 (${sources.length})</summary>`;
        sources.forEach(s => {
            html += `<div class="source-item"><span class="score">${(s.score * 100).toFixed(0)}%</span> ${escapeHtml(s.filename)} - ${escapeHtml(s.kb_name)}</div>`;
        });
        html += '</details></div>';
    }

    html += '</div>';
    div.innerHTML = html;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function appendLoading() {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = 'chat-message assistant';
    div.innerHTML = `<div class="msg-avatar"><i class="fas fa-robot"></i></div><div class="msg-bubble"><div class="typing-indicator"><span></span><span></span><span></span></div></div>`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return div;
}

function handleInputKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
    // 自动调整高度
    const el = e.target;
    setTimeout(() => { el.style.height = 'auto'; el.style.height = el.scrollHeight + 'px'; }, 0);
}

// ── 对话管理 ──
async function loadConversations() {
    try {
        const res = await fetch('/api/chat/conversations');
        const convs = await res.json();
        const list = document.getElementById('conv-list');
        list.innerHTML = convs.slice(0, 15).map(c => `
            <div class="conv-item ${c.id === currentConvId ? 'active' : ''}" onclick="loadConvMessages('${c.id}')">
                <i class="fas fa-comment" style="font-size:12px;color:#64748b;"></i>
                <span class="conv-title">${escapeHtml(c.title)}</span>
                <span class="conv-delete" onclick="event.stopPropagation();deleteConv('${c.id}')"><i class="fas fa-times"></i></span>
            </div>
        `).join('');
    } catch (e) { /* ignore */ }
}

async function loadConvMessages(convId) {
    currentConvId = convId;
    switchView('chat');
    const container = document.getElementById('chat-messages');
    container.innerHTML = '';
    try {
        const res = await fetch(`/api/chat/conversations/${convId}`);
        const data = await res.json();
        data.messages.forEach(m => {
            let sources = [];
            try { sources = typeof m.sources === 'string' ? JSON.parse(m.sources) : m.sources; } catch(e) {}
            appendMessage(m.role, m.content, sources.length ? sources : undefined);
        });
    } catch (e) { console.error(e); }
    loadConversations();
}

function newConversation() {
    currentConvId = null;
    const container = document.getElementById('chat-messages');
    container.innerHTML = `<div class="empty-state" id="chat-empty"><i class="fas fa-robot"></i><p>新对话，请输入你的问题</p></div>`;
    loadConversations();
}

async function deleteConv(convId) {
    await fetch(`/api/chat/conversations/${convId}`, { method: 'DELETE' });
    if (currentConvId === convId) newConversation();
    else loadConversations();
}

// ── 数据看板 ──
async function loadStats() {
    try {
        const res = await fetch('/api/chat/stats');
        const stats = await res.json();
        const grid = document.getElementById('stats-grid');
        const items = [
            { icon: 'fa-database', label: '知识库', value: stats.kb_count, color: '#3b82f6' },
            { icon: 'fa-file-alt', label: '文档总数', value: stats.doc_count, color: '#10b981' },
            { icon: 'fa-puzzle-piece', label: '文本分块', value: stats.chunk_total, color: '#f59e0b' },
            { icon: 'fa-comments', label: '对话数', value: stats.conv_count, color: '#8b5cf6' },
            { icon: 'fa-question-circle', label: '提问次数', value: stats.query_count, color: '#ef4444' },
        ];
        grid.innerHTML = items.map(it => `
            <div class="stat-card">
                <div style="display:flex;align-items:center;gap:10px;">
                    <div style="width:40px;height:40px;border-radius:10px;background:${it.color}15;color:${it.color};display:flex;align-items:center;justify-content:center;">
                        <i class="fas ${it.icon}"></i>
                    </div>
                    <div>
                        <div class="stat-value">${it.value}</div>
                        <div class="stat-label">${it.label}</div>
                    </div>
                </div>
            </div>
        `).join('');

        document.getElementById('system-info').innerHTML = `
            <div><i class="fas fa-server" style="width:20px;"></i> 技术栈：Python + FastAPI + DeepSeek + Chroma</div>
            <div><i class="fas fa-cogs" style="width:20px;"></i> RAG 流程：文档解析 → 智能分块 → 向量化 → 语义检索 → 增强生成</div>
            <div><i class="fas fa-shield-alt" style="width:20px;"></i> 支持格式：PDF、Word、TXT、Markdown</div>
            <div><i class="fas fa-clock" style="width:20px;"></i> 当前时间：${new Date().toLocaleString('zh-CN')}</div>
        `;
    } catch (e) { console.error(e); }
}

// ── 工具函数 ──
function showModal() { document.getElementById('modal-overlay').classList.add('show'); }
function closeModal() { document.getElementById('modal-overlay').classList.remove('show'); }
document.getElementById('modal-overlay').addEventListener('click', e => { if (e.target === e.currentTarget) closeModal(); });

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function getFileIcon(ext) {
    const icons = { '.pdf': 'fa-file-pdf', '.docx': 'fa-file-word', '.txt': 'fa-file-alt', '.md': 'fa-file-code', '.markdown': 'fa-file-code' };
    return icons[ext] || 'fa-file';
}

function statusText(status) {
    const map = { completed: '已完成', processing: '处理中', failed: '失败' };
    return map[status] || status;
}
