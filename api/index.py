"""
api/index.py — FastAPI backend pour le Moteur Sémantique PDF
Remplace Streamlit par une API REST + JWT
"""

import os
import sys
import tempfile
import shutil
from datetime import datetime, timedelta
from typing import List, Optional

# Ajouter le dossier parent au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
except ImportError:
    pass

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import jwt

from database import (
    init_db, get_user_id, verifier_utilisateur, email_existe,
    hacher_mot_de_passe, generer_code, creer_utilisateur,
    creer_utilisateur_verifie, valider_email,
    sauvegarder_document, sauvegarder_recherche,
    get_historique_documents, get_historique_recherches,
    supprimer_document, nettoyer_utilisateurs_inactifs,
    get_ip_utilisateur,
)
from email_service import envoyer_code_verification
from document_processor import extraire_texte, decouper_chunks
from vectoriser import (
    vectoriser_chunks, creer_index, sauvegarder_index, charger_index,
    rechercher_avec_metadata, get_user_index_path, get_model,
)

# ── Configuration ────────────────────────────────────────────
JWT_SECRET = os.getenv("JWT_SECRET", "moteur_pdf_jwt_secret_2026!")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24
INDEX_BASE = "/tmp/index_faiss" if (os.getenv("VERCEL") or not os.access(".", os.W_OK)) else "index_faiss"
TOP_K = 3

# ── App FastAPI ──────────────────────────────────────────────
app = FastAPI(title="Moteur Sémantique Multidocument", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Init DB au démarrage
init_db()
nettoyer_utilisateurs_inactifs(jours=30)


# ── Modèles Pydantic ────────────────────────────────────────
class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str

class VerifyRequest(BaseModel):
    email: str
    code: str

class ResendRequest(BaseModel):
    email: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    email: str
    code: str
    new_password: str

class SearchRequest(BaseModel):
    query: str
    pdf_name: Optional[str] = None


# ── Utilitaires JWT ─────────────────────────────────────────
def create_token(email: str) -> str:
    payload = {
        "email": email,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(request: Request) -> dict:
    """Extrait et vérifie le JWT depuis le header Authorization."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token manquant")
    token = auth_header.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        email = payload.get("email")
        if not email:
            raise HTTPException(status_code=401, detail="Token invalide")
        user_id = get_user_id(email)
        if not user_id:
            raise HTTPException(status_code=401, detail="Utilisateur introuvable")
        return {"email": email, "user_id": user_id}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expiré")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token invalide")


# ── Routes Auth ─────────────────────────────────────────────
@app.post("/api/auth/login")
async def login(data: LoginRequest):
    email_cleaned = data.email.strip().lower()
    success, result = verifier_utilisateur(email_cleaned, data.password)
    if success:
        token = create_token(email_cleaned)
        return {"token": token, "email": email_cleaned}
    raise HTTPException(status_code=401, detail=result)


@app.post("/api/auth/register")
async def register(data: RegisterRequest, request: Request):
    email = data.email.strip().lower()
    password = data.password

    if not email or "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Adresse e-mail invalide.")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Le mot de passe doit contenir au moins 6 caractères.")
    if email_existe(email):
        raise HTTPException(status_code=409, detail="❌ Un compte existe déjà avec cette adresse email. Veuillez vous connecter ou utiliser une autre adresse.")

    ip = get_ip_utilisateur(request)
    res = creer_utilisateur(email, password, ip)
    if not res["succes"]:
        raise HTTPException(status_code=400, detail=res.get("erreur", "Erreur"))

    code = res["code_verification"]
    succes_mail, msg = envoyer_code_verification(email, code)
    if not succes_mail:
        return {"message": f"Compte créé mais l'envoi de l'e-mail a échoué : {msg}", "email": email}

    return {"message": f"Code de vérification envoyé à {email}", "email": email}


@app.post("/api/auth/verify")
async def verify(data: VerifyRequest):
    res = valider_email(data.email.strip().lower(), data.code.strip())
    if res["succes"]:
        return {"message": res.get("message", "Compte vérifié avec succès.")}
    raise HTTPException(status_code=400, detail=res.get("erreur", "Code incorrect"))


@app.post("/api/auth/resend")
async def resend(data: ResendRequest):
    from database import reinitialiser_code
    email = data.email.strip().lower()
    res = reinitialiser_code(email)
    if not res["succes"]:
        raise HTTPException(status_code=400, detail=res.get("erreur", "Erreur"))

    code = res["code_verification"]
    succes_mail, msg = envoyer_code_verification(email, code)
    if succes_mail:
        return {"message": f"Nouveau code envoyé à {email}"}
    raise HTTPException(status_code=500, detail=f"Envoi échoué : {msg}")


@app.post("/api/auth/forgot-password")
async def forgot_password(data: ForgotPasswordRequest):
    from database import generer_code_oubli_mdp
    from email_service import envoyer_email_reinitialisation

    email = data.email.strip().lower()
    if not email_existe(email):
        raise HTTPException(status_code=404, detail="❌ Aucun compte trouvé avec cette adresse email")

    res = generer_code_oubli_mdp(email)
    if not res["succes"]:
        raise HTTPException(status_code=400, detail=res.get("erreur", "Erreur lors de la génération du code"))

    code = res["code_verification"]
    succes_mail, msg = envoyer_email_reinitialisation(email, code)
    if not succes_mail:
        raise HTTPException(status_code=500, detail=f"L'envoi de l'e-mail a échoué : {msg}")

    return {"message": "✅ Un code de réinitialisation a été envoyé à votre email"}


@app.post("/api/auth/reset-password")
async def reset_password(data: ResetPasswordRequest):
    from database import valider_code_oubli_mdp, modifier_mot_de_passe

    email = data.email.strip().lower()
    code = data.code.strip()
    new_password = data.new_password

    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Le mot de passe doit contenir au moins 6 caractères.")

    res_verif = valider_code_oubli_mdp(email, code)
    if not res_verif["succes"]:
        raise HTTPException(status_code=400, detail=res_verif.get("erreur", "Code incorrect, réessayez"))

    res_mod = modifier_mot_de_passe(email, new_password)
    if not res_mod["succes"]:
        raise HTTPException(status_code=400, detail=res_mod.get("erreur", "Erreur lors de la modification"))

    return {"message": "✅ Mot de passe modifié avec succès ! Vous pouvez maintenant vous connecter."}



@app.get("/api/auth/me")
async def me(request: Request):
    user = get_current_user(request)
    return {"email": user["email"], "user_id": user["user_id"]}


# ── Routes Documents ────────────────────────────────────────
@app.post("/api/upload")
async def upload_files(request: Request, files: List[UploadFile] = File(...)):
    user = get_current_user(request)
    user_id = user["user_id"]
    index_dir = get_user_index_path(user_id, INDEX_BASE)

    # Charger l'index existant
    vecteurs_existants, chunks_existants = charger_index(index_dir)
    chunks_par_fichier = {}
    if chunks_existants:
        for c in chunks_existants:
            if isinstance(c, dict):
                fname = c.get("fichier", "unknown")
                chunks_par_fichier.setdefault(fname, []).append(c)

    nouveaux_docs = 0
    for uploaded_file in files:
        if uploaded_file.filename in chunks_par_fichier:
            continue  # Déjà indexé

        ext = os.path.splitext(uploaded_file.filename)[1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            content = await uploaded_file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            paragraphes = extraire_texte(tmp_path)
            if not paragraphes:
                continue
            
            # Correction du nom de fichier interne si nécessaire pour le chunks
            for p in paragraphes:
                p["fichier"] = uploaded_file.filename
                
            chunks = decouper_chunks(paragraphes)
            chunks_par_fichier[uploaded_file.filename] = chunks
            
            # type_fichier est l'extension sans le point, majuscule (PDF, DOCX, etc)
            type_fichier = ext.replace(".", "").upper()
            sauvegarder_document(user_id, uploaded_file.filename, len(chunks), type_fichier=type_fichier)
            nouveaux_docs += 1
        finally:
            os.unlink(tmp_path)

    # Reconstruire l'index complet
    all_chunks = [c for cl in chunks_par_fichier.values() for c in cl]
    all_textes = [c["texte"] if isinstance(c, dict) else c for c in all_chunks]

    if not all_chunks:
        raise HTTPException(status_code=400, detail="Impossible de lire le texte des fichiers uploadés.")

    vecteurs = vectoriser_chunks(all_textes)
    vecteurs = creer_index(vecteurs)
    sauvegarder_index(vecteurs, all_chunks, path=index_dir)

    return {
        "message": f"{len(all_chunks)} passages enregistrés depuis {len(chunks_par_fichier)} fichier(s).",
        "nb_pdfs": len(chunks_par_fichier),
        "nb_passages": len(all_chunks),
        "nouveaux": nouveaux_pdfs,
    }


@app.get("/api/documents")
async def get_documents(request: Request):
    user = get_current_user(request)
    docs = get_historique_documents(user["user_id"])
    return {"documents": docs}


@app.delete("/api/documents/{filename}")
async def delete_document(filename: str, request: Request):
    user = get_current_user(request)
    user_id = user["user_id"]
    index_dir = get_user_index_path(user_id, INDEX_BASE)

    supprimer_document(user_id, filename)

    # Recharger et reconstruire l'index sans ce fichier
    vecteurs_old, chunks_old = charger_index(index_dir)
    if chunks_old:
        remaining = [c for c in chunks_old if isinstance(c, dict) and c.get("fichier") != filename]
        if remaining:
            textes = [c["texte"] if isinstance(c, dict) else c for c in remaining]
            new_vecteurs = creer_index(vectoriser_chunks(textes))
            sauvegarder_index(new_vecteurs, remaining, path=index_dir)
        else:
            if os.path.exists(index_dir):
                shutil.rmtree(index_dir)
    return {"message": f"'{filename}' supprimé avec succès."}


@app.post("/api/reset")
async def reset_all(request: Request):
    user = get_current_user(request)
    user_id = user["user_id"]
    index_dir = get_user_index_path(user_id, INDEX_BASE)

    docs = get_historique_documents(user_id)
    for doc in docs:
        supprimer_document(user_id, doc["nom_fichier"])

    if os.path.exists(index_dir):
        shutil.rmtree(index_dir)

    return {"message": "Tous vos documents ont été supprimés."}


# ── Routes Recherche ────────────────────────────────────────
@app.post("/api/search")
async def search(data: SearchRequest, request: Request):
    user = get_current_user(request)
    user_id = user["user_id"]
    index_dir = get_user_index_path(user_id, INDEX_BASE)

    vecteurs, chunks = charger_index(index_dir)
    if vecteurs is None or chunks is None:
        raise HTTPException(status_code=400, detail="Aucun document indexé. Uploadez d'abord un PDF.")

    query = data.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Veuillez saisir une question.")

    model = get_model()
    query_vector = model.encode([query])[0]
    resultats = rechercher_avec_metadata(query_vector, vecteurs, chunks, top_k=TOP_K)

    # Sauvegarder la recherche
    nom_pdf = data.pdf_name or "document"
    if resultats:
        meilleur = resultats[0]
        sauvegarder_recherche(user_id, nom_pdf, query, meilleur["texte"], meilleur["score"])

    return {"resultats": resultats, "question": query}


@app.get("/api/search/history/{filename}")
async def search_history(filename: str, request: Request):
    user = get_current_user(request)
    recherches = get_historique_recherches(user["user_id"], filename)
    return {"recherches": recherches}


@app.get("/api/stats")
async def stats(request: Request):
    user = get_current_user(request)
    user_id = user["user_id"]
    index_dir = get_user_index_path(user_id, INDEX_BASE)

    docs = get_historique_documents(user_id)
    _, chunks = charger_index(index_dir)
    nb_passages = len(chunks) if chunks else 0

    total_recherches = 0
    for doc in docs:
        recherches = get_historique_recherches(user_id, doc["nom_fichier"])
        total_recherches += len(recherches)

    return {
        "nb_pdfs": len(docs),
        "nb_passages": nb_passages,
        "nb_recherches": total_recherches,
    }


# ── Servir le frontend (dev local) ─────────────────────────
PUBLIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")

@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(PUBLIC_DIR, "index.html"))

@app.get("/{filepath:path}")
async def serve_static(filepath: str):
    full_path = os.path.join(PUBLIC_DIR, filepath)
    if os.path.isfile(full_path):
        return FileResponse(full_path)
    return FileResponse(os.path.join(PUBLIC_DIR, "index.html"))
