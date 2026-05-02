// ─── Terminal & Command Center Logic ──────────────────────────────────────
let logEventSource = null;
let currentAppId = null;
let currentTarget = 'be';

function setTarget(target) {
    currentTarget = target;
    const appId = (target === 'be') ? 0 : 1;

    document.querySelectorAll('#target-be, #target-fe').forEach(btn => {
        btn.classList.remove('btn-primary');
        btn.classList.add('btn-ghost');
    });
    const activeBtn = document.getElementById(`target-${target}`);
    if (activeBtn) {
        activeBtn.classList.remove('btn-ghost');
        activeBtn.classList.add('btn-primary');
    }

    const logLabel = document.getElementById('active-log-label');
    if (logLabel) logLabel.innerText = target === 'be' ? 'BE_LOGS' : 'FE_LOGS';

    startLogStream(appId);

    document.querySelectorAll('.process-info').forEach(el => el.style.display = 'none');
    const activeInfo = document.getElementById(`process-info-${target}`);
    if (activeInfo) activeInfo.style.display = 'flex';
}

async function runGit(action) {
    appendTerminal(`>>> GIT ${action.toUpperCase()} [${currentTarget.toUpperCase()}]`, 'info');
    try {
        const data = await fetch(`/api/git-${action}?target=${currentTarget}`, { method: 'POST' }).then(r => r.json());
        appendTerminal(data.output || data.message, data.status === 'success' ? 'success' : 'error');
    } catch (e) {
        appendTerminal('FATAL: Command failed', 'error');
    }
}

async function runAction(action) {
    appendTerminal(`>>> ${action.toUpperCase()} [${currentTarget.toUpperCase()}]`, 'info');
    try {
        const data = await fetch(`/api/${action}?target=${currentTarget}`, { method: 'POST' }).then(r => r.json());
        appendTerminal(data.output || data.message, data.status === 'success' ? 'success' : 'error');
    } catch (e) {
        appendTerminal('FATAL: Command failed', 'error');
    }
}

async function pm2Reload(appId) {
    appendTerminal(`>>> PM2 RELOAD [ID:${appId}]`, 'warn');
    try {
        const data = await fetch(`/api/pm2-reload/${appId}`, { method: 'POST' }).then(r => r.json());
        appendTerminal(data.output || data.message, data.status === 'success' ? 'success' : 'error');
    } catch (e) {
        appendTerminal('FATAL: PM2 action failed', 'error');
    }
}

async function clearLogs(appId) {
    appendTerminal(`>>> FLUSH LOGS [ID:${appId}]`, 'warn');
    try {
        const data = await fetch(`/api/clear-logs/${appId}`, { method: 'POST' }).then(r => r.json());
        appendTerminal(data.output || data.message, data.status === 'success' ? 'success' : 'error');
    } catch (e) {
        appendTerminal('FATAL: Clear logs failed', 'error');
    }
}

async function toggleEnv(env, action) {
    const label = action === 'start' ? `▶ STARTING ${env.toUpperCase()}` : `■ STOPPING ${env.toUpperCase()}`;
    appendTerminal(label, 'info');
    try {
        const data = await fetch(`/api/env/${action}/${env}`, { method: 'POST' }).then(r => r.json());
        if (data.status === 'success') {
            appendTerminal(`✓ ${data.message}`, 'success');
            if (data.killed_count !== undefined) appendTerminal(`  ↳ Terminated ${data.killed_count} processes`, 'warn');
        } else {
            appendTerminal(`✗ ${data.message}`, 'error');
        }
    } catch (e) {
        appendTerminal('FATAL: Env control failed', 'error');
    }
}

function appendTerminal(msg, type = 'info') {
    const t = document.getElementById('terminal-content');
    if (!t) return;
    const colors = { success: '#10B981', error: '#F43F5E', warn: '#F59E0B', info: '#0EA5E9' };
    const line = document.createElement('div');
    line.style.cssText = `color:${colors[type]||'#94a3b8'};padding:1px 0;border-left:2px solid ${colors[type]||'rgba(255,255,255,.1)'};padding-left:8px;margin:1px 0;`;
    line.textContent = msg;
    t.appendChild(line);
    if (t.children.length > 300) t.removeChild(t.children[0]);
    t.scrollTop = t.scrollHeight;
}

function startLogStream(appId) {
    if (currentAppId === appId) return;
    stopLogStream();
    currentAppId = appId;
    const t = document.getElementById('terminal-content');
    if (t) t.innerHTML = `<span style="color:#0EA5E9;opacity:.5">CONNECTED // APP_ID:${appId} // STREAMING...</span>`;
    logEventSource = new EventSource(`/api/logs/${appId}`);
    logEventSource.onmessage = (e) => {
        const t = document.getElementById('terminal-content');
        if (!t) return;
        const line = document.createElement('div');
        line.style.cssText = 'padding:1px 0 1px 8px;border-left:1px solid rgba(255,255,255,.04);color:#64748B;';
        line.textContent = e.data;
        t.appendChild(line);
        if (t.children.length > 300) t.removeChild(t.children[0]);
        t.scrollTop = t.scrollHeight;
    };
    logEventSource.onerror = () => {
        appendTerminal('STREAM_INTERRUPTED', 'error');
        stopLogStream();
    };
}

function stopLogStream() {
    if (logEventSource) { logEventSource.close(); logEventSource = null; currentAppId = null; }
}

function clearTerminal() {
    const t = document.getElementById('terminal-content');
    if (t) t.innerHTML = '<span style="color:#0EA5E9;opacity:.5">BUFFER_CLEARED // READY</span>';
}

async function injectCommand() {
    const input = document.getElementById('terminal-input');
    if (!input) return;
    const command = input.value.trim();
    if (!command) return;

    appendTerminal(`$ ${command}`, 'info');
    input.value = '';

    try {
        const response = await fetch('/api/terminal/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target: currentTarget, command })
        });
        const data = await response.json();
        
        if (data.status === 'success') {
            if (data.stdout) appendTerminal(data.stdout, 'info');
            if (data.stderr) appendTerminal(data.stderr, 'error');
            if (!data.stdout && !data.stderr) appendTerminal('✓ Command executed (no output)', 'success');
        } else {
            appendTerminal(`✗ ERROR: ${data.message}`, 'error');
        }
    } catch (e) {
        appendTerminal(`FATAL: ${e.message}`, 'error');
    }
}
