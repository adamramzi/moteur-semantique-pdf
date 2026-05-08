import fitz  # PyMuPDF

def extraire_texte(pdf_path):
    """
    Ouvre un fichier PDF avec PyMuPDF, extrait le texte de chaque page
    et retourne une liste de paragraphes non vides.
    """
    doc = fitz.open(pdf_path)
    paragraphes = []
    
    for page in doc:
        # On utilise "blocks" pour récupérer les blocs de texte distincts (paragraphes)
        blocs = page.get_text("blocks")
        for b in blocs:
            if b[6] == 0:  # 0 signifie que c'est un bloc de texte
                # Nettoyage du texte (suppression des sauts de ligne à l'intérieur du bloc)
                texte = b[4].strip()
                texte = " ".join(texte.split())
                if texte:
                    paragraphes.append(texte)
                    
    doc.close()
    return paragraphes

def decouper_chunks(texte_liste, taille=200):
    """
    Prend la liste de paragraphes, les regroupe en chunks de maximum 'taille' mots,
    et retourne une liste de chunks.
    """
    chunks = []
    chunk_courant = []
    mots_courants = 0
    
    for para in texte_liste:
        mots_para = para.split()
        # Si ajouter ce paragraphe dépasse la taille max, on sauvegarde le chunk courant
        if mots_courants + len(mots_para) > taille and chunk_courant:
            chunks.append(" ".join(chunk_courant))
            chunk_courant = mots_para
            mots_courants = len(mots_para)
        else:
            chunk_courant.extend(mots_para)
            mots_courants += len(mots_para)
            
    # Ajouter le dernier chunk s'il n'est pas vide
    if chunk_courant:
        chunks.append(" ".join(chunk_courant))
        
    return chunks
