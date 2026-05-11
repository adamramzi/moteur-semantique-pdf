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


def decouper_chunks(paragraphes_meta, taille=100, overlap=20):
    """
    Prend une liste de dictionnaires avec métadonnées, les regroupe en chunks
    de maximum 'taille' mots avec un chevauchement de 'overlap' mots.

    Le chevauchement permet de conserver le contexte entre deux chunks consécutifs.
    Exemple : chunk1 = mots 1→100, chunk2 = mots 80→180, chunk3 = mots 160→260

    Chaque chunk conserve le numéro de page du premier mot qui le compose.

    Args:
        paragraphes_meta: Liste de dict {"texte": ..., "page": ..., "fichier": ...}
        taille:           Nombre maximum de mots par chunk (défaut: 100).
        overlap:          Nombre de mots de chevauchement entre chunks (défaut: 20).

    Returns:
        Liste de dict : {"texte": "...", "page": N, "fichier": "nom.pdf"}
    """
    # Construire une liste plate de (mot, page, fichier) pour le sliding window
    mots_avec_meta = []
    for para in paragraphes_meta:
        texte = para["texte"]
        page = para.get("page", 1)
        fichier = para.get("fichier", "")
        for mot in texte.split():
            mots_avec_meta.append((mot, page, fichier))

    if not mots_avec_meta:
        return []

    chunks = []
    pas = max(1, taille - overlap)  # Avancer de (taille - overlap) mots à chaque itération
    i = 0

    while i < len(mots_avec_meta):
        fin = min(i + taille, len(mots_avec_meta))
        fenetre = mots_avec_meta[i:fin]

        texte_chunk = " ".join(m[0] for m in fenetre)
        page_debut = fenetre[0][1]
        fichier = fenetre[0][2]

        chunks.append({
            "texte": texte_chunk,
            "page": page_debut,
            "fichier": fichier,
        })

        # Avancer avec le pas (taille - overlap)
        i += pas

        # Éviter de créer un chunk minuscule à la fin
        if i < len(mots_avec_meta) and len(mots_avec_meta) - i < overlap:
            break

    return chunks

