// ─── File Manager Logic ─────────────────────────────────────────────────────
let fmCurrentPath = '';
let fmSelectedItems = new Set();
let fmMode = 'local'; // 'local' | 'ftp'
let fmClipboard = null; // { action: 'copy'|'cut', paths: [] }

// ─── Auth ────────────────────────────────────────────────────────────────────

async function fmLogin() {
    const pw = document.getElementById('fm-password-input').value;
    const errEl = document.getElementById('fm-login-error');
    try {
        const resp = await fetch('/api/fm/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password: pw })
        });
        const data = await resp.json();
        if (data.status === 'success') {
            document.getElementById('fm-lock-screen').classList.add('hidden');
            document.getElementById('fm-workspace').classList.remove('hidden');
            fmBrowse('');
        } else {
            errEl.innerText = data.message || 'Invalid password';
            errEl.classList.remove('hidden');
        }
    } catch (e) {
        errEl.innerText = 'Connection error';
        errEl.classList.remove('hidden');
    }
}

async function fmCheckStatus() {
    try {
        const resp = await fetch('/api/fm/status');
        const data = await resp.json();
        if (data.authenticated) {
            document.getElementById('fm-lock-screen').classList.add('hidden');
            document.getElementById('fm-workspace').classList.remove('hidden');
            fmBrowse('');
        }
    } catch (e) { /* ignore */ }
}

async function fmLogout() {
    await fetch('/api/fm/logout', { method: 'POST' });
    document.getElementById('fm-lock-screen').classList.remove('hidden');
    document.getElementById('fm-workspace').classList.add('hidden');
    document.getElementById('fm-password-input').value = '';
}

// ─── Browse ──────────────────────────────────────────────────────────────────

async function fmBrowse(path) {
    fmSelectedItems.clear();
    fmCurrentPath = path;
    fmUpdateBreadcrumb(path);

    const body = document.getElementById('fm-file-body');
    body.innerHTML = `<tr><td colspan="5" class="px-6 py-12 text-center text-slate-400 text-xs font-mono animate-pulse">SCANNING DIRECTORY...</td></tr>`;

    try {
        const url = fmMode === 'ftp'
            ? `/api/fm/ftp/browse?path=${encodeURIComponent(path || '/')}`
            : `/api/fm/browse?path=${encodeURIComponent(path)}`;
        const resp = await fetch(url);
        const data = await resp.json();
        if (data.error) { fmShowError(data.error); return; }
        fmRenderFiles(data);
    } catch (e) {
        fmShowError('Failed to load directory: ' + e);
    }
}

function fmRenderFiles(data) {
    const body = document.getElementById('fm-file-body');
    body.innerHTML = '';

    // Parent directory row
    if (data.parent !== null && data.parent !== undefined) {
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-slate-50 dark:hover:bg-white/[0.02] cursor-pointer transition-colors';
        tr.innerHTML = `
            <td class="px-4 py-3 w-8"><div class="w-4 h-4"></div></td>
            <td class="px-4 py-3" colspan="4">
                <div class="flex items-center gap-3" ondblclick="fmBrowse('${escFm(data.parent)}')">
                    <div class="w-8 h-8 flex items-center justify-center text-slate-400">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 9l-7 7-7-7"/></svg>
                    </div>
                    <span class="text-xs font-bold text-slate-400 font-mono">.. (Parent Directory)</span>
                </div>
            </td>`;
        body.appendChild(tr);
    }

    if (!data.items || data.items.length === 0) {
        body.innerHTML += `<tr><td colspan="5" class="px-6 py-8 text-center text-slate-400 text-xs font-mono">EMPTY DIRECTORY</td></tr>`;
        return;
    }

    data.items.forEach(item => {
        const icon = item.is_dir ? fmDirIcon() : fmFileIcon(item.ext || '');
        const size = item.size != null ? fmFormatSize(item.size) : '—';
        const safeP = escFm(item.path);
        const safeName = escFm(item.name);

        const tr = document.createElement('tr');
        tr.className = 'group hover:bg-slate-50 dark:hover:bg-white/[0.02] cursor-pointer transition-colors border-b border-slate-50 dark:border-white/[0.02]';
        tr.dataset.path = item.path;
        tr.innerHTML = `
            <td class="px-4 py-2.5 w-8">
                <input type="checkbox" class="fm-check w-4 h-4 rounded border-slate-300 accent-primary" 
                    onchange="fmToggleSelect(this, '${safeP}')" onclick="event.stopPropagation()">
            </td>
            <td class="px-4 py-2.5" ondblclick="${item.is_dir ? `fmBrowse('${safeP}')` : `fmDownload('${safeP}')`}">
                <div class="flex items-center gap-3">
                    <div class="w-7 h-7 flex items-center justify-center flex-shrink-0">${icon}</div>
                    <span class="text-xs font-medium text-slate-700 dark:text-slate-200 truncate max-w-[280px]">${item.name}</span>
                </div>
            </td>
            <td class="px-4 py-2.5 text-[10px] font-mono text-slate-400">${item.ext || (item.is_dir ? 'DIR' : '—')}</td>
            <td class="px-4 py-2.5 text-[10px] font-mono text-slate-400">${size}</td>
            <td class="px-4 py-2.5 text-[10px] font-mono text-slate-400">${item.modified || '—'}</td>`;
        body.appendChild(tr);
    });

    document.getElementById('fm-path-display').innerText = data.path;
    document.getElementById('fm-item-count').innerText = `${data.items.length} ITEMS`;
}

function fmToggleSelect(checkbox, path) {
    if (checkbox.checked) {
        fmSelectedItems.add(path);
    } else {
        fmSelectedItems.delete(path);
    }
    document.getElementById('fm-selected-count').innerText = fmSelectedItems.size > 0 ? `${fmSelectedItems.size} selected` : '';
}

function fmSelectAll() {
    const checks = document.querySelectorAll('.fm-check');
    const allChecked = [...checks].every(c => c.checked);
    checks.forEach(c => {
        c.checked = !allChecked;
        const path = c.closest('tr')?.dataset.path;
        if (path) {
            if (!allChecked) fmSelectedItems.add(path);
            else fmSelectedItems.delete(path);
        }
    });
}

// ─── Operations ─────────────────────────────────────────────────────────────

function fmDownload(path) {
    if (fmMode === 'ftp') {
        window.location.href = `/api/fm/ftp/download?path=${encodeURIComponent(path)}`;
    } else {
        window.location.href = `/api/fm/download?path=${encodeURIComponent(path)}`;
    }
}

async function fmDelete() {
    if (fmSelectedItems.size === 0) { fmShowToast('Select at least one item first.', 'warn'); return; }
    if (!confirm(`Delete ${fmSelectedItems.size} item(s)? This cannot be undone.`)) return;
    for (const path of fmSelectedItems) {
        await fetch('/api/fm/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path })
        });
    }
    fmSelectedItems.clear();
    fmBrowse(fmCurrentPath);
    fmShowToast('Deleted successfully.', 'success');
}

async function fmRename() {
    if (fmSelectedItems.size !== 1) { fmShowToast('Select exactly one item to rename.', 'warn'); return; }
    const path = [...fmSelectedItems][0];
    const name = path.split('/').pop();
    const newName = prompt('New name:', name);
    if (!newName || newName === name) return;
    const resp = await fetch('/api/fm/rename', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path, new_name: newName })
    });
    const data = await resp.json();
    if (data.status === 'success') { fmBrowse(fmCurrentPath); fmShowToast('Renamed.', 'success'); }
    else fmShowToast(data.error, 'error');
}

async function fmMkdir() {
    const name = prompt('New folder name:');
    if (!name) return;
    const resp = await fetch('/api/fm/mkdir', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: fmCurrentPath, name })
    });
    const data = await resp.json();
    if (data.status === 'success') { fmBrowse(fmCurrentPath); fmShowToast('Folder created.', 'success'); }
    else fmShowToast(data.error, 'error');
}

async function fmZip() {
    if (fmSelectedItems.size === 0) { fmShowToast('Select items to compress.', 'warn'); return; }
    const name = prompt('Archive filename:', 'archive.zip') || 'archive.zip';
    const resp = await fetch('/api/fm/zip', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paths: [...fmSelectedItems], dest: fmCurrentPath, name })
    });
    const data = await resp.json();
    if (data.status === 'success') { fmBrowse(fmCurrentPath); fmShowToast(`Compressed → ${data.archive}`, 'success'); }
    else fmShowToast(data.error, 'error');
}

async function fmExtract() {
    if (fmSelectedItems.size !== 1) { fmShowToast('Select exactly one archive to extract.', 'warn'); return; }
    const path = [...fmSelectedItems][0];
    const resp = await fetch('/api/fm/extract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path, dest: fmCurrentPath })
    });
    const data = await resp.json();
    if (data.status === 'success') { fmBrowse(fmCurrentPath); fmShowToast(`Extracted to ${data.extracted_to}`, 'success'); }
    else fmShowToast(data.error, 'error');
}

// ─── Upload ───────────────────────────────────────────────────────────────────

function fmTriggerUpload() {
    document.getElementById('fm-file-input').click();
}

async function fmUpload(input) {
    if (!input.files.length) return;
    const progress = document.getElementById('fm-upload-progress');
    progress.classList.remove('hidden');

    const formData = new FormData();
    formData.append('path', fmCurrentPath);
    for (const file of input.files) formData.append('files', file);

    try {
        const resp = await fetch('/api/fm/upload', { method: 'POST', body: formData });
        const data = await resp.json();
        if (data.status === 'success') {
            fmBrowse(fmCurrentPath);
            fmShowToast(`${data.uploaded.length} file(s) uploaded.`, 'success');
        } else {
            fmShowToast(data.error, 'error');
        }
    } catch (e) {
        fmShowToast('Upload failed: ' + e, 'error');
    } finally {
        progress.classList.add('hidden');
        input.value = '';
    }
}

// ─── Drag & Drop Upload ───────────────────────────────────────────────────────

function fmInitDragDrop() {
    const zone = document.getElementById('fm-drop-zone');
    if (!zone) return;
    ['dragenter', 'dragover'].forEach(ev => zone.addEventListener(ev, e => {
        e.preventDefault();
        zone.classList.add('border-primary', 'bg-primary/5');
    }));
    ['dragleave', 'drop'].forEach(ev => zone.addEventListener(ev, e => {
        e.preventDefault();
        zone.classList.remove('border-primary', 'bg-primary/5');
    }));
    zone.addEventListener('drop', async e => {
        const files = e.dataTransfer.files;
        const formData = new FormData();
        formData.append('path', fmCurrentPath);
        for (const f of files) formData.append('files', f);
        const resp = await fetch('/api/fm/upload', { method: 'POST', body: formData });
        const data = await resp.json();
        if (data.status === 'success') { fmBrowse(fmCurrentPath); fmShowToast(`${data.uploaded.length} dropped file(s) uploaded.`, 'success'); }
    });
}

// ─── FTP ────────────────────────────────────────────────────────────────────

async function fmFtpConnect() {
    const host = document.getElementById('ftp-host').value;
    const port = document.getElementById('ftp-port').value || 21;
    const user = document.getElementById('ftp-user').value || 'anonymous';
    const pwd  = document.getElementById('ftp-password').value || '';
    const statusEl = document.getElementById('ftp-status');

    statusEl.innerText = 'Connecting...';
    statusEl.className = 'text-[10px] font-bold text-amber-400';

    try {
        const resp = await fetch('/api/fm/ftp/connect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ host, port: parseInt(port), user, password: pwd })
        });
        const data = await resp.json();
        if (data.status === 'success') {
            fmMode = 'ftp';
            statusEl.innerText = `✓ CONNECTED — ${host}`;
            statusEl.className = 'text-[10px] font-bold text-success';
            document.getElementById('ftp-panel').classList.add('hidden');
            document.getElementById('ftp-disconnect-btn').classList.remove('hidden');
            document.getElementById('fm-mode-badge').innerText = 'FTP MODE';
            fmBrowse('/');
        } else {
            statusEl.innerText = data.error;
            statusEl.className = 'text-[10px] font-bold text-accent';
        }
    } catch (e) {
        statusEl.innerText = 'Connection failed: ' + e;
        statusEl.className = 'text-[10px] font-bold text-accent';
    }
}

async function fmFtpDisconnect() {
    await fetch('/api/fm/ftp/disconnect', { method: 'POST' });
    fmMode = 'local';
    document.getElementById('ftp-panel').classList.remove('hidden');
    document.getElementById('ftp-disconnect-btn').classList.add('hidden');
    document.getElementById('fm-mode-badge').innerText = 'LOCAL MODE';
    document.getElementById('ftp-status').innerText = '';
    fmBrowse('');
}

// ─── Breadcrumb ────────────────────────────────────────────────────────────

function fmUpdateBreadcrumb(path) {
    const bc = document.getElementById('fm-breadcrumb');
    const parts = path.split('/').filter(Boolean);
    let html = `<button onclick="fmBrowse('')" class="text-primary font-bold text-xs hover:underline">~</button>`;
    let accum = '';
    parts.forEach(p => {
        accum += '/' + p;
        const acc = accum;
        html += ` <span class="text-slate-400 mx-1">/</span>
            <button onclick="fmBrowse('${escFm(acc)}')" class="text-xs font-mono text-slate-500 hover:text-primary transition truncate max-w-[120px]">${p}</button>`;
    });
    bc.innerHTML = html;
}

// ─── Helpers ────────────────────────────────────────────────────────────────

function escFm(str) { return (str || '').replace(/'/g, "\\'").replace(/\\/g, '/'); }

function fmFormatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    if (bytes < 1073741824) return (bytes / 1048576).toFixed(1) + ' MB';
    return (bytes / 1073741824).toFixed(2) + ' GB';
}

function fmShowError(msg) {
    document.getElementById('fm-file-body').innerHTML = `
        <tr><td colspan="5" class="px-6 py-8 text-center text-accent text-xs font-mono">${msg}</td></tr>`;
}

function fmShowToast(msg, type = 'info') {
    const colors = { success: 'bg-emerald-500', error: 'bg-accent', warn: 'bg-amber-500', info: 'bg-primary' };
    const toast = document.createElement('div');
    toast.className = `fixed bottom-6 right-6 z-[200] px-5 py-3 rounded-xl text-white font-bold text-xs shadow-2xl ${colors[type]} animate-fade-in`;
    toast.innerText = msg;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
}

function fmDirIcon() {
    return `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#F59E0B" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>`;
}

function fmFileIcon(ext) {
    const colors = {
        '.zip': '#F43F5E', '.gz': '#F43F5E', '.tar': '#F43F5E', '.rar': '#F43F5E',
        '.py': '#3B82F6', '.js': '#F59E0B', '.ts': '#3B82F6', '.jsx': '#06B6D4', '.tsx': '#06B6D4',
        '.html': '#EF4444', '.css': '#6366F1', '.json': '#10B981', '.env': '#8B5CF6',
        '.jpg': '#EC4899', '.png': '#EC4899', '.gif': '#EC4899', '.webp': '#EC4899', '.svg': '#EC4899',
        '.pdf': '#EF4444', '.md': '#64748B', '.txt': '#94A3B8', '.log': '#94A3B8',
        '.sh': '#10B981', '.sql': '#0EA5E9',
    };
    const color = colors[ext] || '#64748B';
    return `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>`;
}

// Bind enter key to login
document.addEventListener('DOMContentLoaded', () => {
    const input = document.getElementById('fm-password-input');
    if (input) input.addEventListener('keydown', e => { if (e.key === 'Enter') fmLogin(); });
    fmInitDragDrop();
});
