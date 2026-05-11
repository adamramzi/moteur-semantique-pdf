"""
pdf_processor.py — Extraction de texte et découpage en chunks
Moteur Sémantique PDF

Supporte :
    - Extraction texte classique via PyMuPDF
    - OCR automatique (EasyOCR) pour les PDFs scannés
    - Métadonnées par chunk : texte, page, fichier
"""

import os
import fitz  # PyMuPDF


def extraire_texte(pdf_path):
    """
    Ouvre un fichier PDF avec PyMuPDF, extrait le texte de chaque page
    et retourne une liste de dictionnaires avec métadonnées.

    Si une page ne contient aucun texte, tente l'OCR automatiquement.

    Args:
        pdf_path: Chemin vers le fichier PDF.

    Returns:
        Liste de dict : {"texte": "...", "page": 3, "fichier": "nom.pdf"}
    """
    nom_fichier = os.path.basename(pdf_path)
    doc = fitz.open(pdf_path)
    paragraphes = []
    pages_vides = []  # Pages sans texte détecté (candidates à l'OCR)

    for num_page, page in enumerate(doc, start=1):
        texte_page = ""
        blocs = page.get_text("blocks")
        for b in blocs:
            if b[6] == 0:  # 0 = bloc de texte
                texte = b[4].strip()
                texte = " ".join(texte.split())
                if texte:
                    paragraphes.append({
                        "texte": texte,
                        "page": num_page,
                        "fichier": nom_fichier,
                    })
                    texte_page += texte

        # Si aucun texte détecté sur cette page, la marquer pour OCR
        if not texte_page.strip():
            pages_vides.append(num_page)

    doc.close()

    # Si des pages sont vides, tenter l'OCR
    if pages_vides:
        paragraphes_ocr = extraire_texte_ocr(pdf_path, pages=pages_vides)
        paragraphes.extend(paragraphes_ocr)

    # Trier par numéro de page pour garder l'ordre logique
    paragraphes.sort(key=lambda p: p["page"])

    return paragraphes


def extraire_texte_ocr(pdf_path, pages=None):
    """
    Convertit les pages PDF en images puis applique EasyOCR pour extraire le texte.

    Args:
        pdf_path: Chemin vers le fichier PDF.
        pages:    Liste des numéros de page (1-indexed) à traiter.
                  Si None, traite toutes les pages.

    Returns:
        Liste de dict : {"texte": "...", "page": N, "fichier": "nom.pdf"}
    """
    try:
        import easyocr
    except ImportError:
        # EasyOCR non installé — retourner une liste vide
        return []

    nom_fichier = os.path.basename(pdf_path)
    doc = fitz.open(pdf_path)
    reader = easyocr.Reader(["fr", "en"], gpu=False, verbose=False)
    paragraphes = []

    for num_page, page in enumerate(doc, start=1):
        # Ne traiter que les pages demandées
        if pages is not None and num_page not in pages:
            continue

        # Convertir la page en image (pixmap) haute résolution
        mat = fitz.Matrix(2.0, 2.0)  # Zoom 2× pour meilleure qualité OCR
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")

        # Appliquer EasyOCR sur les bytes de l'image
        resultats = reader.readtext(img_bytes, detail=0)

        texte_complet = " ".join(resultats).strip()
        if texte_complet:
            paragraphes.append({
                "texte": texte_complet,
                "page": num_page,
                "fichier": nom_fichier,
            })

    doc.close()
    return paragraphes


def decouper_chunks(paragraphes_meta, taille=200):
    """
    Prend une liste de dictionnaires avec métadonnées, les regroupe en chunks
    de maximum 'taille' mots, et retourne une liste de dicts enrichis.

    Chaque chunk conserve le numéro de page du premier paragraphe qui le compose.

    Args:
        paragraphes_meta: Liste de dict {"texte": ..., "page": ..., "fichier": ...}
        taille:           Nombre maximum de mots par chunk.

    Returns:
        Liste de dict : {"texte": "...", "page": N, "fichier": "nom.pdf"}
    """
    chunks = []
    chunk_mots = []
    mots_courants = 0
    page_debut = 1
    fichier = ""

    for para in paragraphes_meta:
        texte = para["texte"]
        mots_para = texte.split()

        if not fichier:
            fichier = para.get("fichier", "")
            page_debut = para.get("page", 1)

        # Si ajouter ce paragraphe dépasse la taille max, sauvegarder le chunk
        if mots_courants + len(mots_para) > taille and chunk_mots:
            chunks.append({
                "texte": " ".join(chunk_mots),
                "page": page_debut,
                "fichier": fichier,
            })
            chunk_mots = mots_para
            mots_courants = len(mots_para)
            page_debut = para.get("page", 1)
            fichier = para.get("fichier", "")
        else:
            chunk_mots.extend(mots_para)
            mots_courants += len(mots_para)

    # Ajouter le dernier chunk
    if chunk_mots:
        chunks.append({
            "texte": " ".join(chunk_mots),
            "page": page_debut,
            "fichier": fichier,
        })

    return chunks
