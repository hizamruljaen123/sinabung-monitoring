// ─── Navigation Logic ─────────────────────────────────────────────────────
const PAGE_TITLES = {
    dashboard: 'CLUSTER STATUS',
    control: 'SERVER CONTROL',
    database: 'DATABASE MGR',
    filemanager: 'FILE MANAGER',
    bot: 'BOT ACTIVITY LOGS'
};

function showPage(pageId) {
    // Hide all pages
    document.querySelectorAll('.page-view').forEach(p => {
        p.classList.add('hidden');
        p.classList.remove('active');
    });

    // Show active page
    const activePage = document.getElementById(pageId + '-view');
    if (activePage) {
        activePage.classList.remove('hidden');
        activePage.classList.add('active');
    }

    // Nav items
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    const activeNav = document.getElementById('nav-' + pageId);
    if (activeNav) activeNav.classList.add('active');

    // Page title
    const titleEl = document.getElementById('page-title');
    if (titleEl) titleEl.innerText = PAGE_TITLES[pageId] || pageId.toUpperCase();

    // Side effects
    if (pageId === 'control') {
        setTarget('be');
    } else if (pageId === 'database') {
        loadDbTables();
        stopLogStream();
    } else if (pageId === 'filemanager') {
        stopLogStream();
        fmCheckStatus();
    } else if (pageId === 'bot') {
        stopLogStream();
        refreshBotHistory();
    } else {
        stopLogStream();
    }
}

async function refreshBotHistory() {
    const tbody = document.getElementById('bot-history-tbody');
    if (!tbody) return;
    
    try {
        const data = await fetch('/api/bot-history').then(r => r.json());
        tbody.innerHTML = data.map(log => `
            <tr class="tbl-row">
                <td style="padding:6px 14px; font-family:'JetBrains Mono'; font-size:9px; color:#64748B;">#${log.id}</td>
                <td style="padding:6px 10px; font-family:'JetBrains Mono'; font-size:9px; color:#0EA5E9;">${log.chat_id}</td>
                <td style="padding:6px 10px; font-family:'JetBrains Mono'; font-size:9px; color:#94a3b8;">${log.message_id}</td>
                <td style="padding:6px 10px; font-family:'JetBrains Mono'; font-size:9px; color:#475569;">${log.sent_at}</td>
                <td style="padding:6px 14px; text-align:right;">
                    <span class="metric-chip chip-green" style="font-size:7px;">DELIVERED</span>
                </td>
            </tr>
        `).join('');
    } catch (e) {
        console.error('Bot history fetch error:', e);
    }
}
