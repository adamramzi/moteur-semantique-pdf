# ── 1. IMPORTS ────────────────────────────────────────────────
import os
import shutil
import tempfile
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import json
import streamlit as st
from sentence_transformers import SentenceTransformer

from pdf_processor import extraire_texte, decouper_chunks
from vectoriser import vectoriser_chunks, creer_index, sauvegarder_index, charger_index, rechercher, rechercher_avec_metadata, get_user_index_path
from database import (
    init_db, get_ip_utilisateur, get_user_id,
    sauvegarder_document, sauvegarder_recherche,
    get_historique_documents, get_historique_recherches,
    supprimer_document, nettoyer_utilisateurs_inactifs,
)
from auth import afficher_page_auth

# ── 2. PAGE CONFIG — doit être la première commande Streamlit ──
st.set_page_config(
    page_title="Moteur Sémantique PDF",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Import après set_page_config car le module utilise st.cache en interne
from streamlit_cookies_manager import EncryptedCookieManager

# ── 3. INITIALISATION DB + NETTOYAGE ─────────────────────────────
init_db()
nettoyer_utilisateurs_inactifs(jours=30)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: linear-gradient(135deg, #0f0c29, #302b63, #24243e); min-height: 100vh; }

.auth-card {
    background: rgba(255,255,255,0.06); border: 1px solid rgba(167,139,250,0.25);
    border-radius: 24px; padding: 2.5rem 2.8rem; width: 100%; max-width: 460px;
    backdrop-filter: blur(16px); box-shadow: 0 8px 40px rgba(0,0,0,0.4);
    position: relative; overflow: hidden;
}
.auth-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg, #a78bfa, #60a5fa, #34d399);
}
.auth-title {
    font-size: 1.7rem; font-weight: 700;
    background: linear-gradient(90deg, #a78bfa, #60a5fa);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 0.3rem; text-align: center;
}
.auth-subtitle { color: #64748b; font-size: 0.9rem; text-align: center; margin-bottom: 1.8rem; }
.code-hint {
    background: rgba(96,165,250,0.1); border: 1px solid rgba(96,165,250,0.3);
    border-radius: 10px; padding: 0.8rem 1rem; color: #93c5fd;
    font-size: 0.88rem; margin: 0.8rem 0; line-height: 1.6;
}
.main-title {
    text-align: center; font-size: 2.4rem; font-weight: 700;
    background: linear-gradient(90deg, #a78bfa, #60a5fa, #34d399);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.2rem;
}
.main-subtitle { text-align: center; color: #94a3b8; font-size: 1rem; margin-bottom: 1.5rem; }
.stat-box {
    background: rgba(255,255,255,0.05); border: 1px solid rgba(167,139,250,0.2);
    border-radius: 14px; padding: 1rem 1.2rem; text-align: center;
    position: relative; overflow: hidden;
}
.stat-box::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, #a78bfa, #60a5fa);
}
.stat-number { font-size: 2rem; font-weight: 700; color: #a78bfa; display: block; }
.stat-label { font-size: 0.78rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; }
.result-card {
    background: rgba(255,255,255,0.05); border: 1px solid rgba(167,139,250,0.25);
    border-radius: 16px; padding: 1.4rem 1.6rem; margin-bottom: 1.2rem;
    backdrop-filter: blur(10px); position: relative; overflow: hidden;
}
.result-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg, #a78bfa, #60a5fa); border-radius: 16px 16px 0 0;
}
.result-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.8rem; }
.chunk-badge {
    background: rgba(167,139,250,0.2); color: #a78bfa;
    border: 1px solid rgba(167,139,250,0.4); border-radius: 20px;
    padding: 0.25rem 0.75rem; font-size: 0.78rem; font-weight: 600; letter-spacing: 0.5px;
}
.score-badge { font-size: 1.2rem; font-weight: 700; color: #34d399; }
.result-text {
    color: #cbd5e1; font-size: 0.95rem; line-height: 1.65;
    border-top: 1px solid rgba(255,255,255,0.06); padding-top: 0.8rem; margin-top: 0.4rem;
}
.history-item {
    background: rgba(255,255,255,0.04); border-left: 3px solid #a78bfa;
    border-radius: 0 8px 8px 0; padding: 0.5rem 0.8rem;
    margin-bottom: 0.5rem; color: #cbd5e1; font-size: 0.85rem;
}
.history-time { color: #64748b; font-size: 0.72rem; display: block; margin-top: 0.15rem; }
.sidebar-info {
    background: rgba(255,255,255,0.05); border-radius: 12px; padding: 1rem;
    border: 1px solid rgba(255,255,255,0.08); color: #cbd5e1; font-size: 0.88rem; line-height: 1.7;
}
.status-ok {
    background: rgba(52,211,153,0.12); border: 1px solid rgba(52,211,153,0.3);
    color: #34d399; border-radius: 10px; padding: 0.7rem 1rem; font-size: 0.9rem;
    font-weight: 500; margin: 0.8rem 0;
}
.status-warn {
    background: rgba(251,191,36,0.1); border: 1px solid rgba(251,191,36,0.3);
    color: #fbbf24; border-radius: 10px; padding: 0.7rem 1rem; font-size: 0.9rem; margin: 0.8rem 0;
}
.doc-card {
    background: rgba(255,255,255,0.04); border: 1px solid rgba(167,139,250,0.2);
    border-radius: 12px; padding: 1rem 1.2rem; margin-bottom: 0.8rem;
    position: relative; overflow: hidden; cursor: pointer;
}
.doc-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, #a78bfa, #34d399);
}
.search-history-card {
    background: rgba(52,211,153,0.05); border: 1px solid rgba(52,211,153,0.2);
    border-radius: 10px; padding: 0.9rem 1.1rem; margin-bottom: 0.7rem;
}
div[data-testid="stButton"] > button {
    background: linear-gradient(90deg, #7c3aed, #3b82f6); color: white;
    border: none; border-radius: 10px; font-weight: 600; letter-spacing: 0.3px;
    transition: opacity 0.2s, transform 0.2s;
}
div[data-testid="stButton"] > button:hover { opacity: 0.88; transform: translateY(-1px); }
hr { border-color: rgba(255,255,255,0.08); }
</style>
""", unsafe_allow_html=True)

# ── 4. COOKIE MANAGER — persistance de session ──────────────
_COOKIE_SECRET = os.getenv("COOKIE_SECRET", "moteur_pdf_secret_k3y_2026!")
cookies = EncryptedCookieManager(prefix="moteur_pdf_", password=_COOKIE_SECRET)
if not cookies.ready():
    st.stop()  # Attend que le navigateur charge les cookies

# Restaurer la session depuis le cookie si l'utilisateur n'est pas encore connecté
if not st.session_state.get("auth_connecte") and cookies.get("session_user"):
    try:
        _session_data = json.loads(cookies["session_user"])
        st.session_state["auth_connecte"] = True
        st.session_state["auth_email"]    = _session_data.get("email", "")
    except Exception:
        pass  # Cookie corrompu — on ignore et on affiche le login

# ── Authentification (étape bloquée si non connecté) ────────────
afficher_page_auth()

# Sauvegarder le cookie si l'utilisateur vient de se connecter (pas encore de cookie)
if st.session_state.get("auth_connecte") and not cookies.get("session_user"):
    cookies["session_user"] = json.dumps({"email": st.session_state.get("auth_email", "")})
    cookies.save()

# ── Récupération user_id ───────────────────────────────────────
INDEX_BASE = "index_faiss"
TOP_K = 3
MAX_HISTORIQUE = 5

email_connecte = st.session_state.get("auth_email", "")
user_id = get_user_id(email_connecte) if email_connecte else None
INDEX_DIR = get_user_index_path(user_id, INDEX_BASE) if user_id else os.path.join(INDEX_BASE, "guest")

# ── Modèle ────────────────────────────────────────────────────
@st.cache_resource(show_spinner="⏳ Chargement du moteur…")
def charger_modele():
    return SentenceTransformer("all-mpnet-base-v2")

# ── Session state — toujours fresh à chaque nouvelle connexion ──
if "_user_id_charge" not in st.session_state or st.session_state.get("_user_id_charge") != user_id:
    st.session_state["vecteurs"]            = None   # pas de chargement auto depuis disque
    st.session_state["chunks"]              = []
    st.session_state["chunks_par_fichier"]  = {}     # {nom_fichier: [chunks...]}
    st.session_state["index_depuis_disque"] = False
    st.session_state["nb_pdfs"]            = 0
    st.session_state["historique"]         = []
    st.session_state["derniers_resultats"] = []
    st.session_state["derniere_question"]  = ""
    st.session_state["pdf_actif"]          = None
    st.session_state["_user_id_charge"]    = user_id

for k, v in [
    ("historique", []), ("derniers_resultats", []),
    ("derniere_question", ""), ("nb_pdfs", 0), ("pdf_actif", None),
    ("chunks_par_fichier", {}),
]:
    if k not in st.session_state:
        st.session_state[k] = v

model = charger_modele()

# ──────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📚 Recherche dans vos PDF")

    st.markdown(f"""
    <div style="background:rgba(167,139,250,0.1);border:1px solid rgba(167,139,250,0.3);
                border-radius:14px;padding:0.9rem 1rem;margin-bottom:0.6rem;
                position:relative;overflow:hidden;">
        <div style="position:absolute;top:0;left:0;right:0;height:2px;
                    background:linear-gradient(90deg,#a78bfa,#60a5fa);"></div>
        <div style="font-size:0.72rem;color:#94a3b8;text-transform:uppercase;
                    letter-spacing:0.8px;margin-bottom:0.45rem;font-weight:600;">
            ✅ Utilisateur connecté
        </div>
        <div style="color:#e2e8f0;font-size:0.88rem;font-weight:600;word-break:break-all;">
            📧 {email_connecte}
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🚪 Se déconnecter", use_container_width=True, key="btn_deconnexion"):
        # 1. Supprimer le cookie de session
        if cookies.get("session_user"):
            del cookies["session_user"]
            cookies.save()
        # 2. Supprimer l'index FAISS de cet utilisateur sur le disque
        if os.path.exists(INDEX_DIR):
            shutil.rmtree(INDEX_DIR)
        # 3. Réinitialiser TOUT le session_state proprement
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

    st.markdown("---")
    st.markdown("### 📊 État de la base de recherche")
    if st.session_state["vecteurs"] is not None:
        n_passages = len(st.session_state["chunks"])
        st.success(f"✅ Prêt — **{n_passages}** passages enregistrés")
        if st.session_state.get("index_depuis_disque"):
            st.info("💾 Documents chargés automatiquement")
    else:
        st.warning("⚠️ Aucun document analysé pour l'instant")

    if st.session_state["historique"]:
        st.markdown("---")
        st.markdown("### 🕐 Dernières recherches")
        for entree in reversed(st.session_state["historique"]):
            st.markdown(f"""
            <div class="history-item">
                🔍 {entree['question']}
                <span class="history-time">{entree['heure']}</span>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🗑️ Réinitialiser")
    if st.button("🗑️ Effacer tous mes documents", use_container_width=True):
        st.session_state["vecteurs"]           = None
        st.session_state["chunks"]             = []
        st.session_state["index_depuis_disque"] = False
        st.session_state["nb_pdfs"]            = 0
        st.session_state["historique"]         = []
        st.session_state["derniers_resultats"] = []
        st.session_state["derniere_question"]  = ""
        st.session_state["pdf_actif"]          = None
        if os.path.exists(INDEX_DIR):
            shutil.rmtree(INDEX_DIR)
        st.rerun()

# ──────────────────────────────────────────────
# TITRE + COMPTEURS
# ──────────────────────────────────────────────
st.markdown('<h1 class="main-title">🔍 Moteur de recherche sémantique PDF</h1>', unsafe_allow_html=True)
st.markdown('<p class="main-subtitle">Posez une question et trouvez instantanément les réponses dans vos fichiers PDF</p>', unsafe_allow_html=True)

n_passages   = len(st.session_state["chunks"])
n_pdfs       = st.session_state["nb_pdfs"]
n_recherches = len(st.session_state["historique"])

col_a, col_b, col_c = st.columns(3)
with col_a:
    st.markdown(f'<div class="stat-box"><span class="stat-number">{n_pdfs}</span><span class="stat-label">📄 Fichiers PDF analysés</span></div>', unsafe_allow_html=True)
with col_b:
    st.markdown(f'<div class="stat-box"><span class="stat-number">{n_passages}</span><span class="stat-label">📝 Passages enregistrés</span></div>', unsafe_allow_html=True)
with col_c:
    st.markdown(f'<div class="stat-box"><span class="stat-number">{n_recherches}</span><span class="stat-label">🔎 Recherches effectuées</span></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# SECTION UPLOAD
# ──────────────────────────────────────────────
st.markdown("## 📤 Ajouter vos fichiers PDF")

uploaded_files = st.file_uploader(
    "Glissez-déposez vos fichiers PDF ici",
    type=["pdf"],
    accept_multiple_files=True,
    label_visibility="collapsed",
)

# Stocker les fichiers uploadés pour le visualiseur PDF
if uploaded_files:
    for uf in uploaded_files:
        if uf.name not in st.session_state.get("pdf_bytes", {}):
            st.session_state.setdefault("pdf_bytes", {})[uf.name] = uf.getvalue()

if uploaded_files:
    if st.button("⚙️ Analyser et enregistrer les documents", use_container_width=False):
        progress = st.progress(0, text="📖 Lecture du texte en cours…")
        chunks_par_fichier = dict(st.session_state.get("chunks_par_fichier", {}))
        nouveaux_pdfs = 0
        total = len(uploaded_files)

        for i, uploaded_file in enumerate(uploaded_files):
            num_fichier = i + 1
            # Ignorer si déjà chargé en session
            if uploaded_file.name in chunks_par_fichier:
                progress.progress(int(num_fichier / total * 50),
                    text=f"⏭️ Fichier {num_fichier}/{total} déjà chargé : {uploaded_file.name}")
                continue

            with st.spinner(f"📄 Analyse du fichier {num_fichier}/{total} : {uploaded_file.name}…"):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(uploaded_file.read())
                    tmp_path = tmp.name

                try:
                    paragraphes = extraire_texte(tmp_path)
                    chunks = decouper_chunks(paragraphes)
                    chunks_par_fichier[uploaded_file.name] = chunks
                    if user_id:
                        sauvegarder_document(user_id, uploaded_file.name, len(chunks))
                    nouveaux_pdfs += 1
                finally:
                    os.unlink(tmp_path)

            progress.progress(int(num_fichier / total * 50),
                text=f"✅ Fichier {num_fichier}/{total} terminé : {uploaded_file.name}")

        # Reconstruire l'index — extraire le texte de chaque chunk dict
        all_chunks = [c for cl in chunks_par_fichier.values() for c in cl]
        all_textes = [c["texte"] if isinstance(c, dict) else c for c in all_chunks]

        if not all_chunks:
            st.error("❌ Impossible de lire le texte de ces fichiers PDF.")
        else:
            progress.progress(60, text="🧠 Analyse du contenu des passages…")
            vecteurs = vectoriser_chunks(all_textes)
            progress.progress(80, text="🔗 Préparation de la base de recherche…")
            vecteurs = creer_index(vecteurs)
            progress.progress(90, text="💾 Sauvegarde en cours…")
            sauvegarder_index(vecteurs, all_chunks, path=INDEX_DIR)

            st.session_state["vecteurs"]           = vecteurs
            st.session_state["chunks"]             = all_chunks
            st.session_state["chunks_par_fichier"] = chunks_par_fichier
            st.session_state["index_depuis_disque"] = False
            st.session_state["nb_pdfs"]            += nouveaux_pdfs

            progress.progress(100, text="✅ Terminé !")
            st.markdown(f"""
            <div class="status-ok">
            ✅ <b>{len(all_chunks)} passages</b> enregistrés depuis
            <b>{len(chunks_par_fichier)}</b> fichier(s) PDF. Vous pouvez maintenant poser vos questions !
            </div>
            """, unsafe_allow_html=True)
            st.rerun()

# ──────────────────────────────────────────────
# SECTION MON HISTORIQUE
# ──────────────────────────────────────────────
st.markdown("---")
st.markdown("## 📚 Mon Historique")

if user_id:
    docs = get_historique_documents(user_id)

    if not docs:
        st.markdown("""
        <div class="status-warn">
        📭 Aucun document analysé pour le moment. Uploadez votre premier PDF ci-dessus !
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"<p style='color:#94a3b8;'>📂 <b>{len(docs)}</b> document(s) analysé(s) dans votre espace personnel.</p>", unsafe_allow_html=True)

        # Sélecteur de PDF
        noms_fichiers = [d["nom_fichier"] for d in docs]
        pdf_selectionne = st.selectbox(
            "📄 Sélectionnez un PDF pour voir son historique de recherches :",
            options=noms_fichiers,
            key="select_pdf_historique",
        )

        # Affichage des cartes de documents avec bouton de suppression
        for doc in docs:
            badge_color = "#a78bfa" if doc["nom_fichier"] == pdf_selectionne else "#64748b"
            border_color = "rgba(167,139,250,0.5)" if doc["nom_fichier"] == pdf_selectionne else "rgba(255,255,255,0.08)"
            col_doc, col_del = st.columns([5, 1])
            with col_doc:
                st.markdown(f"""
                <div style="background:rgba(255,255,255,0.04);border:1px solid {border_color};
                            border-radius:12px;padding:0.9rem 1.2rem;margin-bottom:0.4rem;
                            position:relative;overflow:hidden;">
                    <div style="position:absolute;top:0;left:0;right:0;height:2px;
                                background:linear-gradient(90deg,{badge_color},#34d399);"></div>
                    <span style="color:#e2e8f0;font-weight:600;font-size:0.95rem;">📄 {doc['nom_fichier']}</span>
                    <span style="display:block;color:#64748b;font-size:0.78rem;margin-top:0.2rem;">
                        🗓️ {doc['date_upload']} &nbsp;|&nbsp;
                        📝 <b style="color:{badge_color};">{doc['nombre_chunks']}</b> passages
                    </span>
                </div>
                """, unsafe_allow_html=True)
            with col_del:
                if st.button("🗑️", key=f"del_{doc['nom_fichier']}", help=f"Supprimer {doc['nom_fichier']}"):
                    nom_a_suppr = doc["nom_fichier"]
                    # 1. Retirer de la base de données
                    if user_id:
                        supprimer_document(user_id, nom_a_suppr)
                    # 2. Retirer les chunks de cet fichier de la session
                    cpf = dict(st.session_state.get("chunks_par_fichier", {}))
                    nb_chunks_suppr = len(cpf.pop(nom_a_suppr, []))
                    all_chunks_restants = [c for cl in cpf.values() for c in cl]
                    # 3. Reconstruire et sauvegarder l'index
                    if all_chunks_restants:
                        vecteurs_new = creer_index(vectoriser_chunks(all_chunks_restants))
                        sauvegarder_index(vecteurs_new, all_chunks_restants, path=INDEX_DIR)
                        st.session_state["vecteurs"] = vecteurs_new
                    else:
                        if os.path.exists(INDEX_DIR):
                            shutil.rmtree(INDEX_DIR)
                        st.session_state["vecteurs"] = None
                    # 4. Mettre à jour les compteurs et l'état
                    st.session_state["chunks"]             = all_chunks_restants
                    st.session_state["chunks_par_fichier"] = cpf
                    st.session_state["nb_pdfs"]            = max(0, st.session_state["nb_pdfs"] - 1)
                    st.session_state["derniers_resultats"] = []
                    st.session_state["derniere_question"]  = ""
                    st.success(f"✅ '{nom_a_suppr}' supprimé ({nb_chunks_suppr} passages retirés)")
                    st.rerun()

        # Historique des recherches pour le PDF sélectionné
        if pdf_selectionne:
            st.markdown(f"### 🔎 Questions posées sur : *{pdf_selectionne}*")
            recherches = get_historique_recherches(user_id, pdf_selectionne)

            if not recherches:
                st.markdown("""
                <div style="background:rgba(96,165,250,0.08);border:1px solid rgba(96,165,250,0.2);
                            border-radius:10px;padding:0.9rem 1.1rem;color:#93c5fd;font-size:0.9rem;">
                    💬 Aucune recherche effectuée sur ce document encore.
                </div>
                """, unsafe_allow_html=True)
            else:
                for r in recherches:
                    score_pct = (r["score"] or 0) * 100
                    passage_court = (r["passage_trouve"] or "")[:300]
                    if len(r["passage_trouve"] or "") > 300:
                        passage_court += "…"
                    st.markdown(f"""
                    <div class="search-history-card">
                        <div style="color:#e2e8f0;font-weight:600;margin-bottom:0.4rem;">
                            ❓ {r['question']}
                        </div>
                        <div style="color:#94a3b8;font-size:0.78rem;margin-bottom:0.5rem;">
                            🕐 {r['date_recherche']} &nbsp;|&nbsp;
                            ✅ <span style="color:#34d399;font-weight:600;">{score_pct:.1f}%</span> de correspondance
                        </div>
                        <div style="color:#cbd5e1;font-size:0.88rem;line-height:1.6;
                                    background:rgba(0,0,0,0.2);border-radius:8px;padding:0.7rem;">
                            📄 {passage_court}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
else:
    st.warning("⚠️ Impossible de récupérer votre historique (user_id introuvable).")

# ──────────────────────────────────────────────
# SECTION RECHERCHE
# ──────────────────────────────────────────────
st.markdown("---")
st.markdown("## 🔎 Poser une question")

# Déterminer le nom du PDF actif (dernier uploadé ou sélectionné)
nom_pdf_actif = st.session_state.get("pdf_actif") or "document"

if st.session_state["vecteurs"] is None:
    st.markdown("""
    <div class="status-warn">
    ⚠️ Veuillez d'abord ajouter et analyser au moins un fichier PDF avant de faire une recherche.
    </div>
    """, unsafe_allow_html=True)
else:
    # Permettre de choisir quel PDF rechercher si plusieurs existent
    if user_id:
        docs_dispo = get_historique_documents(user_id)
        if docs_dispo:
            noms = [d["nom_fichier"] for d in docs_dispo]
            nom_pdf_actif = st.selectbox(
                "📄 Rechercher dans quel document ?",
                options=noms,
                key="select_pdf_recherche",
            )

    query = st.text_input(
        "✍️ Écrivez votre question ici :",
        placeholder="Ex : Quels sont les principaux résultats ? De quoi parle ce document ?",
    )

    col1, col2 = st.columns([1, 5])
    with col1:
        rechercher_btn = st.button("🔍 Rechercher", use_container_width=True)

    if rechercher_btn:
        if not query.strip():
            st.warning("⚠️ Veuillez saisir une question avant de lancer la recherche.")
        else:
            with st.spinner("Recherche en cours…"):
                query_vector = model.encode([query])[0]
                resultats = rechercher_avec_metadata(
                    query_vector,
                    st.session_state["vecteurs"],
                    st.session_state["chunks"],
                    top_k=TOP_K,
                )

            # Sauvegarde du meilleur résultat en base
            if user_id and resultats:
                meilleur = resultats[0]
                sauvegarder_recherche(
                    user_id,
                    nom_pdf_actif,
                    query,
                    meilleur["texte"],
                    meilleur["score"],
                )

            historique = st.session_state["historique"]
            historique.append({"question": query, "heure": datetime.now().strftime("%H:%M:%S")})
            st.session_state["historique"]         = historique[-MAX_HISTORIQUE:]
            st.session_state["derniers_resultats"] = resultats
            st.session_state["derniere_question"]  = query

    if st.session_state["derniers_resultats"]:
        q = st.session_state["derniere_question"]
        st.markdown(f'### 📋 Passages trouvés pour : *"{q}"*')

        contenu_export = f"RÉSULTATS DE RECHERCHE\nQuestion : {q}\nDate     : {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}\n" + "=" * 60 + "\n\n"

        for idx_res, res in enumerate(st.session_state["derniers_resultats"]):
            score_pct     = res["score"] * 100
            texte         = res["texte"]
            texte_affiche = texte if len(texte) <= 600 else texte[:600] + "…"
            chunk_num     = res["chunk_index"] + 1
            page_num      = res.get("page", 0)
            fichier_nom   = res.get("fichier", "")

            # Métadonnées sous le passage
            meta_html = ""
            if fichier_nom or page_num:
                meta_parts = []
                if fichier_nom:
                    meta_parts.append(f"📄 Fichier : <b>{fichier_nom}</b>")
                if page_num:
                    meta_parts.append(f"📖 Page : <b>{page_num}</b>")
                meta_html = f'<div style="color:#94a3b8;font-size:0.82rem;margin-top:0.6rem;padding-top:0.5rem;border-top:1px solid rgba(255,255,255,0.06);">{" &nbsp;|&nbsp; ".join(meta_parts)}</div>'

            st.markdown(f"""
            <div class="result-card">
                <div class="result-header">
                    <span class="chunk-badge">📄 Passage #{chunk_num}</span>
                    <span class="score-badge">{score_pct:.1f}% correspondance</span>
                </div>
                <div class="result-text">{texte_affiche}</div>
                {meta_html}
            </div>
            """, unsafe_allow_html=True)

            # Bouton visualiseur PDF
            pdf_data = st.session_state.get("pdf_bytes", {}).get(fichier_nom)
            if pdf_data and fichier_nom:
                with st.expander(f"👁️ Voir le PDF — {fichier_nom}", expanded=False):
                    st.download_button(
                        label=f"💾 Télécharger {fichier_nom}",
                        data=pdf_data,
                        file_name=fichier_nom,
                        mime="application/pdf",
                        key=f"dl_pdf_{idx_res}_{fichier_nom}",
                    )
                    st.info(f"📖 Le passage trouvé se trouve à la **page {page_num}** de ce document.")

            contenu_export += f"Passage #{chunk_num} — Correspondance : {score_pct:.1f}%"
            if fichier_nom:
                contenu_export += f" | Fichier : {fichier_nom}"
            if page_num:
                contenu_export += f" | Page : {page_num}"
            contenu_export += "\n" + "-" * 40 + f"\n{texte}\n\n"

        st.markdown("---")
        st.download_button(
            label="💾 Télécharger les résultats en fichier texte",
            data=contenu_export.encode("utf-8"),
            file_name=f"resultats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            use_container_width=False,
        )
