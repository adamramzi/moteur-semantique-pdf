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
    
    # Résolution dynamique du chemin absolu de chromedriver.exe (4 niveaux car dans tests/Chat/CHAT-03/test_CHAT_03.py)
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    chromedriver_path = os.path.join(base_dir, "chromedriver.exe")
    
    service = Service(executable_path=chromedriver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.maximize_window()
    
    yield driver
    
    driver.quit()

def test_envoi_message_typing(driver):
    """
    [ CHAT-03 ] - Envoi de message (Typing) :
    Vérifie qu'après l'envoi d'un message, le champ de saisie se vide instantanément,
    la bulle de message de l'utilisateur s'affiche dans la zone de chat et l'indicateur
    de chargement (typing indicator) apparaît temporairement à l'écran.
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

    # ── Prérequis : Simuler la présence d'un document en injectant une valeur valide dans le DOM (évite le blocage du test CHAT-01)
    driver.execute_script("""
        pdfActif = 'dummy_document.pdf';
        const select = document.getElementById('chat-pdf-select');
        select.innerHTML = '<option value="dummy_document.pdf">dummy_document.pdf</option>';
        select.value = 'dummy_document.pdf';
        select.disabled = false;
    """)

    # ── Étape 1 : Saisir une question dans le champ de texte du chat
    chat_input = wait.until(EC.visibility_of_element_located((By.ID, "chat-input")))
    chat_input.clear()
    chat_input.send_keys("Quelle est la définition d'un test E2E ?")

    # ── Étape 2 : Cliquer sur le bouton d'envoi
    btn_send = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "btn-send-gemini")))
    btn_send.click()

    # ── Étape 3 (Assertion Input) : Vérifier que le champ de saisie se vide instantanément
    assert chat_input.get_attribute("value") == "", "Erreur : Le champ de saisie ne s'est pas vidé après l'envoi."

    # ── Étape 4 (Assertion Bulle) : Vérifier qu'une bulle de message appartenant à l'utilisateur (.msg-user) apparaît dans le chat
    user_message = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "msg-user")))
    assert user_message.is_displayed(), "Erreur : Le message de l'utilisateur n'est pas affiché dans la zone de chat."
    assert "définition d'un test E2E" in user_message.text, f"Erreur : Le texte de la bulle utilisateur est incorrect : '{user_message.text}'"

    # ── Étape 5 (Assertion Loader) : Vérifier la présence de l'indicateur de chargement (.typing-indicator)
    # WebDriverWait est configuré avec un délai court car le loader est éphémère (remplacé par la réponse IA ou erreur serveur)
    loader = WebDriverWait(driver, 3).until(
        EC.presence_of_element_located((By.CLASS_NAME, "typing-indicator"))
    )
    assert loader.is_displayed(), "Erreur : L'indicateur de chargement (typing-indicator) n'est pas visible."
