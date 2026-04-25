// ─── Terminal & Command Center Logic ──────────────────────────────────────
let logEventSource = null;
let currentAppId = null;
let currentTarget = 'fe'; // Default to Frontend

function setTarget(target) {
    currentTarget = target;
    const appId = (target === 'be') ? 0 : 1;
    const label = (target === 'be') ? 'BACKEND_STREAM' : 'FRONTEND_STREAM';

    // Update UI for target selection
    document.querySelectorAll('.target-btn').forEach(btn => {
        btn.classList.remove('bg-primary', 'text-white', 'shadow-lg', 'shadow-primary/20');
        btn.classList.add('bg-slate-100', 'dark:bg-white/5', 'text-slate-600', 'dark:text-slate-400');
    });
    
    const activeBtn = document.getElementById(`target-${target}`);
    if (activeBtn) {
        activeBtn.classList.add('bg-primary', 'text-white', 'shadow-lg', 'shadow-primary/20');
        activeBtn.classList.remove('bg-slate-100', 'dark:bg-white/5', 'text-slate-600', 'dark:text-slate-400');
    }

    // Update Live Stream label
    const logLabel = document.getElementById('active-log-label');
    if (logLabel) {
        logLabel.innerText = label;
        logLabel.classList.toggle('text-primary', target === 'be');
        logLabel.classList.toggle('text-blue-500', target === 'fe');
    }

    // Auto-switch logs and process display
    startLogStream(appId);
    
    // Toggle visibility of target-specific process info
    document.querySelectorAll('.process-info').forEach(el => el.classList.add('hidden'));
    const activeInfo = document.getElementById(`process-info-${target}`);
    if (activeInfo) activeInfo.classList.remove('hidden');
}

// --- Git Logic ---
async function runGit(action) {
    const terminal = document.getElementById('terminal-content');
    terminal.innerHTML += `\n\n<span class="text-primary font-bold">>>> EXECUTING GIT ${action.toUpperCase()} [${currentTarget.toUpperCase()}]...</span>\n`;
    terminal.scrollTop = terminal.scrollHeight;

    try {
        const resp = await fetch(`/api/git-${action}?target=${currentTarget}`, { method: 'POST' });
        const data = await resp.json();
        const colorClass = data.status === 'success' ? 'text-success' : 'text-accent';
        terminal.innerHTML += `<div class="${colorClass} mt-2 bg-white/5 p-3 rounded-lg border border-white/5">${data.output}</div>`;
    } catch (err) {
        terminal.innerHTML += `<div class="text-accent mt-2">FATAL: Execution failed. System unreachable.</div>`;
    }
    terminal.scrollTop = terminal.scrollHeight;
}

// --- Generic Action Logic ---
async function runAction(action) {
    const terminal = document.getElementById('terminal-content');
    terminal.innerHTML += `\n\n<span class="text-primary font-bold">>>> EXECUTING ${action.toUpperCase()} [${currentTarget.toUpperCase()}]...</span>\n`;
    terminal.scrollTop = terminal.scrollHeight;

    try {
        const resp = await fetch(`/api/${action}?target=${currentTarget}`, { method: 'POST' });
        const data = await resp.json();
        const colorClass = data.status === 'success' ? 'text-success' : 'text-accent';
        terminal.innerHTML += `<div class="${colorClass} mt-2 bg-white/5 p-3 rounded-lg border border-white/5">${data.output}</div>`;
    } catch (err) {
        terminal.innerHTML += `<div class="text-accent mt-2">FATAL: Execution failed. System unreachable.</div>`;
    }
    terminal.scrollTop = terminal.scrollHeight;
}

async function pm2Action(action, appId) {
    const terminal = document.getElementById('terminal-content');
    terminal.innerHTML += `\n\n<span class="text-blue-400 font-bold">>>> EXECUTING PM2 ${action.toUpperCase()} [ID: ${appId}]...</span>\n`;
    terminal.scrollTop = terminal.scrollHeight;

    try {
        const resp = await fetch(`/api/pm2-action/${action}/${appId}`, { method: 'POST' });
        const data = await resp.json();
        const colorClass = data.status === 'success' ? 'text-emerald-400' : 'text-rose-400';
        terminal.innerHTML += `<div class="${colorClass} mt-2 bg-white/5 p-3 rounded-lg border border-white/5 font-mono text-[10px] whitespace-pre-wrap">${data.output}</div>`;
    } catch (err) {
        terminal.innerHTML += `<div class="text-rose-500 mt-2 italic">FATAL: Action command failed to reach the core.</div>`;
    }
    terminal.scrollTop = terminal.scrollHeight;
}

async function pm2Reload(appId) {
    return pm2Action('reload', appId);
}

async function clearLogs(appId) {
    const terminal = document.getElementById('terminal-content');
    terminal.innerHTML += `\n\n<span class="text-yellow-400 font-bold">>>> FLUSHING PM2 LOGS [ID: ${appId}]...</span>\n`;
    terminal.scrollTop = terminal.scrollHeight;

    try {
        const resp = await fetch(`/api/clear-logs/${appId}`, { method: 'POST' });
        const data = await resp.json();
        const colorClass = data.status === 'success' ? 'text-emerald-400' : 'text-rose-400';
        terminal.innerHTML += `<div class="${colorClass} mt-2 bg-white/5 p-3 rounded-lg border border-white/5 font-mono text-[10px] whitespace-pre-wrap">${data.output}</div>`;
    } catch (err) {
        terminal.innerHTML += `<div class="text-rose-500 mt-2 italic">FATAL: Clear logs command failed.</div>`;
    }
    terminal.scrollTop = terminal.scrollHeight;
}

// --- Environment Toggle Logic ---
async function toggleEnv(env, action) {
    const terminal = document.getElementById('terminal-content');
    const actionLabel = action === 'start' ? 'INITIALIZING' : 'SHUTTING_DOWN';
    terminal.innerHTML += `\n\n<span class="text-primary font-bold">>>> ${actionLabel} ENVIRONMENT: [${env.toUpperCase()}]...</span>\n`;
    terminal.scrollTop = terminal.scrollHeight;

    try {
        const resp = await fetch(`/api/env/${action}/${env}`, { method: 'POST' });
        const data = await resp.json();
        const colorClass = data.status === 'success' ? 'text-success' : 'text-accent';
        
        if (data.status === 'success') {
            terminal.innerHTML += `<div class="${colorClass} mt-2 bg-white/5 p-3 rounded-lg border border-white/5 font-bold">✅ ${data.message}</div>`;
            if (data.killed_count !== undefined) {
                terminal.innerHTML += `<div class="text-slate-500 text-[10px] ml-4">Processes terminated: ${data.killed_count}</div>`;
            }
        } else {
            terminal.innerHTML += `<div class="${colorClass} mt-2 bg-rose-500/10 p-3 rounded-lg border border-rose-500/20 font-bold">❌ ERROR: ${data.message}</div>`;
        }
    } catch (err) {
        terminal.innerHTML += `<div class="text-accent mt-2">FATAL: Environment control command failed.</div>`;
    }
    terminal.scrollTop = terminal.scrollHeight;
}

// --- Log Streaming Logic ---
function startLogStream(appId) {
    if (currentAppId === appId) return;
    stopLogStream();

    currentAppId = appId;
    const terminal = document.getElementById('terminal-content');
    terminal.innerHTML = `<div class="text-primary opacity-50 mb-4 tracking-tighter">CONNECTED_TO_APP_ID: ${appId} // FETCHING_REALTIME_STREAM...</div>`;

    // UI updates for log stream label are now handled in setTarget()
    // and we no longer have separate .log-tab buttons.

    logEventSource = new EventSource(`/api/logs/${appId}`);
    logEventSource.onmessage = function (event) {
        const line = document.createElement('div');
        line.className = 'mb-1 border-l-2 border-white/5 pl-3 hover:bg-white/5 transition-colors';
        line.textContent = event.data;
        terminal.appendChild(line);

        // Keep only last 200 lines
        if (terminal.childNodes.length > 200) {
            terminal.removeChild(terminal.childNodes[0]);
        }
        terminal.scrollTop = terminal.scrollHeight;
    };

    logEventSource.onerror = function () {
        terminal.innerHTML += `<div class="text-accent font-bold mt-4">STREAM_INTERRUPTED: Retrying connection...</div>`;
        stopLogStream();
    };
}

function stopLogStream() {
    if (logEventSource) {
        logEventSource.close();
        logEventSource = null;
        currentAppId = null;
    }
}

function clearTerminal() {
    document.getElementById('terminal-content').innerHTML = `<div class="text-primary opacity-50 mb-4 tracking-tighter">BUFFER_CLEARED // WAITING_FOR_DATA...</div>`;
}
