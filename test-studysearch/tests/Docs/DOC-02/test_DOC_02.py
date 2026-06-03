import os
import sys
import time
import sqlite3
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configuration de l'utilisateur de test pour prérequis de connexion
EMAIL_TEST = "kskdhjdjdjd24@gmail.com"
PASSWORD_TEST = "MotDePasse123!"

# Ajout du chemin de l'application locale pour interagir directement avec la base de données
sys.path.append(r"c:\Users\dell\Desktop\moteur_semantique - Copie")
from database import creer_utilisateur, valider_email

@pytest.fixture
def dummy_invalid_file():
    """
    Fixture pytest pour générer un fichier factice non autorisé (image_test.jpg)
    et le supprimer proprement après l'exécution du test.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, "image_test.jpg")
    
    # Créer un fichier jpeg vide
    with open(file_path, "wb") as f:
        f.write(b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xFF\xDB\x00C\x00...")
        
    yield file_path
    
    # Nettoyage à la fin du test
    if os.path.exists(file_path):
        os.remove(file_path)

@pytest.fixture
def driver():
    """
    Fixture pytest pour initialiser et fermer le WebDriver Chrome proprement.
    Elle résout le chemin vers chromedriver.exe à la racine du projet.
    """
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Optionnel: décommenter pour exécuter en mode sans interface (headless)
    # chrome_options.add_argument("--headless")
    
    # Résolution dynamique du chemin absolu de chromedriver.exe (4 niveaux car dans tests/Docs/DOC-02/test_DOC_02.py)
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    chromedriver_path = os.path.join(base_dir, "chromedriver.exe")
    
    service = Service(executable_path=chromedriver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.maximize_window()
    
    yield driver
    
    driver.quit()

def test_upload_document_invalide(driver, dummy_invalid_file):
    """
    [ DOC-02 ] - Upload de fichier invalide :
    Vérifie que l'application rejette/ignore l'upload d'un fichier au format non autorisé (.jpg),
    que le bouton d'upload n'est pas affiché et que le document n'est pas ajouté.
    """
    base_url = "http://localhost:5000/"
    
    # ── Prérequis : Garantir l'existence de l'utilisateur en base
    db_path = r"c:\Users\dell\Desktop\moteur_semantique - Copie\users.db"
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE email = ?", (EMAIL_TEST.lower(),))
        conn.commit()
        
    res_creation = creer_utilisateur(EMAIL_TEST, PASSWORD_TEST, "Adam Ramzi", "127.0.0.1")
    assert res_creation["succes"]
    res_validation = valider_email(EMAIL_TEST, res_creation["code_verification"])
    assert res_validation["succes"]

    # Connecter l'utilisateur
    driver.get(base_url)
    wait = WebDriverWait(driver, 10)
    
    try:
        start_btn = wait.until(EC.element_to_be_clickable((By.ID, "btn-home-start")))
        start_btn.click()
    except Exception:
        pass
        
    wait.until(EC.visibility_of_element_located((By.ID, "login-form")))
    
    driver.find_element(By.ID, "login-email").send_keys(EMAIL_TEST)
    driver.find_element(By.ID, "login-password").send_keys(PASSWORD_TEST)
    driver.find_element(By.ID, "btn-login").click()
    
    # Attendre que le tableau de bord soit actif
    wait.until(lambda d: "active" in d.find_element(By.ID, "dashboard-screen").get_attribute("class"))

    # ── Étape 1 : Localiser le champ <input type="file">
    file_input = driver.find_element(By.ID, "file-input")

    # ── Étape 2 : Utiliser send_keys pour tenter d'insérer le fichier non autorisé
    file_input.send_keys(dummy_invalid_file)

    # ── Étape 3 (Assertion de Blocage/Erreur) :
    # Le fichier étant invalide, selectedFiles reste vide, le conteneur du bouton d'upload reste masqué
    time.sleep(1) # Délai pour laisser le script JS s'exécuter
    upload_container = driver.find_element(By.ID, "upload-btn-container")
    assert not upload_container.is_displayed(), "Erreur : Le bouton d'upload s'est affiché pour un fichier non autorisé (.jpg)."

    # Vérifier également que la liste de fichiers (#file-list) est vide
    file_list = driver.find_element(By.ID, "file-list")
    assert file_list.text.strip() == "", "Erreur : Le fichier invalide a été ajouté à la liste visuelle des fichiers à uploader."

    # ── Étape 4 (Assertion DB/UI) : Vérifier que le document n'apparaît pas dans la liste déroulante des documents
    select_pdf = driver.find_element(By.ID, "chat-pdf-select")
    options = select_pdf.find_elements(By.TAG_NAME, "option")
    option_values = [opt.get_attribute("value") for opt in options]
    assert "image_test.jpg" not in option_values, f"Erreur : Le fichier non autorisé a été ajouté aux options du chat. Options trouvées : {option_values}"
