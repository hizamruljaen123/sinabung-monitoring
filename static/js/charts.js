// ─── Chart Configuration & Stats Polling ──────────────────────────────────
const MAX_DATA_POINTS = 60;
let chartLabels = [], cpuData = [], ramData = [];

function getChartOpts() {
    return {
        responsive: true, maintainAspectRatio: false,
        scales: {
            x: { display: false },
            y: { display: false, beginAtZero: true, max: 100 }
        },
        plugins: { legend: { display: false }, tooltip: { enabled: false } },
        elements: {
            line: { tension: 0.4, borderWidth: 1.5, capStyle: 'round' },
            point: { radius: 0 }
        },
        animation: false
    };
}

const ctxCpu = document.getElementById('cpuChart')?.getContext('2d');
const ctxRam = document.getElementById('ramChart')?.getContext('2d');
let cpuChart, ramChart;

if (ctxCpu) {
    const cpuGrad = ctxCpu.createLinearGradient(0, 0, 0, 80);
    cpuGrad.addColorStop(0, 'rgba(14,165,233,0.3)');
    cpuGrad.addColorStop(1, 'rgba(14,165,233,0)');
    cpuChart = new Chart(ctxCpu, {
        type: 'line',
        data: { labels: chartLabels, datasets: [{ data: cpuData, borderColor: '#0EA5E9', backgroundColor: cpuGrad, fill: true }] },
        options: getChartOpts()
    });
}

if (ctxRam) {
    const ramGrad = ctxRam.createLinearGradient(0, 0, 0, 80);
    ramGrad.addColorStop(0, 'rgba(99,102,241,0.3)');
    ramGrad.addColorStop(1, 'rgba(99,102,241,0)');
    ramChart = new Chart(ctxRam, {
        type: 'line',
        data: { labels: chartLabels, datasets: [{ data: ramData, borderColor: '#6366F1', backgroundColor: ramGrad, fill: true }] },
        options: getChartOpts()
    });
}

function heatColor(val, max) {
    const r = Math.min(val / max, 1);
    if (r < 0.4) return '#10B981';
    if (r < 0.75) return '#F59E0B';
    return '#F43F5E';
}

async function fetchStats() {
    try {
        const data = await fetch('/api/stats').then(r => r.json());

        // Header bar
        const onlineCount = data.services.filter(s => s.status === 'ONLINE').length;
        const totalCount = data.services.length;
        document.getElementById('last-update')?.setText?.(`${data.time}`) || (document.getElementById('last-update') && (document.getElementById('last-update').innerText = data.time));
        document.getElementById('header-cpu') && (document.getElementById('header-cpu').innerText = `CPU ${data.total_cpu}%`);
        document.getElementById('header-ram') && (document.getElementById('header-ram').innerText = `RAM ${data.ram_percent}%`);
        document.getElementById('header-nodes') && (document.getElementById('header-nodes').innerText = `${onlineCount}/${totalCount} UP`);

        // KPI Cards
        const cpuEl = document.getElementById('kpi-cpu');
        if (cpuEl) {
            cpuEl.innerText = data.total_cpu + '%';
            const cpuBar = document.getElementById('kpi-cpu-bar');
            if (cpuBar) { cpuBar.style.width = data.total_cpu + '%'; cpuBar.style.background = heatColor(data.total_cpu, 100); }
        }
        const ramEl = document.getElementById('kpi-ram');
        if (ramEl) {
            ramEl.innerText = data.ram_percent + '%';
            const ramBar = document.getElementById('kpi-ram-bar');
            if (ramBar) { ramBar.style.width = data.ram_percent + '%'; ramBar.style.background = heatColor(data.ram_percent, 100); }
            const ramDet = document.getElementById('kpi-ram-detail');
            if (ramDet) ramDet.innerText = `${data.total_ram} / ${data.total_ram_capacity} GB`;
        }
        const nodesOn = document.getElementById('kpi-nodes-on');
        if (nodesOn) nodesOn.innerText = onlineCount;
        const nodesTotal = document.getElementById('kpi-nodes-total');
        if (nodesTotal) nodesTotal.innerText = totalCount;

        // Service counts
        const svcOn = document.getElementById('svc-online-count');
        if (svcOn) svcOn.innerText = `${onlineCount} ONLINE`;
        const svcOff = document.getElementById('svc-offline-count');
        if (svcOff) {
            const offCount = totalCount - onlineCount;
            svcOff.innerText = `${offCount} OFFLINE`;
            svcOff.classList.toggle('hidden', offCount === 0);
        }

        // DB Stats
        const dbCont = document.getElementById('db-stats-container');
        if (dbCont) {
            dbCont.innerHTML = Object.entries(data.db_counts).map(([t, c]) => {
                const val = c === -1 ? '<span style="color:#F43F5E">OFFLINE</span>' : `<span style="font-family:\'JetBrains Mono\';color:#94a3b8">${c.toLocaleString()}</span>`;
                return `<div class="tbl-row" style="display:flex;justify-content:space-between;align-items:center;padding:4px 4px;font-size:9px;">
                    <span style="color:#64748B;text-transform:uppercase;letter-spacing:.04em;">${t.replace(/_/g,' ')}</span>
                    ${val}
                </div>`;
            }).join('');
        }

        // Services Table
        const tbody = document.getElementById('services-tbody');
        if (tbody) {
            const sorted = [...data.services].sort((a,b) => {
                if (a.status !== b.status) return a.status === 'ONLINE' ? -1 : 1;
                return b.ram - a.ram;
            });

            // Calculate Totals
            const totalSvcCpu = sorted.reduce((sum, s) => sum + (s.cpu || 0), 0);
            const totalSvcRam = sorted.reduce((sum, s) => sum + (s.ram || 0), 0);
            
            // Calculate percentages of total system
            const cpuShare = (totalSvcCpu / Math.max(data.total_cpu, 1) * 100).toFixed(1);
            const ramGb = totalSvcRam / 1024;
            const ramShare = (ramGb / Math.max(data.total_ram_capacity, 1) * 100).toFixed(1);

            const summaryRow = `
                <tr style="background:rgba(14,165,233,0.1); border-bottom:1px solid rgba(14,165,233,0.3); position:sticky; top:0; z-index:15;">
                    <td colspan="3" style="padding:10px 14px; font-size:9px; font-weight:800; color:#0EA5E9; text-transform:uppercase; letter-spacing:.12em;">
                        <div class="flex items-center gap-2">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
                            App Resource Summary
                        </div>
                    </td>
                    <td style="padding:10px 10px;">
                        <div style="display:flex; flex-direction:column; gap:1px;">
                            <span style="font-family:\'JetBrains Mono\'; font-size:11px; font-weight:800; color:#0EA5E9;">${totalSvcCpu.toFixed(1)}%</span>
                            <span style="font-size:7px; color:#475569; font-weight:600;">SYS SHARE: ${cpuShare}%</span>
                        </div>
                    </td>
                    <td style="padding:10px 10px;">
                        <div style="display:flex; flex-direction:column; gap:1px;">
                            <span style="font-family:\'JetBrains Mono\'; font-size:11px; font-weight:800; color:#6366F1;">${totalSvcRam.toLocaleString()} MB</span>
                            <span style="font-size:7px; color:#475569; font-weight:600;">SYS SHARE: ${ramShare}%</span>
                        </div>
                    </td>
                    <td colspan="2" style="text-align:right; padding-right:14px;">
                        <div class="flex flex-col items-end gap-1">
                            <span class="metric-chip chip-blue" style="font-size:8px; padding:2px 8px;">${sorted.length} MANAGED NODES</span>
                        </div>
                    </td>
                </tr>`;

            const rowsHtml = sorted.map(svc => {
                const cpuC = heatColor(svc.cpu, 100);
                const ramC = heatColor(svc.ram, 2048);
                const cpuW = Math.min(svc.cpu, 100);
                const ramW = Math.min((svc.ram/2048)*100, 100);
                const statusHtml = svc.status === 'ONLINE'
                    ? `<span class="metric-chip chip-green"><span class="status-dot online" style="width:4px;height:4px;"></span>LIVE</span>`
                    : `<span class="metric-chip chip-slate">OFFLINE</span>`;
                const errHtml = svc.errors > 0
                    ? `<span class="metric-chip chip-red">${svc.errors} ERR</span>`
                    : `<span style="font-size:9px;color:#374151;">—</span>`;
                return `<tr class="tbl-row ${svc.status==='OFFLINE'?'opacity-30':''}">
                    <td style="padding:5px 14px;font-size:10px;font-weight:600;color:#cbd5e1;text-transform:uppercase;letter-spacing:.04em;">${svc.name}</td>
                    <td style="padding:5px 10px;"><span style="font-family:\'JetBrains Mono\';font-size:9px;color:#475569;">${svc.port}</span></td>
                    <td style="padding:5px 10px;"><span style="font-family:\'JetBrains Mono\';font-size:9px;color:#374151;">${svc.pid}</span></td>
                    <td style="padding:5px 10px;min-width:80px;">
                        <div style="display:flex;align-items:center;gap:6px;">
                            <div class="bar-track" style="width:48px;"><div class="bar-fill" style="width:${cpuW}%;background:${cpuC};"></div></div>
                            <span style="font-family:\'JetBrains Mono\';font-size:9px;color:${cpuC};min-width:28px;">${svc.cpu}%</span>
                        </div>
                    </td>
                    <td style="padding:5px 10px;min-width:100px;">
                        <div style="display:flex;align-items:center;gap:6px;">
                            <div class="bar-track" style="width:48px;"><div class="bar-fill" style="width:${ramW}%;background:${ramC};"></div></div>
                            <span style="font-family:\'JetBrains Mono\';font-size:9px;color:${ramC};min-width:40px;">${svc.ram}MB</span>
                        </div>
                    </td>
                    <td style="padding:5px 10px;">${errHtml}</td>
                    <td style="padding:5px 14px;text-align:right;">${statusHtml}</td>
                </tr>`;
            }).join('');

            tbody.innerHTML = summaryRow + rowsHtml;
        }

        // Charts
        chartLabels.push(data.time);
        cpuData.push(data.total_cpu);
        ramData.push(data.ram_percent);
        if (chartLabels.length > MAX_DATA_POINTS) { chartLabels.shift(); cpuData.shift(); ramData.shift(); }
        cpuChart?.update('none');
        ramChart?.update('none');

    } catch (e) {
        console.error('Stats fetch error:', e);
        const lu = document.getElementById('last-update');
        if (lu) lu.innerText = 'CONNECTION LOST';
    }
}

setInterval(fetchStats, 3000);
fetchStats();
