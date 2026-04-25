// ─── Navigation Logic ─────────────────────────────────────────────────────
const PAGE_TITLES = {
    dashboard: 'CLUSTER STATUS',
    control: 'SERVER CONTROL',
    database: 'DATABASE MGR',
    filemanager: 'FILE MANAGER'
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
    } else {
        stopLogStream();
    }
}
