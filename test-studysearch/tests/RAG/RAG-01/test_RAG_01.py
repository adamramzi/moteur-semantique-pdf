import os
import sys
import time
import sqlite3
import pytest
from selenium import webdriver
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
def driver():
    """
    Fixture pytest pour initialiser et fermer le WebDriver Chrome proprement.
    Elle utilise Selenium Manager pour configurer ChromeDriver en mode headless.
    """
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--headless")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.maximize_window()
    
    yield driver
    
    driver.quit()

def test_reponse_bassee_sur_document(driver, dummy_pdf):
    """
    [ RAG-01 ] - Réponse basée sur le document :
    Vérifie que l'assistant IA RAG de StudySearch extrait et restitue correctement
    une information spécifique contenue dans un document PDF importé par l'utilisateur.
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

    # Uploader le document fact_test.pdf
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
    
    # Vérifier que fact_test.pdf est bien sélectionné par défaut
    assert select_pdf.get_attribute("value") == "fact_test.pdf", "Erreur : Le document fact_test.pdf n'est pas sélectionné par défaut."

    # ── Étape 1 : Saisir la question dans la zone de chat
    chat_input = wait.until(EC.visibility_of_element_located((By.ID, "chat-input")))
    chat_input.clear()
    chat_input.send_keys("Quel est le code d'accès au serveur principal ?")

    # ── Étape 2 : Cliquer sur le bouton d'envoi
    btn_send = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "btn-send-gemini")))
    btn_send.click()

    # ── Étape 3 : Attendre la disparition du loader/typing-indicator (avec un délai maximum de 30 secondes pour l'IA)
    # L'indicateur de chargement a pour classe `.typing-indicator`
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CLASS_NAME, "typing-indicator"))
    )
    WebDriverWait(driver, 30).until_not(
        EC.presence_of_element_located((By.CLASS_NAME, "typing-indicator"))
    )

    # ── Étape 4 (Assertion de l'IA) : Extraire la dernière réponse de l'IA
    # Les réponses de l'IA ont la classe `.msg-bot` dans le DOM
    bot_messages = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "msg-bot")))
    last_bot_msg = bot_messages[-1]
    
    # Vérifier que le secret "8842-OMEGA" est bien présent dans la réponse
    response_text = last_bot_msg.text
    print(f"Réponse retournée par l'IA : '{response_text}'")
    assert "8842-OMEGA" in response_text, f"Erreur : L'IA n'a pas inclus le code secret '8842-OMEGA' dans sa réponse. Reçu : '{response_text}'"
