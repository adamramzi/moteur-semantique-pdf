import os
import shutil
import tempfile
from datetime import datetime

import streamlit as st
from sentence_transformers import SentenceTransformer

from pdf_processor import extraire_texte, decouper_chunks
from vectoriser import vectoriser_chunks, creer_index, sauvegarder_index, charger_index, rechercher

# ──────────────────────────────────────────────
# Configuration de la page
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Moteur Sémantique PDF",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────
# CSS personnalisé
# ──────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    min-height: 100vh;
}

.main-title {
    text-align: center;
    font-size: 2.4rem;
    font-weight: 700;
    background: linear-gradient(90deg, #a78bfa, #60a5fa, #34d399);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.2rem;
}

.main-subtitle {
    text-align: center;
    color: #94a3b8;
    font-size: 1rem;
    margin-bottom: 1.5rem;
}

/* Compteur stats */
.stat-box {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(167, 139, 250, 0.2);
    border-radius: 14px;
    padding: 1rem 1.2rem;
    text-align: center;
    position: relative;
    overflow: hidden;
}

.stat-box::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #a78bfa, #60a5fa);
}

.stat-number {
    font-size: 2rem;
    font-weight: 700;
    color: #a78bfa;
    display: block;
}

.stat-label {
    font-size: 0.78rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* Cartes de résultats */
.result-card {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(167, 139, 250, 0.25);
    border-radius: 16px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1.2rem;
    backdrop-filter: blur(10px);
    position: relative;
    overflow: hidden;
}

.result-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #a78bfa, #60a5fa);
    border-radius: 16px 16px 0 0;
}

.result-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.8rem;
}

.chunk-badge {
    background: rgba(167, 139, 250, 0.2);
    color: #a78bfa;
    border: 1px solid rgba(167, 139, 250, 0.4);
    border-radius: 20px;
    padding: 0.25rem 0.75rem;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.5px;
}

.score-badge {
    font-size: 1.2rem;
    font-weight: 700;
    color: #34d399;
}

.result-text {
    color: #cbd5e1;
    font-size: 0.95rem;
    line-height: 1.65;
    border-top: 1px solid rgba(255,255,255,0.06);
    padding-top: 0.8rem;
    margin-top: 0.4rem;
}

/* Historique */
.history-item {
    background: rgba(255,255,255,0.04);
    border-left: 3px solid #a78bfa;
    border-radius: 0 8px 8px 0;
    padding: 0.5rem 0.8rem;
    margin-bottom: 0.5rem;
    color: #cbd5e1;
    font-size: 0.85rem;
    cursor: default;
}

.history-time {
    color: #64748b;
    font-size: 0.72rem;
    display: block;
    margin-top: 0.15rem;
}

/* Sidebar */
.sidebar-info {
    background: rgba(255,255,255,0.05);
    border-radius: 12px;
    padding: 1rem;
    border: 1px solid rgba(255,255,255,0.08);
    color: #cbd5e1;
    font-size: 0.88rem;
    line-height: 1.7;
}

.status-ok {
    background: rgba(52, 211, 153, 0.12);
    border: 1px solid rgba(52, 211, 153, 0.3);
    color: #34d399;
    border-radius: 10px;
    padding: 0.7rem 1rem;
    font-size: 0.9rem;
    font-weight: 500;
    margin: 0.8rem 0;
}

.status-warn {
    background: rgba(251, 191, 36, 0.1);
    border: 1px solid rgba(251, 191, 36, 0.3);
    color: #fbbf24;
    border-radius: 10px;
    padding: 0.7rem 1rem;
    font-size: 0.9rem;
    margin: 0.8rem 0;
}

div[data-testid="stButton"] > button {
    background: linear-gradient(90deg, #7c3aed, #3b82f6);
    color: white;
    border: none;
    border-radius: 10px;
    font-weight: 600;
    letter-spacing: 0.3px;
    transition: opacity 0.2s, transform 0.2s;
}

div[data-testid="stButton"] > button:hover {
    opacity: 0.88;
    transform: translateY(-1px);
}

hr { border-color: rgba(255,255,255,0.08); }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Constantes
# ──────────────────────────────────────────────
INDEX_DIR = "index_faiss"
TOP_K = 3
MAX_HISTORIQUE = 5


# ──────────────────────────────────────────────
# Modèle (mis en cache)
# ──────────────────────────────────────────────
@st.cache_resource(show_spinner="⏳ Préparation du moteur de recherche, veuillez patienter…")
def charger_modele():
    return SentenceTransformer("all-MiniLM-L6-v2")


# ──────────────────────────────────────────────
# Initialisation du session_state
# ──────────────────────────────────────────────
if "vecteurs" not in st.session_state:
    vecteurs, chunks = charger_index(INDEX_DIR)
    st.session_state["vecteurs"]          = vecteurs
    st.session_state["chunks"]            = chunks if chunks is not None else []
    st.session_state["index_depuis_disque"] = vecteurs is not None
    st.session_state["nb_pdfs"]           = 0          # compteur de PDFs indexés
    st.session_state["historique"]        = []          # liste des 5 dernières recherches
    st.session_state["derniers_resultats"] = []         # résultats de la dernière recherche
    st.session_state["derniere_question"]  = ""

if "historique" not in st.session_state:
    st.session_state["historique"] = []
if "derniers_resultats" not in st.session_state:
    st.session_state["derniers_resultats"] = []
if "derniere_question" not in st.session_state:
    st.session_state["derniere_question"] = ""
if "nb_pdfs" not in st.session_state:
    st.session_state["nb_pdfs"] = 0

model = charger_modele()

# ──────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📚 Recherche dans vos PDF")
    st.markdown("---")

    st.markdown("### ℹ️ Comment ça marche ?")
    st.markdown("""
    <div class="sidebar-info">
    Cette application vous permet de chercher des informations dans vos documents PDF en posant une question simple.<br><br>
    🧠 <b>Compréhension du texte</b><br>
    &nbsp;&nbsp;Le moteur comprend le sens de votre question<br><br>
    📐 <b>Comparaison intelligente</b><br>
    &nbsp;&nbsp;Trouve les passages les plus proches de votre question<br><br>
    📄 <b>Lecture automatique des PDF</b><br>
    &nbsp;&nbsp;Extrait tout le texte de vos fichiers<br><br>
    🌐 <b>Interface simple</b><br>
    &nbsp;&nbsp;Accessible depuis votre navigateur
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 📊 État de la base de recherche")

    if st.session_state["vecteurs"] is not None:
        n_passages = len(st.session_state["chunks"])
        st.success(f"✅ Prêt — **{n_passages}** passages enregistrés")
        if st.session_state.get("index_depuis_disque"):
            st.info("💾 Documents chargés automatiquement")
    else:
        st.warning("⚠️ Aucun document analysé pour l'instant")

    # ── Historique des recherches ──────────────────────────────────────
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
    if st.button("🗑️ Effacer tous les documents", use_container_width=True):
        st.session_state["vecteurs"]           = None
        st.session_state["chunks"]             = []
        st.session_state["index_depuis_disque"] = False
        st.session_state["nb_pdfs"]            = 0
        st.session_state["historique"]         = []
        st.session_state["derniers_resultats"] = []
        st.session_state["derniere_question"]  = ""
        if os.path.exists(INDEX_DIR):
            shutil.rmtree(INDEX_DIR)
        st.rerun()

# ──────────────────────────────────────────────
# TITRE + COMPTEURS
# ──────────────────────────────────────────────
st.markdown('<h1 class="main-title">🔍 Moteur de recherche sémantique de documents PDF</h1>', unsafe_allow_html=True)
st.markdown('<p class="main-subtitle">Posez une question et trouvez instantanément les réponses dans vos fichiers PDF</p>', unsafe_allow_html=True)

# ── Compteurs ─────────────────────────────────────────────────────────────
n_passages  = len(st.session_state["chunks"])
n_pdfs      = st.session_state["nb_pdfs"]
n_recherches = len(st.session_state["historique"])

col_a, col_b, col_c = st.columns(3)
with col_a:
    st.markdown(f"""
    <div class="stat-box">
        <span class="stat-number">{n_pdfs}</span>
        <span class="stat-label">📄 Fichiers PDF analysés</span>
    </div>
    """, unsafe_allow_html=True)
with col_b:
    st.markdown(f"""
    <div class="stat-box">
        <span class="stat-number">{n_passages}</span>
        <span class="stat-label">📝 Passages enregistrés</span>
    </div>
    """, unsafe_allow_html=True)
with col_c:
    st.markdown(f"""
    <div class="stat-box">
        <span class="stat-number">{n_recherches}</span>
        <span class="stat-label">🔎 Recherches effectuées</span>
    </div>
    """, unsafe_allow_html=True)

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

if uploaded_files:
    if st.button("⚙️ Analyser et enregistrer les documents", use_container_width=False):
        all_chunks = []
        progress = st.progress(0, text="📖 Lecture du texte en cours…")

        for i, uploaded_file in enumerate(uploaded_files):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name

            try:
                paragraphes = extraire_texte(tmp_path)
                chunks = decouper_chunks(paragraphes)
                all_chunks.extend(chunks)
            finally:
                os.unlink(tmp_path)

            progress.progress(
                int((i + 1) / len(uploaded_files) * 50),
                text=f"📄 Fichier lu : {uploaded_file.name}"
            )

        if not all_chunks:
            st.error("❌ Impossible de lire le texte de ces fichiers PDF.")
        else:
            progress.progress(60, text="🧠 Analyse du contenu des passages…")
            vecteurs = vectoriser_chunks(all_chunks)

            progress.progress(80, text="🔗 Préparation de la base de recherche…")
            vecteurs = creer_index(vecteurs)

            progress.progress(90, text="💾 Sauvegarde en cours…")
            sauvegarder_index(vecteurs, all_chunks, path=INDEX_DIR)

            st.session_state["vecteurs"]           = vecteurs
            st.session_state["chunks"]             = all_chunks
            st.session_state["index_depuis_disque"] = False
            st.session_state["nb_pdfs"]            += len(uploaded_files)

            progress.progress(100, text="✅ Terminé !")
            st.markdown(f"""
            <div class="status-ok">
            ✅ <b>{len(all_chunks)} passages</b> enregistrés depuis
            <b>{len(uploaded_files)}</b> fichier(s) PDF. Vous pouvez maintenant poser vos questions !
            </div>
            """, unsafe_allow_html=True)
            st.rerun()

# ──────────────────────────────────────────────
# SECTION RECHERCHE
# ──────────────────────────────────────────────
st.markdown("---")
st.markdown("## 🔎 Poser une question")

if st.session_state["vecteurs"] is None:
    st.markdown("""
    <div class="status-warn">
    ⚠️ Veuillez d'abord ajouter et analyser au moins un fichier PDF avant de faire une recherche.
    </div>
    """, unsafe_allow_html=True)
else:
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
                resultats = rechercher(
                    query_vector,
                    st.session_state["vecteurs"],
                    st.session_state["chunks"],
                    top_k=TOP_K,
                )

            # Mettre à jour l'historique (max 5 entrées)
            historique = st.session_state["historique"]
            historique.append({
                "question": query,
                "heure": datetime.now().strftime("%H:%M:%S"),
            })
            st.session_state["historique"] = historique[-MAX_HISTORIQUE:]
            st.session_state["derniers_resultats"] = resultats
            st.session_state["derniere_question"]  = query

    # Affichage des résultats (de la dernière recherche mémorisée)
    if st.session_state["derniers_resultats"]:
        q = st.session_state["derniere_question"]
        st.markdown(f"### 📋 Passages trouvés pour : *\"{q}\"*")

        contenu_export = f"RÉSULTATS DE RECHERCHE\n"
        contenu_export += f"Question : {q}\n"
        contenu_export += f"Date     : {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}\n"
        contenu_export += "=" * 60 + "\n\n"

        for res in st.session_state["derniers_resultats"]:
            score_pct   = res["score"] * 100
            texte       = res["texte"]
            texte_affiche = texte if len(texte) <= 600 else texte[:600] + "…"
            chunk_num   = res["chunk_index"] + 1

            st.markdown(f"""
            <div class="result-card">
                <div class="result-header">
                    <span class="chunk-badge">📄 Passage #{chunk_num}</span>
                    <span class="score-badge" title="Degré de correspondance avec votre question">{score_pct:.1f}% correspondance</span>
                </div>
                <div class="result-text">{texte_affiche}</div>
            </div>
            """, unsafe_allow_html=True)

            contenu_export += f"Passage #{chunk_num} — Correspondance : {score_pct:.1f}%\n"
            contenu_export += "-" * 40 + "\n"
            contenu_export += texte + "\n\n"

        # ── Bouton d'export ────────────────────────────────────────────────
        st.markdown("---")
        st.download_button(
            label="💾 Télécharger les résultats en fichier texte",
            data=contenu_export.encode("utf-8"),
            file_name=f"resultats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            use_container_width=False,
        )
