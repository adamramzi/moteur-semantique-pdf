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

def test_prevention_doublons(driver, dummy_pdf):
    """
    [ DOC-03 ] - Prévention des doublons :
    Vérifie qu'un utilisateur ne peut pas importer deux fois exactement le même document.
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

    # ── Étape 1 : Premier upload
    file_input = driver.find_element(By.ID, "file-input")
    file_input.send_keys(dummy_pdf)

    # Nettoyer le conteneur de toast pour éviter que le toast "Connexion réussie !" ne fausse les assertions d'upload
    driver.execute_script("document.getElementById('toast-container').innerHTML = '';")

    # Lancer l'upload
    btn_upload = wait.until(EC.element_to_be_clickable((By.ID, "btn-upload")))
    btn_upload.click()

    # Attendre la fin de l'upload et s'assurer que le fichier est indexé
    wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "toast-success")))
    select_pdf = wait.until(EC.presence_of_element_located((By.ID, "chat-pdf-select")))
    wait.until(lambda d: d.find_element(By.ID, "chat-pdf-select").is_enabled())

    # ── Étape 2 : Tentative de doublon (réinjecter le même fichier)
    # Nettoyer les toasts pour isoler la nouvelle erreur
    driver.execute_script("document.getElementById('toast-container').innerHTML = '';")
    
    # On renvoie le même fichier
    file_input = driver.find_element(By.ID, "file-input")
    file_input.send_keys(dummy_pdf)

    # ── Étape 3 (Assertion d'Erreur) : Attendre le toast d'erreur de doublon
    toast_error = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "toast-error")))
    assert toast_error.is_displayed(), "Erreur : Le toast d'erreur de doublon n'est pas affiché."
    assert "déjà" in toast_error.text.lower() or "existe" in toast_error.text.lower(), \
        f"Erreur : Le texte du toast d'erreur doublon est incorrect : '{toast_error.text}'"

    # ── Étape 4 (Assertion d'Intégrité) : Vérifier qu'il n'y a qu'une seule occurrence de doublon_test.pdf dans la liste déroulante
    options = select_pdf.find_elements(By.TAG_NAME, "option")
    occurrences = [opt.get_attribute("value") for opt in options if opt.get_attribute("value") == "doublon_test.pdf"]
    assert len(occurrences) == 1, f"Erreur : Le fichier doublon_test.pdf apparaît plusieurs fois ({len(occurrences)}) dans les options de recherche."
