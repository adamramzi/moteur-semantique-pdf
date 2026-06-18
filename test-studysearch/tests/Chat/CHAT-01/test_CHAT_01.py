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
    # chrome_options.add_argument("--headless")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.maximize_window()
    
    yield driver
    
    driver.quit()

def test_blocage_sans_document(driver):
    """
    [ CHAT-01 ] - Blocage sans document :
    Vérifie que l'utilisateur est bloqué avec un toast d'erreur s'il tente d'envoyer
    un message dans le chat sans avoir sélectionné de document.
    """
    base_url = "http://localhost:5000/"
    
    # ── Prérequis : Garantir l'existence de l'utilisateur en base et l'absence de documents
    db_path = r"c:\Users\dell\Desktop\moteur_semantique - Copie\users.db"
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        # Supprimer d'éventuels documents résiduels pour cet e-mail de test
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

    # S'assurer qu'aucun document n'est sélectionné par défaut
    select_element = driver.find_element(By.ID, "chat-pdf-select")
    assert select_element.get_attribute("disabled") == "true" or select_element.get_attribute("value") == "", \
        "Erreur : Un document semble sélectionné par défaut alors qu'aucun n'a été téléversé."

    # ── Étape 1 : Saisir une question de test dans la barre de chat
    chat_input = wait.until(EC.visibility_of_element_located((By.ID, "chat-input")))
    chat_input.clear()
    chat_input.send_keys("Est-ce que ça fonctionne sans document ?")

    # ── Étape 2 : Cliquer sur le bouton d'envoi
    btn_send = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "btn-send-gemini")))
    btn_send.click()

    # ── Étape 3 (Assertion d'échec) : Vérifier que le message n'apparaît pas dans la zone de chat
    time.sleep(1) # Petit délai de sécurité pour s'assurer qu'aucune bulle ne s'affiche
    user_messages = driver.find_elements(By.CLASS_NAME, "msg-user")
    assert len(user_messages) == 0, "Erreur : Le message a été ajouté à la zone de chat alors qu'aucun document n'est ciblé."

    # ── Étape 4 (Assertion UI) : Vérifier l'apparition du toast d'erreur
    toast_error = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "toast-error")))
    assert toast_error.is_displayed(), "Erreur : Le toast d'erreur n'est pas affiché."
    assert "cibler un document" in toast_error.text.lower() or "sélectionner un document" in toast_error.text.lower(), \
        f"Erreur : Le texte du toast d'erreur est inattendu : '{toast_error.text}'"
