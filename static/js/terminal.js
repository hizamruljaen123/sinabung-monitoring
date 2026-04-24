// ─── Terminal & Command Center Logic ──────────────────────────────────────
let logEventSource = null;
let currentAppId = null;

// --- Git Logic ---
async function runGit(action) {
    const terminal = document.getElementById('terminal-content');
    terminal.innerHTML += `\n\n<span class="text-primary font-bold">>>> EXECUTING GIT ${action.toUpperCase()}...</span>\n`;
    terminal.scrollTop = terminal.scrollHeight;

    try {
        const resp = await fetch(`/api/git-${action}`, { method: 'POST' });
        const data = await resp.json();
        const colorClass = data.status === 'success' ? 'text-success' : 'text-accent';
        terminal.innerHTML += `<div class="${colorClass} mt-2 bg-white/5 p-3 rounded-lg border border-white/5">${data.output}</div>`;
    } catch (err) {
        terminal.innerHTML += `<div class="text-accent mt-2">FATAL: Execution failed. System unreachable.</div>`;
    }
    terminal.scrollTop = terminal.scrollHeight;
}

async function pm2Reload(appId) {
    const terminal = document.getElementById('terminal-content');
    terminal.innerHTML += `\n\n<span class="text-blue-400 font-bold">>>> EXECUTING PM2 RELOAD [ID: ${appId}]...</span>\n`;
    terminal.scrollTop = terminal.scrollHeight;

    try {
        const resp = await fetch(`/api/pm2-reload/${appId}`, { method: 'POST' });
        const data = await resp.json();
        const colorClass = data.status === 'success' ? 'text-emerald-400' : 'text-rose-400';
        terminal.innerHTML += `<div class="${colorClass} mt-2 bg-white/5 p-3 rounded-lg border border-white/5 font-mono text-[10px] whitespace-pre-wrap">${data.output}</div>`;
    } catch (err) {
        terminal.innerHTML += `<div class="text-rose-500 mt-2 italic">FATAL: Reload command failed to reach the core.</div>`;
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

    // Update UI tabs
    document.querySelectorAll('.log-tab').forEach(t => {
        t.classList.remove('border-primary', 'bg-primary/5', 'text-primary');
        t.classList.add('border-transparent', 'bg-slate-50', 'dark:bg-white/[0.02]', 'text-slate-500', 'dark:text-slate-400');
        t.querySelector('div').classList.remove('bg-primary', 'animate-pulse');
        t.querySelector('div').classList.add('bg-slate-400');
    });

    const activeTab = document.getElementById(`btn-log-${appId}`);
    activeTab.classList.add('border-primary', 'bg-primary/5', 'text-primary');
    activeTab.classList.remove('border-transparent', 'bg-slate-50', 'dark:bg-white/[0.02]', 'text-slate-500', 'dark:text-slate-400');
    activeTab.querySelector('div').classList.add('bg-primary', 'animate-pulse');
    activeTab.querySelector('div').classList.remove('bg-slate-400');

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
