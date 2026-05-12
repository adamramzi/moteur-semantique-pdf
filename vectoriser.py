"""
vectoriser.py — Embeddings et recherche sémantique
Moteur Sémantique PDF

Utilise l'API HuggingFace Inference (gratuite) pour générer les embeddings.
Compatible Vercel (pas de PyTorch / sentence-transformers).
"""

import os
import pickle
import numpy as np
import requests
import time

# ── Configuration ─────────────────────────────────────────────
HF_API_URL = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-mpnet-base-v2"
HF_API_TOKEN = os.getenv("HF_API_TOKEN", "")

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def _embed_batch(texts, batch_size=32):
    """
    Envoie les textes par batches à l'API HuggingFace via le client officiel.
    """
    token = os.getenv("HF_API_TOKEN", "").strip()
    if not token:
        raise ValueError(
            "Le token d'accès Hugging Face (HF_API_TOKEN) est manquant. "
            "Veuillez ajouter 'HF_API_TOKEN' dans vos variables d'environnement Vercel !"
        )
    
    from huggingface_hub import InferenceClient
    client = InferenceClient(token=token)
    
    all_embeddings = []
    # Le nom exact du modèle
    model_id = "sentence-transformers/all-mpnet-base-v2"

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        
        for attempt in range(MAX_RETRIES):
            try:
                # Le client gère automatiquement le bon endpoint (feature-extraction)
                output = client.feature_extraction(batch, model=model_id)
                # L'output est un objet ou une liste de listes. On le convertit.
                embeddings = np.array(output, dtype=np.float32)
                all_embeddings.append(embeddings)
                break
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
                else:
                    raise Exception(f"Erreur HuggingFace API après retries : {e}")

    if all_embeddings:
        return np.vstack(all_embeddings)
    return np.array([], dtype=np.float32)


def get_model():
    """
    Placeholder pour compatibilité.
    L'embedding est maintenant fait via l'API, pas de modèle local.
    Retourne un objet avec une méthode encode().
    """
    class HFAPIModel:
        def encode(self, texts, convert_to_numpy=True):
            if isinstance(texts, str):
                texts = [texts]
            return _embed_batch(texts)

    return HFAPIModel()


def vectoriser_chunks(chunks):
    """
    Encode les chunks en embeddings numpy via l'API HuggingFace.

    Args:
        chunks: Liste de chaînes de texte.

    Returns:
        numpy array de shape (n_chunks, embedding_dim).
    """
    return _embed_batch(chunks)


def creer_index(vecteurs):
    """
    Retourne simplement les vecteurs numpy (pas besoin de FAISS).
    """
    return vecteurs


def get_user_index_path(user_id: int, base: str = "index_faiss") -> str:
    """
    Retourne le chemin du dossier d'index propre à l'utilisateur.
    Sur Vercel, utilise /tmp pour le stockage temporaire.
    Ex : /tmp/index_faiss/user_42/
    """
    # Sur Vercel, utiliser /tmp (seul dossier writable)
    if os.getenv("VERCEL") or not os.access(".", os.W_OK):
        base = os.path.join("/tmp", base)
    return os.path.join(base, f"user_{user_id}")


def sauvegarder_index(vecteurs, chunks, path="index_faiss"):
    """
    Sauvegarde les vecteurs et les chunks sur le disque avec pickle.
    Le path peut être un dossier utilisateur : index_faiss/user_{id}/
    """
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "vecteurs.pkl"), "wb") as f:
        pickle.dump(vecteurs, f)
    with open(os.path.join(path, "chunks.pkl"), "wb") as f:
        pickle.dump(chunks, f)


def charger_index(path="index_faiss"):
    """
    Charge les vecteurs et chunks depuis le disque.
    Retourne (vecteurs, chunks) ou (None, None) si introuvable.
    Le path peut être un dossier utilisateur : index_faiss/user_{id}/
    """
    vecteurs_path = os.path.join(path, "vecteurs.pkl")
    chunks_path = os.path.join(path, "chunks.pkl")

    if os.path.exists(vecteurs_path) and os.path.exists(chunks_path):
        with open(vecteurs_path, "rb") as f:
            vecteurs = pickle.load(f)
        with open(chunks_path, "rb") as f:
            chunks = pickle.load(f)
        return vecteurs, chunks
    return None, None


def _extraire_texte(chunk):
    """Extrait le texte d'un chunk (dict ou string)."""
    return chunk["texte"] if isinstance(chunk, dict) else chunk


def _enrichir_contexte(idx, chunks):
    """
    Retourne le texte enrichi avec les chunks précédent et suivant.
    chunk_precedent + chunk_actuel + chunk_suivant
    """
    parties = []
    if idx > 0:
        parties.append(_extraire_texte(chunks[idx - 1]))
    parties.append(_extraire_texte(chunks[idx]))
    if idx < len(chunks) - 1:
        parties.append(_extraire_texte(chunks[idx + 1]))
    return " ".join(parties)


def rechercher(query_vector, vecteurs, chunks, top_k=3):
    """
    Calcule la similarité cosinus entre query_vector et tous les vecteurs.
    Retourne les top_k résultats avec texte enrichi (chunk précédent + actuel + suivant).

    Supporte les chunks sous forme de strings simples ou de dicts avec métadonnées.
    """
    # Normalisation
    q_norm = query_vector / (np.linalg.norm(query_vector) + 1e-10)
    v_norms = vecteurs / (np.linalg.norm(vecteurs, axis=1, keepdims=True) + 1e-10)

    # Produit scalaire = similarité cosinus
    scores = np.dot(v_norms, q_norm)

    # Top K indices
    top_indices = np.argsort(scores)[::-1][:top_k]

    resultats = []
    for idx in top_indices:
        resultats.append({
            "score": float(scores[idx]),
            "chunk_index": int(idx),
            "texte": _enrichir_contexte(idx, chunks),
        })
    return resultats


def rechercher_avec_metadata(query_vector, vecteurs, chunks, top_k=3):
    """
    Calcule la similarité cosinus et retourne les résultats avec métadonnées complètes
    et texte enrichi (chunk précédent + actuel + suivant).

    Args:
        query_vector: Vecteur de la requête (numpy array).
        vecteurs:     Matrice des vecteurs de tous les chunks.
        chunks:       Liste de dicts {"texte": ..., "page": ..., "fichier": ...}.
        top_k:        Nombre de résultats à retourner.

    Returns:
        Liste de dicts triée par score décroissant :
            {"texte": str, "score": float, "chunk_index": int, "page": int, "fichier": str}
    """
    # Normalisation
    q_norm = query_vector / (np.linalg.norm(query_vector) + 1e-10)
    v_norms = vecteurs / (np.linalg.norm(vecteurs, axis=1, keepdims=True) + 1e-10)

    # Produit scalaire = similarité cosinus
    scores = np.dot(v_norms, q_norm)

    # Top K indices
    top_indices = np.argsort(scores)[::-1][:top_k]

    resultats = []
    for idx in top_indices:
        chunk = chunks[idx]
        texte_enrichi = _enrichir_contexte(idx, chunks)

        if isinstance(chunk, dict):
            resultats.append({
                "score": float(scores[idx]),
                "chunk_index": int(idx),
                "texte": texte_enrichi,
                "page": chunk.get("page", 0),
                "fichier": chunk.get("fichier", ""),
            })
        else:
            resultats.append({
                "score": float(scores[idx]),
                "chunk_index": int(idx),
                "texte": texte_enrichi,
                "page": 0,
                "fichier": "",
            })
    return resultats
