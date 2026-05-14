/**
 * Sinabung Local Hub — Service Manager JS
 */

async function refreshLocalServices() {
    const grid = document.getElementById('local-services-grid');
    try {
        const response = await fetch('/api/local/services');
        const services = await response.json();
        
        renderServiceGrid(services);
    } catch (error) {
        console.error('Failed to fetch local services:', error);
    }
}

function renderServiceGrid(services) {
    const grid = document.getElementById('local-services-grid');
    grid.innerHTML = '';

    services.forEach(svc => {
        const isOnline = svc.status === 'ONLINE';
        const card = document.createElement('div');
        card.className = `service-card ${isOnline ? 'online' : 'offline'}`;
        
        card.innerHTML = `
            <div class="flex justify-between items-start mb-3">
                <div>
                    <h3 class="text-sm font-bold text-slate-200">${svc.name}</h3>
                    <p class="text-[9px] font-mono text-slate-500 uppercase tracking-wider">${svc.id}</p>
                </div>
                <label class="switch">
                    <input type="checkbox" ${isOnline ? 'checked' : ''} onchange="toggleService('${svc.id}', this.checked)">
                    <span class="slider"></span>
                </label>
            </div>
            
            <div class="space-y-1.5">
                <div class="flex justify-between items-center text-[10px]">
                    <span class="text-slate-500 font-medium">STATUS</span>
                    <span class="${isOnline ? 'text-success' : 'text-slate-500'} font-bold">${svc.status}</span>
                </div>
                <div class="flex justify-between items-center text-[10px]">
                    <span class="text-slate-500 font-medium">PORT / PID</span>
                    <span class="text-slate-400 font-mono">${svc.port} / ${svc.pid}</span>
                </div>
                
                ${isOnline ? `
                <div class="grid grid-cols-2 gap-2 mt-2 pt-2 border-t border-white/5">
                    <div class="flex flex-col">
                        <span class="text-[8px] text-slate-500 uppercase font-bold">CPU</span>
                        <span class="text-[11px] font-mono text-primary">${svc.cpu}%</span>
                    </div>
                    <div class="flex flex-col">
                        <span class="text-[8px] text-slate-500 uppercase font-bold">RAM</span>
                        <span class="text-[11px] font-mono text-secondary">${svc.ram}MB</span>
                    </div>
                </div>
                ` : `
                <div class="h-[34px] flex items-center justify-center opacity-20 italic text-[9px]">
                    Service is currently inactive
                </div>
                `}
            </div>
        `;
        grid.appendChild(card);
    });
}

async function toggleService(serviceId, shouldStart) {
    const action = shouldStart ? 'start' : 'stop';
    try {
        const response = await fetch(`/api/local/control/${action}/${serviceId}`, {
            method: 'POST'
        });
        const result = await response.json();
        
        if (result.status === 'success') {
            // Wait a bit for process to start/stop then refresh
            setTimeout(refreshLocalServices, 1500);
        } else {
            alert(`Error: ${result.message}`);
            refreshLocalServices(); // Revert toggle
        }
    } catch (error) {
        console.error(`Failed to ${action} service ${serviceId}:`, error);
        refreshLocalServices();
    }
}

// Initial load and periodic refresh
if (window.location.pathname === '/' || window.location.pathname === '/index') {
    refreshLocalServices();
    setInterval(() => {
        const localPage = document.getElementById('view-local');
        if (localPage && localPage.classList.contains('active')) {
            refreshLocalServices();
        }
    }, 5000);
}
