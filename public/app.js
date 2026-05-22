// ── État global ─────────────────────────────────────────────
const API = '/api';
let token = localStorage.getItem('token') || '';
let userEmail = localStorage.getItem('email') || '';
let regEmail = '';
let selectedFiles = [];
let searchHistory = [];
let pdfActif = '';
let conversations = JSON.parse(localStorage.getItem('studysearch_convos') || '[]');
let currentConvId = null;
let allUserDocuments = [];

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
    const text = await res.text();
    let data;
    try {
        data = JSON.parse(text);
    } catch (e) {
        console.error("Réponse non-JSON:", text);
        throw new Error("Erreur serveur: " + text);
    }
    if (!res.ok) throw new Error(data.detail || data.error || 'Erreur serveur');
    return data;
}

// ── Navigation ──────────────────────────────────────────────
function goHome() { show('home-screen'); }
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
        console.log("email recherché:", email);
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
$('btn-logout').addEventListener('click', () => {
    token = ''; userEmail = '';
    localStorage.removeItem('token'); localStorage.removeItem('email');
    goHome();
    toast('Déconnecté.', 'info');
});

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
        if (validExts.includes(ext) && !selectedFiles.find(sf => sf.name === f.name)) {
            selectedFiles.push(f);
        }
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
    if (!currentConvId) nouvelleConversation();
    const fd = new FormData();
    selectedFiles.forEach(f => fd.append('files', f));

    try {
        loading(true, '⏳ Analyse des documents…');
        const data = await api('/upload', { method: 'POST', body: fd });
        toast(data.message, 'success');
        
        let conv = conversations.find(c => c.id === currentConvId);
        if (!conv) {
            conv = {
                id: currentConvId,
                email: userEmail,
                nom: 'Conversation ' + (conversations.filter(c => c.email === userEmail).length + 1),
                messages: [],
                documents: [],
                pdf_name: ""
            };
            conversations.push(conv);
        }
        if (conv) {
            conv.documents = conv.documents || [];
            // Ajoute uniquement si le document n'y est pas déjà
            selectedFiles.forEach(f => {
                if (!conv.documents.includes(f.name)) {
                    conv.documents.push(f.name);
                }
            });
            if (!pdfActif || pdfActif === "") pdfActif = selectedFiles[0].name;
            saveCurrentConversation();
        }
        
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

function updateDocumentDropdown() {
    const select = $('chat-pdf-select');
    if (!select) return;

    const conv = conversations.find(c => c.id === currentConvId);
    const convDocsNames = conv ? (conv.documents || []) : [];
    const filteredDocs = allUserDocuments.filter(d => convDocsNames.includes(d.nom_fichier));

    if (filteredDocs.length === 0) {
        select.innerHTML = '<option value="">-- Aucun document dans cette conversation --</option>';
        select.disabled = true;
    } else {
        select.innerHTML = '<option value="">-- Choisir un document --</option>' + 
            filteredDocs.map(d => `<option value="${d.nom_fichier}">${d.nom_fichier}</option>`).join('');
        select.disabled = false;
    }

    if (!convDocsNames.includes(pdfActif)) {
        pdfActif = "";
    }
    select.value = pdfActif;
}

// ── Dashboard Loading ───────────────────────────────────────
async function loadDashboard() {
    try {
        const [stats, docsRes] = await Promise.all([api('/stats'), api('/documents')]);

        // Sidebar status
        const sidebarStatus = $('sidebar-status');
        if (sidebarStatus) {
            sidebarStatus.innerHTML = stats.nb_passages > 0
                ? `<div class="status-ok">✅ Prêt — <b>${stats.nb_passages}</b> passages</div>`
                : `<div class="status-warn">⚠️ Aucun document analysé</div>`;
        }

        allUserDocuments = docsRes.documents;
        updateDocumentDropdown();

        // Afficher uniquement les conversations dans la barre latérale
        renderConversations();
    } catch (e) {
        if (e.message.includes('Token') || e.message.includes('401')) goAuth();
        else toast(e.message, 'error');
    }
}

// Configurer le changement de document ciblé
document.addEventListener('DOMContentLoaded', () => {
    const chatPdfSelect = $('chat-pdf-select');
    if (chatPdfSelect) {
        chatPdfSelect.addEventListener('change', () => {
            pdfActif = chatPdfSelect.value;
            saveCurrentConversation();
        });
    }
});

// ── History Section (Gestion des Conversations) ──────────────
function renderConversations() {
    const el = $('history-content');
    if (!el) return;
    
    // Filtrer les conversations de l'utilisateur actuel
    const userConvos = conversations.filter(c => c.email === userEmail);
    
    if (!userConvos.length) {
        el.innerHTML = `<div class="empty-state">💬 Aucune conversation. Cliquez sur "Nouvelle conversation" pour commencer !</div>`;
        return;
    }

    let html = `<p style="color:var(--muted);margin-bottom:1rem;">💬 <b>${userConvos.length}</b> conversation(s)</p>`;
    html += `<div class="doc-grid">`;
    userConvos.forEach(c => {
        const isActive = c.id === currentConvId ? ' border-color: rgba(167,139,250,0.8); background: rgba(167,139,250,0.08);' : '';
        html += `
        <div class="doc-card" style="cursor:pointer;${isActive}" onclick="ouvrirConversation('${c.id}')">
            <div class="doc-info">
                <h4>💬 ${c.nom}</h4>
            </div>
            <button class="btn btn-danger btn-sm" style="padding: 4px 8px;" onclick="event.stopPropagation(); supprimerConversation('${c.id}')">🗑️</button>
        </div>`;
    });
    html += `</div>`;
    el.innerHTML = html;
}

function ouvrirConversation(id) {
    const convo = conversations.find(c => c.id === id);
    if (!convo) return;
    currentConvId = convo.id;
    messagesChat = [...convo.messages];
    
    pdfActif = convo.pdf_name || "";
    updateDocumentDropdown();
    
    renderConversations();
    renderMessages();
}

function saveCurrentConversation() {
    if (!currentConvId) return;
    let conv = conversations.find(c => c.id === currentConvId);
    if (messagesChat.length === 0 && (!conv || !conv.documents || conv.documents.length === 0)) return;

    if (!conv) {
        conv = {
            id: currentConvId,
            email: userEmail,
            nom: 'Conversation ' + (conversations.filter(c => c.email === userEmail).length + 1),
            messages: messagesChat,
            documents: [],
            pdf_name: pdfActif
        };
        conversations.push(conv);
    } else {
        conv.messages = messagesChat;
        conv.pdf_name = pdfActif;
    }
    localStorage.setItem('studysearch_convos', JSON.stringify(conversations));
    renderConversations();
}

window.supprimerConversation = async function(id) {
    const convToDelete = conversations.find(c => c.id === id);
    if (!convToDelete) return;

    if (!confirm("Supprimer cette conversation et effacer définitivement ses documents du serveur ?")) return;

    try {
        loading(true, 'Suppression de la conversation et de ses documents…');
        if (convToDelete && convToDelete.documents) {
            for (let docName of convToDelete.documents) {
                // Vérifier si une AUTRE conversation utilise ce même document
                let isUsedElsewhere = conversations.some(c => c.id !== id && c.documents && c.documents.includes(docName));

                if (!isUsedElsewhere) {
                    // Suppression physique du serveur uniquement s'il est orphelin
                    try {
                        await api('/documents/' + encodeURIComponent(docName), { method: 'DELETE' });
                    } catch (e) { console.error("Erreur suppression:", e); }
                }
            }
        }
        
        conversations = conversations.filter(c => c.id !== id);
        localStorage.setItem('studysearch_convos', JSON.stringify(conversations));

        if (currentConvId === id) {
            currentConvId = null;
            pdfActif = "";
            messagesChat = [];
            nouvelleConversation();
        }
        
        await loadDashboard();
    } catch (e) {
        toast("Erreur lors de la suppression : " + e.message, 'error');
    } finally {
        loading(false);
    }
};

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

// ── Chat Section ────────────────────────────────────────────
let chatMode = 'resume'
let messagesChat = []

function setMode(mode) {
    chatMode = mode
    document.getElementById('btn-mode-resume').classList.toggle('active', mode === 'resume')
    document.getElementById('btn-mode-recherche').classList.toggle('active', mode === 'recherche')
}

function nouvelleConversation() {
    currentConvId = Date.now().toString(); // ID temporaire
    messagesChat = [];
    pdfActif = ""; // Réinitialise le document

    // Réinitialisation visuelle
    updateDocumentDropdown();

    renderMessages();
    // CRITIQUE : Ne pas push dans le tableau 'conversations' ni sauvegarder ici.
}
window.nouvelleConversation = nouvelleConversation;

function renderMessages() {
    const container = document.getElementById('chat-messages')
    if (messagesChat.length === 0) {
        container.innerHTML = '<div class="chat-welcome"><p>📂 Uploadez vos documents puis posez votre question !</p></div>'
        return
    }
    container.innerHTML = messagesChat.map(m => {
        if (m.role === 'user') return `<div class="msg-user">${m.content}</div>`
        return `<div class="msg-bot">${m.content}<div class="msg-meta">🤖 ${m.mode === 'resume' ? 'Mode Résumé' : 'Mode Recherche'} ${m.score ? '— ' + (m.score * 100).toFixed(1) + '% pertinence' : ''}</div></div>`
    }).join('')
    container.scrollTop = container.scrollHeight
}

async function doChat() {
    if (!pdfActif || pdfActif === "") {
        return toast('Veuillez cibler un document avant de poser votre question.', 'error');
    }
    const input = document.getElementById('chat-input')
    const query = input.value.trim()
    if (!query) return toast('Saisissez une question.', 'error')
    
    if (!currentConvId) {
        nouvelleConversation();
    }
    
    const userMsg = { role: 'user', content: query };
    messagesChat.push(userMsg);
    
    saveCurrentConversation();
    
    const convo = conversations.find(c => c.id === currentConvId);
    if (!convo) return;
    
    let isFirstMessage = (convo && convo.nom.startsWith('Conversation '));
    if (isFirstMessage) {
        api('/generate-title', { method: 'POST', body: JSON.stringify({ query, pdf_name: pdfActif }) })
            .then(res => {
                if (res && res.titre) {
                    convo.nom = res.titre;
                    saveCurrentConversation();
                    renderConversations();
                }
            })
            .catch(err => console.error(err));
    }
    
    input.value = ''
    renderMessages()
    try {
        let botMsg = null;
        if (chatMode === 'resume') {
            const data = await api('/chat', { method: 'POST', body: JSON.stringify({ query, mode: 'resume', pdf_name: pdfActif }) })
            botMsg = { role: 'bot', content: data.reponse, mode: 'resume', score: data.score };
        } else {
            const data = await api('/search', { method: 'POST', body: JSON.stringify({ query, pdf_name: pdfActif }) })
            let reponse = '<strong>🔍 Extraits pertinents :</strong><br><br>'
            if (data.resultats && data.resultats.length > 0) {
                data.resultats.forEach((r, i) => {
                    reponse += `<strong>Extrait ${i+1}</strong> — ${(r.score*100).toFixed(1)}% pertinence<br>`
                    reponse += `<em>Page ${r.page || '?'}</em><br>`
                    reponse += `${r.texte}<br><br>`
                })
                botMsg = { role: 'bot', content: reponse, mode: 'recherche', score: data.resultats[0].score };
            } else {
                botMsg = { role: 'bot', content: '❌ Aucun extrait trouvé.', mode: 'recherche', score: 0 };
            }
        }
        
        if (botMsg) {
            messagesChat.push(botMsg);
            convo.messages.push(botMsg);
            localStorage.setItem('studysearch_convos', JSON.stringify(conversations));
        }
    } catch (error) {
        const errMsg = { role: 'bot', content: '❌ Erreur : ' + error.message, mode: chatMode, score: 0 };
        messagesChat.push(errMsg);
        convo.messages.push(errMsg);
        localStorage.setItem('studysearch_convos', JSON.stringify(conversations));
    }
    renderMessages()
}

// ── Home Screen Events ──────────────────────────────────────
$('btn-home-start').addEventListener('click', () => {
    if (token && userEmail) {
        goDashboard();
    } else {
        show('auth-screen');
        $('tab-login').click();
    }
});

$('home-login-link').addEventListener('click', (e) => {
    e.preventDefault();
    show('auth-screen');
    $('tab-login').click();
});

// ── Init ────────────────────────────────────────────────────
if (token && userEmail) {
    api('/auth/me').then(() => goDashboard()).catch(() => goHome());
} else {
    goHome();
}
