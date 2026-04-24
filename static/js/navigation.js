// ─── Navigation Logic ─────────────────────────────────────────────────────
function showPage(pageId) {
    document.querySelectorAll('.page-view').forEach(p => p.classList.add('hidden'));
    document.getElementById(pageId + '-view').classList.remove('hidden');

    // Update Sidebar Active State
    document.querySelectorAll('.nav-item').forEach(n => {
        n.classList.remove('bg-primary/10', 'text-primary', 'border-primary/20', 'font-semibold');
        n.classList.add('text-slate-500', 'dark:text-slate-400');
    });
    const activeNav = document.getElementById('nav-' + pageId);
    activeNav.classList.remove('text-slate-500', 'dark:text-slate-400');
    activeNav.classList.add('bg-primary/10', 'text-primary', 'border-primary/20', 'font-semibold');

    if (pageId === 'control') {
        setTarget('be'); // Default to BE logs and unified target
    } else if (pageId === 'database') {
        loadDbTables();
        stopLogStream();
    } else if (pageId === 'filemanager') {
        stopLogStream();
        fmCheckStatus(); // Check if already authenticated
    } else {
        stopLogStream();
    }
}
