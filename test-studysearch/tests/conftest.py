import pytest
import os

@pytest.fixture
def dummy_pdf(tmp_path):
    """
    Fixture globale pour générer un faux fichier PDF temporaire.
    Retourne le chemin absolu du fichier sous forme de string.
    """
    pdf_dir = tmp_path / "documents"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = pdf_dir / "dummy_document.pdf"
    
    # Écriture d'un contenu PDF factice simple
    pdf_path.write_bytes(b"%PDF-1.4\n%dummy content")
    
    return str(pdf_path.resolve())

@pytest.fixture
def dummy_invalid_file(tmp_path):
    """
    Fixture globale pour générer un faux fichier texte invalide temporaire.
    Retourne le chemin absolu du fichier sous forme de string.
    """
    invalid_dir = tmp_path / "invalid"
    invalid_dir.mkdir(parents=True, exist_ok=True)
    file_path = invalid_dir / "dummy_invalid.txt"
    
    # Écriture d'un contenu texte simple
    file_path.write_text("Ceci est un fichier texte invalide pour les tests d'extension de document.", encoding="utf-8")
    
    return str(file_path.resolve())
