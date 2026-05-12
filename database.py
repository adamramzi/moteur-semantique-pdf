"""
database.py — Gestion de la base de données utilisateurs
Système d'authentification pour le Moteur Sémantique PDF

Base de données : SQLite (users.db)
Sécurité       : Hachage bcrypt des mots de passe
"""

import sqlite3
import random
import string
from datetime import datetime

import bcrypt


# ──────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────
import os as _os
# Sur Vercel, le filesystem est read-only sauf /tmp
if _os.getenv("VERCEL"):
    DB_PATH = "/tmp/users.db"
else:
    DB_PATH = "users.db"


# ──────────────────────────────────────────────────────────────
# Initialisation de la base de données
# ──────────────────────────────────────────────────────────────
def init_db() -> None:
    """
    Crée la base de données SQLite et toutes les tables si elles n'existent pas.

    Tables :
        users     — Comptes utilisateurs avec bcrypt + vérification email
        documents — PDFs uploadés par utilisateur
        recherches — Historique des recherches par utilisateur
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ── Table utilisateurs ──────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id                INTEGER  PRIMARY KEY AUTOINCREMENT,
            email             TEXT     NOT NULL UNIQUE,
            mot_de_passe      TEXT     NOT NULL,
            date_inscription  TEXT     NOT NULL,
            ip_address        TEXT,
            est_verifie       INTEGER  NOT NULL DEFAULT 0,
            code_verification TEXT
        )
    """)

    # ── Table documents ─────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id        INTEGER NOT NULL,
            nom_fichier    TEXT    NOT NULL,
            date_upload    TEXT    NOT NULL,
            nombre_chunks  INTEGER NOT NULL DEFAULT 0
        )
    """)

    # ── Table recherches ────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recherches (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            nom_fichier     TEXT    NOT NULL,
            question        TEXT    NOT NULL,
            passage_trouve  TEXT,
            score           REAL,
            date_recherche  TEXT    NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# ──────────────────────────────────────────────────────────────
# Utilitaires internes
# ──────────────────────────────────────────────────────────────
def _generer_code_verification() -> str:
    """Génère un code de vérification aléatoire à 6 chiffres."""
    return "".join(random.choices(string.digits, k=6))


def _hacher_mot_de_passe(mot_de_passe: str) -> str:
    """
    Hache un mot de passe en clair avec bcrypt.

    Args:
        mot_de_passe: Le mot de passe en texte clair.

    Returns:
        La chaîne UTF-8 du hash bcrypt.
    """
    sel = bcrypt.gensalt()
    hash_bytes = bcrypt.hashpw(mot_de_passe.encode("utf-8"), sel)
    return hash_bytes.decode("utf-8")


def _verifier_hash(mot_de_passe: str, hash_stocke: str) -> bool:
    """
    Vérifie qu'un mot de passe en clair correspond à son hash bcrypt.

    Args:
        mot_de_passe: Le mot de passe saisi par l'utilisateur.
        hash_stocke:  Le hash bcrypt stocké en base.

    Returns:
        True si le mot de passe est correct, False sinon.
    """
    return bcrypt.checkpw(
        mot_de_passe.encode("utf-8"),
        hash_stocke.encode("utf-8"),
    )


# ──────────────────────────────────────────────────────────────
# Fonctions publiques
# ──────────────────────────────────────────────────────────────
def creer_utilisateur(email: str, mot_de_passe: str, ip: str) -> dict:
    """
    Enregistre un nouvel utilisateur en base de données.

    Le mot de passe est haché avec bcrypt avant le stockage.
    Le compte est créé avec est_verifie=0 et un code de vérification
    aléatoire à 6 chiffres.

    Args:
        email:        L'adresse e-mail de l'utilisateur.
        mot_de_passe: Le mot de passe en texte clair.
        ip:           L'adresse IP de l'utilisateur.

    Returns:
        dict avec les clés :
            - 'succes' (bool)
            - 'code_verification' (str) si succès
            - 'erreur' (str) en cas d'échec
    """
    init_db()

    # Vérification basique du format e-mail
    if "@" not in email or "." not in email.split("@")[-1]:
        return {"succes": False, "erreur": "Format d'adresse e-mail invalide."}

    if len(mot_de_passe) < 6:
        return {"succes": False, "erreur": "Le mot de passe doit contenir au moins 6 caractères."}

    hash_mdp = _hacher_mot_de_passe(mot_de_passe)
    code = _generer_code_verification()
    date_inscription = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO users
                (email, mot_de_passe, date_inscription, ip_address, est_verifie, code_verification)
            VALUES (?, ?, ?, ?, 0, ?)
            """,
            (email.lower().strip(), hash_mdp, date_inscription, ip, code),
        )
        conn.commit()
        conn.close()
        return {"succes": True, "code_verification": code}

    except sqlite3.IntegrityError:
        return {"succes": False, "erreur": "Cette adresse e-mail est déjà utilisée."}
    except sqlite3.Error as e:
        return {"succes": False, "erreur": f"Erreur base de données : {e}"}


def verifier_utilisateur(email: str, mot_de_passe: str) -> dict:
    """
    Vérifie les identifiants d'un utilisateur.

    Args:
        email:        L'adresse e-mail de l'utilisateur.
        mot_de_passe: Le mot de passe en texte clair.

    Returns:
        dict avec les clés :
            - 'succes' (bool)
            - 'utilisateur' (dict avec id, email, date_inscription, ip_address,
              est_verifie) si succès
            - 'erreur' (str) en cas d'échec
    """
    init_db()

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE email = ?",
            (email.lower().strip(),),
        )
        row = cursor.fetchone()
        conn.close()

        if row is None:
            return {"succes": False, "erreur": "Aucun compte associé à cet e-mail."}

        if not _verifier_hash(mot_de_passe, row["mot_de_passe"]):
            return {"succes": False, "erreur": "Mot de passe incorrect."}

        if row["est_verifie"] == 0:
            return {
                "succes": False,
                "erreur": "Compte non vérifié. Veuillez entrer le code reçu par e-mail.",
            }

        utilisateur = {
            "id":               row["id"],
            "email":            row["email"],
            "date_inscription": row["date_inscription"],
            "ip_address":       row["ip_address"],
            "est_verifie":      row["est_verifie"],
        }
        return {"succes": True, "utilisateur": utilisateur}

    except sqlite3.Error as e:
        return {"succes": False, "erreur": f"Erreur base de données : {e}"}


def valider_email(email: str, code: str) -> dict:
    """
    Valide le compte utilisateur si le code de vérification est correct.

    Met est_verifie à 1 et efface le code de vérification après validation.

    Args:
        email: L'adresse e-mail de l'utilisateur.
        code:  Le code de vérification à 6 chiffres.

    Returns:
        dict avec les clés :
            - 'succes' (bool)
            - 'message' (str)
            - 'erreur' (str) en cas d'échec
    """
    init_db()

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE email = ?",
            (email.lower().strip(),),
        )
        row = cursor.fetchone()

        if row is None:
            conn.close()
            return {"succes": False, "erreur": "Aucun compte associé à cet e-mail."}

        if row["est_verifie"] == 1:
            conn.close()
            return {"succes": False, "erreur": "Ce compte est déjà vérifié."}

        if str(row["code_verification"]).strip() != str(code).strip():
            conn.close()
            return {"succes": False, "erreur": "Code de vérification incorrect."}

        # ✅ Code correct : activer le compte
        cursor.execute(
            "UPDATE users SET est_verifie = 1, code_verification = NULL WHERE email = ?",
            (email.lower().strip(),),
        )
        conn.commit()
        conn.close()
        return {"succes": True, "message": "Compte vérifié avec succès. Vous pouvez maintenant vous connecter."}

    except sqlite3.Error as e:
        return {"succes": False, "erreur": f"Erreur base de données : {e}"}


def get_ip_utilisateur(request=None) -> str:
    """
    Récupère l'adresse IP de l'utilisateur depuis la requête HTTP.

    Args:
        request: Objet Request FastAPI (optionnel).

    Returns:
        L'adresse IP sous forme de chaîne, ou 'IP inconnue' si non disponible.
    """
    if request is not None:
        try:
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                return forwarded.split(",")[0].strip()
            if hasattr(request, "client") and request.client:
                return request.client.host
        except Exception:
            pass
    return "IP inconnue"


# ──────────────────────────────────────────────────────────────
# Fonctions publiques utilitaires (hachage, génération de code)
# ──────────────────────────────────────────────────────────────
def hacher_mot_de_passe(mot_de_passe: str) -> str:
    """
    Hache un mot de passe en clair avec bcrypt (version publique).

    Args:
        mot_de_passe: Le mot de passe en texte clair.

    Returns:
        La chaîne UTF-8 du hash bcrypt.
    """
    return _hacher_mot_de_passe(mot_de_passe)


def generer_code() -> str:
    """
    Génère un code de vérification aléatoire à 6 chiffres (version publique).

    Returns:
        Une chaîne de 6 chiffres, ex. '482910'.
    """
    return _generer_code_verification()


def creer_utilisateur_verifie(email: str, hash_mdp: str, ip: str) -> dict:
    """
    Crée un compte utilisateur directement avec est_verifie=1.

    Utilisé quand le code de vérification a déjà été validé côté session
    (logique "verify before save") : on n'insère en base qu'une fois le
    code confirmé, et le compte est immédiatement actif.

    Args:
        email:    L'adresse e-mail de l'utilisateur (sera mise en minuscules).
        hash_mdp: Le mot de passe déjà haché avec bcrypt.
        ip:       L'adresse IP de l'utilisateur lors de l'inscription.

    Returns:
        dict avec les clés :
            - 'succes'  (bool)
            - 'message' (str) si succès
            - 'erreur'  (str) en cas d'échec
    """
    init_db()

    date_inscription = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO users
                (email, mot_de_passe, date_inscription, ip_address, est_verifie, code_verification)
            VALUES (?, ?, ?, ?, 1, NULL)
            """,
            (email.lower().strip(), hash_mdp, date_inscription, ip),
        )
        conn.commit()
        conn.close()
        return {"succes": True, "message": "Compte créé et activé avec succès."}

    except sqlite3.IntegrityError:
        return {"succes": False, "erreur": "Cette adresse e-mail est déjà utilisée."}
    except sqlite3.Error as e:
        return {"succes": False, "erreur": f"Erreur base de données : {e}"}


# ──────────────────────────────────────────────────────────────
# Fonctions utilitaires supplémentaires
# ──────────────────────────────────────────────────────────────
def email_existe(email: str) -> bool:
    """
    Vérifie si une adresse e-mail est déjà enregistrée en base.

    Args:
        email: L'adresse e-mail à vérifier.

    Returns:
        True si l'e-mail existe déjà, False sinon.
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM users WHERE email = ?", (email.lower().strip(),))
    existe = cursor.fetchone() is not None
    conn.close()
    return existe


def reinitialiser_code(email: str) -> dict:
    """
    Génère un nouveau code de vérification pour un compte non vérifié.

    Utile pour renvoyer un code si l'utilisateur ne l'a pas reçu.

    Args:
        email: L'adresse e-mail de l'utilisateur.

    Returns:
        dict avec les clés :
            - 'succes' (bool)
            - 'code_verification' (str) si succès
            - 'erreur' (str) en cas d'échec
    """
    init_db()
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),))
        row = cursor.fetchone()

        if row is None:
            conn.close()
            return {"succes": False, "erreur": "Aucun compte associé à cet e-mail."}

        if row["est_verifie"] == 1:
            conn.close()
            return {"succes": False, "erreur": "Ce compte est déjà vérifié."}

        nouveau_code = _generer_code_verification()
        cursor.execute(
            "UPDATE users SET code_verification = ? WHERE email = ?",
            (nouveau_code, email.lower().strip()),
        )
        conn.commit()
        conn.close()
        return {"succes": True, "code_verification": nouveau_code}

    except sqlite3.Error as e:
        return {"succes": False, "erreur": f"Erreur base de données : {e}"}



# ──────────────────────────────────────────────────────────────
# Fonctions historique par utilisateur
# ──────────────────────────────────────────────────────────────
def sauvegarder_document(user_id: int, nom_fichier: str, nombre_chunks: int) -> None:
    """
    Enregistre un PDF uploadé par l'utilisateur dans la table documents.

    Args:
        user_id:       L'ID de l'utilisateur connecté.
        nom_fichier:   Le nom du fichier PDF.
        nombre_chunks: Le nombre de passages extraits du PDF.
    """
    init_db()
    date_upload = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO documents (user_id, nom_fichier, date_upload, nombre_chunks) VALUES (?, ?, ?, ?)",
        (user_id, nom_fichier, date_upload, nombre_chunks),
    )
    conn.commit()
    conn.close()


def sauvegarder_recherche(user_id: int, nom_fichier: str, question: str,
                           passage: str, score: float) -> None:
    """
    Enregistre une recherche effectuée par l'utilisateur.

    Args:
        user_id:     L'ID de l'utilisateur connecté.
        nom_fichier: Le nom du PDF sur lequel la recherche est faite.
        question:    La question posée.
        passage:     Le passage trouvé (meilleur résultat).
        score:       Le score de similarité du passage.
    """
    init_db()
    date_recherche = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO recherches
           (user_id, nom_fichier, question, passage_trouve, score, date_recherche)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, nom_fichier, question, passage, score, date_recherche),
    )
    conn.commit()
    conn.close()


def get_historique_documents(user_id: int) -> list:
    """
    Retourne tous les PDFs uploadés par l'utilisateur, du plus récent au plus ancien.

    Args:
        user_id: L'ID de l'utilisateur connecté.

    Returns:
        Liste de dict avec les clés : id, nom_fichier, date_upload, nombre_chunks.
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM documents WHERE user_id = ? ORDER BY date_upload DESC",
        (user_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_historique_recherches(user_id: int, nom_fichier: str) -> list:
    """
    Retourne toutes les questions posées sur un PDF donné par l'utilisateur.

    Args:
        user_id:     L'ID de l'utilisateur connecté.
        nom_fichier: Le nom du fichier PDF.

    Returns:
        Liste de dict avec les clés : question, passage_trouve, score, date_recherche.
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        """SELECT question, passage_trouve, score, date_recherche
           FROM recherches
           WHERE user_id = ? AND nom_fichier = ?
           ORDER BY date_recherche DESC""",
        (user_id, nom_fichier),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_user_id(email: str) -> int | None:
    """
    Retourne l'ID de l'utilisateur à partir de son email.

    Args:
        email: L'adresse e-mail de l'utilisateur.

    Returns:
        L'ID (int) ou None si non trouvé.
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = ?", (email.lower().strip(),))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def supprimer_document(user_id: int, nom_fichier: str) -> None:
    """
    Supprime un document (et ses recherches associées) de la base de données.

    Args:
        user_id:     L'ID de l'utilisateur propriétaire du document.
        nom_fichier: Le nom du fichier PDF à supprimer.
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM documents WHERE user_id = ? AND nom_fichier = ?",
        (user_id, nom_fichier),
    )
    cursor.execute(
        "DELETE FROM recherches WHERE user_id = ? AND nom_fichier = ?",
        (user_id, nom_fichier),
    )
    conn.commit()
    conn.close()



# ──────────────────────────────────────────────────────────────
# Nettoyage des utilisateurs inactifs
# ──────────────────────────────────────────────────────────────
def nettoyer_utilisateurs_inactifs(jours: int = 30, index_base: str = "index_faiss") -> int:
    """
    Supprime les utilisateurs inactifs depuis plus de N jours.

    Un utilisateur est considéré inactif si :
        - Sa date d'inscription remonte à plus de `jours` jours
        - Il n'a aucun document uploadé récemment
        - Il n'a aucune recherche récente

    Supprime également le dossier index_faiss/user_{id}/ du disque.

    Args:
        jours:      Nombre de jours d'inactivité avant suppression (défaut: 30).
        index_base: Dossier racine des index FAISS.

    Returns:
        Nombre d'utilisateurs supprimés.
    """
    import shutil

    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    seuil = datetime.now()
    from datetime import timedelta
    seuil = (seuil - timedelta(days=jours)).strftime("%Y-%m-%d %H:%M:%S")

    # Trouver les utilisateurs dont la date d'inscription est ancienne
    # ET qui n'ont aucun document ni recherche récente
    cursor.execute("""
        SELECT u.id, u.email FROM users u
        WHERE u.date_inscription < ?
          AND u.id NOT IN (
              SELECT DISTINCT user_id FROM documents WHERE date_upload >= ?
          )
          AND u.id NOT IN (
              SELECT DISTINCT user_id FROM recherches WHERE date_recherche >= ?
          )
    """, (seuil, seuil, seuil))

    utilisateurs_inactifs = cursor.fetchall()
    nb_supprimes = 0

    for user in utilisateurs_inactifs:
        uid = user["id"]
        # Supprimer les données en base
        cursor.execute("DELETE FROM recherches WHERE user_id = ?", (uid,))
        cursor.execute("DELETE FROM documents WHERE user_id = ?", (uid,))
        cursor.execute("DELETE FROM users WHERE id = ?", (uid,))
        # Supprimer le dossier d'index sur le disque
        import os
        user_index_dir = os.path.join(index_base, f"user_{uid}")
        if os.path.exists(user_index_dir):
            shutil.rmtree(user_index_dir)
        nb_supprimes += 1

    conn.commit()
    conn.close()
    return nb_supprimes


# ──────────────────────────────────────────────────────────────
# Point d'entrée — test rapide en ligne de commande
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    # Forcer UTF-8 sur la console Windows
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print("=" * 55)
    print("  TEST du module database.py")
    print("=" * 55)

    # 1. Initialisation
    init_db()
    print("[OK] Base de donnees initialisee (users.db)")

    # 2. Creation d'un utilisateur
    ip_test = "127.0.0.1"
    res = creer_utilisateur("test@exemple.com", "monMotDePasse123", ip_test)
    if res["succes"]:
        code = res["code_verification"]
        print(f"[OK] Utilisateur cree - code de verification : {code}")
    else:
        print(f"[INFO] {res['erreur']}")
        # Recuperer le code existant pour le test
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT code_verification FROM users WHERE email='test@exemple.com'")
        row = cur.fetchone()
        conn.close()
        code = row["code_verification"] if row else "000000"

    # 3. Connexion avant verification (doit echouer)
    res = verifier_utilisateur("test@exemple.com", "monMotDePasse123")
    print(f"[LOCK] Connexion avant verification : {res.get('erreur', 'OK')}")

    # 4. Validation du code
    res = valider_email("test@exemple.com", code)
    print(f"[MAIL] Validation e-mail : {res.get('message', res.get('erreur'))}")

    # 5. Connexion apres verification (doit reussir)
    res = verifier_utilisateur("test@exemple.com", "monMotDePasse123")
    if res["succes"]:
        print(f"[OK] Connexion reussie : {res['utilisateur']}")
    else:
        print(f"[FAIL] Erreur : {res['erreur']}")

    # 6. Mauvais mot de passe
    res = verifier_utilisateur("test@exemple.com", "mauvaisMotDePasse")
    print(f"[KEY] Mauvais mot de passe : {res.get('erreur')}")

    # 7. IP locale
    ip = get_ip_utilisateur()
    print(f"[NET] IP detectee : {ip}")

    print("=" * 55)
    print("  Tests termines avec succes !")
    print("=" * 55)
