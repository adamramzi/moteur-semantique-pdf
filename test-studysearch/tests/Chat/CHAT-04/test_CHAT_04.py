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

def test_generation_titre_auto(driver):
    """
    [ CHAT-04 ] - Génération du titre auto :
    Vérifie qu'après l'envoi d'un premier message dans une nouvelle discussion,
    le titre de la conversation dans la sidebar est mis à jour de façon contextuelle
    au lieu de garder un titre générique par défaut.
    """
    base_url = "http://localhost:5000/"
    
    # ── Prérequis : Garantir l'existence de l'utilisateur en base et nettoyer ses anciennes conversations
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

    # Vider le localStorage pour démarrer dans un état propre sans anciennes conversations
    driver.execute_script("""
        localStorage.removeItem('conversations');
        localStorage.removeItem('studysearch_convos');
        conversations = [];
        renderConversations();
    """)

    # ── Prérequis : Cliquer sur le bouton "Nouvelle discussion"
    btn_new = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Nouvelle discussion')]")))
    btn_new.click()

    # Simuler la présence d'un document actif (pour contourner le blocage sans document)
    driver.execute_script("""
        pdfActif = 'dummy_document.pdf';
        const select = document.getElementById('chat-pdf-select');
        select.innerHTML = '<option value="dummy_document.pdf">dummy_document.pdf</option>';
        select.value = 'dummy_document.pdf';
        select.disabled = false;
    """)

    # ── Étape 1 : Saisir et envoyer un premier message
    chat_input = wait.until(EC.visibility_of_element_located((By.ID, "chat-input")))
    chat_input.clear()
    chat_input.send_keys("Peux-tu me résumer le chapitre 1 ?")
    
    btn_send = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "btn-send-gemini")))
    btn_send.click()

    # ── Étape 2 : Noter le titre initial temporaire (de type "Conversation X")
    # Dès que le message est envoyé, la conversation est enregistrée localement avec son nom par défaut
    convo_header = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#history-content h4")))
    initial_title = convo_header.text
    assert "Conversation" in initial_title, f"Erreur : Le titre par défaut n'est pas présent dans la sidebar. Reçu : '{initial_title}'"

    # ── Étape 3 (Assertion de mise à jour) : Attendre la génération automatique du titre contextuel
    # On attend que le titre ne contienne plus le mot "Conversation"
    wait.until(lambda d: "Conversation" not in d.find_element(By.CSS_SELECTOR, "#history-content h4").text)
    
    # Récupérer l'élément à nouveau pour éviter StaleElementReferenceException
    updated_title = driver.find_element(By.CSS_SELECTOR, "#history-content h4").text
    print(f"Titre après génération automatique : '{updated_title}'")
    
    # Vérifier que le titre a bien changé et n'est plus le titre par défaut "Conversation 1"
    assert updated_title != initial_title, f"Erreur : Le titre n'a pas été modifié. Titre actuel : '{updated_title}'"
    assert "Conversation" not in updated_title, f"Erreur : Le titre mis à jour contient toujours 'Conversation' : '{updated_title}'"
    assert len(updated_title.strip()) > 2, f"Erreur : Le titre généré est vide ou trop court. Reçu : '{updated_title}'"

