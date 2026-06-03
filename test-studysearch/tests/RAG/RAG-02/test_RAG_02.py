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
from fpdf import FPDF

# Configuration de l'utilisateur de test pour prérequis de connexion
EMAIL_TEST = "kskdhjdjdjd24@gmail.com"
PASSWORD_TEST = "MotDePasse123!"

# Ajout du chemin de l'application locale pour interagir directement avec la base de données
sys.path.append(r"c:\Users\dell\Desktop\moteur_semantique - Copie")
from database import creer_utilisateur, valider_email

@pytest.fixture
def dummy_pdf():
    """
    Fixture pytest pour générer dynamiquement un petit fichier PDF factice (computer_science.pdf)
    contenant uniquement des données informatiques, et le supprimer proprement à la fin du test.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(current_dir, "computer_science.pdf")
    
    # Génération du PDF avec fpdf2
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(200, 10, text="L'informatique est la science du traitement automatique de l'information par des ordinateurs.")
    pdf.output(pdf_path)
    
    yield pdf_path
    
    # Nettoyage à la fin du test
    if os.path.exists(pdf_path):
        os.remove(pdf_path)

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
    
    # Résolution dynamique du chemin absolu de chromedriver.exe (4 niveaux car dans tests/RAG/RAG-02/test_RAG_02.py)
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    chromedriver_path = os.path.join(base_dir, "chromedriver.exe")
    
    service = Service(executable_path=chromedriver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.maximize_window()
    
    yield driver
    
    driver.quit()

def test_question_hors_contexte(driver, dummy_pdf):
    """
    [ RAG-02 ] - Question hors contexte :
    Vérifie que l'assistant IA refuse de répondre s'il est interrogé sur un sujet
    totalement absent du document importé, évitant ainsi d'halluciner des réponses hors contexte.
    """
    base_url = "http://localhost:5000/"
    
    # ── Prérequis : Garantir l'existence de l'utilisateur en base et nettoyer ses anciens documents
    db_path = r"c:\Users\dell\Desktop\moteur_semantique - Copie\users.db"
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM documents WHERE user_id = (SELECT id FROM users WHERE email = ?)", (EMAIL_TEST.lower(),))
        cursor.execute("DELETE FROM user_indices WHERE user_id = (SELECT id FROM users WHERE email = ?)", (EMAIL_TEST.lower(),))
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

    # Uploader le document computer_science.pdf
    file_input = driver.find_element(By.ID, "file-input")
    file_input.send_keys(dummy_pdf)

    # Nettoyer les toasts de connexion
    driver.execute_script("document.getElementById('toast-container').innerHTML = '';")

    # Analyser et enregistrer le document
    wait.until(EC.visibility_of_element_located((By.ID, "upload-btn-container")))
    btn_upload = wait.until(EC.element_to_be_clickable((By.ID, "btn-upload")))
    btn_upload.click()

    # Attendre la fin du traitement (dropdown actif et toast succès)
    wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "toast-success")))
    select_pdf = wait.until(EC.presence_of_element_located((By.ID, "chat-pdf-select")))
    wait.until(lambda d: d.find_element(By.ID, "chat-pdf-select").is_enabled())

    # ── Étape 1 : Saisir la question hors sujet dans le chat
    chat_input = wait.until(EC.visibility_of_element_located((By.ID, "chat-input")))
    chat_input.clear()
    chat_input.send_keys("Quelle est la recette de la tarte aux pommes ?")

    # ── Étape 2 : Cliquer sur le bouton d'envoi
    btn_send = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "btn-send-gemini")))
    btn_send.click()

    # ── Étape 3 : Attendre la fin de la génération de la réponse (disparition de .typing-indicator)
    # WebDriverWait est configuré avec un délai de 30 secondes pour le traitement du modèle RAG
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CLASS_NAME, "typing-indicator"))
    )
    WebDriverWait(driver, 30).until_not(
        EC.presence_of_element_located((By.CLASS_NAME, "typing-indicator"))
    )

    # ── Étape 4 (Assertion d'anti-hallucination) : Extraire la dernière réponse de l'IA
    bot_messages = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "msg-bot")))
    last_bot_msg = bot_messages[-1]
    
    response_text = last_bot_msg.text
    print(f"Réponse IA hors contexte : '{response_text}'")
    
    # Validation du refus d'halluciner :
    # La réponse ne doit pas contenir d'informations sur la recette de tarte ("pommes")
    assert "pommes" not in response_text.lower(), "Erreur : L'IA a halluciné une réponse concernant les pommes."
    
    # La réponse doit correspondre au message de fallback ou contenir des mots-clés de restriction (contexte, document, désolé)
    assert "désolé" in response_text.lower() or "trouve pas" in response_text.lower() or "document" in response_text.lower(), \
        f"Erreur : La réponse de l'IA ne mentionne pas la restriction ou l'absence d'information dans le document : '{response_text}'"
