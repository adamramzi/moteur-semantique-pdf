import pytest
from fpdf import FPDF

@pytest.fixture
def dummy_pdf(tmp_path):
    """Crée un VRAI fichier PDF temporaire valide pour les tests RAG"""
    file_path = tmp_path / "dummy_document.pdf"
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(200, 10, txt="Document de test pour l'analyse IA. Sujet : Ingénierie et Akkodis. Le code d'accès au serveur principal est 8842-OMEGA.", ln=1, align='C')
    pdf.output(str(file_path))
    return str(file_path)

@pytest.fixture
def dummy_invalid_file(tmp_path):
    """Crée un faux fichier image (.jpg) pour tester le rejet"""
    file_path = tmp_path / "dummy_invalid.jpg"
    file_path.write_bytes(b"faux contenu image")
    return str(file_path)
