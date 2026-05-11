import os
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer

# Charge le modèle une seule fois — all-mpnet-base-v2 est plus précis que MiniLM
model = SentenceTransformer('all-mpnet-base-v2')


def vectoriser_chunks(chunks):
    """
    Encode les chunks en embeddings numpy et retourne les vecteurs.
    """
    vecteurs = model.encode(chunks, convert_to_numpy=True)
    return vecteurs


def creer_index(vecteurs):
    """
    Retourne simplement les vecteurs numpy (remplace l'index FAISS).
    """
    return vecteurs


def get_user_index_path(user_id: int, base: str = "index_faiss") -> str:
    """
    Retourne le chemin du dossier d'index propre à l'utilisateur.
    Ex : index_faiss/user_42/
    """
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

