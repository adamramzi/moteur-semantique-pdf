// ── État global ─────────────────────────────────────────────
const API = '/api';
let token = localStorage.getItem('token') || '';
let userEmail = localStorage.getItem('email') || '';
let regEmail = '';
let selectedFiles = [];
let searchHistory = [];

// ── Utilitaires ─────────────────────────────────────────────
function getFileIcon(filename) {
    if (!filename) return '📄';
    const ext = filename.split('.').pop().toLowerCase();
    if (ext === 'pdf') return '📄';
    if (ext === 'docx' || ext === 'doc') return '📝';
    if (ext === 'pptx' || ext === 'ppt') return '📊';
    if (ext === 'xlsx' || ext === 'xls') return '📈';
    if (ext === 'txt' || ext === 'rtf') return '📃';
    return '📄';
}

function $(id) { return document.getElementById(id); }
function show(id) { document.querySelectorAll('.screen').forEach(s => s.classList.remove('active')); $(id).classList.add('active'); }

function toast(msg, type = 'info') {
    const t = document.createElement('div');
    t.className = `toast toast-${type}`;
    t.textContent = msg;
    $('toast-container').appendChild(t);
    setTimeout(() => t.remove(), 4000);
}

function loading(show, text) {
    const el = $('loading-overlay');
    if (show) { $('loading-text').textContent = text || 'Chargement…'; el.classList.add('active'); }
    else el.classList.remove('active');
}

async function api(path, opts = {}) {
    const headers = opts.headers || {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    if (!(opts.body instanceof FormData) && opts.body) headers['Content-Type'] = 'application/json';

    const res = await fetch(`${API}${path}`, { ...opts, headers });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Erreur serveur');
    return data;
}

// ── Navigation ──────────────────────────────────────────────
function goAuth() { token = ''; userEmail = ''; localStorage.removeItem('token'); localStorage.removeItem('email'); show('auth-screen'); }
function goDashboard() { show('dashboard-screen'); $('sidebar-email').textContent = userEmail; loadDashboard(); }

// ── Auth Tabs ───────────────────────────────────────────────
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        document.querySelectorAll('#auth-screen .auth-form').forEach(f => f.classList.remove('active'));
        let targetFormId = 'login-form';
        if (btn.dataset.tab === 'register') targetFormId = 'register-form';
        if (btn.dataset.tab === 'forgot') targetFormId = 'forgot-form';
        $(targetFormId).classList.add('active');
    });
});

// ── Login ───────────────────────────────────────────────────
$('btn-login').addEventListener('click', async () => {
    const email = $('login-email').value.trim();
    const pwd = $('login-password').value;
    if (!email || !pwd) return toast('Remplissez tous les champs.', 'error');
    try {
        loading(true, 'Connexion…');
        const data = await api('/auth/login', { method: 'POST', body: JSON.stringify({ email, password: pwd }) });
        token = data.token; userEmail = data.email;
        localStorage.setItem('token', token); localStorage.setItem('email', userEmail);
        toast('Connexion réussie !', 'success');
        goDashboard();
    } catch (e) { toast(e.message, 'error'); }
    finally { loading(false); }
});

// ── Register ────────────────────────────────────────────────
$('btn-register').addEventListener('click', async () => {
    const email = $('reg-email').value.trim();
    const pwd = $('reg-password').value;
    const pwd2 = $('reg-password2').value;
    if (!email || !pwd || !pwd2) return toast('Remplissez tous les champs.', 'error');
    if (pwd !== pwd2) return toast('Les mots de passe ne correspondent pas.', 'error');
    if (pwd.length < 6) return toast('Minimum 6 caractères pour le mot de passe.', 'error');
    try {
        loading(true, 'Création du compte…');
        const data = await api('/auth/register', { method: 'POST', body: JSON.stringify({ email, password: pwd }) });
        regEmail = email;
        $('verify-email-text').textContent = `Code envoyé à ${email}`;
        toast(data.message, 'success');
        show('verify-screen');
    } catch (e) { toast(e.message, 'error'); }
    finally { loading(false); }
});

// ── Forgot Password ─────────────────────────────────────────
$('btn-forgot-request').addEventListener('click', async () => {
    const email = $('forgot-email').value.trim();
    if (!email) return toast('Saisissez votre adresse e-mail.', 'error');
    try {
        loading(true, 'Vérification du compte…');
        const data = await api('/auth/forgot-password', { method: 'POST', body: JSON.stringify({ email }) });
        toast(data.message, 'success');
        regEmail = email; // Reuse regEmail to store the email for reset
        // Switch to reset form
        $('forgot-form').classList.remove('active');
        $('reset-form').classList.add('active');
    } catch (e) { toast(e.message, 'error'); }
    finally { loading(false); }
});

$('btn-reset-password').addEventListener('click', async () => {
    const code = $('reset-code').value.trim();
    const newPwd = $('reset-password').value;
    const confirmPwd = $('reset-password-confirm').value;

    if (!code || !newPwd || !confirmPwd) return toast('Remplissez tous les champs.', 'error');
    if (newPwd !== confirmPwd) return toast('❌ Les mots de passe ne correspondent pas', 'error');
    if (newPwd.length < 6) return toast('Minimum 6 caractères pour le mot de passe.', 'error');

    try {
        loading(true, 'Réinitialisation…');
        const data = await api('/auth/reset-password', {
            method: 'POST',
            body: JSON.stringify({ email: regEmail, code, new_password: newPwd })
        });
        toast(data.message, 'success');
        // Reset forms and go to login tab
        $('reset-code').value = '';
        $('reset-password').value = '';
        $('reset-password-confirm').value = '';
        $('reset-form').classList.remove('active');
        $('tab-login').click();
    } catch (e) { toast(e.message, 'error'); }
    finally { loading(false); }
});

$('btn-cancel-reset').addEventListener('click', () => {
    $('reset-form').classList.remove('active');
    $('forgot-form').classList.add('active');
});

// ── Verify ──────────────────────────────────────────────────
$('btn-verify').addEventListener('click', async () => {
    const code = $('verify-code').value.trim();
    if (!code) return toast('Entrez le code reçu.', 'error');
    try {
        loading(true, 'Vérification…');
        await api('/auth/verify', { method: 'POST', body: JSON.stringify({ email: regEmail, code }) });
        toast('Compte vérifié ! Connectez-vous.', 'success');
        show('auth-screen');
        $('tab-login').click();
    } catch (e) { toast(e.message, 'error'); }
    finally { loading(false); }
});

$('btn-resend').addEventListener('click', async () => {
    try {
        const data = await api('/auth/resend', { method: 'POST', body: JSON.stringify({ email: regEmail }) });
        toast(data.message, 'success');
    } catch (e) { toast(e.message, 'error'); }
});

$('btn-cancel-verify').addEventListener('click', () => { show('auth-screen'); });

// ── Logout ──────────────────────────────────────────────────
$('btn-logout').addEventListener('click', () => { goAuth(); toast('Déconnecté.', 'info'); });

// ── Upload Zone ─────────────────────────────────────────────
const uploadZone = $('upload-zone');
const fileInput = $('file-input');

uploadZone.addEventListener('click', () => fileInput.click());
uploadZone.addEventListener('dragover', e => { e.preventDefault(); uploadZone.classList.add('dragover'); });
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('dragover'));
uploadZone.addEventListener('drop', e => { e.preventDefault(); uploadZone.classList.remove('dragover'); addFiles(e.dataTransfer.files); });
fileInput.addEventListener('change', () => addFiles(fileInput.files));

function addFiles(files) {
    const validExts = ['.pdf', '.docx', '.doc', '.pptx', '.ppt', '.xlsx', '.xls', '.txt', '.rtf'];
    for (const f of files) {
        const ext = '.' + f.name.split('.').pop().toLowerCase();
        if (validExts.includes(ext) && !selectedFiles.find(sf => sf.name === f.name)) selectedFiles.push(f);
    }
    renderFileList();
}

function renderFileList() {
    const list = $('file-list');
    const btnC = $('upload-btn-container');
    if (!selectedFiles.length) { list.innerHTML = ''; btnC.style.display = 'none'; return; }
    btnC.style.display = 'block';
    list.innerHTML = selectedFiles.map((f, i) => `
        <div class="file-item">
            <span class="file-item-name">${getFileIcon(f.name)} ${f.name}</span>
            <span class="file-item-size">${(f.size / 1024).toFixed(0)} Ko</span>
            <button class="file-remove" onclick="removeFile(${i})">✕</button>
        </div>
    `).join('');
}
window.removeFile = (i) => { selectedFiles.splice(i, 1); renderFileList(); };

// ── Upload Action ───────────────────────────────────────────
$('btn-upload').addEventListener('click', async () => {
    if (!selectedFiles.length) return toast('Sélectionnez au moins un document.', 'error');
    const fd = new FormData();
    selectedFiles.forEach(f => fd.append('files', f));

    try {
        loading(true, '⏳ Analyse des documents…');
        const data = await api('/upload', { method: 'POST', body: fd });
        toast(data.message, 'success');
        selectedFiles = [];
        renderFileList();
        loadDashboard();
    } catch (e) { toast(e.message, 'error'); }
    finally { loading(false); }
});

// ── Reset ───────────────────────────────────────────────────
$('btn-reset').addEventListener('click', async () => {
    if (!confirm('Supprimer tous vos documents ?')) return;
    try {
        loading(true, 'Suppression…');
        await api('/reset', { method: 'POST', body: '{}' });
        toast('Tous les documents supprimés.', 'success');
        loadDashboard();
    } catch (e) { toast(e.message, 'error'); }
    finally { loading(false); }
});

// ── Dashboard Loading ───────────────────────────────────────
async function loadDashboard() {
    try {
        const [stats, docsRes] = await Promise.all([api('/stats'), api('/documents')]);
        $('stat-pdfs').textContent = stats.nb_pdfs;
        $('stat-passages').textContent = stats.nb_passages;
        $('stat-searches').textContent = stats.nb_recherches;

        // Sidebar status
        $('sidebar-status').innerHTML = stats.nb_passages > 0
            ? `<div class="status-ok">✅ Prêt — <b>${stats.nb_passages}</b> passages</div>`
            : `<div class="status-warn">⚠️ Aucun document analysé</div>`;

        renderHistory(docsRes.documents);
        renderSearchSection(docsRes.documents);
    } catch (e) {
        if (e.message.includes('Token') || e.message.includes('401')) goAuth();
        else toast(e.message, 'error');
    }
}

// ── History Section ─────────────────────────────────────────
function renderHistory(docs) {
    const el = $('history-content');
    if (!docs.length) {
        el.innerHTML = `<div class="empty-state">📭 Aucun document analysé. Uploadez votre premier document ci-dessus !</div>`;
        return;
    }

    let html = `<p style="color:var(--muted);margin-bottom:1rem;">📂 <b>${docs.length}</b> document(s) analysé(s)</p>`;
    html += `<div class="search-select"><select id="history-pdf-select">`;
    docs.forEach((d, i) => { html += `<option value="${d.nom_fichier}">${d.nom_fichier}</option>`; });
    html += `</select></div>`;
    html += `<div class="doc-grid">`;
    docs.forEach(d => {
        html += `
        <div class="doc-card">
            <div class="doc-info">
                <h4>${getFileIcon(d.nom_fichier)} ${d.nom_fichier}</h4>
                <div class="doc-meta">🗓️ ${d.date_upload} &nbsp;|&nbsp; 📝 <b>${d.nombre_chunks}</b> passages</div>
            </div>
            <button class="btn btn-danger btn-sm" onclick="deleteDoc('${d.nom_fichier.replace(/'/g, "\\'")}')">🗑️</button>
        </div>`;
    });
    html += `</div><div id="search-history-results" style="margin-top:1.5rem;"></div>`;
    el.innerHTML = html;

    const select = $('history-pdf-select');
    select.addEventListener('change', () => loadSearchHistory(select.value));
    if (docs.length) loadSearchHistory(docs[0].nom_fichier);
}

async function loadSearchHistory(filename) {
    try {
        const data = await api(`/search/history/${encodeURIComponent(filename)}`);
        const el = $('search-history-results');
        if (!data.recherches.length) {
            el.innerHTML = `<div class="code-hint-box">💬 Aucune recherche effectuée sur ce document.</div>`;
            return;
        }
        el.innerHTML = `<h3 style="font-size:1rem;margin-bottom:.8rem;">🔎 Recherches sur : <em>${filename}</em></h3>` +
            data.recherches.map(r => {
                const pct = ((r.score || 0) * 100).toFixed(1);
                const passage = (r.passage_trouve || '').substring(0, 300) + ((r.passage_trouve || '').length > 300 ? '…' : '');
                return `<div class="search-history-card">
                    <h4>❓ ${r.question}</h4>
                    <div class="search-history-meta">🕐 ${r.date_recherche} &nbsp;|&nbsp; ✅ <span style="color:var(--green);font-weight:600;">${pct}%</span></div>
                    <div class="search-history-passage">📄 ${passage}</div>
                </div>`;
            }).join('');
    } catch (e) { toast(e.message, 'error'); }
}

window.deleteDoc = async (name) => {
    if (!confirm(`Supprimer "${name}" ?`)) return;
    try {
        loading(true, 'Suppression…');
        await api(`/documents/${encodeURIComponent(name)}`, { method: 'DELETE' });
        toast(`"${name}" supprimé.`, 'success');
        loadDashboard();
    } catch (e) { toast(e.message, 'error'); }
    finally { loading(false); }
};

// ── Search Section ──────────────────────────────────────────
function renderSearchSection(docs) {
    const el = $('search-content');
    if (!docs.length) {
        el.innerHTML = `<div class="status-warn">⚠️ Ajoutez et analysez au moins un document avant de chercher.</div>`;
        return;
    }

    let html = `<div class="search-select"><label style="font-size:.85rem;color:var(--muted);display:block;margin-bottom:.4rem;">📄 Rechercher dans :</label>
        <select id="search-pdf-select">`;
    docs.forEach(d => { html += `<option value="${d.nom_fichier}">${d.nom_fichier}</option>`; });
    html += `</select></div>
        <div class="search-bar">
            <input type="text" id="search-input" placeholder="Ex : Quels sont les principaux résultats ?">
            <button class="btn btn-primary" id="btn-search">🔍 Rechercher</button>
        </div>
        <div id="search-results"></div>`;
    el.innerHTML = html;

    $('btn-search').addEventListener('click', doSearch);
    $('search-input').addEventListener('keydown', e => { if (e.key === 'Enter') doSearch(); });
}

async function doSearch() {
    const query = $('search-input').value.trim();
    const pdfSelect = $('search-pdf-select');
    if (!query) return toast('Saisissez une question.', 'error');

    try {
        loading(true, '🔍 Recherche en cours…');
        const data = await api('/search', {
            method: 'POST',
            body: JSON.stringify({ query, pdf_name: pdfSelect ? pdfSelect.value : null })
        });

        // Update sidebar history
        searchHistory.unshift({ question: query, heure: new Date().toLocaleTimeString() });
        searchHistory = searchHistory.slice(0, 5);
        renderSidebarHistory();

        // Render results
        renderResults(data.resultats, query);
        loadDashboard(); // refresh stats
    } catch (e) { toast(e.message, 'error'); }
    finally { loading(false); }
}

function renderSidebarHistory() {
    if (!searchHistory.length) { $('sidebar-history-section').style.display = 'none'; return; }
    $('sidebar-history-section').style.display = 'block';
    $('sidebar-history').innerHTML = searchHistory.map(h =>
        `<div class="history-item">🔍 ${h.question}<span class="history-time">${h.heure}</span></div>`
    ).join('');
}

function renderResults(results, question) {
    const el = $('search-results');
    if (!results || !results.length) { el.innerHTML = `<div class="empty-state">Aucun résultat trouvé.</div>`; return; }

    let html = `<h3 style="margin:1rem 0;">📋 Passages trouvés pour : <em>"${question}"</em></h3>`;
    results.forEach(r => {
        const pct = (r.score * 100).toFixed(1);
        const txt = r.texte.length > 600 ? r.texte.substring(0, 600) + '…' : r.texte;
        let meta = '';
        if (r.fichier) meta += `${getFileIcon(r.fichier)} Fichier : <b>${r.fichier}</b>`;
        if (r.page) meta += `${meta ? ' &nbsp;|&nbsp; ' : ''}📖 Page : <b>${r.page}</b>`;

        html += `<div class="result-card">
            <div class="result-header">
                <span class="chunk-badge">📄 Passage #${r.chunk_index + 1}</span>
                <span class="score-badge">${pct}%</span>
            </div>
            <div class="result-text">${txt}</div>
            ${meta ? `<div class="result-meta">${meta}</div>` : ''}
        </div>`;
    });

    // Export button
    html += `<button class="btn btn-secondary" onclick="exportResults()" style="margin-top:.5rem;">💾 Télécharger les résultats</button>`;
    el.innerHTML = html;

    // Store for export
    window._lastResults = { results, question };
}

window.exportResults = () => {
    const { results, question } = window._lastResults || {};
    if (!results) return;
    let txt = `RÉSULTATS DE RECHERCHE\nQuestion : ${question}\nDate : ${new Date().toLocaleString()}\n${'='.repeat(60)}\n\n`;
    results.forEach(r => {
        txt += `Passage #${r.chunk_index + 1} — ${(r.score * 100).toFixed(1)}%`;
        if (r.fichier) txt += ` | Fichier : ${r.fichier}`;
        if (r.page) txt += ` | Page : ${r.page}`;
        txt += `\n${'-'.repeat(40)}\n${r.texte}\n\n`;
    });
    const blob = new Blob([txt], { type: 'text/plain' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `resultats_${Date.now()}.txt`;
    a.click();
};

// ── Init ────────────────────────────────────────────────────
if (token && userEmail) {
    api('/auth/me').then(() => goDashboard()).catch(() => goAuth());
} else {
    goAuth();
}
