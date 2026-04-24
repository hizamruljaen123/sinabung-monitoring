// ─── Database Manager Logic ───────────────────────────────────────────────
let currentDbTable = null;
let currentDbPage = 1;
let currentDbSchema = [];
let totalDbPages = 1;
const openSubRows = new Set();

async function loadDbTables() {
    try {
        const resp = await fetch('/api/db/tables');
        const tables = await resp.json();
        const list = document.getElementById('db-table-list');
        list.innerHTML = tables.map(t => `
            <button onclick="selectDbTable('${t}')" class="db-table-item px-4 py-2.5 rounded-xl text-left text-[11px] font-bold uppercase tracking-wider transition-all duration-200 hover:bg-slate-100 dark:hover:bg-white/5 text-slate-500 dark:text-slate-400">
                ${t.replace(/_/g, ' ')}
            </button>
        `).join('');
    } catch (err) {
        console.error("Failed to load tables:", err);
    }
}

async function selectDbTable(tableName) {
    currentDbTable = tableName;
    currentDbPage = 1;

    document.querySelectorAll('.db-table-item').forEach(el => {
        const isActive = el.innerText.trim().toLowerCase() === tableName.replace(/_/g, ' ').toLowerCase();
        el.classList.toggle('bg-primary/10', isActive);
        el.classList.toggle('text-primary', isActive);
    });

    document.getElementById('current-table-title').innerText = tableName.replace(/_/g, ' ');
    document.getElementById('btn-add-record').classList.remove('hidden');
    document.getElementById('record-count').classList.remove('hidden');

    await loadTableSchema();
    await loadTableData();
}

function getVisibleColumns() {
    let visibleCols;
    let hasMore = true;

    if (currentDbTable === 'article') {
        const priority = ['tanggal', 'judul', 'sumber'];
        visibleCols = currentDbSchema.filter(col => priority.includes(col.Field.toLowerCase()));
        visibleCols.sort((a, b) => priority.indexOf(a.Field.toLowerCase()) - priority.indexOf(b.Field.toLowerCase()));
        if (visibleCols.length === 0) visibleCols = currentDbSchema.slice(0, 3);
    } else {
        visibleCols = currentDbSchema.length > 6 ? currentDbSchema.slice(0, 6) : currentDbSchema;
        hasMore = currentDbSchema.length > 6;
    }
    return { visibleCols, hasMore };
}

async function loadTableSchema() {
    try {
        const resp = await fetch(`/api/db/schema/${currentDbTable}`);
        currentDbSchema = await resp.json();

        const { visibleCols, hasMore } = getVisibleColumns();

        const table = document.getElementById('db-data-table');
        table.style.width = '100%';
        table.style.minWidth = 'unset';

        const headerRow = document.getElementById('db-table-header');
        headerRow.innerHTML =
            (hasMore ? `<th class="w-8 px-3 py-4 text-center">
                <div class="w-4 h-4 rounded-full bg-primary/10 border border-primary/20 mx-auto"></div>
            </th>` : '') +
            visibleCols.map(col =>
                `<th class="px-5 py-4 text-[10px] uppercase tracking-wider text-slate-400 dark:text-slate-500 font-bold whitespace-nowrap">${col.Field}</th>`
            ).join('');
    } catch (err) {
        console.error("Schema Load Error:", err);
    }
}

async function loadTableData() {
    try {
        const resp = await fetch(`/api/db/data/${currentDbTable}?page=${currentDbPage}&per_page=15`);
        const data = await resp.json();

        const idCol = currentDbSchema.find(s => s.Key === 'PRI')?.Field || currentDbSchema[0].Field;
        const { visibleCols, hasMore } = getVisibleColumns();
        const totalCols = visibleCols.length + (hasMore ? 1 : 0);

        const tbody = document.getElementById('db-table-body');
        tbody.innerHTML = '';

        data.data.forEach((row, idx) => {
            const idVal = row[idCol];
            const subId = `sub-${idx}`;

            const tr = document.createElement('tr');
            tr.className = 'group hover:bg-slate-50 dark:hover:bg-white/[0.015] transition-colors cursor-pointer border-b border-slate-50 dark:border-white/[0.02]';

            let mainHtml = '';
            if (hasMore) {
                mainHtml += `<td class="w-8 px-3 py-3.5 text-center">
                    <div id="chevron-${idx}" class="inline-flex items-center justify-center w-5 h-5 rounded text-slate-400 group-hover:text-primary transition-transform duration-200">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"/></svg>
                    </div>
                </td>`;
            }

            visibleCols.forEach(col => {
                const val = row[col.Field];
                const display = val === null ? '<span class="opacity-25 italic text-[10px]">null</span>'
                    : (typeof val === 'string' && val.length > 25 ? val.substring(0, 22) + '...' : String(val));
                mainHtml += `<td class="px-5 py-3.5 font-mono text-[11px] text-slate-600 dark:text-slate-400 whitespace-nowrap overflow-hidden text-ellipsis max-w-[150px]">${display}</td>`;
            });

            tr.innerHTML = mainHtml;
            tr.onclick = () => toggleSubRow(idx, row, idCol, idVal);
            tbody.appendChild(tr);

            const subTr = document.createElement('tr');
            subTr.id = subId;
            subTr.className = 'hidden bg-slate-50/50 dark:bg-white/[0.01]';
            subTr.innerHTML = `<td colspan="${totalCols}" class="px-0 py-0">
                <div id="sub-content-${idx}" class="p-0 border-l-4 border-primary/20"></div>
            </td>`;
            tbody.appendChild(subTr);
        });

        document.getElementById('record-count').innerText = `${data.total} RECORDS`;
        document.getElementById('page-info').innerText = `Page ${data.page} of ${data.total_pages}`;
        totalDbPages = data.total_pages;

        document.getElementById('btn-prev-db').disabled = currentDbPage <= 1;
        document.getElementById('btn-next-db').disabled = currentDbPage >= totalDbPages;

    } catch (err) {
        console.error("Data Load Error:", err);
    }
}

function toggleSubRow(idx, row, idCol, idVal) {
    const subTr = document.getElementById(`sub-${idx}`);
    const chevron = document.getElementById(`chevron-${idx}`);
    const isOpen = openSubRows.has(idx);

    if (isOpen) {
        subTr.classList.add('hidden');
        if (chevron) chevron.style.transform = '';
        openSubRows.delete(idx);
    } else {
        renderSubRow(idx, row, idCol, idVal);
        subTr.classList.remove('hidden');
        if (chevron) chevron.style.transform = 'rotate(90deg)';
        openSubRows.add(idx);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function renderSubRow(idx, row, idCol, idVal) {
    const container = document.getElementById(`sub-content-${idx}`);

    const fieldsHtml = currentDbSchema.map(col => {
        const rawVal = row[col.Field] === null ? '' : String(row[col.Field]);
        const isPK = col.Key === 'PRI' && col.Extra === 'auto_increment';
        const isLong = rawVal.length > 100;
        const displayVal = isLong ? rawVal.substring(0, 100) + '...' : rawVal;

        const isImageUrl = (typeof rawVal === 'string') && (rawVal.match(/\.(jpeg|jpg|gif|png|webp)$/i) || rawVal.startsWith('http') && col.Field.toLowerCase().includes('image'));

        return `
            <div class="grid grid-cols-[180px_1fr] gap-6 items-start py-4 px-8 border-b border-slate-100 dark:border-white/5 hover:bg-slate-100/50 dark:hover:bg-white/[0.02] transition-colors">
                <div class="flex flex-col sticky top-0">
                    <span class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">${col.Field}</span>
                    <span class="text-[8px] font-mono text-slate-300 dark:text-slate-600 mt-1">${col.Type} ${isPK ? '(PRIMARY)' : ''}</span>
                    ${isImageUrl ? `
                        <div class="mt-3 w-16 h-16 rounded-lg bg-slate-100 dark:bg-white/5 overflow-hidden border border-slate-200 dark:border-white/10 flex items-center justify-center">
                            <img src="${rawVal}" class="w-full h-full object-cover" onerror="this.parentElement.remove()">
                        </div>
                    ` : ''}
                </div>
                <div class="relative w-full group/field">
                    <div 
                        id="field-${idx}-${col.Field}"
                        data-field="${col.Field}"
                        data-full-value="${escapeHtml(rawVal)}"
                        data-original="${escapeHtml(rawVal)}"
                        data-is-expanded="false"
                        contenteditable="${isPK ? 'false' : 'true'}"
                        ondblclick="expandToTextArea(this)"
                        class="sub-field-text text-xs font-mono text-slate-700 dark:text-slate-300 outline-none min-h-[1.5rem] leading-relaxed break-words whitespace-pre-wrap ${isPK ? 'opacity-50 cursor-not-allowed' : 'p-2 hover:bg-primary/5 rounded-lg focus:bg-primary/10 transition-all'}"
                        style="word-break: break-word; overflow-wrap: break-word; max-width: 100%; max-height: 200px; overflow-y: auto;"
                    >${escapeHtml(displayVal)}</div>
                    ${isLong ? '<span class="absolute right-2 bottom-1 text-[8px] font-bold text-primary/40 uppercase tracking-tighter pointer-events-none group-hover/field:opacity-100 opacity-0 transition-opacity">Double click to expand</span>' : ''}
                </div>
            </div>`;
    }).join('');

    container.innerHTML = `
        <div class="flex flex-col bg-white dark:bg-[#05070A] max-w-full overflow-hidden">
            <div class="px-8 py-5 bg-slate-50 dark:bg-white/[0.03] flex justify-between items-center border-b border-slate-200 dark:border-white/10 sticky top-0 z-20 backdrop-blur-md">
                <div class="flex items-center gap-4">
                    <span class="text-[11px] font-bold text-slate-600 dark:text-slate-400 uppercase tracking-tighter">DATA_NODE: <span class="text-primary font-mono select-all">${idVal}</span></span>
                    <div class="h-4 w-[1px] bg-slate-200 dark:bg-white/10"></div>
                    <span class="text-[9px] text-slate-400 font-medium">Safe HTML view. Multi-line scroll enabled.</span>
                </div>
                <div class="flex gap-2">
                    <button onclick="saveInlineEdit('${idCol}', '${idVal}', ${idx})" class="px-5 py-2 bg-primary text-white rounded-xl text-[10px] font-bold uppercase tracking-widest hover:shadow-lg hover:shadow-primary/20 transition-all active:scale-95">
                        Save Changes
                    </button>
                    <button onclick="deleteRecord('${idCol}', '${idVal}')" class="px-5 py-2 bg-accent/10 text-accent rounded-xl text-[10px] font-bold uppercase tracking-widest hover:bg-accent hover:text-white transition active:scale-95">
                        Delete Record
                    </button>
                    <button onclick="toggleSubRow(${idx})" class="px-5 py-2 bg-slate-200/50 dark:bg-white/10 text-slate-600 dark:text-slate-300 rounded-xl text-[10px] font-bold uppercase tracking-widest hover:bg-slate-300 transition">
                        Close
                    </button>
                </div>
            </div>
            <div class="flex flex-col max-h-[600px] overflow-y-auto custom-scrollbar w-full">
                ${fieldsHtml}
            </div>
        </div>`;
}

function expandToTextArea(el) {
    if (el.getAttribute('data-is-expanded') === 'true' || el.contentEditable === 'false') return;

    const fieldId = el.id;
    const fullValEncoded = el.getAttribute('data-full-value');
    const fieldName = el.getAttribute('data-field');
    const originalValEncoded = el.getAttribute('data-original');

    const decodeHtml = (html) => {
        const txt = document.createElement("textarea");
        txt.innerHTML = html;
        return txt.value;
    };

    const fullVal = decodeHtml(fullValEncoded);
    const wrapper = document.createElement('div');
    wrapper.className = 'flex flex-col gap-3 w-full animate-fade-in';

    const textarea = document.createElement('textarea');
    textarea.className = 'w-full bg-slate-50 dark:bg-white/[0.05] text-xs font-mono text-slate-800 dark:text-white p-4 rounded-xl border border-primary/30 outline-none focus:border-primary transition-all min-h-[150px] custom-scrollbar shadow-inner';
    textarea.value = fullVal;
    textarea.setAttribute('data-field', fieldName);
    textarea.setAttribute('data-original', originalValEncoded);
    textarea.setAttribute('data-full-value', fullValEncoded);
    textarea.style.height = 'auto';
    textarea.style.height = (textarea.scrollHeight + 20) + 'px';

    textarea.onkeydown = (e) => {
        if (e.key === 'Escape') {
            collapseTextArea(wrapper, fieldId, fieldName, fullValEncoded, originalValEncoded);
        }
    };

    const actionRow = document.createElement('div');
    actionRow.className = 'flex gap-2 justify-end';
    actionRow.innerHTML = `
        <button onclick="this.parentElement.parentElement.querySelector('textarea').dispatchEvent(new Event('save'))" class="px-3 py-1 bg-primary text-white text-[9px] font-bold uppercase rounded-lg hover:opacity-90 transition">Save Field</button>
        <button onclick="collapseTextArea(this.parentElement.parentElement, '${fieldId}', '${fieldName}', \`${fullValEncoded}\`, \`${originalValEncoded}\`)" class="px-3 py-1 bg-slate-100 dark:bg-white/10 text-slate-500 text-[9px] font-bold uppercase rounded-lg hover:bg-slate-200 transition">Cancel</button>
    `;

    wrapper.appendChild(textarea);
    wrapper.appendChild(actionRow);

    const parent = el.parentElement;
    parent.innerHTML = '';
    parent.appendChild(wrapper);
    textarea.focus();
}

function collapseTextArea(wrapper, fieldId, fieldName, fullValEncoded, originalValEncoded) {
    const parent = wrapper.parentElement;
    const decodeHtml = (html) => {
        const txt = document.createElement("textarea");
        txt.innerHTML = html;
        return txt.value;
    };
    const fullVal = decodeHtml(fullValEncoded);
    const isLong = fullVal.length > 100;
    const displayVal = isLong ? fullVal.substring(0, 100) + '...' : fullVal;

    const div = document.createElement('div');
    div.id = fieldId;
    div.className = `sub-field-text text-xs font-mono text-slate-700 dark:text-slate-300 outline-none min-h-[1.5rem] leading-relaxed break-words whitespace-pre-wrap p-2 hover:bg-primary/5 rounded-lg focus:bg-primary/10 transition-all`;
    div.setAttribute('data-field', fieldName);
    div.setAttribute('data-full-value', fullValEncoded);
    div.setAttribute('data-original', originalValEncoded);
    div.setAttribute('data-is-expanded', 'false');
    div.contentEditable = 'true';
    div.ondblclick = function () { expandToTextArea(this); };
    div.style.cssText = "word-break: break-word; overflow-wrap: break-word; max-width: 100%; max-height: 200px; overflow-y: auto;";
    div.innerHTML = escapeHtml(displayVal);

    parent.innerHTML = '';
    parent.appendChild(div);

    if (isLong) {
        const hint = document.createElement('span');
        hint.className = 'absolute right-2 bottom-1 text-[8px] font-bold text-primary/40 uppercase tracking-tighter pointer-events-none opacity-0 group-hover/field:opacity-100 transition-opacity';
        hint.innerText = 'Double click to expand';
        parent.appendChild(hint);
    }
}

async function saveInlineEdit(idCol, idVal, idx) {
    const container = document.getElementById(`sub-content-${idx}`);
    const fields = container.querySelectorAll('[data-field]');
    const payload = {};

    const decodeHtml = (html) => {
        const txt = document.createElement("textarea");
        txt.innerHTML = html;
        return txt.value;
    };

    fields.forEach(el => {
        const field = el.getAttribute('data-field');
        const originalEncoded = el.getAttribute('data-original');
        const current = el.tagName === 'TEXTAREA' ? el.value : el.innerText.trim();
        const original = decodeHtml(originalEncoded);

        if (el.tagName === 'TEXTAREA' || el.getAttribute('data-is-expanded') === 'true') {
            if (current !== original) {
                payload[field] = current === '' ? null : current;
            }
        } else {
            const fullValueEncoded = el.getAttribute('data-full-value');
            const fullValue = decodeHtml(fullValueEncoded);
            if (current !== fullValue.substring(0, 100) + '...' && current !== fullValue) {
                payload[field] = current;
            }
        }
    });

    if (Object.keys(payload).length === 0) {
        fields.forEach(el => el.style.borderColor = '');
        return;
    }

    try {
        const resp = await fetch(`/api/db/data/${currentDbTable}/${idCol}/${idVal}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const result = await resp.json();
        if (result.status === 'success') {
            fields.forEach(el => {
                const field = el.getAttribute('data-field');
                if (payload[field] !== undefined) {
                    el.style.borderColor = '#22c55e';
                    el.setAttribute('data-original', el.innerText.trim());
                    setTimeout(() => el.style.borderColor = '', 1500);
                }
            });
            loadTableData();
        } else {
            alert('Save Error: ' + result.message);
        }
    } catch (err) {
        alert('Fatal: ' + err);
    }
}

function changeDbPage(dir) {
    currentDbPage += dir;
    loadTableData();
}

// --- Modal Logic ---
function openAddModal() {
    document.getElementById('modal-title').innerText = `ADD TO ${currentDbTable.toUpperCase()}`;
    renderForm({});
    document.getElementById('btn-save-record').onclick = () => saveRecord('POST');
    document.getElementById('record-modal').classList.remove('hidden');
}

function openEditModal(row) {
    document.getElementById('modal-title').innerText = `EDIT RECORD // ${currentDbTable.toUpperCase()}`;
    renderForm(row);
    const idCol = currentDbSchema.find(s => s.Key === 'PRI')?.Field || currentDbSchema[0].Field;
    const idVal = row[idCol];
    document.getElementById('btn-save-record').onclick = () => saveRecord('PUT', idCol, idVal);
    document.getElementById('record-modal').classList.remove('hidden');
}

function renderForm(data) {
    const container = document.getElementById('form-fields');
    container.innerHTML = currentDbSchema.map(col => {
        const val = data[col.Field] || '';
        const isReadonly = col.Key === 'PRI' && col.Extra === 'auto_increment';
        return `
            <div class="flex flex-col gap-2">
                <label class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">${col.Field} <span class="text-[9px] lowercase italic opacity-50">(${col.Type})</span></label>
                ${col.Type.includes('text') || col.Type.includes('longtext')
                    ? `<textarea name="${col.Field}" class="bg-slate-50 dark:bg-white/[0.02] border border-slate-200 dark:border-white/10 rounded-xl px-4 py-3 text-sm text-slate-700 dark:text-slate-200 focus:border-primary transition outline-none h-32 custom-scrollbar">${val}</textarea>`
                    : `<input type="text" name="${col.Field}" value="${val}" ${isReadonly ? 'readonly opacity-50' : ''} class="bg-slate-50 dark:bg-white/[0.02] border border-slate-200 dark:border-white/10 rounded-xl px-4 py-3 text-sm text-slate-700 dark:text-slate-200 focus:border-primary transition outline-none">`
                }
            </div>
        `;
    }).join('');
}

async function saveRecord(method, idCol, idVal) {
    const formData = new FormData(document.getElementById('record-form'));
    const payload = {};
    formData.forEach((val, key) => { if (val !== "") payload[key] = val; });

    const url = method === 'POST'
        ? `/api/db/data/${currentDbTable}`
        : `/api/db/data/${currentDbTable}/${idCol}/${idVal}`;

    try {
        const resp = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const result = await resp.json();
        if (result.status === 'success') {
            closeModal();
            loadTableData();
        } else {
            alert("Error: " + result.message);
        }
    } catch (err) {
        alert("Fatal Error: " + err);
    }
}

async function deleteRecord(idCol, idVal) {
    if (!confirm(`Are you sure you want to delete record ${idVal}?`)) return;
    try {
        const resp = await fetch(`/api/db/data/${currentDbTable}/${idCol}/${idVal}`, { method: 'DELETE' });
        const result = await resp.json();
        if (result.status === 'success') {
            loadTableData();
        } else {
            alert("Delete Error: " + result.message);
        }
    } catch (err) {
        alert("Fatal Error: " + err);
    }
}

function closeModal() {
    document.getElementById('record-modal').classList.add('hidden');
}
