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
    chrome_options.add_argument("--headless")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.maximize_window()
    
    yield driver
    
    driver.quit()

def test_changement_de_mode(driver):
    """
    [ CHAT-02 ] - Changement de mode :
    Vérifie que l'utilisateur peut changer le mode de chat (de Mode Résumé à Mode Recherche)
    et que le bouton de sélection reflète cette mise à jour.
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

    # ── Étape 1 : Localiser le bouton de sélection de mode (Mode Résumé par défaut)
    btn_selector = wait.until(EC.element_to_be_clickable((By.ID, "btn-model-selector")))
    assert "Mode Résumé" in btn_selector.text, f"Erreur : Le mode initial est incorrect. Reçu : '{btn_selector.text}'"

    # Cliquer pour ouvrir la liste des options
    btn_selector.click()

    # ── Étape 2 : Cliquer sur l'option "Mode Recherche"
    option_recherche = wait.until(EC.element_to_be_clickable((
        By.XPATH, "//div[@id='model-menu']//div[contains(., 'Mode Recherche')]"
    )))
    option_recherche.click()

    # ── Étape 3 (Assertion du texte) : Vérifier la mise à jour du texte du bouton
    wait.until(lambda d: "Mode Recherche" in d.find_element(By.ID, "btn-model-selector").text)
    assert "Mode Recherche" in btn_selector.text, f"Erreur : Le texte du bouton n'a pas été mis à jour après la sélection. Reçu : '{btn_selector.text}'"

    # ── Étape 4 (Assertion UI) : Vérifier que le menu d'options s'est fermé
    menu = driver.find_element(By.ID, "model-menu")
    assert "hidden" in menu.get_attribute("class"), "Erreur : Le menu de sélection de mode n'a pas été masqué après le clic."
