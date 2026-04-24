// ─── Chart Configuration & Stats Polling ──────────────────────────────────
const MAX_DATA_POINTS = 40;
let chartLabels = [];
let cpuData = [];
let ramData = [];

function getChartConfig(isDark) {
    const gridColor = isDark ? 'rgba(255, 255, 255, 0.03)' : 'rgba(0, 0, 0, 0.03)';
    const textColor = isDark ? '#64748B' : '#94A3B8';

    return {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            x: { display: true, grid: { display: false }, ticks: { display: false } },
            y: {
                beginAtZero: true,
                max: 100,
                grid: { color: gridColor, drawBorder: false },
                ticks: {
                    color: textColor,
                    font: { size: 10, family: 'JetBrains Mono', weight: '500' },
                    padding: 10,
                    callback: value => value + '%'
                }
            }
        },
        plugins: {
            legend: { display: false },
            tooltip: {
                backgroundColor: isDark ? '#1E293B' : '#FFFFFF',
                titleColor: isDark ? '#F1F5F9' : '#0F172A',
                bodyColor: isDark ? '#F1F5F9' : '#0F172A',
                padding: 12,
                cornerRadius: 12,
                displayColors: false,
                borderWidth: 1,
                borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'
            }
        },
        elements: {
            line: { tension: 0.4, borderWidth: 3, capStyle: 'round' },
            point: { radius: 0, hoverRadius: 6, hitRadius: 10 }
        },
        interaction: { intersect: false, mode: 'index' }
    };
}

const ctxCpu = document.getElementById('cpuChart').getContext('2d');
const ctxRam = document.getElementById('ramChart').getContext('2d');

const cpuGradient = ctxCpu.createLinearGradient(0, 0, 0, 200);
cpuGradient.addColorStop(0, 'rgba(14, 165, 233, 0.2)');
cpuGradient.addColorStop(1, 'rgba(14, 165, 233, 0)');

const ramGradient = ctxRam.createLinearGradient(0, 0, 0, 200);
ramGradient.addColorStop(0, 'rgba(99, 102, 241, 0.2)');
ramGradient.addColorStop(1, 'rgba(99, 102, 241, 0)');

const isDarkInitial = document.documentElement.classList.contains('dark');

const cpuChart = new Chart(ctxCpu, {
    type: 'line',
    data: { labels: chartLabels, datasets: [{ label: 'CPU Load', data: cpuData, borderColor: '#0EA5E9', backgroundColor: cpuGradient, fill: true }] },
    options: { ...getChartConfig(isDarkInitial), plugins: { ...getChartConfig(isDarkInitial).plugins, title: { display: true, text: 'CORE PROCESSOR LOAD', align: 'start', color: isDarkInitial ? '#F1F5F9' : '#0F172A', font: { family: 'Outfit', size: 14, weight: '700' }, padding: { bottom: 20 } } } }
});

const ramChart = new Chart(ctxRam, {
    type: 'line',
    data: { labels: chartLabels, datasets: [{ label: 'RAM Usage', data: ramData, borderColor: '#6366F1', backgroundColor: ramGradient, fill: true }] },
    options: { ...getChartConfig(isDarkInitial), plugins: { ...getChartConfig(isDarkInitial).plugins, title: { display: true, text: 'GLOBAL MEMORY POOL', align: 'start', color: isDarkInitial ? '#F1F5F9' : '#0F172A', font: { family: 'Outfit', size: 14, weight: '700' }, padding: { bottom: 20 } } } }
});

function updateChartColors(isDark) {
    const options = getChartConfig(isDark);
    const titleColor = isDark ? '#F1F5F9' : '#0F172A';

    cpuChart.options = { ...options, plugins: { ...options.plugins, title: { display: true, text: 'CORE PROCESSOR LOAD', align: 'start', color: titleColor, font: { family: 'Outfit', size: 14, weight: '700' }, padding: { bottom: 20 } } } };
    ramChart.options = { ...options, plugins: { ...options.plugins, title: { display: true, text: 'GLOBAL MEMORY POOL', align: 'start', color: titleColor, font: { family: 'Outfit', size: 14, weight: '700' }, padding: { bottom: 20 } } } };

    cpuChart.update();
    ramChart.update();
}

// ─── Helper functions ────────────────────────────────────────────────────

function getColor(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || "#000";
}

function getHeatmapColor(value, max) {
    const ratio = Math.min(value / max, 1);
    if (ratio < 0.4) return getColor("--success");
    if (ratio < 0.75) return getColor("--warning");
    return getColor("--accent");
}

// ─── Stats Polling ──────────────────────────────────────────────────────────

async function fetchStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();

        document.getElementById('last-update').innerText = `SYNCHRONIZED: ${data.time}`;

        // Metrics Cards
        const active = data.services.filter(s => s.status === 'ONLINE').length;
        const total = data.services.length;

        document.getElementById('metrics-container').innerHTML = `
            <div class="grid grid-cols-1 gap-4">
                <div class="stat-card p-5 group">
                    <div class="flex justify-between items-center mb-3">
                        <p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">CPU UTILIZATION</p>
                        <span class="text-[9px] font-bold text-primary bg-primary/5 border border-primary/10 px-1.5 py-0.5 rounded">REAL-TIME</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <h3 class="text-2xl font-bold font-mono text-slate-800 dark:text-white">${data.total_cpu}%</h3>
                        <div class="w-1.5 h-1.5 rounded-full bg-success"></div>
                    </div>
                </div>

                <div class="stat-card p-5 group">
                    <div class="flex justify-between items-center mb-3">
                        <p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">MEMORY ALLOCATION</p>
                        <span class="text-[9px] font-bold text-secondary bg-secondary/5 border border-secondary/10 px-1.5 py-0.5 rounded">${data.ram_percent}%</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <h3 class="text-2xl font-bold font-mono text-slate-800 dark:text-white">${data.total_ram}</h3>
                        <span class="text-[10px] text-slate-400 font-bold tracking-tighter uppercase">GB / ${data.total_ram_capacity} GB</span>
                    </div>
                </div>

                <div class="stat-card p-5 group">
                    <div class="flex justify-between items-center mb-3">
                        <p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">ACTIVE CLUSTER NODES</p>
                        <span class="text-[9px] font-bold text-success bg-success/5 border border-success/10 px-1.5 py-0.5 rounded">OPTIMAL</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <h3 class="text-2xl font-bold font-mono text-slate-800 dark:text-white">${active}</h3>
                        <span class="text-[10px] text-slate-400 font-bold tracking-tighter uppercase">NODES / ${total} ONLINE</span>
                    </div>
                </div>
            </div>
        `;

        // Database Stats
        let dbHtml = '';
        for (const [table, count] of Object.entries(data.db_counts)) {
            const formattedCount = count === -1 ? 'OFFLINE' : count.toLocaleString();
            dbHtml += `
                <div class="flex items-center justify-between px-3 py-2 hover:bg-slate-50 dark:hover:bg-white/[0.02] transition-all group cursor-default border-b border-slate-50 dark:border-white/[0.02] last:border-0">
                    <div class="flex items-center gap-2">
                        <div class="w-1 h-1 rounded-full ${count === -1 ? 'bg-accent' : 'bg-primary/30'}"></div>
                        <span class="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-tight">${table.replace(/_/g, ' ')}</span>
                    </div>
                    <span class="font-mono text-[11px] font-bold text-slate-700 dark:text-slate-200">${formattedCount}</span>
                </div>
            `;
        }
        document.getElementById('db-stats-container').innerHTML = dbHtml;

        // Services Table
        const sortedServices = [...data.services].sort((a, b) => {
            if (b.errors !== a.errors) return b.errors - a.errors;
            if (b.cpu !== a.cpu) return b.cpu - a.cpu;
            return b.ram - a.ram;
        });

        const tbody = document.querySelector('#services-table tbody');
        tbody.innerHTML = '';

        sortedServices.forEach((svc) => {
            const cpuColor = getHeatmapColor(svc.cpu, 100);
            const ramColor = getHeatmapColor(svc.ram, 2048);

            const tr = document.createElement('tr');
            tr.className = `group hover:bg-slate-50 dark:hover:bg-white/[0.02] transition-colors duration-150 ${svc.status === 'OFFLINE' ? 'opacity-40' : ''}`;
            tr.innerHTML = `
                <td class="px-6 py-3.5"><span class="font-bold text-slate-700 dark:text-slate-200 text-xs tracking-tight uppercase">${svc.name}</span></td>
                <td class="px-4 py-3.5"><span class="text-[10px] font-mono text-slate-500 dark:text-slate-400 font-bold">${svc.port}</span></td>
                <td class="px-4 py-3.5 font-mono text-[10px] text-slate-400 uppercase tracking-tighter">${svc.pid}</td>
                <td class="px-4 py-3.5">
                    <div class="flex items-center gap-2">
                        <div class="w-12 h-1 bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden">
                            <div class="h-full rounded-full transition-all duration-700" style="width: ${Math.min(svc.cpu, 100)}%; background: ${cpuColor}"></div>
                        </div>
                        <span class="font-mono text-[10px] font-bold text-slate-600 dark:text-slate-400">${svc.cpu}%</span>
                    </div>
                </td>
                <td class="px-4 py-3.5">
                    <div class="flex items-center gap-2">
                        <div class="w-12 h-1 bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden">
                            <div class="h-full rounded-full transition-all duration-700" style="width: ${Math.min((svc.ram / 2048) * 100, 100)}%; background: ${ramColor}"></div>
                        </div>
                        <span class="font-mono text-[10px] font-bold text-slate-600 dark:text-slate-400">${svc.ram}MB</span>
                    </div>
                </td>
                <td class="px-4 py-3.5">
                    ${svc.errors > 0
                        ? `<span class="text-accent font-bold text-[9px] uppercase tracking-wider flex items-center gap-1"><div class="w-1 h-1 rounded-full bg-accent animate-pulse"></div> ${svc.errors} ERR</span>`
                        : `<span class="text-slate-400 font-bold text-[9px] uppercase tracking-wider">Optimal</span>`}
                </td>
                <td class="px-6 py-3.5 text-right">
                    <div class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded border border-transparent ${svc.status === 'ONLINE' ? 'bg-success/5 text-success border-success/10' : 'bg-slate-100 dark:bg-white/5 text-slate-400'}">
                        <div class="w-1 h-1 rounded-full ${svc.status === 'ONLINE' ? 'bg-success' : 'bg-slate-400'}"></div>
                        <span class="text-[9px] font-bold uppercase tracking-widest">${svc.status}</span>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });

        // Update Charts
        chartLabels.push(data.time);
        cpuData.push(data.total_cpu);
        ramData.push(data.ram_percent);

        if (chartLabels.length > MAX_DATA_POINTS) {
            chartLabels.shift(); cpuData.shift(); ramData.shift();
        }

        cpuChart.update('none');
        ramChart.update('none');

    } catch (error) {
        console.error('Monitoring Sync Error:', error);
        document.getElementById('status-pulse').className = 'status-dot bg-accent';
        document.getElementById('last-update').innerText = 'CONNECTION LOST';
    }
}

setInterval(fetchStats, 3000);
fetchStats();
