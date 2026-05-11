"""
auth.py — Page d'authentification Streamlit
Moteur Sémantique PDF

Logique d'inscription "verify before save" :
    1. L'utilisateur remplit le formulaire → code généré + stocké en session
    2. L'e-mail est envoyé, rien n'est écrit en base
    3. Seulement après validation du code → compte créé avec est_verifie=1
    4. Si l'utilisateur ferme la page → aucune trace en base

Expose une seule fonction publique :
    afficher_page_auth() → bloque l'app via st.stop() si non connecté.
"""

import time

import streamlit as st

from database import (
    email_existe,
    hacher_mot_de_passe,
    generer_code,
    creer_utilisateur_verifie,
    verifier_utilisateur,
    get_ip_utilisateur,
)
from email_service import envoyer_code_verification


# ──────────────────────────────────────────────────────────────
# CSS de la page d'authentification
# ──────────────────────────────────────────────────────────────
_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    min-height: 100vh;
}

/* ── Onglets ── */
div[data-testid="stTabs"] button {
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    color: #94a3b8 !important;
    border-radius: 10px 10px 0 0 !important;
    transition: color 0.2s !important;
}

div[data-testid="stTabs"] button[aria-selected="true"] {
    color: #a78bfa !important;
    border-bottom: 2px solid #a78bfa !important;
}

/* ── Boutons ── */
div[data-testid="stButton"] > button {
    background: linear-gradient(90deg, #7c3aed, #3b82f6) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    letter-spacing: 0.3px !important;
    padding: 0.55rem 1.2rem !important;
    transition: opacity 0.2s, transform 0.15s !important;
}

div[data-testid="stButton"] > button:hover {
    opacity: 0.88 !important;
    transform: translateY(-1px) !important;
}

/* ── Encart code ── */
.code-box {
    background: rgba(96,165,250,0.08);
    border: 1px solid rgba(96,165,250,0.3);
    border-radius: 14px;
    padding: 1rem 1.2rem;
    color: #93c5fd;
    font-size: 0.9rem;
    line-height: 1.7;
    margin: 0.8rem 0 1.2rem;
}

/* ── Carte en-tête ── */
.auth-card {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(167,139,250,0.25);
    border-radius: 20px;
    padding: 1.8rem 2rem 1.4rem;
    text-align: center;
    position: relative;
    overflow: hidden;
    margin-bottom: 1.4rem;
}

.auth-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #a78bfa, #60a5fa, #34d399);
}

.auth-logo  { font-size: 40px; margin-bottom: 8px; }

.auth-title {
    font-size: 1.7rem;
    font-weight: 700;
    background: linear-gradient(90deg, #a78bfa, #60a5fa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 4px;
}

.auth-subtitle {
    color: #64748b;
    font-size: 0.9rem;
}

hr { border-color: rgba(255,255,255,0.08); }
</style>
"""


# ──────────────────────────────────────────────────────────────
# Initialisation du session_state d'authentification
# ──────────────────────────────────────────────────────────────
def _init_auth_state() -> None:
    """Initialise les clés d'auth dans st.session_state si absentes."""
    defauts = {
        "auth_connecte":    False,   # L'utilisateur est-il connecté ?
        "auth_email":       "",      # E-mail de l'utilisateur connecté
        "auth_en_attente":  False,   # En attente de validation du code ?
        # Données temporaires d'inscription (jamais en base avant validation)
        "reg_email_temp":   "",      # E-mail saisi lors de l'inscription
        "reg_hash_temp":    "",      # Mot de passe haché (bcrypt)
        "reg_code_temp":    "",      # Code de vérification à 6 chiffres
        "reg_ip_temp":      "",      # IP de l'utilisateur
    }
    for cle, valeur in defauts.items():
        if cle not in st.session_state:
            st.session_state[cle] = valeur


def _effacer_inscription_temp() -> None:
    """Supprime les données temporaires d'inscription du session_state."""
    for cle in ("reg_email_temp", "reg_hash_temp", "reg_code_temp", "reg_ip_temp"):
        st.session_state[cle] = ""
    st.session_state["auth_en_attente"] = False


# ──────────────────────────────────────────────────────────────
# Affichage des erreurs avec messages clairs
# ──────────────────────────────────────────────────────────────
def _afficher_erreur(erreur: str) -> None:
    """Traduit les messages d'erreur techniques en messages lisibles."""
    traductions = {
        "déjà utilisée":          "❌ Cette adresse e-mail est déjà associée à un compte. Connectez-vous ou utilisez une autre adresse.",
        "déjà utilisé":           "❌ Cette adresse e-mail est déjà associée à un compte.",
        "Mot de passe incorrect":  "❌ Mot de passe incorrect. Vérifiez votre saisie et réessayez.",
        "Aucun compte":            "❌ Aucun compte trouvé avec cette adresse e-mail.",
        "Format":                  "❌ Adresse e-mail invalide. Vérifiez le format (ex : vous@exemple.com).",
        "6 caractères":            "❌ Le mot de passe doit contenir au moins 6 caractères.",
        "non vérifié":             "⚠️ Votre compte n'est pas encore vérifié.",
    }
    for cle, message in traductions.items():
        if cle.lower() in erreur.lower():
            st.error(message)
            return
    st.error(f"❌ {erreur}")


# ──────────────────────────────────────────────────────────────
# Onglet 1 — Connexion
# ──────────────────────────────────────────────────────────────
def _onglet_connexion() -> None:
    """Formulaire de connexion classique."""
    email = st.text_input(
        "📧 Adresse e-mail",
        placeholder="vous@exemple.com",
        key="login_email",
    )
    mdp = st.text_input(
        "🔑 Mot de passe",
        placeholder="••••••••",
        key="login_mdp",
        type="password",
    )

    if st.button("🔐 Se connecter", use_container_width=True, key="btn_login"):
        if not email.strip() or not mdp.strip():
            st.warning("⚠️ Veuillez remplir tous les champs.")
            return

        res = verifier_utilisateur(email.strip(), mdp)

        if res["succes"]:
            st.session_state["auth_connecte"] = True
            st.session_state["auth_email"]    = res["utilisateur"]["email"]
            st.success("✅ Connexion réussie !")
            time.sleep(1)
            st.rerun()
        else:
            _afficher_erreur(res.get("erreur", "Erreur inconnue."))


# ──────────────────────────────────────────────────────────────
# Onglet 2 — Inscription (étape 1 : saisie du formulaire)
# ──────────────────────────────────────────────────────────────
def _onglet_inscription() -> None:
    """
    Étape 1 de l'inscription.

    Actions :
        1. Vérifie que l'e-mail n'existe pas encore en base.
        2. Génère un code à 6 chiffres.
        3. Hache le mot de passe avec bcrypt.
        4. Stocke email, hash, code et IP dans st.session_state UNIQUEMENT
           (rien n'est écrit en base de données).
        5. Envoie le code par e-mail.
        6. Redirige vers l'écran de vérification.
    """
    email = st.text_input(
        "📧 Adresse e-mail",
        placeholder="vous@exemple.com",
        key="reg_email",
    )
    mdp = st.text_input(
        "🔑 Mot de passe",
        placeholder="Minimum 6 caractères",
        key="reg_mdp",
        type="password",
    )
    mdp2 = st.text_input(
        "🔁 Confirmer le mot de passe",
        placeholder="••••••••",
        key="reg_mdp2",
        type="password",
    )

    if st.button("✨ Créer mon compte", use_container_width=True, key="btn_register"):

        # ── Validations côté client ────────────────────────────
        if not email.strip() or not mdp.strip() or not mdp2.strip():
            st.warning("⚠️ Veuillez remplir tous les champs.")
            return

        if "@" not in email or "." not in email.split("@")[-1]:
            st.error("❌ Adresse e-mail invalide.")
            return

        if mdp != mdp2:
            st.error("❌ Les mots de passe ne correspondent pas.")
            return

        if len(mdp) < 6:
            st.error("❌ Le mot de passe doit contenir au moins 6 caractères.")
            return

        # ── Vérification en base : l'e-mail existe déjà ? ─────
        if email_existe(email.strip()):
            st.error(
                "❌ Cette adresse e-mail est déjà associée à un compte. "
                "Connectez-vous ou utilisez une autre adresse."
            )
            return

        # ── Génération du code + hachage du mot de passe ──────
        code     = generer_code()                        # 6 chiffres aléatoires
        hash_mdp = hacher_mot_de_passe(mdp)             # bcrypt hash
        ip       = get_ip_utilisateur()

        # ── Stockage TEMPORAIRE en session (pas en base) ───────
        st.session_state["reg_email_temp"]  = email.strip().lower()
        st.session_state["reg_hash_temp"]   = hash_mdp
        st.session_state["reg_code_temp"]   = code
        st.session_state["reg_ip_temp"]     = ip
        st.session_state["auth_en_attente"] = True

        # ── Envoi du code par e-mail ───────────────────────────
        succes_mail, msg_mail = envoyer_code_verification(email.strip(), code)

        if succes_mail:
            st.success(
                f"✅ Un e-mail de vérification a été envoyé à **{email.strip()}**.\n\n"
                "Consultez votre boîte mail (vérifiez aussi les spams)."
            )
        else:
            st.error(
                f"❌ L'envoi de l'e-mail a échoué : {msg_mail}\n\n"
                "Vérifiez votre configuration Gmail dans le fichier .env."
            )
            # Annuler l'inscription temporaire si l'e-mail n'est pas parti
            _effacer_inscription_temp()
            return

        time.sleep(2)
        st.rerun()


# ──────────────────────────────────────────────────────────────
# Écran de vérification (étape 2 : saisie du code)
# ──────────────────────────────────────────────────────────────
def _ecran_verification() -> None:
    """
    Étape 2 de l'inscription.

    Actions :
        - Compare le code saisi avec celui stocké dans st.session_state.
        - Si correct → crée le compte en base avec est_verifie=1.
        - Si incorrect → affiche "Code incorrect, réessayez."
        - Bouton "Renvoyer" → génère un nouveau code (session seulement)
          et renvoie l'e-mail.
        - Bouton "Annuler" → supprime les données temporaires (aucune trace en base).
    """
    email = st.session_state.get("reg_email_temp", "")

    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown(f"""
        <div class="auth-card">
            <div class="auth-logo">📧</div>
            <div class="auth-title">Vérification</div>
            <div class="auth-subtitle">Code envoyé à <strong>{email}</strong></div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="code-box">
            🔐 Entrez le code à <strong>6 chiffres</strong> envoyé à :<br>
            <strong style="color:#60a5fa;">{email}</strong><br><br>
            Si vous ne le trouvez pas, vérifiez vos <em>spams</em> ou cliquez
            sur <em>"Renvoyer le code"</em>.
        </div>
        """, unsafe_allow_html=True)

        code_saisi = st.text_input(
            "Code de vérification",
            placeholder="Ex : 482910",
            max_chars=6,
            key="verif_code_input",
        )

        col_a, col_b = st.columns(2)

        with col_a:
            if st.button("✅ Valider mon compte", use_container_width=True, key="btn_valider"):
                if not code_saisi.strip():
                    st.warning("⚠️ Veuillez entrer le code reçu.")
                    return

                code_attendu = st.session_state.get("reg_code_temp", "")

                # ── Comparaison du code (session uniquement, pas de DB) ──
                if code_saisi.strip() != code_attendu.strip():
                    st.error("❌ Code incorrect. Vérifiez votre saisie ou demandez un nouveau code.")
                    return

                # ── Code correct → création du compte en base ────────────
                hash_mdp = st.session_state.get("reg_hash_temp", "")
                ip       = st.session_state.get("reg_ip_temp", "0.0.0.0")

                res = creer_utilisateur_verifie(email, hash_mdp, ip)

                if res["succes"]:
                    _effacer_inscription_temp()  # Nettoie le session_state
                    st.success(
                        "🎉 Compte créé et activé avec succès !\n\n"
                        "Vous pouvez maintenant vous connecter."
                    )
                    time.sleep(2)
                    st.rerun()
                else:
                    _afficher_erreur(res.get("erreur", "Erreur lors de la création du compte."))

        with col_b:
            if st.button("🔄 Renvoyer le code", use_container_width=True, key="btn_renvoi"):
                # Génère un nouveau code et le stocke en session (pas en base)
                nouveau_code = generer_code()
                st.session_state["reg_code_temp"] = nouveau_code

                succes_mail, msg_mail = envoyer_code_verification(email, nouveau_code)
                if succes_mail:
                    st.info(f"📬 Nouveau code envoyé à **{email}**.")
                else:
                    st.error(f"❌ Envoi échoué : {msg_mail}")

        st.markdown("---")
        if st.button("← Annuler et revenir", key="btn_annuler_verif"):
            # Supprime TOUTES les données temporaires → aucune trace en base
            _effacer_inscription_temp()
            st.info("Inscription annulée. Aucun compte n'a été créé.")
            time.sleep(1)
            st.rerun()


# ──────────────────────────────────────────────────────────────
# Fonction principale publique
# ──────────────────────────────────────────────────────────────
def afficher_page_auth() -> None:
    """
    Affiche la page d'authentification complète et bloque l'accès
    à l'application via st.stop() tant que l'utilisateur n'est pas connecté.

    Logique d'inscription "verify before save" :
        - Le compte n'est créé en base QUE si le code e-mail est validé.
        - Si l'utilisateur abandonne, aucune donnée n'est persistée.

    Usage dans app.py :
        from auth import afficher_page_auth
        afficher_page_auth()
        # Code exécuté uniquement si connecté
    """
    # Injection du CSS
    st.markdown(_CSS, unsafe_allow_html=True)

    # Initialisation de l'état
    _init_auth_state()

    # Si déjà connecté → ne rien faire
    if st.session_state["auth_connecte"]:
        return

    # ── Étape 2 : écran de vérification du code ────────────────
    if st.session_state.get("auth_en_attente"):
        _ecran_verification()
        st.stop()
        return

    # ── Étape 1 : onglets connexion / inscription ───────────────
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("""
        <div class="auth-card">
            <div class="auth-logo">🔍</div>
            <div class="auth-title">Moteur Sémantique PDF</div>
            <div class="auth-subtitle">Recherche intelligente dans vos documents</div>
        </div>
        """, unsafe_allow_html=True)

        onglet_connexion, onglet_inscription = st.tabs([
            "🔐  Se connecter",
            "✨  Créer un compte",
        ])

        with onglet_connexion:
            _onglet_connexion()

        with onglet_inscription:
            _onglet_inscription()

    # Bloque l'exécution du reste de app.py
    st.stop()
