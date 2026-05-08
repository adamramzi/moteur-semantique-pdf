import os
import fitz
from pdf_processor import extraire_texte, decouper_chunks
from vectoriser import vectoriser_chunks, creer_index, sauvegarder_index

def creer_pdf_test(pdf_path):
    """Créer un PDF de test si aucun n'est fourni ou n'existe."""
    doc = fitz.open()
    page = doc.new_page()
    texte = (
        "L'intelligence artificielle générative transforme notre façon de travailler.\n\n"
        "Elle nous permet de créer des moteurs de recherche sémantiques capables de comprendre le sens des phrases. "
        "Les modèles de langage comme MiniLM encodent le texte en vecteurs mathématiques appelés embeddings. "
        "Ensuite, des bibliothèques telles que FAISS permettent de chercher rapidement les vecteurs les plus similaires.\n\n"
        "Le pipeline complet comprend généralement l'extraction du texte, le découpage en blocs (chunks), "
        "la vectorisation, et l'indexation. Une fois tout sauvegardé, on peut faire des recherches très rapides."
    )
    # Insérer le texte
    page.insert_text(fitz.Point(50, 50), texte)
    doc.save(pdf_path)
    doc.close()

def main():
    pdf_test_path = "document_test.pdf"
    
    print(f"--- Lancement du Test Pipeline ---")
    
    if not os.path.exists(pdf_test_path):
        print(f"Création d'un PDF de test local : {pdf_test_path}...")
        creer_pdf_test(pdf_test_path)
    else:
        print(f"Utilisation du PDF existant : {pdf_test_path}")

    print("\n1. Extraction du texte...")
    paragraphes = extraire_texte(pdf_test_path)
    print(f"   -> {len(paragraphes)} paragraphes extraits.")

    print("\n2. Découpage en chunks...")
    # On choisit une taille de 30 mots pour le test pour forcer la création de plusieurs chunks
    chunks = decouper_chunks(paragraphes, taille=30)
    print(f"   -> {len(chunks)} chunks créés.")
    
    print("\n3. Vectorisation des chunks...")
    vecteurs = vectoriser_chunks(chunks)
    print(f"   -> Vecteurs créés avec la dimension : {vecteurs.shape}")

    print("\n4. Création de l'index FAISS...")
    index = creer_index(vecteurs)
    print(f"   -> Index créé avec {index.ntotal} éléments (chunks).")

    print("\n5. Sauvegarde de l'index...")
    sauvegarder_index(index, chunks, path="index_faiss")
    
    # Vérification
    if os.path.exists("index_faiss/index.faiss") and os.path.exists("index_faiss/chunks.pkl"):
        print("\n✅ Succès ! L'index et les chunks ont bien été sauvegardés dans le dossier 'index_faiss'.")
    else:
        print("\n❌ Erreur lors de la sauvegarde.")

if __name__ == "__main__":
    main()
